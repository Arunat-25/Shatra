// Frontend/lobby.js
const API_BASE = "http://localhost:8000";

function showError(message) {
    const container = document.getElementById("error_container");
    const msgEl = document.getElementById("error_message");
    if (container && msgEl) {
        msgEl.textContent = message;
        container.style.display = "block";
        setTimeout(() => {
            container.style.display = "none";
        }, 5000);
    }
}

function navigateToGame(roomId, playerId) {
    window.location.href = `/Frontend/Board.html?room=${roomId}&player=${playerId}`;
}

// Создать игру (quick) — остаться на странице, ждать P2
let pollInterval = null;

document.getElementById("btn-create-game")?.addEventListener("click", async function() {
    const button = this;
    button.disabled = true;
    button.textContent = "Создание...";
    
    try {
        const res = await fetch(`${API_BASE}/rooms`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ type: "quick" })
        });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Ошибка создания комнаты");
        }
        const data = await res.json();
        button.textContent = "Ожидание соперника...";
        fetchRooms();
        
        // Поллим статус — когда P2 присоединится, переходим на Board.html
        if (pollInterval) clearInterval(pollInterval);
        pollInterval = setInterval(async () => {
            try {
                const statusRes = await fetch(`${API_BASE}/rooms/${data.room_id}/status`);
                const status = await statusRes.json();
                if (status.player2_connected) {
                    clearInterval(pollInterval);
                    pollInterval = null;
                    navigateToGame(data.room_id, 1);
                }
            } catch (e) {}
        }, 1000);
        
    } catch (e) {
        showError(e.message || "Сервер недоступен");
        button.disabled = false;
        button.textContent = "Создать игру";
    }
});

// Вызов другу (friend) — сразу перейти в комнату с экраном ожидания
document.getElementById("btn-challenge-friend")?.addEventListener("click", async function() {
    const button = this;
    button.disabled = true;
    button.textContent = "Создание...";
    
    try {
        const res = await fetch(`${API_BASE}/rooms`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ type: "friend" })
        });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Ошибка создания комнаты");
        }
        const data = await res.json();
        navigateToGame(data.room_id, 1);
    } catch (e) {
        showError(e.message || "Сервер недоступен");
        button.disabled = false;
        button.textContent = "Вызов другу";
    }
});

// Загружаем список комнат при открытии страницы
document.addEventListener("DOMContentLoaded", fetchRooms);

// Кнопка обновления списка
document.getElementById("btn-refresh-rooms")?.addEventListener("click", fetchRooms);

// Автообновление каждые 10 секунд
setInterval(fetchRooms, 10000);

async function fetchRooms() {
    const listEl = document.getElementById("rooms-list");
    if (!listEl) return;
    
    try {
        const res = await fetch(`${API_BASE}/rooms`);
        if (!res.ok) throw new Error("Ошибка загрузки");
        const data = await res.json();
        
        if (data.rooms.length === 0) {
            listEl.innerHTML = '<p class="rooms-empty">Нет доступных комнат</p>';
            return;
        }
        
        let html = "";
        for (const room of data.rooms) {
            const typeLabel = room.type === "quick" ? "Быстрая игра" : "Вызов другу";
            const created = new Date(room.created_at).toLocaleTimeString();
            html += `
                <div class="room-item" data-room-id="${room.room_id}">
                    <div class="room-item-info">
                        <span class="room-item-type">${typeLabel}</span>
                        <span class="room-item-id">ID: ${room.room_id}</span>
                        <span class="room-item-time">${created}</span>
                    </div>
                </div>
            `;
        }
        listEl.innerHTML = html;
        
        // Клик по комнате — P2 присоединяется
        listEl.querySelectorAll(".room-item").forEach(item => {
            item.style.cursor = "pointer";
            item.addEventListener("click", async function() {
                const targetRoomId = this.dataset.roomId;
                if (!targetRoomId) return;
                
                try {
                    const res = await fetch(`${API_BASE}/rooms/${targetRoomId}/join`, {
                        method: "POST"
                    });
                    if (!res.ok) {
                        const err = await res.json();
                        throw new Error(err.detail || "Ошибка присоединения");
                    }
                    
                    // Открываем WebSocket как P2 — когда P1 уже ждёт
                    const joiningWs = new WebSocket(`ws://localhost:8000/ws/${targetRoomId}/2/`);
                    joiningWs.onmessage = (event) => {
                        const msg = JSON.parse(event.data);
                        if (msg.movers_color || msg.players_color) {
                            navigateToGame(targetRoomId, 2);
                        }
                    };
                    joiningWs.onerror = () => {
                        showError("Ошибка подключения к комнате");
                    };
                    
                    // Визуально отмечаем комнату как выбранную
                    this.classList.add("room-item-joined");
                    this.style.pointerEvents = "none";
                    this.style.opacity = "0.7";
                    
                } catch (e) {
                    showError(e.message || "Ошибка присоединения к комнате");
                }
            });
        });
        
    } catch (e) {
        listEl.innerHTML = '<p class="rooms-error">Ошибка загрузки комнат</p>';
        showError(e.message || "Сервер недоступен");
    }
}