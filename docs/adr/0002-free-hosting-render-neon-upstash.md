# ADR 0002 — Free hosting on Render + Neon + Upstash

- **Status:** Accepted
- **Date:** 2026-11-21

## Context

The project has no budget for a server. Audience is initially tens to a few
hundred Russian-speaking players. Need a public playable URL without a paid VPS
or a credit card.

## Decision

Use free tiers only:
- Render (web service, Docker, free plan) for the app.
- Neon for PostgreSQL.
- Upstash for Redis.

Configuration is captured in `render.yaml`; manual steps in `docs/DEPLOY_RENDER.md`.
The Docker image is universal, so moving to a VPS later needs no code changes.

## Consequences

- Render free tier sleeps after ~15 min of inactivity (first visitor waits ~1 min).
- Rust AI microservice is not deployed on the free tier; `AI_ENGINE=python`.
- Data persists in Neon/Upstash across redeploys.
