// =============================================================================
// Context
// -----------------------------------------------------------------------------
// Module:  mcp
// Purpose: Model Context Protocol server implementation. Speaks JSON-RPC 2.0
//          over newline-delimited stdio (the MCP "stdio" transport). It
//          advertises eight tools - one per query-engine capability - and
//          dispatches `tools/call` requests onto `queries.rs`, returning the
//          formatted text as MCP `content` blocks.
//
//          The protocol handling is split out from I/O so it can be unit
//          tested: `handle_request` is a pure (Dataset, Value) -> Option<Value>
//          function, and `serve_stdio` is the thin runtime loop in main.rs.
//
// Methods: initialize, notifications/initialized, tools/list, tools/call.
// =============================================================================

use crate::data::Dataset;
use crate::queries::MatchFilter;
use serde_json::{json, Value};

const PROTOCOL_VERSION: &str = "2024-11-05";
const DEFAULT_MATCH_LIMIT: usize = 25;
const DEFAULT_WINS_LIMIT: usize = 10;
const DEFAULT_PLAYER_LIMIT: usize = 25;

/// JSON-RPC error codes used by this server.
mod codes {
    pub const METHOD_NOT_FOUND: i64 = -32601;
    pub const INVALID_PARAMS: i64 = -32602;
}

/// The list of tools advertised to clients, as an MCP `tools/list` payload.
pub fn tool_definitions() -> Value {
    json!([
        {
            "name": "search_matches",
            "description": "Search matches by team, opponent, competition and/or season. When both 'team' and 'opponent' are given, a head-to-head summary is appended. Results are newest-first.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team": {"type": "string", "description": "Team name, e.g. 'Flamengo' (state suffixes and accents optional)"},
                    "opponent": {"type": "string", "description": "Optional second team to restrict to matches between the two"},
                    "competition": {"type": "string", "description": "Optional competition filter, e.g. 'Brasileirão', 'Copa do Brasil', 'Libertadores'"},
                    "season": {"type": "integer", "description": "Optional season year, e.g. 2019"},
                    "limit": {"type": "integer", "description": "Max matches to list (default 25)"}
                }
            }
        },
        {
            "name": "team_stats",
            "description": "Win/draw/loss record, goals for/against and win rate for a team, optionally restricted by season, competition and venue.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team": {"type": "string"},
                    "season": {"type": "integer"},
                    "competition": {"type": "string"},
                    "venue": {"type": "string", "enum": ["home", "away", "all"], "description": "Restrict to home or away matches (default all)"}
                },
                "required": ["team"]
            }
        },
        {
            "name": "head_to_head",
            "description": "Head-to-head record (wins, draws, goals) between two teams across all competitions in the dataset.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team1": {"type": "string"},
                    "team2": {"type": "string"}
                },
                "required": ["team1", "team2"]
            }
        },
        {
            "name": "competition_standings",
            "description": "League standings for a competition and season, calculated from match results (3 points per win, 1 per draw).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "competition": {"type": "string", "description": "e.g. 'Brasileirão'"},
                    "season": {"type": "integer"}
                },
                "required": ["competition", "season"]
            }
        },
        {
            "name": "league_statistics",
            "description": "Aggregate statistics (average goals per match, home/away win rates, draw rate) for a competition and/or season, or the whole dataset.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "competition": {"type": "string"},
                    "season": {"type": "integer"}
                }
            }
        },
        {
            "name": "biggest_wins",
            "description": "The largest-margin victories matching an optional team / competition / season filter.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team": {"type": "string"},
                    "competition": {"type": "string"},
                    "season": {"type": "integer"},
                    "limit": {"type": "integer", "description": "default 10"}
                }
            }
        },
        {
            "name": "list_competitions",
            "description": "List all competitions in the dataset with match counts and the range of seasons covered.",
            "inputSchema": {"type": "object", "properties": {}}
        },
        {
            "name": "search_players",
            "description": "Search FIFA player data by name, nationality, club and/or position. Results sorted by overall rating, highest first.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Substring of the player's name"},
                    "nationality": {"type": "string", "description": "e.g. 'Brazil'"},
                    "club": {"type": "string", "description": "e.g. 'Flamengo'"},
                    "position": {"type": "string", "description": "e.g. 'GK', 'ST', 'CB'"},
                    "limit": {"type": "integer", "description": "default 25"}
                }
            }
        }
    ])
}

fn str_arg<'a>(args: &'a Value, key: &str) -> Option<&'a str> {
    args.get(key).and_then(|v| v.as_str()).filter(|s| !s.is_empty())
}

fn int_arg(args: &Value, key: &str) -> Option<i32> {
    args.get(key).and_then(|v| match v {
        Value::Number(n) => n.as_i64().map(|i| i as i32),
        Value::String(s) => s.parse().ok(),
        _ => None,
    })
}

fn usize_arg(args: &Value, key: &str, default: usize) -> usize {
    int_arg(args, key)
        .filter(|&n| n > 0)
        .map(|n| n as usize)
        .unwrap_or(default)
}

