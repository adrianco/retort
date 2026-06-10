// ============================================================================
// CONTEXT: Brazilian Soccer MCP Server - MCP protocol layer
//
// Purpose:  Implements the Model Context Protocol (JSON-RPC 2.0) surface:
//             initialize                -> protocol handshake + server info
//             notifications/initialized -> acknowledged silently
//             ping                      -> {}
//             tools/list                -> the 9 tool definitions below
//             tools/call                -> dispatch into queries.rs
//
// Tools:    search_matches, get_team_stats, head_to_head, get_standings,
//           search_players, get_player, analyze_stats, best_records,
//           list_competitions
//
// Contract: handle_request(dataset, request) -> Option<response>
//           Notifications (no "id") return None. Tool execution errors are
//           reported MCP-style: result.isError = true with a text message,
//           so the LLM can read and react to them.
// ============================================================================

use crate::data::Dataset;
use crate::queries::{self, MatchFilters, PlayerFilters};
use serde_json::{json, Value};

pub const PROTOCOL_VERSION: &str = "2024-11-05";
pub const SERVER_NAME: &str = "brazilian-soccer-mcp";
pub const SERVER_VERSION: &str = env!("CARGO_PKG_VERSION");

pub fn tool_definitions() -> Value {
    let team_prop = |desc: &str| json!({"type": "string", "description": desc});
    json!([
        {
            "name": "search_matches",
            "description": "Search Brazilian soccer matches by team, opponent, competition (Brasileirão Série A/B/C, Copa do Brasil, Copa Libertadores), season or date range. Returns match list (date, teams, score, round) plus a head-to-head summary when both team and opponent are given. Team names are normalized: 'Palmeiras', 'Palmeiras-SP' and 'Sociedade Esportiva Palmeiras' all match.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team": team_prop("Team name, any common spelling (e.g. 'Flamengo', 'Atlético-MG')"),
                    "opponent": team_prop("Second team, to find matches between two specific clubs"),
                    "competition": team_prop("Competition name, e.g. 'Brasileirão', 'Copa do Brasil', 'Libertadores'"),
                    "season": {"type": "integer", "description": "Season year, e.g. 2019"},
                    "date_from": {"type": "string", "description": "Earliest date, 'YYYY-MM-DD' or 'YYYY'"},
                    "date_to": {"type": "string", "description": "Latest date, 'YYYY-MM-DD' or 'YYYY'"},
                    "limit": {"type": "integer", "description": "Max matches to return (default 20, max 100)"}
                }
            }
        },
        {
            "name": "get_team_stats",
            "description": "Win/draw/loss record, goals for/against, win rate and home/away split for a team, optionally filtered by season and competition. Also breaks the record down per competition.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team": team_prop("Team name (required)"),
                    "season": {"type": "integer", "description": "Season year filter"},
                    "competition": team_prop("Competition filter")
                },
                "required": ["team"]
            }
        },
        {
            "name": "head_to_head",
            "description": "Head-to-head record between two clubs: wins per side, draws, goals, and the most recent matches.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team1": team_prop("First team (required)"),
                    "team2": team_prop("Second team (required)"),
                    "competition": team_prop("Optional competition filter")
                },
                "required": ["team1", "team2"]
            }
        },
        {
            "name": "get_standings",
            "description": "League table for a Brasileirão season computed from match results (3 pts/win). Identifies the champion and the relegation zone. Available: Série A 2003-2022 (Série B/C where data exists).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "season": {"type": "integer", "description": "Season year, e.g. 2019 (required)"},
                    "competition": team_prop("Defaults to Brasileirão Série A")
                },
                "required": ["season"]
            }
        },
        {
            "name": "search_players",
            "description": "Search the FIFA player database (18k players) by name, nationality (e.g. 'Brazil'), club, position (e.g. ST, GK, CDM) and minimum overall rating. Sorted by overall rating descending.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Partial or full player name"},
                    "nationality": {"type": "string", "description": "Exact nationality, e.g. 'Brazil'"},
                    "club": {"type": "string", "description": "Club name, normalized like team names"},
                    "position": {"type": "string", "description": "Position code: GK, CB, CDM, CM, CAM, LW, RW, ST..."},
                    "min_overall": {"type": "integer", "description": "Minimum FIFA overall rating"},
                    "limit": {"type": "integer", "description": "Max players to return (default 20, max 100)"}
                }
            }
        },
        {
            "name": "get_player",
            "description": "Full profile of a single player: ratings, club, physicals, value/wage and key skill ratings. Best match by name.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Player name (required)"}
                },
                "required": ["name"]
            }
        },
        {
            "name": "analyze_stats",
            "description": "Aggregate statistics over matches: average goals per match, home-win/draw/away-win rates and the biggest wins, optionally filtered by competition and season.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "competition": {"type": "string", "description": "Competition filter"},
                    "season": {"type": "integer", "description": "Season year filter"},
                    "top_n": {"type": "integer", "description": "How many biggest wins to list (default 10)"}
                }
            }
        },
        {
            "name": "best_records",
            "description": "Rank teams by win rate at home, away, or overall, with optional competition/season filter and a minimum-matches threshold.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "venue": {"type": "string", "enum": ["home", "away", "overall"], "description": "Which record to rank (default 'home')"},
                    "competition": {"type": "string", "description": "Competition filter"},
                    "season": {"type": "integer", "description": "Season year filter"},
                    "min_matches": {"type": "integer", "description": "Minimum matches played to qualify (default 10)"},
                    "limit": {"type": "integer", "description": "Max teams to return (default 10)"}
                }
            }
        },
        {
            "name": "list_competitions",
            "description": "Lists the competitions in the knowledge base with record counts and season coverage, plus dataset diagnostics.",
            "inputSchema": {"type": "object", "properties": {}}
        }
    ])
}

