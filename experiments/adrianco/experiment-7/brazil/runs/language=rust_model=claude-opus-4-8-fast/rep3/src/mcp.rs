// =============================================================================
// mcp — Model Context Protocol server (JSON-RPC 2.0 over stdio)
// -----------------------------------------------------------------------------
// Context:
//   Implements the MCP stdio transport: newline-delimited JSON-RPC 2.0 messages
//   on stdin/stdout. Supported methods:
//     * initialize              -> handshake / capability advertisement
//     * notifications/initialized (no response)
//     * ping                    -> {}
//     * tools/list              -> the tool catalog (schemas below)
//     * tools/call              -> dispatch to the `queries` layer
//
//   Tool results are returned as MCP "content" blocks containing the
//   human-readable answer text produced by `queries`. The catalog covers every
//   capability category in TASK.md.
// =============================================================================

use crate::queries::{
    self, MatchFilter, PlayerFilter, PlayerSort, Venue,
};
use crate::normalize::parse_date;
use crate::store::DataStore;
use serde_json::{json, Value};
use std::io::{BufRead, Write};

const PROTOCOL_VERSION: &str = "2024-11-05";
const SERVER_NAME: &str = "brazilian-soccer-mcp";
const SERVER_VERSION: &str = "0.1.0";

/// Run the MCP server loop, reading requests from `input` and writing responses
/// to `output`. Returns when the input stream closes (EOF).
pub fn serve<R: BufRead, W: Write>(store: &DataStore, mut input: R, mut output: W) -> std::io::Result<()> {
    let mut line = String::new();
    loop {
        line.clear();
        let n = input.read_line(&mut line)?;
        if n == 0 {
            break; // EOF
        }
        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }
        let request: Value = match serde_json::from_str(trimmed) {
            Ok(v) => v,
            Err(e) => {
                write_message(&mut output, &error_response(&Value::Null, -32700, &format!("Parse error: {}", e)))?;
                continue;
            }
        };

        // Notifications (no "id") get no response.
        let id = request.get("id").cloned();
        let method = request.get("method").and_then(|m| m.as_str()).unwrap_or("");

        if id.is_none() {
            // It's a notification; nothing to send back.
            continue;
        }
        let id = id.unwrap();

        let response = handle_request(store, method, &request, &id);
        if let Some(resp) = response {
            write_message(&mut output, &resp)?;
        }
    }
    Ok(())
}

fn write_message<W: Write>(output: &mut W, msg: &Value) -> std::io::Result<()> {
    let s = serde_json::to_string(msg)?;
    output.write_all(s.as_bytes())?;
    output.write_all(b"\n")?;
    output.flush()
}

fn handle_request(store: &DataStore, method: &str, request: &Value, id: &Value) -> Option<Value> {
    match method {
        "initialize" => Some(success(id, initialize_result())),
        "ping" => Some(success(id, json!({}))),
        "tools/list" => Some(success(id, json!({ "tools": tool_catalog() }))),
        "tools/call" => Some(handle_tool_call(store, request, id)),
        other => Some(error_response(
            id,
            -32601,
            &format!("Method not found: {}", other),
        )),
    }
}

fn initialize_result() -> Value {
    json!({
        "protocolVersion": PROTOCOL_VERSION,
        "capabilities": { "tools": {} },
        "serverInfo": { "name": SERVER_NAME, "version": SERVER_VERSION },
        "instructions": "Query Brazilian soccer matches, teams, players and competitions. Use tools/list to see available queries."
    })
}

fn success(id: &Value, result: Value) -> Value {
    json!({ "jsonrpc": "2.0", "id": id, "result": result })
}

fn error_response(id: &Value, code: i64, message: &str) -> Value {
    json!({ "jsonrpc": "2.0", "id": id, "error": { "code": code, "message": message } })
}

/// Wrap a query string into the MCP tool-result content shape.
fn tool_text_result(text: String, is_error: bool) -> Value {
    json!({
        "content": [ { "type": "text", "text": text } ],
        "isError": is_error
    })
}

