mod data;
mod mcp;
mod tools;

use anyhow::Result;
use mcp::{JsonRpcRequest, JsonRpcResponse};
use serde_json::{json, Value};
use std::io::{self, BufRead, Write};
use std::path::Path;

fn get_string(params: &Value, key: &str) -> Option<String> {
    params.get(key).and_then(|v| v.as_str()).map(|s| s.to_string())
}

fn get_i32(params: &Value, key: &str) -> Option<i32> {
    params.get(key).and_then(|v| v.as_i64()).map(|n| n as i32)
}

fn get_usize(params: &Value, key: &str, default: usize) -> usize {
    params
        .get(key)
        .and_then(|v| v.as_u64())
        .map(|n| n as usize)
        .unwrap_or(default)
}

fn handle_tool_call(db: &data::Database, name: &str, args: &Value) -> Result<Value, String> {
    let empty = json!({});
    let params = if args.is_object() { args } else { &empty };

    let text = match name {
        "search_matches" => tools::search_matches(
            db,
            get_string(params, "team").as_deref(),
            get_string(params, "team2").as_deref(),
            get_string(params, "competition").as_deref(),
            get_i32(params, "season"),
            get_string(params, "date_from").as_deref(),
            get_string(params, "date_to").as_deref(),
            get_usize(params, "limit", 20),
        ),
        "team_stats" => {
            let team = get_string(params, "team").ok_or("Missing required parameter: team")?;
            tools::team_stats(
                db,
                &team,
                get_string(params, "competition").as_deref(),
                get_i32(params, "season"),
            )
        }
        "head_to_head" => {
            let team1 = get_string(params, "team1").ok_or("Missing required parameter: team1")?;
            let team2 = get_string(params, "team2").ok_or("Missing required parameter: team2")?;
            tools::head_to_head(
                db,
                &team1,
                &team2,
                get_string(params, "competition").as_deref(),
                get_i32(params, "season"),
                get_usize(params, "limit", 10),
            )
        }
        "search_players" => tools::search_players(
            db,
            get_string(params, "name").as_deref(),
            get_string(params, "nationality").as_deref(),
            get_string(params, "club").as_deref(),
            get_string(params, "position").as_deref(),
            get_i32(params, "min_overall"),
            get_usize(params, "max_results", 20),
        ),
        "season_standings" => {
            let competition =
                get_string(params, "competition").ok_or("Missing required parameter: competition")?;
            let season = get_i32(params, "season").ok_or("Missing required parameter: season")?;
            tools::season_standings(db, &competition, season, get_usize(params, "limit", 20))
        }
        "biggest_wins" => tools::biggest_wins(
            db,
            get_string(params, "competition").as_deref(),
            get_i32(params, "season"),
            get_usize(params, "limit", 10),
        ),
        "competition_stats" => tools::competition_stats(
            db,
            get_string(params, "competition").as_deref(),
            get_i32(params, "season"),
        ),
        "top_scoring_teams" => tools::top_scoring_teams(
            db,
            get_string(params, "competition").as_deref(),
            get_i32(params, "season"),
            get_usize(params, "limit", 10),
        ),
        _ => return Err(format!("Unknown tool: {}", name)),
    };

    Ok(json!({
        "content": [{"type": "text", "text": text}]
    }))
}

fn process_request(db: &data::Database, request: &JsonRpcRequest) -> Option<JsonRpcResponse> {
    let id = request.id.clone();

    match request.method.as_str() {
        "initialize" => Some(JsonRpcResponse::success(id, mcp::server_info())),

        "notifications/initialized" | "initialized" => None, // notification, no response

        "tools/list" => Some(JsonRpcResponse::success(
            id,
            json!({ "tools": mcp::tool_definitions() }),
        )),

        "tools/call" => {
            let params = request.params.as_ref().cloned().unwrap_or(json!({}));
            let name = params.get("name").and_then(|v| v.as_str()).unwrap_or("");
            let args = params.get("arguments").cloned().unwrap_or(json!({}));

            match handle_tool_call(db, name, &args) {
                Ok(result) => Some(JsonRpcResponse::success(id, result)),
                Err(e) => Some(JsonRpcResponse::error(id, -32602, e)),
            }
        }

        "ping" => Some(JsonRpcResponse::success(id, json!({}))),

        _ => Some(JsonRpcResponse::error(
            id,
            -32601,
            format!("Method not found: {}", request.method),
        )),
    }
}

fn find_data_dir() -> std::path::PathBuf {
    // Try relative to binary location first, then current dir
    let candidates = [
        Path::new("data/kaggle"),
        Path::new("../data/kaggle"),
        Path::new("../../data/kaggle"),
    ];
    for c in &candidates {
        if c.exists() {
            return c.to_path_buf();
        }
    }
    // Fall back to env var or default
    std::env::var("SOCCER_DATA_DIR")
        .map(|s| std::path::PathBuf::from(s))
        .unwrap_or_else(|_| Path::new("data/kaggle").to_path_buf())
}

fn main() -> Result<()> {
    let data_dir = find_data_dir();

    // Load all data upfront
    eprintln!("Loading data from {}...", data_dir.display());
    let db = data::Database::load(&data_dir)?;
    eprintln!(
        "Loaded {} matches and {} players.",
        db.matches.len(),
        db.players.len()
    );

    let stdin = io::stdin();
    let stdout = io::stdout();
    let mut out = stdout.lock();

    for line in stdin.lock().lines() {
        let line = line?;
        let line = line.trim();
        if line.is_empty() {
            continue;
        }

        let request: JsonRpcRequest = match serde_json::from_str(line) {
            Ok(r) => r,
            Err(e) => {
                let resp = JsonRpcResponse::error(None, -32700, format!("Parse error: {}", e));
                writeln!(out, "{}", serde_json::to_string(&resp)?)?;
                out.flush()?;
                continue;
            }
        };

        if let Some(response) = process_request(&db, &request) {
            writeln!(out, "{}", serde_json::to_string(&response)?)?;
            out.flush()?;
        }
    }

    Ok(())
}
