//! Minimal MCP (Model Context Protocol) server over a newline-delimited
//! JSON-RPC 2.0 stdio transport. Implements `initialize`, `tools/list`,
//! `tools/call` and `ping`.

use std::io::{BufRead, Write};

use serde_json::{json, Value};

use crate::data::Dataset;
use crate::queries::{self, MatchQuery, PlayerQuery, Venue};

pub const PROTOCOL_VERSION: &str = "2024-11-05";

/// Run the stdio server loop, reading requests from `reader` and writing
/// responses to `writer`. Each message is a single line of JSON.
pub fn serve(ds: &Dataset, reader: impl BufRead, mut writer: impl Write) -> std::io::Result<()> {
    for line in reader.lines() {
        let line = line?;
        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }
        let request: Value = match serde_json::from_str(trimmed) {
            Ok(v) => v,
            Err(e) => {
                let resp = error_response(Value::Null, -32700, &format!("Parse error: {e}"));
                writeln!(writer, "{resp}")?;
                writer.flush()?;
                continue;
            }
        };

        if let Some(resp) = handle_request(ds, &request) {
            writeln!(writer, "{resp}")?;
            writer.flush()?;
        }
    }
    Ok(())
}

/// Handle one JSON-RPC request. Returns `None` for notifications (no `id`),
/// which must not produce a response.
pub fn handle_request(ds: &Dataset, req: &Value) -> Option<Value> {
    let method = req.get("method").and_then(Value::as_str).unwrap_or("");
    let id = req.get("id").cloned();
    let is_notification = id.is_none();

    match method {
        "initialize" => Some(success(
            id.unwrap_or(Value::Null),
            json!({
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": { "tools": {} },
                "serverInfo": {
                    "name": "brazilian-soccer-mcp",
                    "version": env!("CARGO_PKG_VERSION"),
                },
            }),
        )),
        "notifications/initialized" | "initialized" => None,
        "ping" => Some(success(id.unwrap_or(Value::Null), json!({}))),
        "tools/list" => Some(success(id.unwrap_or(Value::Null), json!({ "tools": tool_definitions() }))),
        "tools/call" => {
            let id = id.unwrap_or(Value::Null);
            let params = req.get("params").cloned().unwrap_or(Value::Null);
            let name = params.get("name").and_then(Value::as_str).unwrap_or("");
            let args = params.get("arguments").cloned().unwrap_or_else(|| json!({}));
            match dispatch_tool(ds, name, &args) {
                Ok(text) => Some(success(
                    id,
                    json!({ "content": [{ "type": "text", "text": text }] }),
                )),
                Err(msg) => Some(success(
                    id,
                    json!({
                        "content": [{ "type": "text", "text": msg }],
                        "isError": true,
                    }),
                )),
            }
        }
        _ => {
            if is_notification {
                None
            } else {
                Some(error_response(
                    id.unwrap_or(Value::Null),
                    -32601,
                    &format!("Method not found: {method}"),
                ))
            }
        }
    }
}

fn success(id: Value, result: Value) -> Value {
    json!({ "jsonrpc": "2.0", "id": id, "result": result })
}

fn error_response(id: Value, code: i64, message: &str) -> Value {
    json!({ "jsonrpc": "2.0", "id": id, "error": { "code": code, "message": message } })
}

// ---------------------------------------------------------------------------
// Argument helpers
// ---------------------------------------------------------------------------

fn arg_str<'a>(args: &'a Value, key: &str) -> Option<&'a str> {
    args.get(key).and_then(Value::as_str).filter(|s| !s.trim().is_empty())
}

fn arg_i32(args: &Value, key: &str) -> Option<i32> {
    match args.get(key) {
        Some(Value::Number(n)) => n.as_i64().map(|v| v as i32),
        Some(Value::String(s)) => s.trim().parse::<i32>().ok(),
        _ => None,
    }
}

fn arg_usize(args: &Value, key: &str) -> usize {
    match args.get(key) {
        Some(Value::Number(n)) => n.as_u64().unwrap_or(0) as usize,
        Some(Value::String(s)) => s.trim().parse::<usize>().unwrap_or(0),
        _ => 0,
    }
}

// ---------------------------------------------------------------------------
// Tool dispatch
// ---------------------------------------------------------------------------

