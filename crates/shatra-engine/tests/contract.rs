use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;

use serde_json::Value;
use shatra_engine::rules::dict::Cells;
use shatra_engine::rules::hints::get_hints;
use shatra_engine::rules::moves::process_move;

fn contract_path() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../tests/fixtures/rules/contract.json")
}

fn parse_board(value: &Value) -> Cells {
    let mut cells = Cells::new();
    if let Value::Object(map) = value {
        for (k, v) in map {
            let key: i32 = k.parse().expect("board key");
            let cell = match v {
                Value::Null => None,
                Value::String(s) => Some(s.clone()),
                other => panic!("unexpected cell value: {other:?}"),
            };
            cells.insert(key, cell);
        }
    }
    cells
}

fn sorted_i32(v: &[i32]) -> Vec<i32> {
    let mut out = v.to_vec();
    out.sort_unstable();
    out
}

fn str_or_empty(v: Option<&Value>) -> String {
    v.and_then(|x| x.as_str()).unwrap_or("").to_string()
}

#[test]
fn rules_contract_matches_engine() {
    let path = contract_path();
    assert!(path.is_file(), "missing contract at {}", path.display());
    let raw = fs::read_to_string(&path).expect("read contract");
    let data: Value = serde_json::from_str(&raw).expect("parse contract");
    let cases = data["cases"].as_array().expect("cases array");

    for case in cases {
        let id = case["id"].as_str().unwrap_or("?");
        let action = &case["action"];
        let expect = &case["expect"];
        let action_type = action["type"].as_str().expect("action type");

        match action_type {
            "hints" => {
                let board = parse_board(&action["board"]);
                let mover = action["mover_color"].as_str().unwrap();
                let from = action["from_cell"].as_i64().unwrap() as i32;
                let chain = action
                    .get("chain_capture_cell")
                    .and_then(|v| v.as_i64())
                    .map(|n| n as i32);
                let batyr_caps: Vec<i32> = action
                    .get("batyr_captured_this_turn")
                    .and_then(|v| v.as_array())
                    .map(|arr| arr.iter().filter_map(|x| x.as_i64().map(|n| n as i32)).collect())
                    .unwrap_or_default();

                let result = get_hints(&board, mover, from, &batyr_caps, chain);
                assert_eq!(
                    sorted_i32(&result.essential_positions),
                    sorted_i32(
                        &expect["essential_positions"]
                            .as_array()
                            .unwrap()
                            .iter()
                            .map(|x| x.as_i64().unwrap() as i32)
                            .collect::<Vec<_>>()
                    ),
                    "case {id}: essential_positions"
                );
                assert_eq!(
                    result.message_code,
                    str_or_empty(expect.get("message_code")),
                    "case {id}: message_code"
                );
            }
            "move" => {
                let board = parse_board(&action["board"]);
                let mover = action["mover_color"].as_str().unwrap();
                let from = action["from_cell"].as_i64().unwrap() as i32;
                let to = action["to_cell"].as_i64().unwrap() as i32;
                let chain = action
                    .get("chain_capture_cell")
                    .and_then(|v| {
                        if v.is_null() {
                            None
                        } else {
                            v.as_i64().map(|n| n as i32)
                        }
                    });
                let batyr_caps: Vec<i32> = action
                    .get("batyr_captured_this_turn")
                    .and_then(|v| v.as_array())
                    .map(|arr| arr.iter().filter_map(|x| x.as_i64().map(|n| n as i32)).collect())
                    .unwrap_or_default();

                let mut history = HashMap::new();
                let result = process_move(
                    &board,
                    mover,
                    from,
                    to,
                    chain,
                    &batyr_caps,
                    &mut history,
                    0,
                );

                assert_eq!(
                    result.message_code,
                    str_or_empty(expect.get("message_code")),
                    "case {id}: message_code"
                );
                if let Some(expected) = expect.get("movers_color") {
                    let exp = if expected.is_null() {
                        None
                    } else {
                        Some(expected.as_str().unwrap().to_string())
                    };
                    assert_eq!(result.movers_color, exp, "case {id}: movers_color");
                }
                if let Some(expected) = expect.get("position_for_mandatory_capture") {
                    let exp = if expected.is_null() {
                        None
                    } else {
                        Some(expected.as_i64().unwrap() as i32)
                    };
                    assert_eq!(
                        result.position_for_mandatory_capture, exp,
                        "case {id}: position_for_mandatory_capture"
                    );
                }
                let exp_caps: Vec<i32> = expect
                    .get("captured_positions")
                    .and_then(|v| v.as_array())
                    .map(|arr| arr.iter().map(|x| x.as_i64().unwrap() as i32).collect())
                    .unwrap_or_default();
                assert_eq!(
                    sorted_i32(&result.captured_positions),
                    sorted_i32(&exp_caps),
                    "case {id}: captured_positions"
                );
                let exp_pieces: Vec<i32> = expect
                    .get("captured_pieces")
                    .and_then(|v| v.as_array())
                    .map(|arr| arr.iter().map(|x| x.as_i64().unwrap() as i32).collect())
                    .unwrap_or_default();
                assert_eq!(result.captured_pieces, exp_pieces, "case {id}: captured_pieces");
                let exp_pass = expect
                    .get("opportunity_pass_the_move")
                    .and_then(|v| v.as_bool())
                    .unwrap_or(false);
                assert_eq!(
                    result.opportunity_pass_the_move, exp_pass,
                    "case {id}: opportunity_pass_the_move"
                );

                if let Some(desk) = expect.get("desk") {
                    let updated = result.updated_positions.as_ref().expect("updated_positions");
                    let expected = parse_board(desk);
                    for key in 1..=62 {
                        assert_eq!(
                            updated.get(&key).cloned().flatten(),
                            expected.get(&key).cloned().flatten(),
                            "case {id}: desk cell {key}"
                        );
                    }
                }
            }
            other => panic!("unknown contract action type: {other}"),
        }
    }
}
