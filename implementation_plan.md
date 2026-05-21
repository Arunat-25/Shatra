# Implementation Plan

[Overview]

Добавить бэкенд-логику лобби (комнаты ожидания) и обновить фронтенд для новой механики игры.

В текущей системе при GET / создаётся комната и сразу возвращается ws-ссылка. Нужно переделать на полноценное лобби: REST API для управления комнатами (создание, список, присоединение, быстрый старт), модифицировать WebSocket чтобы первый игрок ждал второго в комнате (показывая ссылку приглашения), и только когда оба подключены — начинать игру. Хранение комнат — в памяти (словарь). Игроки без аутентификации.

[Types]

Типы данных для хранения комнат и ответов API:

```python
from typing import Literal, Optional
from pydantic import BaseModel
from datetime import datetime

# Тип комнаты
RoomType = Literal["quick", "friend"]

# Состояние комнаты
class Room(BaseModel):
    room_id: str           # uuid
    type: RoomType
    creator_color: str = "белый"  # кто создал
    created_at: datetime
    player1_connected: bool = False  # создатель подключился
    player2_connected: bool = False  # второй игрок подключился
    player1_ws: Optional[WebSocket] = None
    player2_ws: Optional[WebSocket] = None
    game_started: bool = False

# Тело запроса на создание комнаты
class CreateRoomRequest(BaseModel):
    type: RoomType = "quick"

# Ответ на создание комнаты  
class CreateRoomResponse(BaseModel):
    room_id: str
    link: str       # ссылка на Board.html?room=XXX
    type: RoomType

# Информация о комнате для списка
class RoomInfo(BaseModel):
    room_id: str
    type: RoomType
    created_at: datetime

# Ответ со списком комнат
class RoomListResponse(BaseModel):
    rooms: list[RoomInfo]

# Ответ быстрого старта
class QuickStartResponse(BaseModel):
    room_id: str
    link: str
```

Локальный словарь для хранения:
```python
rooms: dict[str, Room] = {}
```

[Files]

Все изменения затрагивают только backend (main.py) и frontend (HTML/JS/CSS).

- **MODIFY** `main.py` — добавить:
  1. Словарь `rooms` для хранения комнат ожидания
  2. REST endpoints: `POST /rooms`, `GET /rooms`, `POST /rooms/{id}/join`, `GET /rooms/quick-start`
  3. Изменить `ConnectionManager.connect()` — разделить на первый и второй вход
  4. Изменить логику WebSocket: первый игрок получает `{"status": "waiting", "link": "..."}`, второй — инициализация игры
  5. При подключении второго игрока — обоим отправляется стартовая доска
  
- **MODIFY** `Frontend/page_where_create_room.html` — переделать в лобби с 4 кнопками:
  - "Создать игру" (type=quick)
  - "Вызов другу" (type=friend)
  - "Быстрый старт"
  - "Зал ожидания" (открывает модальное окно)

- **MODIFY** `Frontend/page_where_create_room.js` — логика кнопок лобби:
  - fetch к REST endpoints
  - редирект на Board.html?room=XXX
  - модальное окно с залом ожидания (GET /rooms, список, кнопка "Присоединиться")

- **MODIFY** `Frontend/Board.html` — добавить экран "ожидания" (скрытый блок с ссылкой):
  - Блок `.waiting-screen` (показывается пока второй игрок не подключился)
  - Блок `.game-screen` (доска, хедер, сообщения — как сейчас)
  - Скрыть `.game-screen` изначально, показывать `.waiting-screen`

- **MODIFY** `Frontend/script.js` — добавить логику ожидания:
  - При получении статуса "waiting" от WebSocket — скрыть доску, показать ожидание
  - При получении инициализации игры (players_color) — скрыть ожидание, показать доску
  - Отображать ссылку на странице ожидания

- **MODIFY** `Frontend/style.css` — стили для:
  - Модального окна зала ожидания (background, позиционирование, анимация)
  - Экрана ожидания (waiting-screen)
  - Кнопок лобби и комнат в списке

[Functions]

### Backend (main.py)

