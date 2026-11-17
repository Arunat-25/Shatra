#!/usr/bin/env python3
"""
Служебный скрипт для отчета по учебному проекту «Национальная игра Алтай Шатра».

Генерирует схемы (архитектура, ER БД, диаграмма последовательности хода,
диаграмма состояний игровой сессии, дерево структуры проекта) как PNG-файлы
в report_assets/img/. Опирается только на реальный код проекта (backend/,
game_engine/, crates/shatra-engine/, services/shatra-ai/, frontend/,
docs/architecture/TARGET_ARCHITECTURE_V2.md, docs/ELO.md, backend/db/models.py).

Запуск:
    source report_assets/.venv/bin/activate
    python3 report_assets/generate_diagrams.py
"""
import os
import subprocess
import textwrap

import graphviz
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

HERE = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(HERE, "img")
os.makedirs(IMG_DIR, exist_ok=True)

FONT_SERIF = "Liberation Serif"
FONT_MONO = "Liberation Mono"

# Регистрируем шрифты явно (headless-окружение может не построить кэш заранее)
for fp in [
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
]:
    if os.path.exists(fp):
        fm.fontManager.addfont(fp)

plt.rcParams["font.family"] = FONT_SERIF
plt.rcParams["axes.unicode_minus"] = False

GV_FONT = "Liberation Serif"


# ---------------------------------------------------------------------------
# 1. Схема архитектуры системы
# ---------------------------------------------------------------------------
def build_architecture_diagram():
    g = graphviz.Digraph("architecture", format="png")
    g.attr(rankdir="LR", fontname=GV_FONT, fontsize="20", labelloc="t",
            label="Архитектура системы «Шатра»", splines="spline",
            bgcolor="white", nodesep="0.55", ranksep="0.9")
    g.attr("node", fontname=GV_FONT, fontsize="15", shape="box",
            style="rounded,filled", color="#4a3524", penwidth="1.3")
    g.attr("edge", fontname=GV_FONT, fontsize="13", color="#4a3524")

    with g.subgraph(name="cluster_client") as c:
        c.attr(label="Клиент (браузер)", fontname=GV_FONT, fontsize="16",
               style="rounded", color="#8a6d3b", bgcolor="#fff6e3")
        c.node("ui", "React UI\n(доска, лобби, чат, таймеры)",
               fillcolor="#ffe9b3")
        c.node("rules_ts", "packages/shatra-rules\n(TypeScript)\nлокальные hints,\nвалидация, optimistic UI",
               fillcolor="#ffe9b3")
        c.node("sync", "Sync layer\n(ply, pendingMoves,\nreconcile)", fillcolor="#ffe9b3")
        c.edge("ui", "rules_ts", dir="both")
        c.edge("ui", "sync", dir="both")

    with g.subgraph(name="cluster_server") as s:
        s.attr(label="Сервер (Docker Compose)", fontname=GV_FONT, fontsize="16",
               style="rounded", color="#2e5339", bgcolor="#e8f3ea")
        s.node("api", "FastAPI (backend/)\nREST + WebSocket v2\n/ws/v2/{room_id}/",
               fillcolor="#c9e8d0")
        s.node("engine_py", "game_engine/ (Python)\nправила — authoritative\n(handle_event)",
               fillcolor="#c9e8d0")
        s.node("redis", "Redis\nсостояние партий,\nтаймеры, TTL", shape="cylinder",
               fillcolor="#d7e6ff")
        s.node("pg", "PostgreSQL\nusers, finished_games,\npresence_sessions,\nbug_reports", shape="cylinder",
               fillcolor="#d7e6ff")
        s.node("ai_py", "backend/ai.py\n(Python minimax,\nAI_ENGINE=python)",
               fillcolor="#c9e8d0")

    with g.subgraph(name="cluster_ai") as a:
        a.attr(label="AI-сервис shatra-ai\n(Rust, gRPC, отдельный контейнер)",
               fontname=GV_FONT, fontsize="16", style="rounded",
               color="#5a2d5c", bgcolor="#f3e6f5")
        a.node("ai_rs", "worker.rs / grpc_impl.rs\npул воркеров, tonic gRPC :50051",
               fillcolor="#e6c9ea")
        a.node("engine_rs", "crates/shatra-engine\n(Rust)\nправила + поиск ходов",
               fillcolor="#e6c9ea")
        a.edge("ai_rs", "engine_rs", dir="both")

    with g.subgraph(name="cluster_mon") as m:
        m.attr(label="Мониторинг (профиль monitoring)", fontname=GV_FONT,
               fontsize="14", style="dashed", color="#777777")
        m.node("prom", "Prometheus", fillcolor="#eeeeee")
        m.node("loki", "Loki + Promtail", fillcolor="#eeeeee")
        m.node("grafana", "Grafana", fillcolor="#eeeeee")
        m.edge("prom", "grafana", dir="forward")
        m.edge("loki", "grafana", dir="forward")

    g.edge("ui", "api", label="WebSocket v2, REST\n(JSON)", dir="both")
    g.edge("api", "engine_py", label="handle_event()\nвалидация хода", dir="both")
    g.edge("api", "redis", label="game state,\nrooms, presence", dir="both")
    g.edge("api", "pg", label="users, рейтинг Elo,\nархив партий", dir="both")
    g.edge("api", "ai_py", label="AI_ENGINE=python", style="dashed")
    g.edge("api", "ai_rs", label="gRPC\nAI_ENGINE=grpc\n(ComputeMove)", color="#5a2d5c")
    g.edge("api", "prom", label="/metrics", style="dotted", color="#777777")

    out = os.path.join(IMG_DIR, "architecture")
    g.render(out, cleanup=True)
    print("architecture.png готово")


