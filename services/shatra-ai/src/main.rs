mod grpc_impl;
mod health;
mod worker;

use std::net::SocketAddr;
use std::sync::Arc;

use tokio::sync::mpsc;
use tonic::transport::Server;
use tracing::info;

use crate::grpc_impl::AiServiceImpl;
use crate::worker::WorkerPool;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "shatra_ai=info,tower=warn".into()),
        )
        .init();

    let grpc_port: u16 = std::env::var("SHATRA_AI_GRPC_PORT")
        .ok()
        .and_then(|s| s.parse().ok())
        .unwrap_or(50051);
    let http_port: u16 = std::env::var("SHATRA_AI_HTTP_PORT")
        .ok()
        .and_then(|s| s.parse().ok())
        .unwrap_or(8081);
    let workers: usize = std::env::var("SHATRA_AI_WORKERS")
        .ok()
        .and_then(|s| s.parse().ok())
        .unwrap_or_else(|| std::thread::available_parallelism().map(|n| n.get()).unwrap_or(2));
    let queue_size: usize = std::env::var("SHATRA_AI_QUEUE_SIZE")
        .ok()
        .and_then(|s| s.parse().ok())
        .unwrap_or(64);

    let pool = Arc::new(WorkerPool::new(workers, queue_size));
    let ai_service = AiServiceImpl { pool: pool.clone() };

    let grpc_addr: SocketAddr = format!("0.0.0.0:{grpc_port}").parse()?;
    let http_addr: SocketAddr = format!("0.0.0.0:{http_port}").parse()?;

    info!(
        grpc_port,
        http_port,
        workers,
        queue_size,
        "starting shatra-ai"
    );

    let grpc_server = Server::builder()
        .add_service(
            grpc_impl::pb::ai_service_server::AiServiceServer::new(ai_service),
        )
        .serve(grpc_addr);

    let http_server = axum::serve(
        tokio::net::TcpListener::bind(http_addr).await?,
        health::router(),
    );

    tokio::select! {
        res = grpc_server => res?,
        res = http_server => res?,
    }

    Ok(())
}

// Re-export for grpc_impl
pub(crate) use worker::ComputeJob;