/// Run a single tool call, returning either the formatted text or an error
/// message describing a missing required argument.
pub fn dispatch_tool(ds: &Dataset, name: &str, args: &Value) -> Result<String, String> {
    match name {
        "search_matches" => {
            let f = MatchFilter {
                team: str_arg(args, "team").map(String::from),
                team2: str_arg(args, "opponent").map(String::from),
                competition: str_arg(args, "competition").map(String::from),
                season: int_arg(args, "season"),
            };
            Ok(ds.search_matches(&f, usize_arg(args, "limit", DEFAULT_MATCH_LIMIT)))
        }
        "team_stats" => {
            let team = str_arg(args, "team").ok_or("missing required argument 'team'")?;
            Ok(ds.team_stats(
                team,
                int_arg(args, "season"),
                str_arg(args, "competition"),
                str_arg(args, "venue").unwrap_or("all"),
            ))
        }
        "head_to_head" => {
            let t1 = str_arg(args, "team1").ok_or("missing required argument 'team1'")?;
            let t2 = str_arg(args, "team2").ok_or("missing required argument 'team2'")?;
            Ok(ds.head_to_head(t1, t2))
        }
        "competition_standings" => {
            let comp =
                str_arg(args, "competition").ok_or("missing required argument 'competition'")?;
            let season = int_arg(args, "season").ok_or("missing required argument 'season'")?;
            Ok(ds.standings(comp, season))
        }
        "league_statistics" => Ok(ds.league_statistics(
            str_arg(args, "competition"),
            int_arg(args, "season"),
        )),
        "biggest_wins" => {
            let f = MatchFilter {
                team: str_arg(args, "team").map(String::from),
                team2: None,
                competition: str_arg(args, "competition").map(String::from),
                season: int_arg(args, "season"),
            };
            Ok(ds.biggest_wins(&f, usize_arg(args, "limit", DEFAULT_WINS_LIMIT)))
        }
        "list_competitions" => Ok(ds.list_competitions()),
        "search_players" => Ok(ds.search_players(
            str_arg(args, "name"),
            str_arg(args, "nationality"),
            str_arg(args, "club"),
            str_arg(args, "position"),
            usize_arg(args, "limit", DEFAULT_PLAYER_LIMIT),
        )),
        other => Err(format!("unknown tool '{other}'")),
    }
}

fn result(id: Value, result: Value) -> Value {
    json!({"jsonrpc": "2.0", "id": id, "result": result})
}

fn error(id: Value, code: i64, message: &str) -> Value {
    json!({"jsonrpc": "2.0", "id": id, "error": {"code": code, "message": message}})
}

/// Handle one parsed JSON-RPC request. Returns `Some(response)` for requests
/// and `None` for notifications (which must not be answered).
pub fn handle_request(ds: &Dataset, req: &Value) -> Option<Value> {
    let method = req.get("method").and_then(|m| m.as_str()).unwrap_or("");
    let id = req.get("id").cloned();

    // Notifications carry no id and expect no response.
    let id = id?;

    match method {
        "initialize" => Some(result(
            id,
            json!({
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {
                    "name": "brazilian-soccer-mcp",
                    "version": env!("CARGO_PKG_VERSION")
                }
            }),
        )),
        "ping" => Some(result(id, json!({}))),
        "tools/list" => Some(result(id, json!({"tools": tool_definitions()}))),
        "tools/call" => {
            let params = req.get("params").cloned().unwrap_or(json!({}));
            let Some(name) = params.get("name").and_then(|n| n.as_str()) else {
                return Some(error(id, codes::INVALID_PARAMS, "missing tool name"));
            };
            let args = params.get("arguments").cloned().unwrap_or(json!({}));
            match dispatch_tool(ds, name, &args) {
                Ok(text) => Some(result(
                    id,
                    json!({"content": [{"type": "text", "text": text}], "isError": false}),
                )),
                Err(msg) => Some(result(
                    id,
                    json!({"content": [{"type": "text", "text": msg}], "isError": true}),
                )),
            }
        }
        other => Some(error(
            id,
            codes::METHOD_NOT_FOUND,
            &format!("method not found: {other}"),
        )),
    }
}

/// Runtime loop: read newline-delimited JSON-RPC messages from `input`, write
/// responses to `output`. Blocks until EOF on `input`.
pub fn serve_stdio<R: std::io::BufRead, W: std::io::Write>(
    ds: &Dataset,
    mut input: R,
    mut output: W,
) -> std::io::Result<()> {
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
        let response = match serde_json::from_str::<Value>(trimmed) {
            Ok(req) => handle_request(ds, &req),
            Err(e) => Some(json!({
                "jsonrpc": "2.0",
                "id": null,
                "error": {"code": -32700, "message": format!("parse error: {e}")}
            })),
        };
        if let Some(resp) = response {
            writeln!(output, "{}", serde_json::to_string(&resp)?)?;
            output.flush()?;
        }
    }
    Ok(())
}
