use std::convert::Infallible;
use std::sync::Arc;

use axum::response::IntoResponse;
use axum::routing::get;
use axum::Router;

pub fn router() -> Router {
    Router::new().route("/health", get(health_handler))
}

async fn health_handler() -> impl IntoResponse {
    let body = serde_json::json!({
        "status": "ok",
        "service": "shatra-ai",
        "version": env!("CARGO_PKG_VERSION"),
    });
    (axum::http::StatusCode::OK, axum::Json(body))
}

// serde_json only for health — add to Cargo.toml