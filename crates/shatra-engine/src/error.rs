use thiserror::Error;

#[derive(Debug, Error)]
pub enum EngineError {
    #[error("shatra-engine not ready: rules/search port in progress")]
    NotReady,
    #[error("no legal move")]
    NoLegalMove,
    #[error("invalid input: {0}")]
    InvalidInput(String),
}
