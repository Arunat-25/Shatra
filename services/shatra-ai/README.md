# shatra-ai (Rust gRPC microservice)

AI turn computation: search + apply rules. Called by `shatra-app` when `AI_ENGINE=grpc`.

## Status

- **Infrastructure:** gRPC service, worker pool, Docker, Python client with fallback
- **Rules (Phase 2a):** `crates/shatra-engine` — contract tests (`cargo test -p shatra-engine`)
- **Search (Phase 2b):** full minimax port from `backend/ai.py` wired into `compute_ai_turn`

With `AI_ENGINE=grpc`, the service runs search + rules in Rust. Python fallback on gRPC errors.

## Local build

```bash
# Generate Python stubs (after proto changes)
python scripts/generate_grpc_stubs.py

# Rust service
cargo build --release -p shatra-ai

# Docker
docker compose build shatra-ai
docker compose up shatra-ai -d
```

## Environment

| Variable | Default | Description |
|----------|---------|-------------|
| `SHATRA_AI_WORKERS` | CPU count | Parallel compute threads |
| `SHATRA_AI_QUEUE_SIZE` | 64 | Bounded request queue |
| `SHATRA_AI_GRPC_PORT` | 50051 | gRPC listen port |
| `SHATRA_AI_HTTP_PORT` | 8081 | HTTP `/health` |

App-side (`.env`):

| Variable | Default | Description |
|----------|---------|-------------|
| `AI_ENGINE` | `python` | `python` or `grpc` |
| `AI_SERVICE_URL` | `shatra-ai:50051` | gRPC target |
| `AI_MOVE_TIME_MS` | 3000 | Search time budget (ms) |
| `AI_SHADOW_VERIFY` | `false` | Staging: compare grpc vs python apply |

## Rollout

1. Deploy with `AI_ENGINE=python` (shatra-ai runs but unused)
2. Staging: `AI_ENGINE=grpc` + `AI_SHADOW_VERIFY=true` after engine port
3. Prod: `AI_ENGINE=grpc`

Rollback: `AI_ENGINE=python`, restart `app` only.