fn opt_str<'a>(args: &'a Value, key: &str) -> Option<&'a str> {
    args.get(key).and_then(|v| v.as_str()).map(str::trim).filter(|s| !s.is_empty())
}

fn opt_int(args: &Value, key: &str) -> Option<i64> {
    args.get(key).and_then(|v| {
        v.as_i64().or_else(|| v.as_str().and_then(|s| s.trim().parse().ok()))
    })
}

pub fn call_tool(ds: &Dataset, name: &str, args: &Value) -> Result<Value, String> {
    match name {
        "search_matches" => queries::search_matches(
            ds,
            &MatchFilters {
                team: opt_str(args, "team"),
                opponent: opt_str(args, "opponent"),
                competition: opt_str(args, "competition"),
                season: opt_int(args, "season").map(|v| v as i32),
                date_from: opt_str(args, "date_from"),
                date_to: opt_str(args, "date_to"),
                limit: opt_int(args, "limit").unwrap_or(20) as usize,
            },
        ),
        "get_team_stats" => {
            let team = opt_str(args, "team").ok_or("missing required argument: team")?;
            queries::team_stats(ds, team, opt_int(args, "season").map(|v| v as i32), opt_str(args, "competition"))
        }
        "head_to_head" => {
            let t1 = opt_str(args, "team1").ok_or("missing required argument: team1")?;
            let t2 = opt_str(args, "team2").ok_or("missing required argument: team2")?;
            queries::head_to_head(ds, t1, t2, opt_str(args, "competition"))
        }
        "get_standings" => {
            let season = opt_int(args, "season").ok_or("missing required argument: season")? as i32;
            queries::standings(ds, season, opt_str(args, "competition"))
        }
        "search_players" => queries::search_players(
            ds,
            &PlayerFilters {
                name: opt_str(args, "name"),
                nationality: opt_str(args, "nationality"),
                club: opt_str(args, "club"),
                position: opt_str(args, "position"),
                min_overall: opt_int(args, "min_overall").map(|v| v as i32),
                limit: opt_int(args, "limit").unwrap_or(20) as usize,
            },
        ),
        "get_player" => {
            let name = opt_str(args, "name").ok_or("missing required argument: name")?;
            queries::get_player(ds, name)
        }
        "analyze_stats" => queries::analyze_stats(
            ds,
            opt_str(args, "competition"),
            opt_int(args, "season").map(|v| v as i32),
            opt_int(args, "top_n").unwrap_or(10) as usize,
        ),
        "best_records" => queries::best_records(
            ds,
            opt_str(args, "venue").unwrap_or("home"),
            opt_str(args, "competition"),
            opt_int(args, "season").map(|v| v as i32),
            opt_int(args, "min_matches").unwrap_or(10) as usize,
            opt_int(args, "limit").unwrap_or(10) as usize,
        ),
        "list_competitions" => Ok(queries::list_competitions(ds)),
        other => Err(format!("unknown tool: {}", other)),
    }
}

fn rpc_result(id: &Value, result: Value) -> Value {
    json!({"jsonrpc": "2.0", "id": id, "result": result})
}

fn rpc_error(id: &Value, code: i64, message: &str) -> Value {
    json!({"jsonrpc": "2.0", "id": id, "error": {"code": code, "message": message}})
}

/// Handle one JSON-RPC request. Returns None for notifications.
pub fn handle_request(ds: &Dataset, req: &Value) -> Option<Value> {
    let method = req.get("method").and_then(|m| m.as_str()).unwrap_or("");
    let id = req.get("id").cloned();

    // Notifications carry no id and never get a response.
    let id = match id {
        Some(v) if !v.is_null() => v,
        _ => {
            return None;
        }
    };

    let response = match method {
        "initialize" => rpc_result(
            &id,
            json!({
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                "instructions": "Knowledge base of Brazilian soccer: Brasileirão Série A 2003-2022, Copa do Brasil, Copa Libertadores, extended match stats, and the FIFA player database. Team names are normalized across datasets - use any common spelling."
            }),
        ),
        "ping" => rpc_result(&id, json!({})),
        "tools/list" => rpc_result(&id, json!({"tools": tool_definitions()})),
        "tools/call" => {
            let name = req
                .get("params")
                .and_then(|p| p.get("name"))
                .and_then(|n| n.as_str())
                .unwrap_or("");
            let default_args = json!({});
            let args = req
                .get("params")
                .and_then(|p| p.get("arguments"))
                .unwrap_or(&default_args);
            match call_tool(ds, name, args) {
                Ok(result) => rpc_result(
                    &id,
                    json!({
                        "content": [{"type": "text", "text": serde_json::to_string_pretty(&result).unwrap()}],
                        "isError": false
                    }),
                ),
                Err(msg) => rpc_result(
                    &id,
                    json!({
                        "content": [{"type": "text", "text": format!("Error: {}", msg)}],
                        "isError": true
                    }),
                ),
            }
        }
        _ => rpc_error(&id, -32601, &format!("Method not found: {}", method)),
    };
    Some(response)
}
