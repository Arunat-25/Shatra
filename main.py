# main.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uuid

from oop_style.models import MoveData, MoveResult
from oop_style.game_logic import GameLogic

app = FastAPI()

# Разрешаем CORS для локальной разработки
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Хранилище активных игр: room_id -> {logic, board, mover, players}
games: dict[str, dict] = {}

def board_to_json(board_dict: dict) -> dict:
    """Конвертирует ключи доски в строки для JS"""
    return {str(k): v for k, v in board_dict.items()}


def boards_keys_to_int(board: dict) -> dict:
    """Конвертирует ключи доски из строк в int (JS → Python)"""
    return {int(k) if isinstance(k, str) else k: v for k, v in board.items()}


def change(position: str | int) -> int:
    """Конвертирует 'position39' или 'position0' -> 39 или 0"""
    if isinstance(position, int):
        return position
    
    if isinstance(position, str):
        # Убираем префикс "position" и конвертируем
        return int(position.replace("position", ""))
    
    return int(position)


def get_starting_board():
    board = {i: None for i in range(1, 63)}
    
    # ⚫ ЧЕРНЫЕ (сверху/слева)
    for i in range(1, 10): board[i] = "черная шатра"
    board[10] = "черный бий"
    for i in range(11, 25): board[i] = "черная шатра"
    board[25] = "черный батыр" # Резерв или на доске, зависит от правил
    
    # ⚪ БЕЛЫЕ (снизу/справа)
    for i in range(39, 53): board[i] = "белая шатра"
    board[53] = "белый бий"
    for i in range(54, 63): board[i] = "белая шатра"
    board[38] = "белый батыр" # Резерв
    
    # Центральная зона (26-37) обычно пустая или заполнена специфично
    # Оставляем None
    
    return board


class ConnectionManager:
    """Управление WebSocket подключениями"""
    def __init__(self):
        self.rooms: dict[str, list[WebSocket]] = {}

    """Управление WebSocket подключениями"""
    def __init__(self):
        self.rooms: dict[str, list[WebSocket]] = {}

    async def connect(self, room_id: str, websocket: WebSocket) -> bool:
        if room_id not in self.rooms:
            self.rooms[room_id] = []
            
            # 🟢 ИСПОЛЬЗУЕМ НАЧАЛЬНУЮ РАССТАНОВКУ ВМЕСТО ПУСТОЙ
            start_board = get_starting_board()
            
            games[room_id] = {
                "logic": GameLogic(),
                "board": start_board,  # <--- ВОТ ЗДЕСЬ БЫЛА ОШИБКА (было None)
                "mover": "белый",
                "players": {}
            }
        
        if len(self.rooms[room_id]) < 2:
            await websocket.accept()
            self.rooms[room_id].append(websocket)
            return True
        return False

    async def disconnect(self, room_id: str, websocket: WebSocket):
        if room_id in self.rooms and websocket in self.rooms[room_id]:
            self.rooms[room_id].remove(websocket)
            if not self.rooms[room_id]:
                self.rooms.pop(room_id, None)
                games.pop(room_id, None)

    async def send_to_room(self, room_id: str, data: dict):
        for ws in self.rooms.get(room_id, []):
            await ws.send_json(data)


manager = ConnectionManager()


@app.get("/")
async def get_room_link():
    """Генерирует уникальную ссылку на комнату"""
    room_id = uuid.uuid4().hex[:8]
    return {"room_link": f"ws://localhost:8000/ws/{room_id}/"}


@app.websocket("/ws/{room_id}/")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    # 1. Подключение
    if not await manager.connect(room_id, websocket):
        await websocket.close(code=1008)
        return

    game = games[room_id]
    
    # 2. Назначаем цвет игроку
    player_index = len(game["players"])
    my_color = "белый" if player_index == 0 else "черный"
    game["players"][websocket] = my_color

    # 3. Отправляем начальные данные
    await websocket.send_json({
        "players_color": my_color,
        "movers_color": game["mover"],
        "desk": game["board"]
    })

    try:
        while True:
            data = await websocket.receive_json()
            print(f"📤 Получено от клиента: {data.get('move_from')} -> {data.get('move_to')}")
            
            # ── Запрос подсказок (подсветка ходов) ─────────────────────
            if "position" in data and "move_from" not in data:
                pos = change(data["position"])
                # Просто делегируем в GameLogic
                hints = game["logic"].get_hints(
                    game["board"], 
                    game["mover"], 
                    pos,
                    data.get("position_for_mandatory_capture")
                )
                await manager.send_to_room(room_id, hints)
                continue

            # ── Обработка хода ─────────────────────────────────────────
            move_data = MoveData(
                positions=boards_keys_to_int(data["board"]),
                mover_color=data["movers_color"],
                from_pos=change(data["move_from"]),
                to_pos=change(data["move_to"]),
                position_for_mandatory_capture=data.get("position_for_mandatory_capture")
            )
            
            # ★★ Вся логика игры происходит здесь ★★
            result: MoveResult = game["logic"].process_move(move_data)
            
            # Обновляем состояние в хранилище
            if result.updated_positions:
                game["board"] = result.updated_positions
            if result.movers_color:
                game["mover"] = result.movers_color
            
            print(f"✅ Обновлённая доска: {len(game['board'])} клеток")

            # Формируем ответ для фронтенда (совместимый формат)
            response = {
                "message": result.message,
                "movers_color": result.movers_color,
                "desk": board_to_json(game["board"]),
                "game_over": result.game_over,
                "winner": result.winner,
                "position_for_mandatory_capture": None,
                "opportunity_pass_the_move": result.opportunity_pass_the_move,
                "essential_positions": [],
                "captured_pieces": result.captured_positions
            }
            
            # Если нужно продолжить взятие — сервер говорит, какую фигуру двигать
            if not result.game_over and result.movers_color:
                # Проверяем, есть ли обязательные взятия с новой позиции
                if game["logic"]._has_mandatory_from_position(game["board"], result.movers_color, move_data.to_pos):
                    response["position_for_mandatory_capture"] = move_data.to_pos
            
            await manager.send_to_room(room_id, response)
            
    except WebSocketDisconnect:
        await manager.disconnect(room_id, websocket)