# ---------------------------------------------------------------------------
# 2. ER-диаграмма БД (по backend/db/models.py и alembic/versions)
# ---------------------------------------------------------------------------
def build_er_diagram():
    g = graphviz.Digraph("er", format="png")
    g.attr(rankdir="LR", fontname=GV_FONT, fontsize="20", labelloc="t",
            label="ER-диаграмма базы данных PostgreSQL", bgcolor="white",
            nodesep="0.6", ranksep="1.0")
    g.attr("node", fontname=GV_FONT, fontsize="13", shape="none")
    g.attr("edge", fontname=GV_FONT, fontsize="12", color="#4a3524", arrowhead="crow", arrowtail="none")

    def table(name, title, rows, pk_rows=()):
        lines = "".join(
            f'<TR><TD ALIGN="LEFT" BGCOLOR="{"#ffe9b3" if r.split()[0] in pk_rows else "white"}">'
            f'<FONT FACE="{GV_FONT}">{r}</FONT></TD></TR>'
            for r in rows
        )
        html = (
            f'<<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="5">'
            f'<TR><TD BGCOLOR="#4a3524" ALIGN="CENTER">'
            f'<FONT COLOR="white" FACE="{GV_FONT}"><B>{title}</B></FONT></TD></TR>'
            f"{lines}</TABLE>>"
        )
        g.node(name, html)

    table("users", "users", [
        "id : UUID (PK)",
        "username : VARCHAR(32) UNIQUE",
        "username_normalized : VARCHAR(32)",
        "password_hash : TEXT",
        "first_name, last_name : VARCHAR",
        "district : VARCHAR(64)",
        "is_admin : BOOLEAN = false",
        "rating : INTEGER = 1200",
        "rated_games_count : INTEGER = 0",
        "rating_gain_blocked_until : TIMESTAMPTZ",
        "created_at, updated_at : TIMESTAMPTZ",
    ], pk_rows={"id"})

    table("refresh_tokens", "refresh_tokens", [
        "id : UUID (PK)",
        "user_id : UUID (FK users.id)",
        "token_hash : VARCHAR(128) UNIQUE",
        "expires_at : TIMESTAMPTZ",
        "revoked_at : TIMESTAMPTZ",
        "created_at : TIMESTAMPTZ",
    ], pk_rows={"id"})

    table("finished_games", "finished_games", [
        "id : UUID (PK)",
        "room_id : VARCHAR(8)",
        "room_type : VARCHAR(16)",
        "white_user_id : UUID (FK users.id)",
        "black_user_id : UUID (FK users.id)",
        "white_client_id, black_client_id : VARCHAR(64)",
        "white_is_anonymous, black_is_anonymous : BOOLEAN",
        "winner_color : VARCHAR(8)",
        "reason : VARCHAR(32)",
        "time_control, increment : INTEGER",
        "moves_count : INTEGER",
        "move_history : JSONB",
        "final_board : JSONB",
        "started_at, finished_at : TIMESTAMPTZ",
        "is_rated : BOOLEAN",
        "white_rating_delta, black_rating_delta : INTEGER",
        "white_gain_capped, black_gain_capped : BOOLEAN",
    ], pk_rows={"id"})

    table("presence_sessions", "presence_sessions", [
        "id : UUID (PK)",
        "client_id : VARCHAR(64)",
        "user_id : UUID (FK users.id)",
        "is_anonymous : BOOLEAN = true",
        "room_id : VARCHAR(8)",
        "connected_at : TIMESTAMPTZ",
        "disconnected_at : TIMESTAMPTZ",
        "last_seen_at : TIMESTAMPTZ",
    ], pk_rows={"id"})

    table("bug_reports", "bug_reports", [
        "id : UUID (PK)",
        "description : TEXT",
        "screenshot : BYTEA",
        "screenshot_mime : VARCHAR(64)",
        "user_id : UUID (FK users.id)",
        "client_id : VARCHAR(64)",
        "page_url, user_agent : VARCHAR(512)",
        "created_at : TIMESTAMPTZ",
    ], pk_rows={"id"})

    g.edge("refresh_tokens", "users", label="user_id → id\n(CASCADE)")
    g.edge("finished_games", "users", label="white_user_id → id\n(SET NULL)")
    g.edge("finished_games", "users", label="black_user_id → id\n(SET NULL)")
    g.edge("presence_sessions", "users", label="user_id → id\n(SET NULL)")
    g.edge("bug_reports", "users", label="user_id → id\n(SET NULL)")

    out = os.path.join(IMG_DIR, "er_diagram")
    g.render(out, cleanup=True)
    print("er_diagram.png готово")


