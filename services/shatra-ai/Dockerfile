# syntax=docker/dockerfile:1

FROM rust:1-bookworm AS builder
WORKDIR /app
COPY Cargo.toml ./
COPY crates/shatra-engine/Cargo.toml crates/shatra-engine/Cargo.toml
COPY crates/shatra-engine/src crates/shatra-engine/src
COPY services/shatra-ai/Cargo.toml services/shatra-ai/Cargo.toml
COPY services/shatra-ai/build.rs services/shatra-ai/build.rs
COPY services/shatra-ai/src services/shatra-ai/src
COPY proto proto

RUN cargo build --release -p shatra-ai

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*
COPY --from=builder /app/target/release/shatra-ai /usr/local/bin/shatra-ai
ENV SHATRA_AI_GRPC_PORT=50051
ENV SHATRA_AI_HTTP_PORT=8081
EXPOSE 50051 8081
HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
  CMD ["/usr/bin/curl", "-sf", "http://127.0.0.1:8081/health"]
ENTRYPOINT ["shatra-ai"]
