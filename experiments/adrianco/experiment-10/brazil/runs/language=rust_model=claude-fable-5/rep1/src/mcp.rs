//! Model Context Protocol server: JSON-RPC 2.0 over stdio
//! (newline-delimited JSON), exposing the query engine as MCP tools.

use std::io::{BufRead, Write};

use chrono::NaiveDate;
use serde_json::{json, Value};

use crate::data::Store;
use crate::query::{self, MatchFilter, PlayerFilter};

pub const PROTOCOL_VERSION: &str = "2024-11-05";
pub const SERVER_NAME: &str = "brazilian-soccer-mcp";
pub const SERVER_VERSION: &str = env!("CARGO_PKG_VERSION");

/// Tool definitions advertised by `tools/list`.
pub fn tool_definitions() -> Value {
    json!([
        {
            "name": "search_matches",
            "description": "Search Brazilian soccer matches (Brasileirão Série A/B/C 2003-2023, Copa do Brasil, Copa Libertadores) by team, opponent, competition, season, stage/round, or date range. Team names are normalized, so 'Palmeiras', 'Palmeiras-SP' and 'São Paulo'/'Sao Paulo' all work.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team": {"type": "string", "description": "Team name (home or away)"},
                    "opponent": {"type": "string", "description": "Second team, to find direct encounters"},
                    "competition": {"type": "string", "description": "Competition filter, e.g. 'Brasileirão', 'Serie A', 'Copa do Brasil', 'Libertadores'"},
                    "season": {"type": "integer", "description": "Season year, e.g. 2019"},
                    "stage": {"type": "string", "description": "Stage or round filter, e.g. 'final', 'semifinals', 'group stage'"},
                    "date_from": {"type": "string", "description": "Earliest date, YYYY-MM-DD"},
                    "date_to": {"type": "string", "description": "Latest date, YYYY-MM-DD"},
                    "limit": {"type": "integer", "description": "Max matches to list (default 20)"}
                }
            }
        },
        {
            "name": "head_to_head",
            "description": "Head-to-head record between two teams: wins, draws, goals, and the most recent matches between them across all loaded competitions.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team1": {"type": "string"},
                    "team2": {"type": "string"},
                    "competition": {"type": "string", "description": "Optional competition filter"}
                },
                "required": ["team1", "team2"]
            }
        },
        {
            "name": "team_stats",
            "description": "Win/draw/loss record, goals for/against and win rate for a team, optionally restricted to a season, competition and venue (home/away/all). Includes a per-competition breakdown.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team": {"type": "string"},
                    "season": {"type": "integer"},
                    "competition": {"type": "string"},
                    "venue": {"type": "string", "enum": ["home", "away", "all"], "description": "Default 'all'"}
                },
                "required": ["team"]
            }
        },
        {
            "name": "league_standings",
            "description": "Calculated Brasileirão Série A table for a season (2003-2023): points, W/D/L, goals; marks the champion and the relegation zone.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "season": {"type": "integer", "description": "Season year, e.g. 2019"}
                },
                "required": ["season"]
            }
        },
        {
            "name": "search_players",
            "description": "Search the FIFA player database (18k players) by name, nationality (e.g. 'Brazil'), club, position (FIFA code like ST/GK or group like 'forward'), and minimum overall rating. Sorted by overall rating unless sort_by is given.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "nationality": {"type": "string"},
                    "club": {"type": "string"},
                    "position": {"type": "string"},
                    "min_overall": {"type": "integer"},
                    "sort_by": {"type": "string", "enum": ["overall", "potential", "age", "name"]},
                    "limit": {"type": "integer", "description": "Max players to list (default 15)"}
                }
            }
        },
        {
            "name": "player_info",
            "description": "Detailed FIFA profile for one player found by (partial, accent-insensitive) name: ratings, club, position, physique, value, key attributes.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"}
                },
                "required": ["name"]
            }
        },
        {
            "name": "competition_stats",
            "description": "Aggregate statistics for a competition and/or season slice: match count, average goals per match, home-win/draw/away-win rates, top scoring teams.",
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
            "description": "Largest margins of victory in the dataset, optionally filtered by competition and season.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "competition": {"type": "string"},
                    "season": {"type": "integer"},
                    "limit": {"type": "integer", "description": "Default 10"}
                }
            }
        },
        {
            "name": "list_competitions",
            "description": "List the loaded competitions, season coverage, match counts per source file, and player count.",
            "inputSchema": {"type": "object", "properties": {}}
        }
    ])
}

fn arg_str(args: &Value, key: &str) -> Option<String> {
    args.get(key)
        .and_then(|v| v.as_str())
        .map(|s| s.trim().to_string())
        .filter(|s| !s.is_empty())
}

fn arg_int(args: &Value, key: &str) -> Option<i64> {
    args.get(key).and_then(|v| {
        v.as_i64()
            .or_else(|| v.as_str().and_then(|s| s.trim().parse().ok()))
    })
}

fn arg_date(args: &Value, key: &str) -> Option<NaiveDate> {
    arg_str(args, key).and_then(|s| NaiveDate::parse_from_str(&s, "%Y-%m-%d").ok())
}