# ---------------------------------------------------------------------------
# 3. Диаграмма состояний игровой сессии (сервер, backend/room_manager.py,
#    backend/session/v2/*, backend/timers.py, DISCONNECT_TIMEOUT)
# ---------------------------------------------------------------------------
def build_state_diagram():
    g = graphviz.Digraph("states", format="png")
    g.attr(rankdir="LR", fontname=GV_FONT, fontsize="20", labelloc="t",
            label="Диаграмма состояний игровой сессии (сервер)", bgcolor="white",
            nodesep="0.5", ranksep="0.9")
    g.attr("node", fontname=GV_FONT, fontsize="13", shape="box",
            style="rounded,filled", fillcolor="#ffe9b3", color="#4a3524")
    g.attr("edge", fontname=GV_FONT, fontsize="12", color="#4a3524")

    g.node("start", "", shape="circle", style="filled", fillcolor="black",
           width="0.15", fixedsize="true")
    g.node("waiting", "Зал ожидания\n(комната создана,\ngame_started=false)")
    g.node("active", "Партия идёт\n(ходы, таймеры,\nRedis game state)")
    g.node("chain", "Обязательное\nпродолжение взятия\n(position_for_mandatory_capture)")
    g.node("disc", "Ожидание\nреконнекта\n(DISCONNECT_TIMEOUT = 30 с)")
    g.node("over", "Партия завершена\n(мат по биям / сдача /\nничья / тайм-аут)")
    g.node("archived", "Архивирована\n(finished_games,\nобновлён рейтинг Elo)", shape="box",
           style="rounded,filled", fillcolor="#c9e8d0")
    g.node("rematch", "Реванш\nзапрошен")

    g.edge("start", "waiting")
    g.edge("waiting", "active", label="второй игрок\nподключился")
    g.edge("active", "chain", label="взятие,\nвозможно продолжение")
    g.edge("chain", "active", label="ход обработан,\nход передан")
    g.edge("active", "active", label="обычный ход\n(delta broadcast)")
    g.edge("active", "disc", label="потеря WS-соединения")
    g.edge("disc", "active", label="реконнект\n(sync/snapshot)")
    g.edge("disc", "over", label="таймаут истёк")
    g.edge("active", "over", label="взятие последнего бия /\nсдача / согласованная ничья /\n3-е повторение позиции /\n3 хода при двух биях")
    g.edge("over", "archived")
    g.edge("archived", "rematch", label="запрос реванша\nобоими игроками")
    g.edge("rematch", "waiting", label="новая комната")

    out = os.path.join(IMG_DIR, "state_diagram")
    g.render(out, cleanup=True)
    print("state_diagram.png готово")


