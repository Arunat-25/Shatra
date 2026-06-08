# Рейтинг Elo

В Shatra используется **классическая формула Elo** (шкала 400) с **динамическим K-фактором** для каждого игрока. Рейтинг обновляется после завершения **рейтинговых** PvP-партий между зарегистрированными пользователями.

Исходный код: `backend/rating/elo.py`, `backend/rating/service.py`.

---

## Формула

### Ожидаемый результат

Для игрока A против B:

\[
E_A = \frac{1}{1 + 10^{(R_B - R_A) / 400}}
\]

Реализация: `expected_score(rating_a, rating_b)` в `backend/rating/elo.py`.

### Изменение рейтинга

После партии для каждого игрока:

\[
\Delta R = \mathrm{round}\bigl(K \cdot (S - E)\bigr)
\]

где:

| Символ | Значение |
|--------|----------|
| \(S\) | Фактический результат: **1.0** (победа), **0.5** (ничья), **0.0** (поражение) |
| \(E\) | Ожидаемый результат по формуле выше |
| \(K\) | K-фактор **этого** игрока (см. ниже) |

У белых и чёрных \(\Delta R\) **могут отличаться**, потому что K считается индивидуально.

Пример при равных рейтингах 1500 и K=20 (стандарт): победа **+10 / −10**, ничья **0 / 0**, поражение **−10 / +10**.

---

## K-фактор

Приоритет правил (первое совпавшее):

| Условие | K |
|---------|---|
| Меньше **30** рейтинговых партий (`rated_games_count`) | **40** |
| Рейтинг ≥ **2400** | **10** |
| Иначе | **20** |

Константы: `NOVICE_GAMES_THRESHOLD = 30`, `MASTER_RATING_THRESHOLD = 2400` в `backend/rating/elo.py`.

---

## Стартовый рейтинг

- Новый пользователь: **1200** (`DEFAULT_RATING`, колонка `users.rating`, server default `1200`).
- Счётчик рейтинговых партий: **0** (`users.rated_games_count`).

Миграция `012_rating_default_1200` переводит пользователей с рейтингом 1500 и нулём рейтинговых игр на 1200 (после ранней миграции `011`, где default был 1500).

---

## Какие партии рейтинговые

Функция `is_rated_match()` в `backend/rating/service.py`:

| Условие | Рейтинг |
|---------|---------|
| Публичная комната (`type: public`) | Да, если **оба** игрока зарегистрированы |
| Приватная комната с флагом «Игра на рейтинг» (`rated: true`) | Да, при тех же условиях |
| Приватная без флага | Нет |
| Игра с ботом, зритель, анонимный игрок | Нет |

«Зарегистрирован» = в `player_meta` есть `user_id`, `is_anonymous: false`.

При создании приватной комнаты флаг передаётся в REST `POST /rooms` (`CreateRoomRequest.rated`); в UI — чекбокс в `GameSetupPicker`.

---

## Результат партии → очки

`score_for_color(my_color, winner_color, reason)`:

| Исход | \(S\) |
|-------|------|
| Победа вашего цвета | 1.0 |
| Поражение | 0.0 |
| Ничья (`reason == draw_agreed`) или нет победителя (`winner_color` пустой/`null`) | 0.5 |

Ничья по любой причине без победителя (пат, согласованная ничья, недостаток материала и т.д.) даёт **0.5** обоим. Победа/поражение определяется полем `winner_color` в состоянии игры (`белый` / `черный`).

---

## Когда применяется рейтинг

1. Игра завершается → `archive_finished_game()` (`backend/game_archive.py`).
2. В одной транзакции с записью в `finished_games`:
   - если партия рейтинговая → `apply_rating()` с `SELECT ... FOR UPDATE` по обоим пользователям;
   - обновляются `users.rating`, `users.rated_games_count`;
   - в `finished_games` пишутся `is_rated`, `white_rating_delta`, `black_rating_delta`.