/// Execute a named tool. Public so it can be exercised directly in tests and
/// from the CLI without going through JSON-RPC framing.
pub fn dispatch_tool(ds: &Dataset, name: &str, args: &Value) -> Result<String, String> {
    match name {
        "search_matches" => Ok(queries::search_matches(
            ds,
            &MatchQuery {
                team: arg_str(args, "team"),
                team2: arg_str(args, "team2"),
                competition: arg_str(args, "competition"),
                season: arg_i32(args, "season"),
                date_from: arg_str(args, "date_from"),
                date_to: arg_str(args, "date_to"),
                limit: arg_usize(args, "limit"),
            },
        )),
        "head_to_head" => {
            let t1 = arg_str(args, "team1").ok_or("`team1` is required")?;
            let t2 = arg_str(args, "team2").ok_or("`team2` is required")?;
            Ok(queries::head_to_head(
                ds,
                t1,
                t2,
                arg_str(args, "competition"),
                arg_i32(args, "season"),
            ))
        }
        "team_stats" => {
            let team = arg_str(args, "team").ok_or("`team` is required")?;
            let venue = match arg_str(args, "venue").map(|s| s.to_lowercase()) {
                Some(ref v) if v == "home" => Venue::Home,
                Some(ref v) if v == "away" => Venue::Away,
                _ => Venue::All,
            };
            Ok(queries::team_stats(
                ds,
                team,
                arg_i32(args, "season"),
                arg_str(args, "competition"),
                venue,
            ))
        }
        "standings" => {
            let season = arg_i32(args, "season").ok_or("`season` is required")?;
            Ok(queries::standings(ds, season, arg_str(args, "competition")))
        }
        "competition_stats" => Ok(queries::competition_stats(
            ds,
            arg_str(args, "competition"),
            arg_i32(args, "season"),
        )),
        "search_players" => Ok(queries::search_players(
            ds,
            &PlayerQuery {
                name: arg_str(args, "name"),
                nationality: arg_str(args, "nationality"),
                club: arg_str(args, "club"),
                position: arg_str(args, "position"),
                min_overall: arg_i32(args, "min_overall"),
                limit: arg_usize(args, "limit"),
            },
        )),
        "top_players" => Ok(queries::top_players(
            ds,
            arg_str(args, "nationality"),
            arg_str(args, "club"),
            arg_str(args, "position"),
            arg_usize(args, "limit"),
        )),
        "list_datasets" => Ok(queries::list_datasets(ds)),
        other => Err(format!("Unknown tool: {other}")),
    }
}

// ---------------------------------------------------------------------------
// Tool schema definitions
// ---------------------------------------------------------------------------

fn str_prop(desc: &str) -> Value {
    json!({ "type": "string", "description": desc })
}
fn int_prop(desc: &str) -> Value {
    json!({ "type": "integer", "description": desc })
}

pub fn tool_definitions() -> Vec<Value> {
    vec![
        json!({
            "name": "search_matches",
            "description": "Search matches by team, opponent, competition, season and/or date range. \
                When two teams are given, includes a head-to-head summary. Competitions: Brasileirão, \
                Copa do Brasil, Copa Libertadores.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team": str_prop("Team name (matches home or away). Variants like 'Flamengo' or 'Flamengo-RJ' work."),
                    "team2": str_prop("Optional second team to find matches between the two."),
                    "competition": str_prop("Competition filter, e.g. 'Brasileirão', 'Copa do Brasil', 'Libertadores'."),
                    "season": int_prop("Season year, e.g. 2019."),
                    "date_from": str_prop("Earliest match date, ISO YYYY-MM-DD."),
                    "date_to": str_prop("Latest match date, ISO YYYY-MM-DD."),
                    "limit": int_prop("Max matches to list (default 25)."),
                },
            },
        }),
        json!({
            "name": "head_to_head",
            "description": "Head-to-head record and recent matches between two teams.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team1": str_prop("First team."),
                    "team2": str_prop("Second team."),
                    "competition": str_prop("Optional competition filter."),
                    "season": int_prop("Optional season filter."),
                },
                "required": ["team1", "team2"],
            },
        }),
        json!({
            "name": "team_stats",
            "description": "Win/draw/loss record, goals for/against and win rate for a team, \
                optionally filtered by season, competition and venue (home/away/all).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team": str_prop("Team name."),
                    "season": int_prop("Optional season year."),
                    "competition": str_prop("Optional competition filter."),
                    "venue": json!({ "type": "string", "enum": ["all", "home", "away"], "description": "Restrict to home or away matches (default all)." }),
                },
                "required": ["team"],
            },
        }),
        json!({
            "name": "standings",
            "description": "Final league standings for a season, calculated from match results \
                (3 points per win, 1 per draw). Defaults to the Brasileirão.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "season": int_prop("Season year, e.g. 2019."),
                    "competition": str_prop("Competition (default 'Brasileirão')."),
                },
                "required": ["season"],
            },
        }),
        json!({
            "name": "competition_stats",
            "description": "Aggregate statistics: average goals per match, home/draw/away win rates, \
                biggest victories and top scoring teams. Filter by competition and/or season.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "competition": str_prop("Optional competition filter."),
                    "season": int_prop("Optional season year."),
                },
            },
        }),
        json!({
            "name": "search_players",
            "description": "Search FIFA player data by name, nationality, club, position and minimum \
                overall rating. Results are sorted by overall rating (highest first).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": str_prop("Player name substring, e.g. 'Neymar'."),
                    "nationality": str_prop("Exact nationality, e.g. 'Brazil'."),
                    "club": str_prop("Club name substring, e.g. 'Flamengo'."),
                    "position": str_prop("Exact position code, e.g. 'GK', 'ST', 'CB'."),
                    "min_overall": int_prop("Minimum FIFA overall rating."),
                    "limit": int_prop("Max players to list (default 20)."),
                },
            },
        }),
        json!({
            "name": "top_players",
            "description": "Highest-rated players for a given nationality, club and/or position. \
                When a nationality is supplied, also returns a per-club breakdown with average ratings.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "nationality": str_prop("Nationality, e.g. 'Brazil'."),
                    "club": str_prop("Club name substring."),
                    "position": str_prop("Position code."),
                    "limit": int_prop("Max players to list (default 20)."),
                },
            },
        }),
        json!({
            "name": "list_datasets",
            "description": "Summary of loaded datasets and row counts (data coverage).",
            "inputSchema": { "type": "object", "properties": {} },
        }),
    ]
}