# ---------------------------------------------------------------------------
# 4. Диаграмма последовательности одного хода (WS v2)
# ---------------------------------------------------------------------------
def build_sequence_diagram():
    actors = [
        "Клиент\n(белые)",
        "packages/\nshatra-rules (TS)",
        "FastAPI\n/ws/v2/",
        "game_engine\n(Python)",
        "Redis",
        "Клиент\n(чёрные)",
    ]
    n = len(actors)
    fig, ax = plt.subplots(figsize=(12, 9), dpi=200)
    ax.set_xlim(-0.5, n - 0.5)
    top = 0
    bottom = -15.5
    ax.set_ylim(bottom, top + 1)
    ax.axis("off")

    for i, name in enumerate(actors):
        ax.add_patch(FancyBboxPatch((i - 0.42, top - 0.55), 0.84, 0.9,
                                     boxstyle="round,pad=0.02",
                                     linewidth=1.3, edgecolor="#4a3524",
                                     facecolor="#ffe9b3"))
        ax.text(i, top - 0.1, name, ha="center", va="center", fontsize=11,
                fontfamily=FONT_SERIF)
        ax.plot([i, i], [top - 0.55, bottom], color="#999999", lw=1.1, ls=(0, (4, 3)))

    def arrow(y, i_from, i_to, text, dashed=False, self_call=False, color="#2e5339"):
        style = "->"
        ls = "dashed" if dashed else "solid"
        if self_call:
            ax.annotate("", xy=(i_from + 0.32, y - 0.35), xytext=(i_from, y),
                        arrowprops=dict(arrowstyle=style, color=color, lw=1.4,
                                        linestyle=ls,
                                        connectionstyle="arc3,rad=1.4"))
            ax.text(i_from + 0.42, y - 0.18, text, fontsize=9.3, va="center",
                     ha="left", fontfamily=FONT_SERIF, color="#222222")
        else:
            ax.annotate("", xy=(i_to, y), xytext=(i_from, y),
                        arrowprops=dict(arrowstyle=style, color=color, lw=1.5,
                                        linestyle=ls))
            xm = (i_from + i_to) / 2
            ax.text(xm, y + 0.16, text, fontsize=9.3, va="bottom", ha="center",
                     fontfamily=FONT_SERIF, color="#222222")

    y = -1.35
    step = 1.55
    arrow(y, 0, 1, "1. select(cell) → getHints(state, cell)\n(0 сетевых запросов)", self_call=False, color="#8a6d3b")
    y -= step
    ax.text(0, y + 0.25, "подсветка доступных\nходов локально", fontsize=8.7,
            ha="center", style="italic", fontfamily=FONT_SERIF, color="#555555")
    y -= step * 0.7
    arrow(y, 0, 2, '2. { v:2, t:"move", from, to, ply }', color="#2e5339")
    y -= step
    arrow(y, 2, 3, "3. logic.handle_event(\n  positions, from, to, mover_color)", color="#2e5339")
    y -= step
    arrow(y, 3, 2, "4. updated_positions, captured,\nmessage_code, chainCell", color="#2e5339")
    y -= step
    arrow(y, 2, 4, "5. set_game(room_id, state)\n(board, ply, clocks, TTL)", color="#1f4e8c")
    y -= step
    arrow(y, 2, 0, '6. { t:"move", ply, captured,\nclocks } (подтверждение)', color="#2e5339")
    y -= step
    arrow(y, 2, 5, '7. { t:"move", ... } (broadcast\nтот же delta сопернику)', color="#2e5339")
    y -= step
    ax.text(5, y + 0.25, "applyMoveDelta():\nанимация хода соперника", fontsize=8.7,
            ha="center", style="italic", fontfamily=FONT_SERIF, color="#555555")

    ax.set_title("Диаграмма последовательности: ход игрока (протокол WebSocket v2)",
                  fontsize=14, fontfamily=FONT_SERIF, pad=14)
    fig.tight_layout()
    fig.savefig(os.path.join(IMG_DIR, "sequence_move.png"), bbox_inches="tight")
    plt.close(fig)
    print("sequence_move.png готово")


