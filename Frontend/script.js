// Frontend/script.js
let BoardLikeDict = {};
let my_color = null;
let movers_color = null;
let position_for_mandatory_capture = null;
let move_from = null;
let ws = null;

document.addEventListener('DOMContentLoaded', async () => {
    await connectToGame();
    setupEventListeners();
});

async function connectToGame() {
    // 1. Проверяем, есть ли комната в URL (например, ?room=abc123)
    const urlParams = new URLSearchParams(window.location.search);
    const roomParam = urlParams.get('room');

    let wsUrl;
    if (roomParam) {
        // Если открыли по ссылке с ?room=... → подключаемся к ней
        wsUrl = `ws://localhost:8000/ws/${roomParam}/`;
    } else {
        // 2. Если URL чистый → запрашиваем новую комнату у бэкенда
        try {
            const res = await fetch("http://localhost:8000/");
            const data = await res.json();
            wsUrl = data.room_link;
            
            // Добавляем ID комнаты в адресную строку, чтобы можно было скопировать
            const roomId = wsUrl.split('/ws/')[1].split('/')[0];
            window.history.replaceState(null, '', `?room=${roomId}`);
        } catch (e) {
            showMessage("Сервер недоступен (проверь порт 8000)", "ошибка");
            console.error(e);
            return;
        }
    }

    console.log("🔗 Подключаемся к:", wsUrl);
    ws = new WebSocket(wsUrl);
    setupWebSocketHandlers();

    // Показываем ссылку на странице для второго игрока
    const infoEl = document.getElementById("room_info");
    if (infoEl) {
        const roomId = wsUrl.split('/ws/')[1].split('/')[0];
        infoEl.innerHTML = ` Комната: <a href="?room=${roomId}" target="_blank">Открыть в новой вкладке</a>`;
    }
}

function setupWebSocketHandlers() {
    ws.onopen = () => console.log("WebSocket подключён");
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log("📥 Ответ от сервера:", data);
        handleServerMessage(data);
    };
    
    ws.onclose = (event) => {
        if (event.code !== 1000) {
            showMessage("Соединение разорвано", "ошибка");
        }
    };
}


function handleServerMessage(data) {
    console.log("📥 Данные от сервера:", data);

    // 1️⃣ Сначала проверяем конец игры (важно!)
    if (data.game_over) {
        showMessage(`Игра окончена: ${data.winner || ''}`, "победа");
        disableBoard();
        if (data.desk) {
            BoardLikeDict = convertBoardKeys(data.desk);
            DrawBoard(BoardLikeDict);
        }
        return;
    }

    // 2️⃣ Подсветка ходов (запрос подсказок)
    if (data.essential_positions !== undefined && !data.message) {
        clearHighlights();
        if (data.essential_positions.length > 0) {
            drawEssentialPositions(data.essential_positions);
        }
        if (data.captured_pieces?.length > 0) {
            drawCapturedPieces(data.captured_pieces);
        }
        return;
    }

    // 3️⃣ Инициализация игры (первое подключение)
    if (data.players_color && data.desk && !data.message) {
        my_color = data.players_color;
        movers_color = data.movers_color;
        BoardLikeDict = convertBoardKeys(data.desk);
        
        document.getElementById("my_color").textContent = `Вы: ${my_color}`;
        document.getElementById("who_mover").textContent = `Ход: ${movers_color}`;
        DrawBoard(BoardLikeDict);
        showMessage("Игра началась!", "инфо");
        return;
    }

    // 4️⃣ Результат хода (самое важное!)
    if (data.message && data.desk) {
        console.log("🔄 Обновление доски, до:", BoardLikeDict[39], BoardLikeDict[32]);
        
        BoardLikeDict = convertBoardKeys(data.desk);
        
        console.log("🔄 После обновления:", BoardLikeDict[39], BoardLikeDict[32]);
        console.log("🔄 Клетка 39:", BoardLikeDict[39], "Клетка 32:", BoardLikeDict[32]);
        
        DrawBoard(BoardLikeDict);
        
        if (data.movers_color) {
            movers_color = data.movers_color;
            document.getElementById("who_mover").textContent = `Ход: ${movers_color}`;
        }
        
        showMessage(data.message, "инфо");
        position_for_mandatory_capture = data.position_for_mandatory_capture || null;
        
        // Кнопка "Передать ход" для бия
        const passBtn = document.getElementById("button_pass_the_move");
        if (data.opportunity_pass_the_move) {
            passBtn.innerHTML = '<button id="btn_pass" class="btn-pass">Передать ход</button>';
            document.getElementById("btn_pass")?.addEventListener("click", sendPassTheMove);
        } else {
            passBtn.innerHTML = '';
        }
        
        return;
    }
}

// 🆕 ДОБАВЬ ЭТУ ФУНКЦИЮ:
function convertBoardKeys(serverBoard) {
    const result = {};
    for (let [key, value] of Object.entries(serverBoard)) {
        result[parseInt(key)] = value;
    }
    return result;
}


