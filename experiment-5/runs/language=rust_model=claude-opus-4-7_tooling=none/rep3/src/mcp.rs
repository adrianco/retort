//! Minimal Model Context Protocol (MCP) server.
//!
//! Implements just enough of the JSON-RPC 2.0 surface to expose our query
//! engine as MCP tools over stdio.  Methods handled:
//!   - `initialize`              -> server info + capabilities
//!   - `notifications/initialized` (notification, no response)
//!   - `tools/list`              -> registered tool descriptors
//!   - `tools/call`              -> dispatch to the corresponding query
//!   - `ping`                    -> empty result
//!   - `prompts/list` / `resources/list` -> empty lists (avoids client errors)
//!
//! Tools are dispatched purely by their `name` field; arguments are matched
//! against this module's per-tool input schemas.

use std::io::{BufRead, Write};

use anyhow::{anyhow, Result};
use serde::Deserialize;
use serde_json::{json, Value};

use crate::data::{Competition, Dataset};
use crate::queries::{
    biggest_wins, competition_stats, find_matches, find_players, head_to_head, standings,
    team_record, MatchFilter, MatchSummary, PlayerFilter, Venue,
};

const PROTOCOL_VERSION: &str = "2024-11-05";
const SERVER_NAME: &str = "brazilian-soccer-mcp";
const SERVER_VERSION: &str = env!("CARGO_PKG_VERSION");

/// Run the MCP server, reading newline-delimited JSON-RPC frames from `input`
/// and writing replies to `output` until EOF.
pub fn serve<R: BufRead, W: Write>(ds: &Dataset, input: R, mut output: W) -> Result<()> {
    for line in input.lines() {
        let line = line?;
        if line.trim().is_empty() {
            continue;
        }
        let req: Value = match serde_json::from_str(&line) {
            Ok(v) => v,
            Err(e) => {
                let err = json!({
                    "jsonrpc": "2.0",
                    "id": Value::Null,
                    "error": { "code": -32700, "message": format!("parse error: {e}") }
                });
                writeln!(output, "{}", err)?;
                output.flush()?;
                continue;
            }
        };
        if let Some(resp) = handle(ds, &req) {
            writeln!(output, "{}", resp)?;
            output.flush()?;
        }
    }
    Ok(())
}

/// Dispatch a single JSON-RPC request.  Returns `None` for notifications
/// (which must not produce a reply).
pub fn handle(ds: &Dataset, req: &Value) -> Option<Value> {
    let id = req.get("id").cloned();
    let method = req.get("method").and_then(|m| m.as_str()).unwrap_or("");
    let params = req.get("params").cloned().unwrap_or(Value::Null);

    // Notifications: no `id` field — never reply.
    let is_notification = id.is_none();

    let result = match method {
        "initialize" => Ok(initialize_result()),
        "notifications/initialized" => {
            // Notification — drop.
            return None;
        }
        "ping" => Ok(json!({})),
        "tools/list" => Ok(json!({ "tools": tool_list() })),
        "tools/call" => match call_tool(ds, &params) {
            Ok(v) => Ok(v),
            Err(e) => Err((-32602, format!("tool error: {e}"))),
        },
        "prompts/list" => Ok(json!({ "prompts": [] })),
        "resources/list" => Ok(json!({ "resources": [] })),
        "resources/templates/list" => Ok(json!({ "resourceTemplates": [] })),
        _ => Err((-32601, format!("method not found: {method}"))),
    };

    if is_notification {
        return None;
    }

    let resp = match result {
        Ok(v) => json!({ "jsonrpc": "2.0", "id": id, "result": v }),
        Err((code, msg)) => json!({
            "jsonrpc": "2.0",
            "id": id,
            "error": { "code": code, "message": msg }
        }),
    };
    Some(resp)
}

fn initialize_result() -> Value {
    json!({
        "protocolVersion": PROTOCOL_VERSION,
        "capabilities": {
            "tools": { "listChanged": false }
        },
        "serverInfo": {
            "name": SERVER_NAME,
            "version": SERVER_VERSION
        },
        "instructions": "Tools answer questions over bundled Brazilian soccer datasets (Brasileirão Série A, Copa do Brasil, Libertadores, an extended stats CSV, a 2003-2019 historical Brasileirão, and the FIFA player database)."
    })
}

// ---------------------------------------------------------------------------
// Tool registry
// ---------------------------------------------------------------------------

