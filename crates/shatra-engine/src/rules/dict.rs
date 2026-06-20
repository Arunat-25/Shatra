use std::collections::HashMap;
use std::sync::OnceLock;

use serde_json::Value;

pub type Cells = HashMap<i32, Option<String>>;
pub type IntListMap = HashMap<i32, Vec<i32>>;
pub type CaptureMap = HashMap<i32, HashMap<i32, i32>>;
pub type BatyrDirs = HashMap<i32, Vec<Vec<i32>>>;

pub struct Dicts {
    pub black_shatra_moves: IntListMap,
    pub white_shatra_moves: IntListMap,
    pub black_biy_moves: IntListMap,
    pub white_biy_moves: IntListMap,
    pub shatra_biy_captures: CaptureMap,
    pub batyr_dirs: BatyrDirs,
}

static DICTS: OnceLock<Dicts> = OnceLock::new();

pub fn dicts() -> &'static Dicts {
    DICTS.get_or_init(load_dicts)
}

fn int_keys(value: &Value) -> Value {
    match value {
        Value::Object(map) => {
            let mut out = serde_json::Map::new();
            for (k, v) in map {
                let nk = if k.chars().all(|c| c.is_ascii_digit()) {
                    k.parse::<i32>().unwrap_or(0).to_string()
                } else {
                    k.clone()
                };
                out.insert(nk, int_keys(v));
            }
            Value::Object(out)
        }
        Value::Array(arr) => Value::Array(arr.iter().map(int_keys).collect()),
        other => other.clone(),
    }
}

fn parse_int_list_map(v: &Value) -> IntListMap {
    let mut out = IntListMap::new();
    if let Value::Object(map) = v {
        for (k, val) in map {
            let key: i32 = k.parse().unwrap_or(0);
            let list: Vec<i32> = val
                .as_array()
                .map(|a| a.iter().filter_map(|x| x.as_i64().map(|n| n as i32)).collect())
                .unwrap_or_default();
            out.insert(key, list);
        }
    }
    out
}

fn parse_capture_map(v: &Value) -> CaptureMap {
    let mut out = CaptureMap::new();
    if let Value::Object(map) = v {
        for (from_k, targets) in map {
            let from: i32 = from_k.parse().unwrap_or(0);
            let mut inner = HashMap::new();
            if let Value::Object(tmap) = targets {
                for (to_k, enemy) in tmap {
                    let to: i32 = to_k.parse().unwrap_or(0);
                    let e: i32 = enemy.as_i64().unwrap_or(0) as i32;
                    inner.insert(to, e);
                }
            }
            out.insert(from, inner);
        }
    }
    out
}

fn parse_batyr_dirs(v: &Value) -> BatyrDirs {
    let mut out = BatyrDirs::new();
    if let Value::Object(map) = v {
        for (k, val) in map {
            let key: i32 = k.parse().unwrap_or(0);
            let dirs: Vec<Vec<i32>> = val
                .as_array()
                .map(|outer| {
                    outer
                        .iter()
                        .map(|dir| {
                            dir.as_array()
                                .map(|a| {
                                    a.iter()
                                        .filter_map(|x| x.as_i64().map(|n| n as i32))
                                        .collect()
                                })
                                .unwrap_or_default()
                        })
                        .collect()
                })
                .unwrap_or_default();
            out.insert(key, dirs);
        }
    }
    out
}

fn load_dicts() -> Dicts {
    let raw: Value = serde_json::from_str(include_str!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../frontend/packages/shatra-rules/src/dictionaries.json"
    )))
    .expect("dictionaries.json parse");
    let d = int_keys(&raw);
    let obj = d.as_object().expect("dict root object");
    Dicts {
        black_shatra_moves: parse_int_list_map(obj.get("black_shatra_possible_moves").unwrap()),
        white_shatra_moves: parse_int_list_map(obj.get("white_shatra_possible_moves").unwrap()),
        black_biy_moves: parse_int_list_map(obj.get("black_biy_possible_moves").unwrap()),
        white_biy_moves: parse_int_list_map(obj.get("white_biy_possible_moves").unwrap()),
        shatra_biy_captures: parse_capture_map(obj.get("shatra_and_biy_possible_captures").unwrap()),
        batyr_dirs: parse_batyr_dirs(obj.get("batyr_moves_and_captures").unwrap()),
    }
}

pub fn normalize_cells(cells: &HashMap<i32, String>) -> Cells {
    cells.iter().map(|(k, v)| (*k, Some(v.clone()))).collect()
}

pub fn normalize_cells_opt(cells: &HashMap<i32, Option<String>>) -> Cells {
    cells
        .iter()
        .map(|(k, v)| (*k, v.clone()))
        .collect()
}
