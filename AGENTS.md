# Shatra

Онлайн-версия алтайской настольной игры «Шатра». Обзор проекта и запуск — в `README.md`.

## Agent skills

### Issue tracker

GitHub Issues репозитория `Arunat-25/Shatra` (через `gh` CLI). See `docs/agents/issue-tracker.md`.

### Triage labels

Стандартная пятёрка меток триажа: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `GLOSSARY.md` в корне репозитория + `docs/adr/`. See `docs/agents/domain.md`.

### Decisions & deploy

Решения: `docs/adr/`. Бесплатный деплой: `docs/DEPLOY_RENDER.md`. Бэкенд-тесты локально: `./scripts/test-backend.sh`.

### Browser automation

Работа с дашбордами через браузер: `snapshot`/`find` + клики по ref, `evaluate` только для компактного чтения состояния. See `docs/agents/browser.md`.