fn tool_list() -> Vec<Value> {
    vec![
        json!({
            "name": "find_matches",
            "description": "Find matches in the dataset filtered by team, opponent, season, and/or competition. Returns matches sorted by date (most recent first).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team": { "type": "string", "description": "Team name (any spelling). Optional." },
                    "opponent": { "type": "string", "description": "Opposing team. Optional." },
                    "season": { "type": "integer", "description": "Season year, e.g. 2019. Optional." },
                    "competition": {
                        "type": "string",
                        "enum": ["brasileirao", "brasileirao_b", "brasileirao_c", "copa_do_brasil", "libertadores", "historico"],
                        "description": "Competition filter. Optional."
                    },
                    "venue": { "type": "string", "enum": ["home", "away", "all"], "default": "all" },
                    "limit": { "type": "integer", "minimum": 1, "default": 25 }
                }
            }
        }),
        json!({
            "name": "team_record",
            "description": "Wins, draws, losses, goals scored/conceded, win rate for a team — optionally restricted to a season, competition, and home/away venue.",
            "inputSchema": {
                "type": "object",
                "required": ["team"],
                "properties": {
                    "team": { "type": "string" },
                    "season": { "type": "integer" },
                    "competition": {
                        "type": "string",
                        "enum": ["brasileirao", "brasileirao_b", "brasileirao_c", "copa_do_brasil", "libertadores", "historico"]
                    },
                    "venue": { "type": "string", "enum": ["home", "away", "all"], "default": "all" }
                }
            }
        }),
        json!({
            "name": "head_to_head",
            "description": "Head-to-head record between two teams across all loaded competitions.",
            "inputSchema": {
                "type": "object",
                "required": ["team_a", "team_b"],
                "properties": {
                    "team_a": { "type": "string" },
                    "team_b": { "type": "string" }
                }
            }
        }),
        json!({
            "name": "standings",
            "description": "Final calculated standings for a given season + competition (computed from match results: 3 pts win, 1 pt draw, tiebreak by wins/goal difference/goals for).",
            "inputSchema": {
                "type": "object",
                "required": ["season", "competition"],
                "properties": {
                    "season": { "type": "integer" },
                    "competition": {
                        "type": "string",
                        "enum": ["brasileirao", "brasileirao_b", "brasileirao_c", "copa_do_brasil", "libertadores", "historico"]
                    },
                    "limit": { "type": "integer", "minimum": 1, "default": 20 }
                }
            }
        }),
        json!({
            "name": "find_players",
            "description": "Search the FIFA player database by name, nationality, club and/or position. Sorted by overall rating by default.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": { "type": "string" },
                    "nationality": { "type": "string" },
                    "club": { "type": "string" },
                    "position": { "type": "string" },
                    "min_overall": { "type": "integer" },
                    "sort_by_overall": { "type": "boolean", "default": true },
                    "limit": { "type": "integer", "minimum": 1, "default": 20 }
                }
            }
        }),
        json!({
            "name": "competition_stats",
            "description": "Aggregate statistics for a competition/season: match count, total goals, average goals per match, home/away/draw rates.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "competition": {
                        "type": "string",
                        "enum": ["brasileirao", "brasileirao_b", "brasileirao_c", "copa_do_brasil", "libertadores", "historico"]
                    },
                    "season": { "type": "integer" }
                }
            }
        }),
        json!({
            "name": "biggest_wins",
            "description": "The biggest goal-difference wins in the dataset, optionally filtered by competition and season.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "competition": {
                        "type": "string",
                        "enum": ["brasileirao", "brasileirao_b", "brasileirao_c", "copa_do_brasil", "libertadores", "historico"]
                    },
                    "season": { "type": "integer" },
                    "limit": { "type": "integer", "minimum": 1, "default": 10 }
                }
            }
        }),
        json!({
            "name": "dataset_summary",
            "description": "How many matches and players are loaded and from which sources.",
            "inputSchema": { "type": "object", "properties": {} }
        }),
    ]
}

// ---------------------------------------------------------------------------
// Tool dispatch
// ---------------------------------------------------------------------------

fn parse_competition(s: &str) -> Option<Competition> {
    match s {
        "brasileirao" | "brasileirao_a" | "serie_a" => Some(Competition::BrasileiraoSerieA),
        "brasileirao_b" | "serie_b" => Some(Competition::BrasileiraoSerieB),
        "brasileirao_c" | "serie_c" => Some(Competition::BrasileiraoSerieC),
        "copa_do_brasil" | "cup" => Some(Competition::CopaDoBrasil),
        "libertadores" => Some(Competition::Libertadores),
        "historico" | "novo" => Some(Competition::BrasileiraoHistorico),
        _ => None,
    }
}

