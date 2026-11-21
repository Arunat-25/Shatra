# ADR 0003 — Python AI engine on the free tier

- **Status:** Accepted
- **Date:** 2026-11-21

## Context

A Rust AI microservice (`services/shatra-ai`) exists and is faster, but it
needs its own container and `protoc` at build time. Free hosting cannot run an
extra always-on service.

## Decision

On the free tier, use the in-process Python AI engine (`AI_ENGINE=python`).
The Rust microservice remains in the repo for optional self-hosting / VPS
deployments where it can run alongside the app.

## Consequences

- One container, no extra infra on the free tier.
- AI move latency is higher than the Rust path; acceptable for the expected scale.
- Switching to Rust later is a config change (`AI_ENGINE=grpc` + service).
