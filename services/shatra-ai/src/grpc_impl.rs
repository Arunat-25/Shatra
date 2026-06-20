use std::sync::Arc;

use shatra_engine::{MoveResult, TurnInput, TurnOutput};
use tonic::{Request, Response, Status};

use crate::worker::WorkerPool;

pub mod pb {
    tonic::include_proto!("shatra.ai.v1");
}

use pb::{ComputeAiTurnRequest, ComputeAiTurnResponse, HealthRequest, HealthResponse, MoveResult as PbMoveResult};

pub struct AiServiceImpl {
    pub pool: Arc<WorkerPool>,
}

#[tonic::async_trait]
impl pb::ai_service_server::AiService for AiServiceImpl {
    async fn compute_ai_turn(
        &self,
        request: Request<ComputeAiTurnRequest>,
    ) -> Result<Response<ComputeAiTurnResponse>, Status> {
        let req = request.into_inner();
        let input = proto_to_input(req)?;
        let output = self.pool.submit(input).await?;
        Ok(Response::new(output_to_proto(output)))
    }

    async fn health(
        &self,
        _request: Request<HealthRequest>,
    ) -> Result<Response<HealthResponse>, Status> {
        Ok(Response::new(HealthResponse {
            status: "ok".into(),
            version: env!("CARGO_PKG_VERSION").into(),
        }))
    }
}

fn proto_to_input(req: ComputeAiTurnRequest) -> Result<TurnInput, Status> {
    Ok(TurnInput {
        board: req.board,
        mover_color: req.mover_color,
        depth: req.depth,
        time_ms: req.time_ms,
        pending_batyr_captures: req.pending_batyr_captures,
        pending_mandatory_position: req.pending_mandatory_position,
        position_history: req.position_history,
        moves_with_two_biys: req.moves_with_two_biys,
    })
}

fn output_to_proto(output: TurnOutput) -> ComputeAiTurnResponse {
    let r = output.result;
    ComputeAiTurnResponse {
        result: Some(PbMoveResult {
            message_code: r.message_code,
            movers_color: r.movers_color,
            game_over: r.game_over,
            winner_color: r.winner_color,
            updated_positions: r.updated_positions,
            captured_positions: r.captured_positions,
            captured_pieces: r.captured_pieces,
            position_for_mandatory_capture: r.position_for_mandatory_capture,
            opportunity_pass_the_move: r.opportunity_pass_the_move,
            from_pos: r.from_pos,
            to_pos: r.to_pos,
        }),
        depth_reached: output.depth_reached,
        search_ms: output.search_ms,
        apply_ms: output.apply_ms,
    }
}

#[allow(dead_code)]
fn move_result_to_proto(r: MoveResult) -> PbMoveResult {
    PbMoveResult {
        message_code: r.message_code,
        movers_color: r.movers_color,
        game_over: r.game_over,
        winner_color: r.winner_color,
        updated_positions: r.updated_positions,
        captured_positions: r.captured_positions,
        captured_pieces: r.captured_pieces,
        position_for_mandatory_capture: r.position_for_mandatory_capture,
        opportunity_pass_the_move: r.opportunity_pass_the_move,
        from_pos: r.from_pos,
        to_pos: r.to_pos,
    }
}
