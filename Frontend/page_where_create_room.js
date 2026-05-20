// Frontend/page_where_create_room.js
document.querySelector('#button_get_link').addEventListener('click', function(event) {
    const button = this;
    button.disabled = true;
    button.textContent = 'Создание комнаты...';

    // Получаем базовый URL страницы
    const baseUrl = window.location.href.split('?')[0];
    // Имитируем ID комнаты (в реальности это делается на бэкенде)
    const roomId = Math.random().toString(36).substring(2, 8);
    const gameUrl = baseUrl.replace('page_where_create_room.html', 'Board.html') + `?room=${roomId}`;
    
    const elementLink = document.getElementById("link_for_room");
    elementLink.href = gameUrl;
    elementLink.textContent = gameUrl;
    
    const linkContainer = document.getElementById("link_container");
    linkContainer.style.display = 'block';
    
    button.textContent = 'Комната создана ✓';
});