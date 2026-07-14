// =============================================================================
// CONTEXT: Brazilian Soccer MCP Server — MCP protocol layer
//
// Implements the Model Context Protocol (https://modelcontextprotocol.io)
// over stdio using newline-delimited JSON-RPC 2.0:
//   * initialize / notifications/initialized handshake
//   * ping
//   * tools/list — advertises seven tools (search_matches, get_team_stats,
//     head_to_head, get_standings, get_competition_stats, search_players,
//     get_player, get_data_summary)
//   * tools/call — dispatches into the query engine and returns text content
//
// Requests with an `id` get exactly one response; notifications get none.
// Tool-level failures are reported as MCP tool results with isError=true,
// protocol-level failures as JSON-RPC error objects.
// =============================================================================

use crate::data::{parse_date, Data};
use crate::query::{MatchFilter, QueryEngine};
use serde_json::{json, Value};
use std::io::{BufRead, Write};

pub const SERVER_NAME: &str = "brazilian-soccer-mcp";
pub const SERVER_VERSION: &str = env!("CARGO_PKG_VERSION");
const PROTOCOL_VERSION: &str = "2024-11-05";

pub struct Server {
    data: Data,
}

fn text_result(text: String) -> Value {
    json!({ "content": [{ "type": "text", "text": text }] })
}

fn error_result(text: String) -> Value {
    json!({ "content": [{ "type": "text", "text": text }], "isError": true })
}

fn rpc_error(id: &Value, code: i64, message: &str) -> Value {
    json!({ "jsonrpc": "2.0", "id": id, "error": { "code": code, "message": message } })
}

fn rpc_result(id: &Value, result: Value) -> Value {
    json!({ "jsonrpc": "2.0", "id": id, "result": result })
}

fn arg_str(args: &Value, key: &str) -> Option<String> {
    args.get(key)
        .and_then(|v| v.as_str())
        .map(|s| s.trim().to_string())
        .filter(|s| !s.is_empty())
}

fn arg_i32(args: &Value, key: &str) -> Option<i32> {
    let v = args.get(key)?;
    if let Some(n) = v.as_i64() {
        return Some(n as i32);
    }
    // Be lenient: LLMs sometimes pass numbers as strings.
    v.as_str().and_then(|s| s.trim().parse().ok())
}

fn arg_usize(args: &Value, key: &str) -> Option<usize> {
    arg_i32(args, key).map(|n| n.max(0) as usize)
}

impl Server {
    pub fn new(data: Data) -> Self {
        Server { data }
    }

    pub fn data(&self) -> &Data {
        &self.data
    }

    /// Handle one JSON-RPC message. Returns None for notifications.
    pub fn handle(&self, msg: &Value) -> Option<Value> {
        let method = msg.get("method").and_then(|m| m.as_str()).unwrap_or("");
        let id = msg.get("id").cloned();
        let is_notification = id.is_none() || method.starts_with("notifications/");
        let id = id.unwrap_or(Value::Null);

        let result = match method {
            "initialize" => Some(json!({
                "protocolVersion": msg
                    .pointer("/params/protocolVersion")
                    .and_then(|v| v.as_str())
                    .unwrap_or(PROTOCOL_VERSION),
                "capabilities": { "tools": {} },
                "serverInfo": { "name": SERVER_NAME, "version": SERVER_VERSION },
                "instructions": "Query Brazilian soccer data: matches (Brasileirão Série A/B/C \
                    2003-2023, Copa do Brasil, Copa Libertadores), team statistics, standings, \
                    head-to-head records and FIFA 19 player data. Team names are normalized, so \
                    'Palmeiras', 'Palmeiras-SP' and accented/unaccented spellings all work."
            })),
            "ping" => Some(json!({})),
            "tools/list" => Some(json!({ "tools": tool_definitions() })),
            "tools/call" => {
                let name = msg
                    .pointer("/params/name")
                    .and_then(|v| v.as_str())
                    .unwrap_or("");
                let args = msg
                    .pointer("/params/arguments")
                    .cloned()
                    .unwrap_or_else(|| json!({}));
                Some(match self.call_tool(name, &args) {
                    Ok(text) => text_result(text),
                    Err(e) => error_result(e),
                })
            }
            "notifications/initialized" | "notifications/cancelled" => None,
            _ => {
                if is_notification {
                    None
                } else {
                    return Some(rpc_error(&id, -32601, &format!("Method not found: {}", method)));
                }
            }
        };
        if is_notification {
            return None;
        }
        result.map(|r| rpc_result(&id, r))
    }

