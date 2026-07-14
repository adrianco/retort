//! ============================================================================
//! Module: mcp
//! Project: Brazilian Soccer MCP Server (Rust)
//!
//! Context:
//!   Implements the Model Context Protocol server over a line-delimited
//!   JSON-RPC 2.0 stdio transport (the standard MCP stdio framing: one JSON
//!   message per line). It advertises a set of tools — one per query category
//!   in the specification — and dispatches `tools/call` requests to the `Store`
//!   query engine, returning the formatted text produced by `format`.
//!
//!   Protocol surface handled:
//!     - initialize                -> server capabilities + info
//!     - notifications/initialized -> ignored (no response, per JSON-RPC)
//!     - ping                      -> empty result
//!     - tools/list                -> the tool catalogue with JSON Schemas
//!     - tools/call                -> run a tool, return text content
//!
//!   The `dispatch_tool` function is deliberately separate from the I/O loop so
//!   the BDD tests can exercise every tool end-to-end without spawning a
//!   process or touching stdin/stdout.
//! ============================================================================

use crate::format;
use crate::store::{Store, Venue};
use serde_json::{json, Value};
use std::io::{BufRead, Write};

pub const SERVER_NAME: &str = "brazilian-soccer-mcp";
pub const SERVER_VERSION: &str = "1.0.0";
pub const PROTOCOL_VERSION: &str = "2024-11-05";

/// Build the static tool catalogue (name, description, input schema).
pub fn tool_catalogue() -> Value {
    json!([
        {
            "name": "search_matches",
            "description": "Find matches by team, opponent, competition, season and/or date range. Returns date, score and competition for each match (sorted newest first).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team": {"type": "string", "description": "Team name (home or away). Suffixes like '-SP' are handled automatically."},
                    "opponent": {"type": "string", "description": "If set, only matches featuring both team and opponent."},
                    "competition": {"type": "string", "description": "Brasileirão, Copa do Brasil or Libertadores."},
                    "season": {"type": "integer", "description": "Year of the season, e.g. 2023."},
                    "date_from": {"type": "string", "description": "Inclusive lower bound, YYYY-MM-DD."},
                    "date_to": {"type": "string", "description": "Inclusive upper bound, YYYY-MM-DD."},
                    "limit": {"type": "integer", "description": "Max results (default 25)."}
                }
            }
        },
        {
            "name": "head_to_head",
            "description": "Head-to-head record (wins/draws/goals and recent matches) between two teams across all competitions.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_a": {"type": "string"},
                    "team_b": {"type": "string"}
                },
                "required": ["team_a", "team_b"]
            }
        },
        {
            "name": "team_stats",
            "description": "Aggregated record for a team (matches, W/D/L, goals for/against, win rate), optionally filtered by season, competition and venue.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team": {"type": "string"},
                    "season": {"type": "integer"},
                    "competition": {"type": "string"},
                    "venue": {"type": "string", "enum": ["home", "away", "any"], "description": "Default 'any'."}
                },
                "required": ["team"]
            }
        },
        {
            "name": "search_players",
            "description": "Search the FIFA player database by name, nationality, club, position and/or minimum overall rating. Sorted by rating descending.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "nationality": {"type": "string", "description": "e.g. 'Brazil'."},
                    "club": {"type": "string"},
                    "position": {"type": "string", "description": "e.g. 'ST', 'GK', 'LW'."},
                    "min_overall": {"type": "integer"},
                    "limit": {"type": "integer", "description": "Max results (default 25)."}
                }
            }
        },
        {
            "name": "standings",
            "description": "Compute final league standings for a competition and season from match results (3pts win / 1 draw).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "season": {"type": "integer"},
                    "competition": {"type": "string", "description": "Default Brasileirão."}
                },
                "required": ["season"]
            }
        },
        {
            "name": "biggest_wins",
            "description": "List the biggest victories (by goal margin), optionally filtered by competition and season.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "competition": {"type": "string"},
                    "season": {"type": "integer"},
                    "limit": {"type": "integer", "description": "Max results (default 10)."}
                }
            }
        },
        {
            "name": "average_goals",
            "description": "Aggregate goal statistics (avg goals/match, home/away win rates) over matches, optionally filtered by competition and season.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "competition": {"type": "string"},
                    "season": {"type": "integer"}
                }
            }
        },
        {
            "name": "data_summary",
            "description": "Overview of all loaded data: total matches and players, seasons covered, matches per source file.",
            "inputSchema": {"type": "object", "properties": {}}
        }
    ])
}