fn parse_venue(s: Option<&str>) -> Venue {
    match s {
        Some("home") => Venue::Home,
        Some("away") => Venue::Away,
        _ => Venue::All,
    }
}

#[derive(Deserialize)]
struct CallArgs {
    name: String,
    #[serde(default)]
    arguments: Value,
}

fn call_tool(ds: &Dataset, params: &Value) -> Result<Value> {
    let call: CallArgs = serde_json::from_value(params.clone())
        .map_err(|e| anyhow!("invalid tools/call params: {e}"))?;
    let args = &call.arguments;
    let payload = match call.name.as_str() {
        "find_matches" => tool_find_matches(ds, args)?,
        "team_record" => tool_team_record(ds, args)?,
        "head_to_head" => tool_head_to_head(ds, args)?,
        "standings" => tool_standings(ds, args)?,
        "find_players" => tool_find_players(ds, args)?,
        "competition_stats" => tool_competition_stats(ds, args)?,
        "biggest_wins" => tool_biggest_wins(ds, args)?,
        "dataset_summary" => tool_dataset_summary(ds),
        other => return Err(anyhow!("unknown tool: {other}")),
    };

    // MCP tool results use a `content` array; we also include the raw JSON
    // under `structuredContent` so programmatic clients can read it directly.
    let text = serde_json::to_string_pretty(&payload).unwrap_or_else(|_| payload.to_string());
    Ok(json!({
        "content": [
            { "type": "text", "text": text }
        ],
        "structuredContent": payload,
        "isError": false
    }))
}

fn s(args: &Value, key: &str) -> Option<String> {
    args.get(key)
        .and_then(|v| v.as_str())
        .map(|s| s.to_string())
}

fn i(args: &Value, key: &str) -> Option<i64> {
    args.get(key).and_then(|v| v.as_i64())
}

fn b(args: &Value, key: &str) -> Option<bool> {
    args.get(key).and_then(|v| v.as_bool())
}

fn tool_find_matches(ds: &Dataset, args: &Value) -> Result<Value> {
    let team = s(args, "team");
    let opponent = s(args, "opponent");
    let competition = s(args, "competition").and_then(|c| parse_competition(&c));
    let venue = s(args, "venue");
    let v = parse_venue(venue.as_deref());
    let limit = i(args, "limit").map(|n| n as usize).or(Some(25));
    let f = MatchFilter {
        team: team.as_deref(),
        opponent: opponent.as_deref(),
        season: i(args, "season").map(|n| n as i32),
        competition,
        home_only: matches!(v, Venue::Home),
        away_only: matches!(v, Venue::Away),
        limit,
    };
    let ms = find_matches(ds, &f);
    let summaries: Vec<MatchSummary> = ms.iter().map(|m| MatchSummary::from(*m)).collect();
    let total = summaries.len();
    Ok(json!({ "count": total, "matches": summaries }))
}

fn tool_team_record(ds: &Dataset, args: &Value) -> Result<Value> {
    let team = s(args, "team").ok_or_else(|| anyhow!("missing 'team'"))?;
    let season = i(args, "season").map(|n| n as i32);
    let competition = s(args, "competition").and_then(|c| parse_competition(&c));
    let venue = parse_venue(s(args, "venue").as_deref());
    let rec = team_record(ds, &team, season, competition, venue);
    Ok(json!({
        "team": rec.team,
        "season": season,
        "competition": competition.map(|c| c.label()),
        "matches": rec.matches,
        "wins": rec.wins,
        "draws": rec.draws,
        "losses": rec.losses,
        "goals_for": rec.goals_for,
        "goals_against": rec.goals_against,
        "goal_difference": rec.goal_difference(),
        "points": rec.points(),
        "win_rate": rec.win_rate(),
    }))
}

fn tool_head_to_head(ds: &Dataset, args: &Value) -> Result<Value> {
    let a = s(args, "team_a").ok_or_else(|| anyhow!("missing 'team_a'"))?;
    let b = s(args, "team_b").ok_or_else(|| anyhow!("missing 'team_b'"))?;
    let h = head_to_head(ds, &a, &b);
    Ok(serde_json::to_value(h)?)
}