3. После commit — WebSocket-сообщение `rating_update` всем в комнате.

Перед стартом PvP и при реконнекте рейтинг подтягивается из БД: `refresh_pvp_ratings_for_room()` → актуальные значения в `players_info`.

---

## База данных

### `users`

| Колонка | Тип | Описание |
|---------|-----|----------|
| `rating` | `INTEGER`, default **1200** | Текущий рейтинг |
| `rated_games_count` | `INTEGER`, default **0** | Число учтённых рейтинговых партий |

### `finished_games`

| Колонка | Тип | Описание |
|---------|-----|----------|
| `is_rated` | `BOOLEAN` | Партия влияла на рейтинг |
| `white_rating_delta` | `INTEGER`, nullable | Δ белых (+/−) |
| `black_rating_delta` | `INTEGER`, nullable | Δ чёрных (+/−) |

Миграции: `alembic/versions/011_user_rating.py`, `012_rating_default_1200.py`.

```bash
alembic upgrade head
```

---

## API и WebSocket

### Профиль и авторизация

`UserPublic` (`GET /api/auth/me`, ответ login/register):

- `rating` — текущий рейтинг;
- `rated_games_count` — число рейтинговых партий.

### История партий

`FinishedGameSummary` (`GET /api/auth/games`):

- `is_rated` — была ли партия рейтинговой;
- `rating_delta` — изменение **вашего** рейтинга (`null`, если не рейтинговая).

### WebSocket во время игры

В `players_info` у зарегистрированных игроков:

```json
{
  "client_id": "...",
  "color": "белый",
  "username": "player",
  "is_anonymous": false,
  "display_name": "player",
  "rating": 1247
}
```

После рейтинговой партии — сообщение:

```json
{
  "type": "rating_update",
  "players_info": [
    {
      "client_id": "...",
      "rating": 1257,
      "rating_delta": 10,
      "...": "..."
    }
  ]
}
```

`rating` в этом сообщении — **уже после** партии; `rating_delta` — изменение за эту игру.

---

## Интерфейс

| Место | Поведение |
|-------|-----------|
| Профиль (`/profile`) | Рейтинг и число рейтинговых партий; в истории — колонка ± |
| PvP за доской | Число рейтинга у ника (не в режиме с ботом) |
| Конец рейтинговой партии | Рядом с рейтингом: **+N** (зелёный) / **−N** (красный) |
| Создание приватной комнаты | Чекбокс «Игра на рейтинг» |

Компоненты: `PlayerNick.jsx`, `PlayerBar.jsx`, `playerDisplay.js`, обработчик `rating_update` в `messageHandlers.js`.

---

## Примеры расчёта

**Равные 1500, оба ≥30 игр (K=20), белые выиграли:** +10 / −10.

**Новичок (5 игр, K=40) vs стандарт (50 игр, K=20), оба 1500, новичок выиграл:** +20 / −10.

**1400 vs 1800 (K=20), ничья:** аутсайдер +8, фаворит −8.

**2450 vs 2450 (K=10), победа:** +5 / −5.

Подробные табличные и property-based тесты: `tests/rating/test_elo.py`, `tests/rating/test_service.py`, интеграция архива: `tests/server/test_game_archive.py` (`TestArchiveRating`).

---

## Архитектура (файлы)

```
backend/rating/
  elo.py          # формула, K, DEFAULT_RATING
  service.py      # eligibility, apply_rating, players_info_with_rating_result
backend/game_archive.py   # вызов apply_rating, broadcast rating_update
backend/player_identity.py # rating в meta, refresh из БД
backend/room_manager.py   # Room.rated для приватных комнат
backend/auth/schemas.py   # UserPublic, FinishedGameSummary
frontend/src/...          # отображение рейтинга и delta
```

Рейтинг **не** вынесен в отдельный микросервис: расчёт синхронный, запись атомарна в транзакции архива партии.