fn str_arg<'a>(args: &'a Value, key: &str) -> Option<&'a str> {
    args.get(key).and_then(|v| v.as_str()).filter(|s| !s.is_empty())
}

fn int_arg(args: &Value, key: &str) -> Option<i64> {
    args.get(key).and_then(|v| {
        v.as_i64()
            .or_else(|| v.as_str().and_then(|s| s.trim().parse::<i64>().ok()))
    })
}

/// Execute a single tool by name with the given JSON arguments. Returns the
/// formatted text result, or an error string. Exposed for testing.
pub fn dispatch_tool(store: &Store, name: &str, args: &Value) -> Result<String, String> {
    match name {
        "search_matches" => {
            let limit = int_arg(args, "limit").unwrap_or(25).max(0) as usize;
            let list = store.search_matches(
                str_arg(args, "team"),
                str_arg(args, "opponent"),
                str_arg(args, "competition"),
                int_arg(args, "season").map(|v| v as i32),
                str_arg(args, "date_from"),
                str_arg(args, "date_to"),
                limit,
            );
            let title = build_match_title(args);
            Ok(format::matches(&title, &list))
        }
        "head_to_head" => {
            let a = str_arg(args, "team_a").ok_or("team_a is required")?;
            let b = str_arg(args, "team_b").ok_or("team_b is required")?;
            Ok(format::head_to_head(&store.head_to_head(a, b)))
        }
        "team_stats" => {
            let team = str_arg(args, "team").ok_or("team is required")?;
            let season = int_arg(args, "season").map(|v| v as i32);
            let comp = str_arg(args, "competition");
            let venue = match str_arg(args, "venue").map(|s| s.to_lowercase()).as_deref() {
                Some("home") => Venue::Home,
                Some("away") => Venue::Away,
                _ => Venue::Any,
            };
            let rec = store.team_stats(team, season, comp, venue);
            let mut ctx = Vec::new();
            if let Some(c) = comp {
                ctx.push(c.to_string());
            }
            if let Some(s) = season {
                ctx.push(s.to_string());
            }
            match venue {
                Venue::Home => ctx.push("home".into()),
                Venue::Away => ctx.push("away".into()),
                Venue::Any => {}
            }
            let context = if ctx.is_empty() {
                "all competitions".to_string()
            } else {
                ctx.join(", ")
            };
            Ok(format::team_record(&rec, &context))
        }
        "search_players" => {
            let limit = int_arg(args, "limit").unwrap_or(25).max(0) as usize;
            let list = store.search_players(
                str_arg(args, "name"),
                str_arg(args, "nationality"),
                str_arg(args, "club"),
                str_arg(args, "position"),
                int_arg(args, "min_overall").map(|v| v as i32),
                limit,
            );
            Ok(format::players("Players", &list))
        }
        "standings" => {
            let season = int_arg(args, "season").ok_or("season is required")? as i32;
            let comp = str_arg(args, "competition").or(Some("Brasileirão"));
            let rows = store.standings(comp, season);
            let title = format!(
                "{} {} standings (computed from matches):",
                comp.unwrap_or("Brasileirão"),
                season
            );
            Ok(format::standings(&title, &rows))
        }
        "biggest_wins" => {
            let limit = int_arg(args, "limit").unwrap_or(10).max(0) as usize;
            let list = store.biggest_wins(
                str_arg(args, "competition"),
                int_arg(args, "season").map(|v| v as i32),
                limit,
            );
            Ok(format::matches("Biggest victories", &list))
        }
        "average_goals" => {
            let comp = str_arg(args, "competition");
            let season = int_arg(args, "season").map(|v| v as i32);
            let g = store.average_goals(comp, season);
            let mut title = String::from("Goal statistics");
            if let Some(c) = comp {
                title.push_str(&format!(" - {c}"));
            }
            if let Some(s) = season {
                title.push_str(&format!(" ({s})"));
            }
            title.push(':');
            Ok(format::goal_stats(&title, &g))
        }
        "data_summary" => Ok(format::summary(&store.summary())),
        other => Err(format!("unknown tool: {other}")),
    }
}

