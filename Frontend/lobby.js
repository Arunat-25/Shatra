// Frontend/page_where_create_room.js
const API_BASE = "http://localhost:8000";
let myRoomId = null;

// Сбрасываем кнопки при загрузке/возврате на страницу
function resetButtons() {
    const btnCreate = document.getElementById("btn-create-game");
    const btnChallenge = document.getElementById("btn-challenge-friend");
    const btnQuick = document.getElementById("btn-quick-start");
    
    if (btnCreate) { btnCreate.disabled = false; btnCreate.textContent = "Создать игру"; }
    if (btnChallenge) { btnChallenge.disabled = false; btnChallenge.textContent = "Вызов другу"; }
    if (btnQuick) { btnQuick.disabled = false; btnQuick.textContent = "Быстрый старт"; }
    
    const linkContainer = document.getElementById("invite-link-container");
    if (linkContainer) {
        linkContainer.style.display = "none";
    }
}

document.addEventListener("DOMContentLoaded", resetButtons);
window.addEventListener("pageshow", resetButtons);

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

function navigateToGame(roomId) {
    window.location.href = `/Frontend/Board.html?room=${roomId}`;
}

// Создать игру (quick) — открыть модалку только со своей комнатой
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
        myRoomId = data.room_id;
        document.getElementById("lobby-modal").style.display = "flex";
        renderMyRoomOnly(data.room_id, data.link);
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
        navigateToGame(data.room_id);
    } catch (e) {
        showError(e.message || "Сервер недоступен");
        button.disabled = false;
        button.textContent = "Вызов другу";
    }
});

// Быстрый старт
document.getElementById("btn-quick-start")?.addEventListener("click", async function() {
    const button = this;
    button.disabled = true;
    button.textContent = "Поиск...";
    
    try {
        const res = await fetch(`${API_BASE}/rooms/quick-start`);
        if (res.status === 404) {
            showError("Нет свободных комнат. Создайте свою!");
            button.disabled = false;
            button.textContent = "Быстрый старт";
            return;
        }
        if (!res.ok) {
            throw new Error("Ошибка поиска комнаты");
        }
        const data = await res.json();
        navigateToGame(data.room_id);
    } catch (e) {
        showError(e.message || "Сервер недоступен");
        button.disabled = false;
        button.textContent = "Быстрый старт";
    }
});

// Зал ожидания
document.getElementById("btn-open-lobby")?.addEventListener("click", function() {
    document.getElementById("lobby-modal").style.display = "flex";
    myRoomId = null;
    fetchRooms();
});

document.getElementById("btn-close-lobby")?.addEventListener("click", function() {
    document.getElementById("lobby-modal").style.display = "none";
});

document.getElementById("lobby-modal")?.addEventListener("click", function(e) {
    if (e.target === this) {
        this.style.display = "none";
    }
});

document.getElementById("btn-refresh-rooms")?.addEventListener("click", function() {
    if (myRoomId) {
        renderMyRoomOnly(myRoomId, `/Frontend/Board.html?room=${myRoomId}`);
    } else {
        fetchRooms();
    }
});

// Показать модалку только со своей комнатой (без списка других комнат)
function renderMyRoomOnly(roomId, link) {
    const listEl = document.getElementById("rooms-list");
    if (!listEl) return;
    
    const fullUrl = `${window.location.protocol}//${window.location.host}${link}`;
    
    listEl.innerHTML = `
        <div class="my-room-section">
            <h3 style="margin-bottom:12px;font-size:1rem;color:#e0e0e0;">Моя комната</h3>
            <div class="room-item my-room-highlight">
                <div class="room-item-info">
                    <span class="room-item-type">Созданная комната</span>
                    <span class="room-item-id" style="font-size:0.9rem;">ID: ${roomId}</span>
                </div>
                <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
                    <input type="text" id="my-room-link" value="${fullUrl}" readonly style="padding:8px 12px;border-radius:8px;border:1px solid rgba(102,126,234,0.3);background:rgba(255,255,255,0.06);color:#a8b4ff;font-family:monospace;font-size:0.8rem;max-width:280px;width:100%;">
                    <button id="btn-copy-my-room-link" class="btn-lobby btn-lobby-small" style="flex-shrink:0;font-size:0.75rem;padding:8px 16px;">Копировать</button>
                </div>
            </div>
            <button id="btn-enter-my-room" class="btn-lobby btn-lobby-accent" style="margin-top:10px;padding:12px 32px;font-size:0.95rem;">Войти в комнату</button>
        </div>
    `;
    
    document.getElementById("btn-enter-my-room")?.addEventListener("click", function() {
        navigateToGame(roomId);
    });
    
    document.getElementById("btn-copy-my-room-link")?.addEventListener("click", function() {
        const input = document.getElementById("my-room-link");
        if (input) {
            input.select();
            navigator.clipboard.writeText(input.value).then(() => {
                this.textContent = "Скопировано!";
                setTimeout(() => { this.textContent = "Копировать"; }, 2000);
            }).catch(() => {
                document.execCommand("copy");
                this.textContent = "Скопировано!";
                setTimeout(() => { this.textContent = "Копировать"; }, 2000);
            });
        }
    });
}

