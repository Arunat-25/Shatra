# Публикация на бесплатном хостинге (Render + Neon + Upstash)

Все три сервиса работают на бесплатных тарифах и не требуют привязки карты.
Время настройки — 15–20 минут. Итог: постоянный URL вида
`https://shatra-xxxx.onrender.com`, где играют онлайн-партии и партия с ботом.

> Ограничения бесплатного тарифа Render: сервис засыпает после ~15 минут
> простоя (первый посетитель ждёт ~1 минуту), 750 часов/месяц. При росте
> аудитории переезжаем на дешёвый VPS — код переносим без изменений
> (Docker-образ универсальный).

## 0. Что понадобится

- Аккаунт GitHub с этим репозиторием.
- Репозиторий должен быть доступен Render (публичный или подключённый).

## 1. Neon — база PostgreSQL

1. Зарегистрируйтесь на [neon.com](https://neon.com) (можно через GitHub).
2. Создайте проект `shatra`; регион выберите ближайший к аудитории (EU).
3. Скопируйте **Connection string** (Pooled connection) вида
   `postgresql://user:pass@ep-xxx-pooler.region.aws.neon.tech/neondb?sslmode=require`.
4. Преобразуйте для SQLAlchemy/asyncpg — замените схему на
   `postgresql+asyncpg://…&sslmode=require`
   (в строке Neon уже есть `?sslmode=require` — замените `?` на `&` после
   смены схемы, либо просто допишите `sslmode=require`).

Итог: `DATABASE_URL=postgresql+asyncpg://…&sslmode=require`

## 2. Upstash — Redis

1. Зарегистрируйтесь на [upstash.com](https://upstash.com) (можно через GitHub).
2. Create Database → `shatra`, регион как у Neon (EU), **Eviction off**.
3. В разделе Details скопируйте `REDIS_URL` вида `rediss://default:pass@host:6379`.

> **Важно:** пароль (токен) в консоли Upstash маскируется и не отображается повторно.  
> Скопируйте его сразу при создании базы или после сброса (Reset Credentials).  
> Если токен потерян — используйте «Reset Credentials» в настройках базы,  
> новый токен будет показан один раз.

Итог: `REDIS_URL=rediss://…`

## 3. Render — приложение

1. Зарегистрируйтесь на [render.com](https://render.com) (можно через GitHub).
2. New → **Blueprint** → выберите репозиторий `Arunat-25/Shatra` —
   Blueprint возьмёт `render.yaml` из корня (веб-сервис Docker, план free).
3. Заполните переменные, которые помечены `sync: false`. Blueprint **не создаёт
   их автоматически** — их нужно ввести вручную в Render → Settings → Environment;
   при запуске с отсутствующими значениями приложение теперь падает сразу с
   понятной ошибкой в логах (fail-fast в `backend/config.py`):

   | Переменная | Значение |
   |---|---|
   | `DATABASE_URL` | строка из шага 1 (обязательно) |
   | `REDIS_URL` | строка из шага 2 (обязательно) |
   | `CORS_ALLOW_ORIGINS` | `https://<имя-сервиса>.onrender.com` (после того как Render покажет URL) |
   | `METRICS_TOKEN` | обязательно в production; любая случайная строка, например `openssl rand -hex 16` |
   | `SENTRY_DSN` / `VITE_SENTRY_DSN` | опционально |

   `JWT_SECRET` сгенерируется автоматически (`generateValue: true`).

   > При редактировании таблицы Environment следите, чтобы каждая переменная
   > встречалась **один раз**: дубли `DATABASE_URL`/`REDIS_URL` ведут к непредсказуемым
   > значениям. Кнопка удаления в строке — иконка без текста (красная, справа).

4. Нажмите **Apply** — соберётся Docker-образ (фронтенд собирается внутри,
   миграции БД применяются при старте контейнера автоматически).

## 4. Проверка после первого деплоя

- `https://<сервис>.onrender.com/health` → `{"status":"ok",…}`.
- Открыть главную страницу → зарегистрироваться → создать комнату.
- Вторым окном/с телефона зайти по ссылке комнаты → сыграть пару ходов.
- Перезапустить сервис в дашборде Render → убедиться, что аккаунт и
  история сохранились (данные в Neon).

## 5. Обновления

Любой пуш в `main` автоматически пересобирает сервис (`autoDeploy: true`).
Проверка CI обязательна перед пушем (см. `.github/workflows/ci.yml`).

## 6. Частые проблемы

| Симптом | Причина | Решение |
|---|---|---|
| Первый вход «висит» ~1 мин | Сервис спит (free tier) | Норма; пробуждение на первом запросе |
| `ssl must be enabled` в логах | Neon требует TLS | Проверьте `sslmode=require` в `DATABASE_URL` |
| `OSError: Connect call failed ('127.0.0.1', 5432)` или `RuntimeError: DATABASE_URL must be set…` | `DATABASE_URL` не задан в Render: приложение упало на дефолтный localhost | Settings → Environment → Edit → добавить Neon-строку → Save, rebuild, and deploy |
| `RuntimeError: METRICS_TOKEN must be set when APP_ENV=production` | Не задан `METRICS_TOKEN` | Добавить token (например, `openssl rand -hex 16`) и redeploy |
| `RuntimeError: REDIS_URL must be set when APP_ENV=production` | Не задан `REDIS_URL` | Добавить Upstash-строку (`rediss://…`) и redeploy |
| Ходы не доходят второму игроку | `CORS_ALLOW_ORIGINS` не совпадает с URL | Укажите точный адрес сервиса |
| 502 после деплоя | Ошибка миграций | Логи Render → раздел `Events`; обычно проблема в `DATABASE_URL` |

## 7. Мониторинг (опционально)

Ошибки фронтенда/бэкенда — Sentry (бесплатный тариф): создайте проект,
впишите `SENTRY_DSN` и `VITE_SENTRY_DSN` в Render и перезапустите деплой.