fn build_match_title(args: &Value) -> String {
    let mut parts = Vec::new();
    if let Some(t) = str_arg(args, "team") {
        if let Some(o) = str_arg(args, "opponent") {
            parts.push(format!("{t} vs {o}"));
        } else {
            parts.push(t.to_string());
        }
    }
    if let Some(c) = str_arg(args, "competition") {
        parts.push(c.to_string());
    }
    if let Some(s) = int_arg(args, "season") {
        parts.push(s.to_string());
    }
    if parts.is_empty() {
        "Matches".to_string()
    } else {
        format!("Matches: {}", parts.join(", "))
    }
}

/// Build a JSON-RPC success response.
fn ok_response(id: Value, result: Value) -> Value {
    json!({"jsonrpc": "2.0", "id": id, "result": result})
}

/// Build a JSON-RPC error response.
fn err_response(id: Value, code: i64, message: &str) -> Value {
    json!({"jsonrpc": "2.0", "id": id, "error": {"code": code, "message": message}})
}

/// Handle one parsed JSON-RPC request, returning an optional response value.
/// Notifications (no `id`) return `None`.
pub fn handle_request(store: &Store, req: &Value) -> Option<Value> {
    let method = req.get("method").and_then(|m| m.as_str()).unwrap_or("");
    let id = req.get("id").cloned();

    // Notifications have no id and expect no response.
    let is_notification = id.is_none();

    match method {
        "initialize" => {
            let result = json!({
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION}
            });
            Some(ok_response(id.unwrap_or(Value::Null), result))
        }
        "ping" => Some(ok_response(id.unwrap_or(Value::Null), json!({}))),
        "tools/list" => {
            let result = json!({"tools": tool_catalogue()});
            Some(ok_response(id.unwrap_or(Value::Null), result))
        }
        "tools/call" => {
            let params = req.get("params").cloned().unwrap_or(json!({}));
            let name = params.get("name").and_then(|n| n.as_str()).unwrap_or("");
            let args = params.get("arguments").cloned().unwrap_or(json!({}));
            match dispatch_tool(store, name, &args) {
                Ok(text) => Some(ok_response(
                    id.unwrap_or(Value::Null),
                    json!({"content": [{"type": "text", "text": text}], "isError": false}),
                )),
                Err(e) => Some(ok_response(
                    id.unwrap_or(Value::Null),
                    json!({"content": [{"type": "text", "text": format!("Error: {e}")}], "isError": true}),
                )),
            }
        }
        _ if is_notification => None,
        _ => Some(err_response(
            id.unwrap_or(Value::Null),
            -32601,
            &format!("Method not found: {method}"),
        )),
    }
}

/// Run the stdio JSON-RPC loop until EOF.
pub fn serve_stdio(store: &Store) -> std::io::Result<()> {
    let stdin = std::io::stdin();
    let mut stdout = std::io::stdout();
    let mut line = String::new();
    loop {
        line.clear();
        let n = stdin.lock().read_line(&mut line)?;
        if n == 0 {
            break; // EOF
        }
        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }
        let req: Value = match serde_json::from_str(trimmed) {
            Ok(v) => v,
            Err(e) => {
                let resp = err_response(Value::Null, -32700, &format!("Parse error: {e}"));
                writeln!(stdout, "{resp}")?;
                stdout.flush()?;
                continue;
            }
        };
        if let Some(resp) = handle_request(store, &req) {
            writeln!(stdout, "{resp}")?;
            stdout.flush()?;
        }
    }
    Ok(())
}
