# Production deploy

Деплой на VPS с Docker: TLS через nginx + certbot (Let's Encrypt), Postgres/Redis только во internal network, опциональный monitoring stack.

Dev/quick demo без своего домена: [README](../README.md) (Cloudflare Tunnel) или `docker compose up` (локально).

---

## Требования

- VPS с Docker Engine и **Docker Compose v2** (`docker compose`, без дефиса)
- Домен с A-record на IP сервера (для Let's Encrypt)
- Открыты порты **80** и **443** (nginx)

> **Не используйте** устаревший `docker-compose` v1 — на новых Docker он падает с `KeyError: 'ContainerConfig'`.

### Установка Compose v2 на VPS

```bash
./scripts/install-compose-v2.sh
docker compose version
```

На Ubuntu без пакета `docker-compose-plugin` скрипт скачает плагин в `~/.docker/cli-plugins/`.

---

## 1. Подготовка сервера

```bash
git clone <repo-url> shatra
cd shatra
# Создайте .env — см. README, раздел «Конфигурация»
```

Заполните `.env`. Для prod обязательны минимум:

| Переменная | Пример | Описание |
|------------|--------|----------|
| `DOMAIN` | `shatra.example.com` | Домен для nginx и TLS |
| `CERTBOT_EMAIL` | `admin@example.com` | Email для Let's Encrypt |
| `JWT_SECRET` | `openssl rand -hex 32` | Обязателен; дефолт запрещён при `APP_ENV=production` |
| `POSTGRES_PASSWORD` | `openssl rand -hex 24` | Пароль БД |
| `CORS_ALLOW_ORIGINS` | `https://shatra.example.com` | Явный origin (или `*` при same-origin через nginx) |
| `SENTRY_DSN` | — | Опционально |
| `VITE_SENTRY_DSN` | — | Build-time для frontend (пересборка образа) |
| `APP_VERSION` | `1.0.0` | Release tag в Sentry |

Для monitoring profile (см. ниже) также:

| Переменная | Описание |
|------------|----------|
| `METRICS_TOKEN` | Bearer token для `/metrics` (Prometheus scrape) |
| `GRAFANA_ADMIN_PASSWORD` | Пароль admin Grafana |

---

## 2. Запуск

**Только приложение** (app + postgres + redis + **shatra-ai** + nginx + certbot):

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Сервис `shatra-ai` (Rust gRPC) поднимается в internal network. По умолчанию `AI_ENGINE=grpc`. Rollback: `AI_ENGINE=python` и перезапустить только `app`.

Подробнее: [services/shatra-ai/README.md](../services/shatra-ai/README.md).

### 2b. Первый TLS-сертификат

После того как DNS A-record указывает на VPS:

```bash
./scripts/init-letsencrypt.sh
```

Скрипт поднимает stack, запрашивает сертификат через certbot (webroot) и перезапускает nginx с HTTPS. До этого nginx работает по HTTP (прокси на app) — достаточно для ACME http-01.

Повторный запуск безопасен: если сертификат уже есть, certonly пропускается.

**С мониторингом** (Prometheus, Loki, Grafana на localhost:3000):

```bash
docker compose -f docker-compose.prod.yml --profile monitoring up -d --build
```

При `--profile monitoring` задайте `METRICS_TOKEN` и `GRAFANA_ADMIN_PASSWORD` в `.env`.

---

## 3. Проверка

```bash
curl -s https://YOUR_DOMAIN/health | jq
```

Ожидается `"status": "ok"` при живых Redis и Postgres.

В браузере:

1. Откройте `https://YOUR_DOMAIN`
2. Создайте комнату, сыграйте ход (WS + REST)

Логи app:

```bash
docker logs shatra-app -f
```

Синтаксис nginx:

```bash
docker exec shatra-nginx nginx -t
```

Grafana (только monitoring profile, через SSH tunnel):

```bash
ssh -L 3000:127.0.0.1:3000 user@your-vps
# локально: http://127.0.0.1:3000
```

См. также [MONITORING.md](MONITORING.md).

### Smoke checklist

| Проверка | Команда / действие | Ожидание |
|----------|-------------------|----------|
| Health через TLS | `curl -s https://$DOMAIN/health` | `"status":"ok"` |
| REST | `curl -s https://$DOMAIN/rooms` | JSON со stats |
| WebSocket | браузер: комната + ход | WS connect, ход проходит |
| Renew dry-run | `docker compose -f docker-compose.prod.yml run --rm --entrypoint certbot certbot renew --dry-run` | success |

---

## 4. Архитектура prod-compose

```
Internet → nginx :443 → app :8000 (internal)
              certbot → webroot + /etc/letsencrypt (shared volume)
              app → postgres, redis (internal, без host ports)
Prometheus (profile) → app /metrics (Bearer METRICS_TOKEN)
Grafana → 127.0.0.1:3000 only
```

- Postgres и Redis **не** проброшены на хост
- `/metrics` защищён, если задан `METRICS_TOKEN`
- При `APP_ENV=production` приложение **не стартует** с `JWT_SECRET=change-me-in-production`
- nginx перезагружает конфиг каждые 12h, чтобы подхватить обновлённые сертификаты после `certbot renew`

---

## 5. Обновление

Вручную:

```bash
./scripts/deploy-prod.sh
```

или:

```bash
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

Миграции применяются автоматически при старте `app` (`alembic upgrade head`).

### Автодеплой при push в `main`

Workflow [`.github/workflows/deploy.yml`](../.github/workflows/deploy.yml) запускается **при каждом push в `main`** и по SSH выполняет `scripts/deploy-prod.sh` на VPS. CI продолжает гоняться параллельно для проверки качества.

**1. На сервере** (один раз):

```bash
chmod +x ~/Shatra/scripts/deploy-prod.sh
```

Убедитесь, что `git pull` работает (для приватного репозитория — [deploy key](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/managing-deploy-keys) с read-доступом в `~/.ssh`).

**2. SSH-ключ для GitHub Actions** (на своём компьютере):

```bash
ssh-keygen -t ed25519 -f shatra-deploy -N "" -C "github-actions-deploy"
```

Публичный ключ `shatra-deploy.pub` добавьте на сервер:

```bash
cat shatra-deploy.pub >> ~/.ssh/authorized_keys
```

**3. Secrets в GitHub** (Settings → Secrets and variables → Actions):

| Secret | Пример | Обязателен |
|--------|--------|------------|
| `DEPLOY_HOST` | `136.234.124.150` | да |
| `DEPLOY_USER` | `root` | да |
| `DEPLOY_SSH_KEY` | содержимое `shatra-deploy` (приватный) | да |
| `DEPLOY_PATH` | `/root/Shatra` | нет (по умолчанию `/root/Shatra`) |
| `DEPLOY_PORT` | `22` | нет |

После этого каждый **push в `main`** пересобирает prod (`docker compose … up -d --build`).

---

## 6. Бэкапы PostgreSQL

Пример cron на хосте (раз в сутки):

```bash
docker exec shatra-postgres pg_dump -U shatra shatra | gzip > /var/backups/shatra-$(date +%F).sql.gz
```

Храните бэкапы отдельно от VPS.

---

## 7. Альтернативы

| Способ | Когда |
|--------|--------|
| [`scripts/tunnel-quick.sh`](../scripts/tunnel-quick.sh) | Быстрый тест с друзьями, без домена |
| `docker compose up` (dev) | Локальная разработка, порты 5432/6379/8000 |
| `docker-compose.prod.yml` | Постоянный публичный сайт на своём домене |

---

## Troubleshooting

**`KeyError: 'ContainerConfig'` при `docker-compose up`**

Установлен Compose v1. Удалите его и используйте v2:

```bash
apt remove -y docker-compose 2>/dev/null || true
./scripts/install-compose-v2.sh
docker compose -f docker-compose.prod.yml up -d --build
```

**App не стартует: JWT_SECRET**

```
RuntimeError: JWT_SECRET must be set...
```

Задайте сильный секрет в `.env` и перезапустите compose.

**Certbot не получает сертификат**

- DNS A-record указывает на VPS
- Порты 80/443 доступны из интернета
- `DOMAIN` и `CERTBOT_EMAIL` в `.env` заданы корректно
- nginx запущен: `docker logs shatra-nginx`
- Повтор: `./scripts/init-letsencrypt.sh`

**Prometheus не scrape /metrics**

- `METRICS_TOKEN` одинаковый в `app` и в monitoring profile
- Проверка: `docker exec shatra-prometheus wget -qO- --header="Authorization: Bearer $TOKEN" http://app:8000/metrics | head`

**502 от nginx**

- `docker logs shatra-app` — app healthy?
- `docker exec shatra-nginx wget -qO- http://app:8000/health`

**Миграция с Caddy**

Старые volumes Caddy больше не нужны:

```bash
docker compose -f docker-compose.prod.yml down
docker volume rm shatra_caddy-data shatra_caddy-config 2>/dev/null || true
docker compose -f docker-compose.prod.yml up -d --build
./scripts/init-letsencrypt.sh
```