// Показать модалку со своей комнатой сверху и списком остальных
async function renderLobbyWithMyRoom(roomId, link) {
    const listEl = document.getElementById("rooms-list");
    if (!listEl) return;
    
    const fullUrl = `${window.location.protocol}//${window.location.host}${link}`;
    
    let html = `
        <div class="my-room-section">
            <h3 style="margin-bottom:12px;font-size:1rem;color:#e0e0e0;">Моя комната</h3>
            <div class="room-item my-room-highlight">
                <div class="room-item-info">
                    <span class="room-item-type">Созданная комната</span>
                    <span class="room-item-id" style="font-size:0.9rem;">ID: ${roomId}</span>
                </div>
                <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
                    <input type="text" id="my-room-link" value="${fullUrl}" readonly style="padding:8px 12px;border-radius:8px;border:1px solid rgba(102,126,234,0.3);background:rgba(255,255,255,0.06);color:#a8b4ff;font-family:monospace;font-size:0.8rem;max-width:280px;width:100%;">
                    <button id="btn-copy-my-room-link" class="btn-lobby btn-lobby-small" style="flex-shrink:0;font-size:0.75rem;padding:8px 16px;">Копировать</button>
                </div>
            </div>
            <button id="btn-enter-my-room" class="btn-lobby btn-lobby-accent" style="margin-top:10px;padding:12px 32px;font-size:0.95rem;">Войти в комнату</button>
        </div>
        <hr style="border:none;border-top:1px solid rgba(255,255,255,0.08);margin:16px 0;">
        <h3 style="margin-bottom:12px;font-size:1rem;color:#e0e0e0;">Доступные комнаты</h3>
    `;
    
    listEl.innerHTML = html + '<p class="rooms-loading">Загрузка комнат...</p>';
    
    // Кнопка "Войти в комнату"
    document.getElementById("btn-enter-my-room")?.addEventListener("click", function() {
        navigateToGame(roomId);
    });
    
    // Кнопка "Копировать"
    document.getElementById("btn-copy-my-room-link")?.addEventListener("click", function() {
        const input = document.getElementById("my-room-link");
        if (input) {
            input.select();
            navigator.clipboard.writeText(input.value).then(() => {
                this.textContent = "Скопировано!";
                setTimeout(() => { this.textContent = "Копировать"; }, 2000);
            }).catch(() => {
                document.execCommand("copy");
                this.textContent = "Скопировано!";
                setTimeout(() => { this.textContent = "Копировать"; }, 2000);
            });
        }
    });
    
    // Загружаем остальные комнаты
    try {
        const res = await fetch(`${API_BASE}/rooms`);
        if (!res.ok) throw new Error("Ошибка загрузки");
        const data = await res.json();
        
        const otherRooms = data.rooms.filter(r => r.room_id !== roomId);
        
        if (otherRooms.length === 0) {
            listEl.innerHTML = html + '<p class="rooms-empty">Других комнат нет</p>';
            return;
        }
        
        let roomsHtml = "";
        for (const room of otherRooms) {
            const typeLabel = room.type === "quick" ? "Быстрая игра" : "Вызов другу";
            const created = new Date(room.created_at).toLocaleTimeString();
            roomsHtml += `
                <div class="room-item">
                    <div class="room-item-info">
                        <span class="room-item-type">${typeLabel}</span>
                        <span class="room-item-id">ID: ${room.room_id}</span>
                        <span class="room-item-time">${created}</span>
                    </div>
                    <button class="btn-lobby btn-lobby-small btn-lobby-join" data-room-id="${room.room_id}">Присоединиться</button>
                </div>
            `;
        }
        listEl.innerHTML = html + roomsHtml;
        
        listEl.querySelectorAll(".btn-lobby-join").forEach(btn => {
            btn.addEventListener("click", async function() {
                const targetRoomId = this.dataset.roomId;
                this.disabled = true;
                this.textContent = "Подключение...";
                
                try {
                    const res = await fetch(`${API_BASE}/rooms/${targetRoomId}/join`, {
                        method: "POST"
                    });
                    if (!res.ok) {
                        const err = await res.json();
                        throw new Error(err.detail || "Ошибка присоединения");
                    }
                    const data = await res.json();
                    navigateToGame(data.room_id);
                } catch (e) {
                    showError(e.message || "Ошибка присоединения к комнате");
                    this.disabled = false;
                    this.textContent = "Присоединиться";
                }
            });
        });
        
    } catch (e) {
        listEl.innerHTML = html + '<p class="rooms-error">Ошибка загрузки комнат</p>';
        showError(e.message || "Сервер недоступен");
    }
}

// Обычная загрузка списка (без своей комнаты)
async function fetchRooms() {
    const listEl = document.getElementById("rooms-list");
    if (!listEl) return;
    
    listEl.innerHTML = '<p class="rooms-loading">Загрузка комнат...</p>';
    
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
                <div class="room-item">
                    <div class="room-item-info">
                        <span class="room-item-type">${typeLabel}</span>
                        <span class="room-item-id">ID: ${room.room_id}</span>
                        <span class="room-item-time">${created}</span>
                    </div>
                    <button class="btn-lobby btn-lobby-small btn-lobby-join" data-room-id="${room.room_id}">Присоединиться</button>
                </div>
            `;
        }
        listEl.innerHTML = html;
        
        listEl.querySelectorAll(".btn-lobby-join").forEach(btn => {
            btn.addEventListener("click", async function() {
                const targetRoomId = this.dataset.roomId;
                this.disabled = true;
                this.textContent = "Подключение...";
                
                try {
                    const res = await fetch(`${API_BASE}/rooms/${targetRoomId}/join`, {
                        method: "POST"
                    });
                    if (!res.ok) {
                        const err = await res.json();
                        throw new Error(err.detail || "Ошибка присоединения");
                    }
                    const data = await res.json();
                    navigateToGame(data.room_id);
                } catch (e) {
                    showError(e.message || "Ошибка присоединения к комнате");
                    this.disabled = false;
                    this.textContent = "Присоединиться";
                }
            });
        });
        
    } catch (e) {
        listEl.innerHTML = '<p class="rooms-error">Ошибка загрузки комнат</p>';
        showError(e.message || "Сервер недоступен");
    }
}