fn tool_standings(ds: &Dataset, args: &Value) -> Result<Value> {
    let season = i(args, "season").ok_or_else(|| anyhow!("missing 'season'"))? as i32;
    let comp = s(args, "competition").ok_or_else(|| anyhow!("missing 'competition'"))?;
    let comp = parse_competition(&comp).ok_or_else(|| anyhow!("unknown competition"))?;
    let limit = i(args, "limit").map(|n| n as usize).unwrap_or(20);
    let mut rows = standings(ds, season, comp);
    rows.truncate(limit);
    Ok(json!({
        "season": season,
        "competition": comp.label(),
        "rows": rows,
    }))
}

fn tool_find_players(ds: &Dataset, args: &Value) -> Result<Value> {
    let name = s(args, "name");
    let nat = s(args, "nationality");
    let club = s(args, "club");
    let pos = s(args, "position");
    let min_overall = i(args, "min_overall").map(|n| n as i32);
    let sort_by_overall = b(args, "sort_by_overall").unwrap_or(true);
    let limit = i(args, "limit").map(|n| n as usize).or(Some(20));
    let f = PlayerFilter {
        name: name.as_deref(),
        nationality: nat.as_deref(),
        club: club.as_deref(),
        position: pos.as_deref(),
        min_overall,
        limit,
        sort_by_overall,
    };
    let ps = find_players(ds, &f);
    Ok(json!({
        "count": ps.len(),
        "players": ps,
    }))
}

fn tool_competition_stats(ds: &Dataset, args: &Value) -> Result<Value> {
    let comp = s(args, "competition").and_then(|c| parse_competition(&c));
    let season = i(args, "season").map(|n| n as i32);
    let st = competition_stats(ds, comp, season);
    Ok(serde_json::to_value(st)?)
}

fn tool_biggest_wins(ds: &Dataset, args: &Value) -> Result<Value> {
    let comp = s(args, "competition").and_then(|c| parse_competition(&c));
    let season = i(args, "season").map(|n| n as i32);
    let limit = i(args, "limit").map(|n| n as usize).unwrap_or(10);
    let ms = biggest_wins(ds, comp, season, limit);
    let summaries: Vec<MatchSummary> = ms.iter().map(|m| MatchSummary::from(*m)).collect();
    Ok(json!({ "count": summaries.len(), "matches": summaries }))
}

fn tool_dataset_summary(ds: &Dataset) -> Value {
    use std::collections::BTreeMap;
    let mut by_comp: BTreeMap<&'static str, usize> = BTreeMap::new();
    for m in &ds.matches {
        *by_comp.entry(m.competition.label()).or_insert(0) += 1;
    }
    json!({
        "total_matches": ds.matches.len(),
        "total_players": ds.players.len(),
        "matches_by_competition": by_comp,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::data::Dataset;
    use std::path::PathBuf;

    fn ds() -> Dataset {
        Dataset::load_from_dir(
            PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("data/kaggle"),
        )
        .unwrap()
    }

    #[test]
    fn initialize_returns_server_info() {
        let req = json!({ "jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {} });
        let resp = handle(&ds(), &req).unwrap();
        assert_eq!(resp["id"], 1);
        assert_eq!(resp["result"]["serverInfo"]["name"], SERVER_NAME);
        assert_eq!(resp["result"]["protocolVersion"], PROTOCOL_VERSION);
    }

    #[test]
    fn tools_list_includes_all_tools() {
        let req = json!({ "jsonrpc": "2.0", "id": 2, "method": "tools/list" });
        let resp = handle(&ds(), &req).unwrap();
        let tools = resp["result"]["tools"].as_array().unwrap();
        let names: Vec<&str> = tools.iter().map(|t| t["name"].as_str().unwrap()).collect();
        for expected in [
            "find_matches", "team_record", "head_to_head", "standings",
            "find_players", "competition_stats", "biggest_wins", "dataset_summary",
        ] {
            assert!(names.contains(&expected), "missing tool: {expected}");
        }
    }

    #[test]
    fn notifications_initialized_returns_none() {
        let req = json!({
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {}
        });
        assert!(handle(&ds(), &req).is_none());
    }

    #[test]
    fn unknown_method_returns_error() {
        let req = json!({ "jsonrpc": "2.0", "id": 99, "method": "no/such" });
        let resp = handle(&ds(), &req).unwrap();
        assert_eq!(resp["error"]["code"], -32601);
    }
}