    fn call_tool(&self, name: &str, args: &Value) -> Result<String, String> {
        let engine = QueryEngine::new(&self.data);
        match name {
            "search_matches" => {
                let filter = MatchFilter {
                    team: arg_str(args, "team"),
                    opponent: arg_str(args, "opponent"),
                    competition: arg_str(args, "competition"),
                    season: arg_i32(args, "season"),
                    date_from: arg_str(args, "date_from").as_deref().and_then(parse_date),
                    date_to: arg_str(args, "date_to").as_deref().and_then(parse_date),
                    stage: arg_str(args, "stage"),
                    limit: arg_usize(args, "limit").unwrap_or(20),
                };
                Ok(engine.search_matches(&filter))
            }
            "get_team_stats" => {
                let team = arg_str(args, "team")
                    .ok_or_else(|| "Missing required argument: team".to_string())?;
                Ok(engine.team_stats(
                    &team,
                    arg_i32(args, "season"),
                    arg_str(args, "competition"),
                    arg_str(args, "venue"),
                ))
            }
            "head_to_head" => {
                let t1 = arg_str(args, "team1")
                    .ok_or_else(|| "Missing required argument: team1".to_string())?;
                let t2 = arg_str(args, "team2")
                    .ok_or_else(|| "Missing required argument: team2".to_string())?;
                Ok(engine.head_to_head(&t1, &t2, arg_str(args, "competition")))
            }
            "get_standings" => {
                let season = arg_i32(args, "season")
                    .ok_or_else(|| "Missing required argument: season".to_string())?;
                Ok(engine.standings(season, arg_str(args, "competition")))
            }
            "get_competition_stats" => Ok(engine.competition_stats(
                arg_str(args, "competition"),
                arg_i32(args, "season"),
            )),
            "search_players" => Ok(engine.search_players(
                arg_str(args, "name"),
                arg_str(args, "nationality"),
                arg_str(args, "club"),
                arg_str(args, "position"),
                arg_i32(args, "min_overall"),
                arg_usize(args, "limit").unwrap_or(15),
            )),
            "get_player" => {
                let name = arg_str(args, "name")
                    .ok_or_else(|| "Missing required argument: name".to_string())?;
                Ok(engine.player_profile(&name))
            }
            "get_data_summary" => Ok(engine.data_summary()),
            other => Err(format!("Unknown tool: {}", other)),
        }
    }

    /// Blocking stdio loop: one JSON-RPC message per line.
    pub fn run<R: BufRead, W: Write>(&self, input: R, mut output: W) -> std::io::Result<()> {
        for line in input.lines() {
            let line = line?;
            if line.trim().is_empty() {
                continue;
            }
            let response = match serde_json::from_str::<Value>(&line) {
                Ok(msg) => self.handle(&msg),
                Err(e) => Some(rpc_error(
                    &Value::Null,
                    -32700,
                    &format!("Parse error: {}", e),
                )),
            };
            if let Some(resp) = response {
                serde_json::to_writer(&mut output, &resp)?;
                output.write_all(b"\n")?;
                output.flush()?;
            }
        }
        Ok(())
    }
}

