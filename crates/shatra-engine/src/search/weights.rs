#[derive(Debug, Clone)]
pub struct EvalWeights {
    pub piece_shatra: i32,
    pub piece_batyr: i32,
    pub piece_biy: i32,
    pub biy_loss_penalty: i32,
    pub hanging_penalty: i32,
    pub promotion_bonus: i32,
    pub promotion_progress_weight: i32,
    pub position_scale: f64,
    pub forced_trap_bonus: i32,
    pub chain_capture_bonus: i32,
    pub sacrifice_setup_bonus: i32,
    pub even_trade_bonus: i32,
    pub side_file_shatra_bonus: i32,
    pub side_file_batyr_bonus: i32,
    pub batyr_anchor_bonus: i32,
    pub danger_zone_penalty: i32,
    pub fortress_entry_shatra_bonus: i32,
    pub fortress_entry_batyr_bonus: i32,
    pub fortress_entry_biy_bonus: i32,
    pub fortress_deploy_penalty: i32,
    pub fortress_intrusion_penalty: i32,
    pub biy_anchor_bonus: i32,
    pub crowded_main_field_threshold: i32,
}

impl Default for EvalWeights {
    fn default() -> Self {
        Self {
            piece_shatra: 100,
            piece_batyr: 350,
            piece_biy: 10_000,
            biy_loss_penalty: 800_000,
            hanging_penalty: 350,
            promotion_bonus: 2_500,
            promotion_progress_weight: 12,
            position_scale: 3.0,
            forced_trap_bonus: 15_000,
            chain_capture_bonus: 8_000,
            sacrifice_setup_bonus: 5_000,
            even_trade_bonus: 60,
            side_file_shatra_bonus: 60,
            side_file_batyr_bonus: 90,
            batyr_anchor_bonus: 110,
            danger_zone_penalty: 140,
            fortress_entry_shatra_bonus: 45,
            fortress_entry_batyr_bonus: 120,
            fortress_entry_biy_bonus: 2_500,
            fortress_deploy_penalty: 120_000,
            fortress_intrusion_penalty: 12_000,
            biy_anchor_bonus: 280,
            crowded_main_field_threshold: 20,
        }
    }
}

impl EvalWeights {
    pub fn piece_value(&self, pt: &str) -> i32 {
        match pt {
            "шатра" => self.piece_shatra,
            "батыр" => self.piece_batyr,
            "бий" => self.piece_biy,
            _ => 0,
        }
    }
}

pub fn default_weights() -> EvalWeights {
    EvalWeights::default()
}