**New functions:**
- `create_room_endpoint(request: CreateRoomRequest) -> dict` — POST /rooms, создаёт комнату, возвращает room_id и ссылку
- `list_rooms_endpoint() -> dict` — GET /rooms, возвращает список комнат где нет второго игрока
- `join_room_endpoint(room_id: str) -> dict` — POST /rooms/{id}/join, присоединяет к комнате, возвращает ссылку. Если комната не существует — 404
- `quick_start_endpoint() -> dict` — GET /rooms/quick-start, ищет первую "quick" комнату без второго игрока, присоединяет. Если нет свободных — 404
- `get_room_for_quick_start() -> str | None` — вспомогательная: найти первую подходящую комнату

**Modified functions:**
- `get_room_link()` → заменить на редирект или просто удалить (раньше был GET /, но теперь не нужен)
- `ConnectionManager.connect()` — модифицировать: если в комнате ещё нет первого игрока, присвоить первому, отправить `{"status": "waiting"}`. Если первый уже есть, присвоить второму, отправить обоим инициализацию
- `websocket_endpoint()` — модифицировать для работы с обновлённым ConnectionManager

### Frontend (JS)

**New functions in `page_where_create_room.js`:**
- `createGame()` — POST /rooms {type: "quick"} → редирект на Board.html?room=XXX
- `challengeFriend()` — POST /rooms {type: "friend"} → редирект на Board.html?room=XXX
- `quickStart()` — GET /rooms/quick-start → редирект. Если 404 — показать ошибку
- `openLobby()` — открыть модальное окно
- `closeLobby()` — закрыть модальное окно
- `fetchRooms()` — GET /rooms → отобразить список в модальном окне
- `joinRoom(roomId)` — POST /rooms/{id}/join → редирект на Board.html?room=XXX
- `navigateToGame(roomId)` — перенаправление на Board.html?room=XXX

**Modified functions in `script.js`:**
- `connectToGame()` — при подключении ждать статус от сервера
- `handleServerMessage()` — добавить обработку `{"status": "waiting", "link": "..."}` — показать экран ожидания
- `showWaitingScreen(link)` — показать блок ожидания со ссылкой
- `hideWaitingScreen()` — скрыть блок ожидания

[Classes]

- **MODIFY** `ConnectionManager` (main.py, 65-98):
  - Добавить поле `rooms: dict[str, Room]` (или использовать существующий)
  - Изменить `connect()`: принимать параметр `is_creator: bool` или определять по наличию первого игрока
  - Добавить методы:
    - `is_room_full(room_id) -> bool`
    - `get_room_status(room_id) -> str` ("waiting" / "ready")
    - `get_waiting_rooms() -> list`

[Дубликат функции] `get_starting_board()` и `board_to_json()`, `boards_keys_to_int()`, `change_position_name_from_frontend()` — остаются без изменений.

[Dependencies]

Без изменений. В requirements.txt уже есть FastAPI, Uvicorn, Pydantic. Ничего нового не требуется.

[Testing]

Тестировать вручную через браузер.
- Открыть главную страницу, нажать "Создать игру" — должен перенаправить на Board.html?room=XXX, показать экран ожидания со ссылкой
- Открыть Board.html?room=XXX в другом окне — должна появиться доска в обоих окнах
- "Вызов другу" — аналогично, но с флагом friend
- "Быстрый старт" — если есть свободная комната, присоединиться
- "Зал ожидания" — открыть модалку, увидеть список, нажать "Присоединиться"

[Implementation Order]

Последовательность изменений, минимизирующая конфликты:

1. Создать структуру данных комнат и импорты в начале main.py (после существующих импортов) — модели Room, CreateRoomRequest и т.д.
2. Добавить словарь rooms и REST endpoints в main.py (POST /rooms, GET /rooms, POST /rooms/{id}/join, GET /rooms/quick-start) 
3. Модифицировать ConnectionManager и websocket_endpoint для поддержки ожидания второго игрока
4. Обновить Frontend/page_where_create_room.html — лобби с 4 кнопками
5. Обновить Frontend/page_where_create_room.js — логика кнопок
6. Обновить Frontend/Board.html — добавить блок ожидания
7. Обновить Frontend/script.js — логика ожидания и старта игры
8. Обновить Frontend/style.css — стили для модалки и экрана ожидания