/// MCP tool definitions with JSON Schema input descriptions.
pub fn tool_definitions() -> Value {
    json!([
        {
            "name": "search_matches",
            "description": "Search soccer matches by team, opponent, competition (Brasileirão Série A/B/C, Copa do Brasil, Copa Libertadores), season (year), date range or stage. When both team and opponent are given, a head-to-head summary is included. Use stage='final' to find cup finals.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team": { "type": "string", "description": "Team name, e.g. 'Flamengo' or 'Palmeiras-SP' (state suffix optional)" },
                    "opponent": { "type": "string", "description": "Second team to restrict to direct meetings" },
                    "competition": { "type": "string", "description": "Competition filter, e.g. 'Brasileirão', 'Serie A', 'Copa do Brasil', 'Libertadores'" },
                    "season": { "type": "integer", "description": "Season year, e.g. 2019" },
                    "date_from": { "type": "string", "description": "Earliest date, YYYY-MM-DD" },
                    "date_to": { "type": "string", "description": "Latest date, YYYY-MM-DD" },
                    "stage": { "type": "string", "description": "Tournament stage: 'group stage', 'round of 16', 'quarterfinals', 'semifinals', 'final'" },
                    "limit": { "type": "integer", "description": "Max matches to list (default 20)" }
                }
            }
        },
        {
            "name": "get_team_stats",
            "description": "Win/draw/loss record, goals for/against and win rate for a team, optionally filtered by season, competition and venue (home/away). Includes a per-competition breakdown.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team": { "type": "string", "description": "Team name" },
                    "season": { "type": "integer", "description": "Season year filter" },
                    "competition": { "type": "string", "description": "Competition filter" },
                    "venue": { "type": "string", "enum": ["home", "away"], "description": "Restrict to home or away matches" }
                },
                "required": ["team"]
            }
        },
        {
            "name": "head_to_head",
            "description": "Head-to-head record between two teams: wins/draws per side, aggregate goals, and the most recent meetings.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team1": { "type": "string", "description": "First team" },
                    "team2": { "type": "string", "description": "Second team" },
                    "competition": { "type": "string", "description": "Optional competition filter" }
                },
                "required": ["team1", "team2"]
            }
        },
        {
            "name": "get_standings",
            "description": "League table for a season calculated from match results (3 points per win, 1 per draw). Defaults to Brasileirão Série A; Serie A data covers 2003-2023. Marks the champion and the relegation zone.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "season": { "type": "integer", "description": "Season year, e.g. 2019" },
                    "competition": { "type": "string", "description": "Competition (default 'Brasileirão Série A'; 'Serie B' also available 2014-2023)" }
                },
                "required": ["season"]
            }
        },
        {
            "name": "get_competition_stats",
            "description": "Aggregate statistics for a competition and/or season: average goals per match, home-win/draw/away-win percentages, biggest victories and highest-scoring matches.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "competition": { "type": "string", "description": "Competition filter (omit for all)" },
                    "season": { "type": "integer", "description": "Season year filter (omit for all)" }
                }
            }
        },
        {
            "name": "search_players",
            "description": "Search the FIFA 19 player database by name, nationality, club, position (exact code like 'ST' or a group: forward/midfielder/defender/goalkeeper) and minimum overall rating. Results are sorted by overall rating descending.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": { "type": "string", "description": "Substring of player name" },
                    "nationality": { "type": "string", "description": "Country, e.g. 'Brazil'" },
                    "club": { "type": "string", "description": "Club name, e.g. 'Santos' or 'Grêmio'" },
                    "position": { "type": "string", "description": "Position code (ST, GK, CB, ...) or group (forward, midfielder, defender, goalkeeper)" },
                    "min_overall": { "type": "integer", "description": "Minimum FIFA overall rating" },
                    "limit": { "type": "integer", "description": "Max players to list (default 15)" }
                }
            }
        },
        {
            "name": "get_player",
            "description": "Detailed FIFA 19 profile for one player found by (partial) name: ratings, position, club, physique, value/wage and top skill attributes.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": { "type": "string", "description": "Player name, e.g. 'Gabriel Barbosa' or 'Neymar'" }
                },
                "required": ["name"]
            }
        },
        {
            "name": "get_data_summary",
            "description": "Inventory of the loaded datasets: row counts per CSV file, competitions with season ranges and match counts, distinct team count and player counts. Useful to learn what questions the data can answer.",
            "inputSchema": { "type": "object", "properties": {} }
        }
    ])
}