fn handle_tool_call(store: &DataStore, request: &Value, id: &Value) -> Value {
    let params = request.get("params").cloned().unwrap_or(Value::Null);
    let name = params.get("name").and_then(|n| n.as_str()).unwrap_or("");
    let args = params.get("arguments").cloned().unwrap_or(json!({}));

    match dispatch_tool(store, name, &args) {
        Ok(text) => success(id, tool_text_result(text, false)),
        Err(msg) => success(id, tool_text_result(format!("Error: {}", msg), true)),
    }
}

// ----------------------------------------------------------------------------
// Argument helpers
// ----------------------------------------------------------------------------

fn arg_str(args: &Value, key: &str) -> Option<String> {
    args.get(key)
        .and_then(|v| v.as_str())
        .map(|s| s.trim().to_string())
        .filter(|s| !s.is_empty())
}

fn arg_i64(args: &Value, key: &str) -> Option<i64> {
    match args.get(key) {
        Some(Value::Number(n)) => n.as_i64(),
        Some(Value::String(s)) => s.trim().parse().ok(),
        _ => None,
    }
}

fn arg_usize(args: &Value, key: &str, default: usize) -> usize {
    arg_i64(args, key).map(|v| v.max(0) as usize).unwrap_or(default)
}

/// Convert a date argument (any supported format) into a sort key bound.
fn arg_date_key(args: &Value, key: &str) -> Option<i64> {
    arg_str(args, key).and_then(|s| {
        let (_, k) = parse_date(&s);
        if k == 0 {
            None
        } else {
            Some(k)
        }
    })
}

/// Dispatch a named tool call to the query layer. `Err` carries a user-facing
/// message for missing required arguments.
pub fn dispatch_tool(store: &DataStore, name: &str, args: &Value) -> Result<String, String> {
    match name {
        "search_matches" => {
            let mut f = MatchFilter::new();
            f.team = arg_str(args, "team");
            f.opponent = arg_str(args, "opponent");
            f.competition = arg_str(args, "competition");
            f.season = arg_i64(args, "season");
            f.start_key = arg_date_key(args, "start_date");
            f.end_key = arg_date_key(args, "end_date");
            f.venue = Venue::parse(&arg_str(args, "venue").unwrap_or_default());
            let limit = arg_usize(args, "limit", 25);
            Ok(queries::search_matches(store, &f, limit))
        }
        "head_to_head" => {
            let t1 = arg_str(args, "team1").ok_or("`team1` is required")?;
            let t2 = arg_str(args, "team2").ok_or("`team2` is required")?;
            let limit = arg_usize(args, "limit", 25);
            Ok(queries::head_to_head(
                store,
                &t1,
                &t2,
                arg_str(args, "competition").as_deref(),
                arg_i64(args, "season"),
                limit,
            ))
        }
        "team_record" => {
            let team = arg_str(args, "team").ok_or("`team` is required")?;
            let venue = Venue::parse(&arg_str(args, "venue").unwrap_or_default());
            Ok(queries::team_record(
                store,
                &team,
                arg_i64(args, "season"),
                arg_str(args, "competition").as_deref(),
                venue,
            ))
        }
        "search_players" => {
            let f = PlayerFilter {
                name: arg_str(args, "name"),
                nationality: arg_str(args, "nationality"),
                club: arg_str(args, "club"),
                position: arg_str(args, "position"),
                min_overall: arg_i64(args, "min_overall"),
            };
            let sort = PlayerSort::parse(&arg_str(args, "sort_by").unwrap_or_default());
            let limit = arg_usize(args, "limit", 25);
            Ok(queries::search_players(store, &f, sort, limit))
        }
        "competition_standings" => {
            let comp = arg_str(args, "competition").ok_or("`competition` is required")?;
            let season = arg_i64(args, "season").ok_or("`season` is required")?;
            Ok(queries::standings(store, &comp, season))
        }
        "competition_summary" => {
            let biggest = arg_usize(args, "biggest_n", 5);
            Ok(queries::competition_summary(
                store,
                arg_str(args, "competition").as_deref(),
                arg_i64(args, "season"),
                biggest,
            ))
        }
        "list_competitions" => Ok(queries::list_competitions(store)),
        "list_seasons" => Ok(queries::list_seasons(
            store,
            arg_str(args, "competition").as_deref(),
        )),
        other => Err(format!("Unknown tool: {}", other)),
    }
}