function DrawBoard(board) {
    console.log("🎨 DrawBoard вызвана, ключи:", Object.keys(board).slice(0, 5));
    
    for (let id = 1; id <= 62; id++) {
        const el = document.getElementById("position" + id);
        if (!el) continue;
        
        const piece = board[id];
        
        // 🔥 Жесткий тест: если 32 должна быть "белая шатра"
        if (id === 32 && piece === "белая шатра") {
            console.log("✅ Клетка 32 должна показать белую шатру!");
        }
        
        if (piece === "черная шатра") {
            el.innerHTML = `${id}<div class="image-in-kletka"><img src="img/черная_точка.png"></div>`;
        } else if (piece === "белая шатра") {
            el.innerHTML = `${id}<div class="image-in-kletka"><img src="img/белая_точка.png"></div>`;
        } else if (piece === "белый бий") {
            el.innerHTML = `${id}<div class="image-in-kletka"><img src="img/белый_бий.png"></div>`;
        } else if (piece === "черный бий") {
            el.innerHTML = `${id}<div class="image-in-kletka"><img src="img/черный_бий.png"></div>`;
        } else if (piece === "белый батыр") {
            el.innerHTML = `${id}<div class="image-in-kletka"><img src="img/белый_батыр.png"></div>`;
        } else if (piece === "черный батыр") {
            el.innerHTML = `${id}<div class="image-in-kletka"><img src="img/черный_батыр.png"></div>`;
        } else {
            el.innerHTML = `${id}`;
        }
    }
}

function drawEssentialPositions(positions) {
    positions.forEach(id => {
        document.getElementById("position" + id)?.classList.add('highlight-essential');
    });
}

function drawCapturedPieces(positions) {
    positions.forEach(id => {
        document.getElementById("position" + id)?.classList.add('highlight-captured');
    });
}

function clearHighlights() {
    document.querySelectorAll('.highlight-essential, .highlight-captured').forEach(el => {
        el.classList.remove('highlight-essential', 'highlight-captured');
    });
}

function setupEventListeners() {
    document.querySelector('.board')?.addEventListener('click', handleBoardClick);
}

function handleBoardClick(event) {
    const cell = event.target.closest('[id^="position"]');
    if (!cell) return;
    
    const positionId = cell.id;
    const positionNum = extractNumber(positionId);

    console.log("🖱️ Клик:", { positionId, positionNum, my_color, movers_color });
    
    if (movers_color !== my_color) {
        showMessage("Не ваш ход!", "предупреждение");
        return;
    }
    
    if (document.querySelector('.board')?.classList.contains('disabled')) return;
    
    // Выбор фигуры
    if (move_from === null) {
        const pieceColor = getPieceColor(positionId);
        if (pieceColor === my_color) {
            move_from = positionId;
            cell.classList.add('highlight-black');
            sendPositionForHints(positionNum); // Запрос подсказок
        }
        return;
    }
    
    // Снять выделение
    if (move_from === positionId) {
        cell.classList.remove('highlight-black');
        clearHighlights();
        move_from = null;
        return;
    }
    
    // Сделать ход
    if (move_from !== null) {
        const fromNum = extractNumber(move_from);
        console.log("🚀 Отправка хода:", { from: fromNum, to: positionNum, board_sample: Object.entries(BoardLikeDict).filter(([k,v]) => v !== null).slice(0, 3) });
        sendMove(fromNum, positionNum);
        document.getElementById(move_from)?.classList.remove('highlight-black');
        clearHighlights();
        move_from = null;
    }
}

function sendMove(fromPos, toPos) {
    ws.send(JSON.stringify({
        move_from: `position${fromPos}`,
        move_to: `position${toPos}`,
        movers_color: movers_color,
        board: BoardLikeDict,
        position_for_mandatory_capture: position_for_mandatory_capture
    }));
}

function sendPositionForHints(posNum) {
    ws.send(JSON.stringify({
        position: `position${posNum}`,
        movers_color: movers_color,
        board: BoardLikeDict,
        position_for_mandatory_capture: position_for_mandatory_capture
    }));
}

function sendPassTheMove() {
    ws.send(JSON.stringify({
        move_from: "position0",
        move_to: "position0",
        movers_color: movers_color,
        board: BoardLikeDict,
        position_for_mandatory_capture: position_for_mandatory_capture
    }));
    document.getElementById("button_pass_the_move").innerHTML = '';
}

function extractNumber(str) {
    const match = str?.match(/position(\d+)/);
    return match ? parseInt(match[1], 10) : null;
}

function getPieceColor(positionId) {
    const num = extractNumber(positionId);
    const piece = BoardLikeDict[num];
    if (!piece) return null;
    if (piece.includes("бел")) return "белый";
    if (piece.includes("чер")) return "черный";
    return null;
}

function showMessage(text, type = "инфо") {
    const el = document.getElementById("message");
    if (!el) return;
    el.textContent = text;
    el.className = `message message-${type}`;
    if (type === "инфо" || type === "предупреждение") {
        setTimeout(() => { if (el.textContent === text) { el.textContent = ''; el.className = 'message'; }}, 3000);
    }
}

function enableBoard() { document.querySelector('.board')?.classList.remove('disabled'); }
function disableBoard() { document.querySelector('.board')?.classList.add('disabled'); }