# ---------------------------------------------------------------------------
# 5. Дерево структуры проекта (моноширинный текст в виде изображения)
# ---------------------------------------------------------------------------
TREE_TEXT = """Shatra/
├── main.py                    # точка входа FastAPI, роуты, lifespan
├── backend/                   # серверная логика (Python, FastAPI)
│   ├── ai.py, ai_client.py     # AI: локальный minimax / gRPC-клиент shatra-ai
│   ├── auth/                   # регистрация, JWT, refresh-токены
│   ├── rating/                 # elo.py, antifraud.py, service.py
│   ├── session/v2/              # обработчики WebSocket-протокола v2
│   ├── db/                      # SQLAlchemy-модели, сессии (asyncpg)
│   ├── admin/, bug_reports/     # админ-панель, баг-репорты
│   ├── observability/           # логирование, метрики, Sentry
│   └── room_manager.py, state.py, game_state.py, timers.py
├── game_engine/                # правила игры (Python) — authoritative
│   ├── pieces/ (shatra, biy, batyr)
│   ├── dictionaries.py, board.py, moves.py, hints.py, endgame.py
│   └── game_rules.md            # эталонная спецификация правил
├── crates/shatra-engine/        # правила + поиск (Rust), контракт-тесты
├── services/shatra-ai/          # AI-микросервис (Rust, gRPC, tonic/axum)
├── proto/shatra/ai/v1/          # protobuf-контракт AI-сервиса
├── frontend/                    # клиент (React 19 + Vite)
│   ├── src/board/, components/, game/, ws/v2/, i18n/, audio/
│   ├── packages/shatra-rules/    # локальный TS-движок правил (client rules)
│   ├── e2e/                      # Playwright end-to-end тесты
│   └── locales/ (ru.json, en.json, alt.json)
├── alembic/versions/            # 14 миграций схемы PostgreSQL
├── tests/                       # 1158 pytest-тестов (backend, rating, e2e-контракты)
├── docker/                      # nginx, prometheus, grafana, loki, promtail
├── docs/                        # ELO.md, DEPLOY.md, MONITORING.md, architecture/
├── scripts/                     # деплой, экспорт контрактов правил, туннель
├── docker-compose.yml, docker-compose.prod.yml
└── Dockerfile
"""


def build_tree_image():
    lines = TREE_TEXT.strip("\n").split("\n")
    fig_h = 0.28 * len(lines) + 0.6
    fig, ax = plt.subplots(figsize=(9.2, fig_h), dpi=220)
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    y0 = 1 - 0.5 / len(lines)
    dy = 1.0 / (len(lines) + 1)
    for i, line in enumerate(lines):
        ax.text(0.01, 1 - (i + 0.7) * dy, line, fontsize=10.3,
                fontfamily=FONT_MONO, va="top", ha="left")
    fig.savefig(os.path.join(IMG_DIR, "project_tree.png"),
                bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("project_tree.png готово")


if __name__ == "__main__":
    build_architecture_diagram()
    build_er_diagram()
    build_state_diagram()
    build_sequence_diagram()
    build_tree_image()
    print("Все схемы сгенерированы в", IMG_DIR)