/// Execute one tool call and return its text result.
pub fn call_tool(store: &Store, name: &str, args: &Value) -> Result<String, String> {
    match name {
        "search_matches" => {
            let filter = MatchFilter {
                team: arg_str(args, "team"),
                opponent: arg_str(args, "opponent"),
                competition: arg_str(args, "competition"),
                season: arg_int(args, "season").map(|s| s as i32),
                date_from: arg_date(args, "date_from"),
                date_to: arg_date(args, "date_to"),
                stage: arg_str(args, "stage"),
            };
            let limit = arg_int(args, "limit").unwrap_or(20).max(1) as usize;
            let matches = query::find_matches(store, &filter);
            let mut out = format!("Found {} matches.\n", matches.len());
            out.push_str(&query::format_matches(&matches, limit));
            Ok(out)
        }
        "head_to_head" => {
            let team1 = arg_str(args, "team1").ok_or("missing required argument: team1")?;
            let team2 = arg_str(args, "team2").ok_or("missing required argument: team2")?;
            Ok(query::head_to_head(
                store,
                &team1,
                &team2,
                arg_str(args, "competition").as_deref(),
            ))
        }
        "team_stats" => {
            let team = arg_str(args, "team").ok_or("missing required argument: team")?;
            let venue = arg_str(args, "venue").unwrap_or_else(|| "all".into());
            Ok(query::team_stats(
                store,
                &team,
                arg_int(args, "season").map(|s| s as i32),
                arg_str(args, "competition").as_deref(),
                &venue,
            ))
        }
        "league_standings" => {
            let season = arg_int(args, "season").ok_or("missing required argument: season")?;
            Ok(query::format_standings(store, season as i32))
        }
        "search_players" => {
            let filter = PlayerFilter {
                name: arg_str(args, "name"),
                nationality: arg_str(args, "nationality"),
                club: arg_str(args, "club"),
                position: arg_str(args, "position"),
                min_overall: arg_int(args, "min_overall").map(|v| v as i32),
            };
            let sort_by = arg_str(args, "sort_by").unwrap_or_else(|| "overall".into());
            let limit = arg_int(args, "limit").unwrap_or(15).max(1) as usize;
            let players = query::find_players(store, &filter, &sort_by);
            let mut out = format!("Found {} players.\n", players.len());
            out.push_str(&query::format_players(&players, limit));
            Ok(out)
        }
        "player_info" => {
            let name = arg_str(args, "name").ok_or("missing required argument: name")?;
            Ok(query::player_info(store, &name))
        }
        "competition_stats" => Ok(query::competition_overview(
            store,
            arg_str(args, "competition").as_deref(),
            arg_int(args, "season").map(|s| s as i32),
        )),
        "biggest_wins" => {
            let limit = arg_int(args, "limit").unwrap_or(10).max(1) as usize;
            Ok(query::biggest_wins(
                store,
                arg_str(args, "competition").as_deref(),
                arg_int(args, "season").map(|s| s as i32),
                limit,
            ))
        }
        "list_competitions" => Ok(query::list_competitions(store)),
        other => Err(format!("unknown tool: {}", other)),
    }
}

/// Build the JSON-RPC response for one request. Returns `None` for
/// notifications (no id), which require no response.
pub fn handle_message(store: &Store, msg: &Value) -> Option<Value> {
    let method = msg.get("method")?.as_str()?;
    let id = msg.get("id");
    // Notifications (initialized, cancelled, ...) get no response.
    let id = match id {
        Some(id) if !id.is_null() => id.clone(),
        _ => return None,
    };

    let result: Result<Value, (i64, String)> = match method {
        "initialize" => Ok(json!({
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": { "tools": {} },
            "serverInfo": { "name": SERVER_NAME, "version": SERVER_VERSION },
            "instructions": "Query Brazilian soccer data: matches (Brasileirão, Copa do Brasil, Libertadores, 2003-2023), FIFA player profiles, team statistics, head-to-head records and calculated league standings."
        })),
        "ping" => Ok(json!({})),
        "tools/list" => Ok(json!({ "tools": tool_definitions() })),
        "tools/call" => {
            let name = msg
                .pointer("/params/name")
                .and_then(|v| v.as_str())
                .unwrap_or("");
            let default_args = json!({});
            let args = msg.pointer("/params/arguments").unwrap_or(&default_args);
            match call_tool(store, name, args) {
                Ok(text) => Ok(json!({
                    "content": [{ "type": "text", "text": text }],
                    "isError": false
                })),
                Err(e) => Ok(json!({
                    "content": [{ "type": "text", "text": format!("Error: {}", e) }],
                    "isError": true
                })),
            }
        }
        "resources/list" => Ok(json!({ "resources": [] })),
        "prompts/list" => Ok(json!({ "prompts": [] })),
        _ => Err((-32601, format!("method not found: {}", method))),
    };

    Some(match result {
        Ok(result) => json!({ "jsonrpc": "2.0", "id": id, "result": result }),
        Err((code, message)) => json!({
            "jsonrpc": "2.0",
            "id": id,
            "error": { "code": code, "message": message }
        }),
    })
}

/// Run the stdio server loop: one JSON-RPC message per line.
pub fn serve(store: &Store) -> std::io::Result<()> {
    let stdin = std::io::stdin();
    let stdout = std::io::stdout();
    let mut out = stdout.lock();
    for line in stdin.lock().lines() {
        let line = line?;
        if line.trim().is_empty() {
            continue;
        }
        let msg: Value = match serde_json::from_str(&line) {
            Ok(v) => v,
            Err(e) => {
                let resp = json!({
                    "jsonrpc": "2.0",
                    "id": null,
                    "error": { "code": -32700, "message": format!("parse error: {}", e) }
                });
                writeln!(out, "{}", resp)?;
                out.flush()?;
                continue;
            }
        };
        if let Some(resp) = handle_message(store, &msg) {
            writeln!(out, "{}", resp)?;
            out.flush()?;
        }
    }
    Ok(())
}
