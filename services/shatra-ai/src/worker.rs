use std::sync::Arc;

use shatra_engine::{compute_ai_turn, EngineError, TurnInput, TurnOutput};
use tokio::sync::{mpsc, oneshot};
use tonic::Status;
use tracing::warn;

pub struct ComputeJob {
    pub input: TurnInput,
    pub respond_to: oneshot::Sender<Result<TurnOutput, Status>>,
}

pub struct WorkerPool {
    tx: mpsc::Sender<ComputeJob>,
}

impl WorkerPool {
    pub fn new(workers: usize, queue_size: usize) -> Self {
        let (tx, rx) = mpsc::channel(queue_size);
        let shared_rx = Arc::new(tokio::sync::Mutex::new(rx));
        for id in 0..workers {
            let rx = shared_rx.clone();
            tokio::spawn(async move {
                worker_loop(id, rx).await;
            });
        }
        Self { tx }
    }

    pub async fn submit(&self, input: TurnInput) -> Result<TurnOutput, Status> {
        let (resp_tx, resp_rx) = oneshot::channel();
        let job = ComputeJob {
            input,
            respond_to: resp_tx,
        };
        self.tx
            .send(job)
            .await
            .map_err(|_| Status::resource_exhausted("AI worker queue full"))?;
        resp_rx
            .await
            .map_err(|_| Status::internal("AI worker dropped response"))?
    }
}

async fn worker_loop(
    worker_id: usize,
    rx: Arc<tokio::sync::Mutex<mpsc::Receiver<ComputeJob>>>,
) {
    loop {
        let job = {
            let mut guard = rx.lock().await;
            guard.recv().await
        };
        let Some(job) = job else {
            break;
        };
        let result = run_compute(job.input);
        if job.respond_to.send(result).is_err() {
            warn!(worker_id, "client dropped before AI response");
        }
    }
}

fn run_compute(input: TurnInput) -> Result<TurnOutput, Status> {
    match compute_ai_turn(input) {
        Ok(out) => Ok(out),
        Err(EngineError::NotReady) => Err(Status::failed_precondition(
            "shatra-engine not ready: rules/search port in progress",
        )),
        Err(EngineError::NoLegalMove) => Err(Status::not_found("no legal move")),
        Err(EngineError::InvalidInput(msg)) => Err(Status::invalid_argument(msg)),
    }
}