// ----------------------------------------------------------------------------
// Tool catalog (JSON schemas)
// ----------------------------------------------------------------------------

fn tool_catalog() -> Value {
    json!([
        {
            "name": "search_matches",
            "description": "Search matches by team, opponent, competition, season and/or date range. Returns matching fixtures (newest first) and, when two teams are given, their head-to-head record.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team": { "type": "string", "description": "Team name (home, away or either). e.g. 'Flamengo'" },
                    "opponent": { "type": "string", "description": "Second team for a specific pairing. e.g. 'Fluminense'" },
                    "competition": { "type": "string", "description": "Competition filter: 'Brasileirão', 'Copa do Brasil', 'Libertadores', 'Serie B', etc." },
                    "season": { "type": "integer", "description": "Season year, e.g. 2023" },
                    "start_date": { "type": "string", "description": "Inclusive lower date bound (YYYY-MM-DD or DD/MM/YYYY)" },
                    "end_date": { "type": "string", "description": "Inclusive upper date bound" },
                    "venue": { "type": "string", "enum": ["home", "away", "all"], "description": "Restrict `team` to home or away fixtures" },
                    "limit": { "type": "integer", "description": "Max fixtures to list (default 25)" }
                }
            }
        },
        {
            "name": "head_to_head",
            "description": "Head-to-head record and match list between two teams, optionally scoped by competition/season.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team1": { "type": "string" },
                    "team2": { "type": "string" },
                    "competition": { "type": "string" },
                    "season": { "type": "integer" },
                    "limit": { "type": "integer", "description": "Max fixtures to list (default 25)" }
                },
                "required": ["team1", "team2"]
            }
        },
        {
            "name": "team_record",
            "description": "Win/draw/loss record, goals and points for a team, optionally scoped by season, competition and venue (home/away).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team": { "type": "string" },
                    "season": { "type": "integer" },
                    "competition": { "type": "string" },
                    "venue": { "type": "string", "enum": ["home", "away", "all"] }
                },
                "required": ["team"]
            }
        },
        {
            "name": "search_players",
            "description": "Search the FIFA player database by name, nationality, club, position and minimum overall rating. Sortable by overall/potential/age/name.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": { "type": "string", "description": "Substring of player name" },
                    "nationality": { "type": "string", "description": "e.g. 'Brazil'" },
                    "club": { "type": "string", "description": "e.g. 'Flamengo'" },
                    "position": { "type": "string", "description": "Exact position code, e.g. 'GK', 'ST', 'CDM'" },
                    "min_overall": { "type": "integer", "description": "Minimum FIFA overall rating" },
                    "sort_by": { "type": "string", "enum": ["overall", "potential", "age", "name"] },
                    "limit": { "type": "integer", "description": "Max players to list (default 25)" }
                }
            }
        },
        {
            "name": "competition_standings",
            "description": "Compute a league table (points, W/D/L, goals, GD) for a competition and season from match results.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "competition": { "type": "string", "description": "e.g. 'Brasileirão'" },
                    "season": { "type": "integer", "description": "e.g. 2019" }
                },
                "required": ["competition", "season"]
            }
        },
        {
            "name": "competition_summary",
            "description": "Aggregate statistics for matches: average goals per match, home/away win rate, draw rate and the biggest victories. Scope with optional competition and/or season.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "competition": { "type": "string" },
                    "season": { "type": "integer" },
                    "biggest_n": { "type": "integer", "description": "How many biggest wins to list (default 5)" }
                }
            }
        },
        {
            "name": "list_competitions",
            "description": "List the competitions available in the dataset with match counts and overall totals.",
            "inputSchema": { "type": "object", "properties": {} }
        },
        {
            "name": "list_seasons",
            "description": "List the seasons available, optionally for a single competition.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "competition": { "type": "string" }
                }
            }
        }
    ])
}
