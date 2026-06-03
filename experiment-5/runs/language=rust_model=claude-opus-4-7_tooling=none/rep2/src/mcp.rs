//! Minimal MCP (Model Context Protocol) server implementation.
//!
//! Implements JSON-RPC 2.0 over stdio with newline-delimited messages.
//! Supports the subset of MCP needed for tool calls:
//!
//! - `initialize`
//! - `notifications/initialized` (no response)
//! - `tools/list`
//! - `tools/call`
//! - `ping`
//! - `notifications/cancelled` (no-op)
//!
//! See https://modelcontextprotocol.io for the protocol specification.

use std::io::{BufRead, Write};

use anyhow::{anyhow, Result};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};

use crate::data::Dataset;
use crate::query::{
    biggest_wins, format_match_list, head_to_head, overall_stats, standings, team_stats,
    MatchQuery, PlayerQuery,
};

pub const PROTOCOL_VERSION: &str = "2024-11-05";
pub const SERVER_NAME: &str = "brazilian-soccer-mcp";
pub const SERVER_VERSION: &str = env!("CARGO_PKG_VERSION");

/// JSON-RPC 2.0 request envelope.
#[derive(Debug, Deserialize)]
pub struct Request {
    #[serde(rename = "jsonrpc")]
    pub _jsonrpc: Option<String>,
    pub id: Option<Value>,
    pub method: String,
    #[serde(default)]
    pub params: Value,
}

/// JSON-RPC 2.0 response envelope.
#[derive(Debug, Serialize)]
pub struct Response {
    pub jsonrpc: &'static str,
    pub id: Value,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub result: Option<Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<ResponseError>,
}

#[derive(Debug, Serialize)]
pub struct ResponseError {
    pub code: i32,
    pub message: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub data: Option<Value>,
}

impl Response {
    pub fn ok(id: Value, result: Value) -> Self {
        Response {
            jsonrpc: "2.0",
            id,
            result: Some(result),
            error: None,
        }
    }
    pub fn err(id: Value, code: i32, message: impl Into<String>) -> Self {
        Response {
            jsonrpc: "2.0",
            id,
            result: None,
            error: Some(ResponseError {
                code,
                message: message.into(),
                data: None,
            }),
        }
    }
}

/// MCP server bound to a dataset. Dispatches JSON-RPC requests to tool handlers.
pub struct Server {
    dataset: Dataset,
}

impl Server {
    pub fn new(dataset: Dataset) -> Self {
        Server { dataset }
    }

    /// Handle one JSON-RPC request and return the response (or `None` for notifications).
    pub fn handle(&self, req: Request) -> Option<Response> {
        let is_notification = req.id.is_none();
        let id = req.id.unwrap_or(Value::Null);

        let result: Result<Value> = match req.method.as_str() {
            "initialize" => self.handle_initialize(),
            "notifications/initialized" | "notifications/cancelled" => {
                return None;
            }
            "ping" => Ok(json!({})),
            "tools/list" => self.handle_tools_list(),
            "tools/call" => self.handle_tools_call(req.params),
            other => Err(anyhow!("method not found: {}", other)),
        };

        if is_notification {
            return None;
        }
        match result {
            Ok(value) => Some(Response::ok(id, value)),
            Err(e) => {
                let code = if req.method.as_str() == "tools/call" {
                    -32602
                } else {
                    -32601
                };
                Some(Response::err(id, code, e.to_string()))
            }
        }
    }

    fn handle_initialize(&self) -> Result<Value> {
        Ok(json!({
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {
                "tools": {}
            },
            "serverInfo": {
                "name": SERVER_NAME,
                "version": SERVER_VERSION
            },
            "instructions": "Brazilian soccer knowledge base with match data (Brasileirão, Copa do Brasil, Libertadores) and FIFA player ratings. Use list_tools to see available tools."
        }))
    }

    fn handle_tools_list(&self) -> Result<Value> {
        Ok(json!({ "tools": tool_definitions() }))
    }

    fn handle_tools_call(&self, params: Value) -> Result<Value> {
        let name = params
            .get("name")
            .and_then(|v| v.as_str())
            .ok_or_else(|| anyhow!("missing tool name"))?;
        let args = params.get("arguments").cloned().unwrap_or(json!({}));

        let (text, structured) = dispatch_tool(&self.dataset, name, args)?;
        Ok(json!({
            "content": [{"type": "text", "text": text}],
            "structuredContent": structured,
            "isError": false,
        }))
    }

    /// Run the stdio loop. Reads newline-delimited JSON-RPC, writes responses
    /// (also newline-delimited) to stdout.
    pub fn serve_stdio(self) -> Result<()> {
        let stdin = std::io::stdin();
        let stdout = std::io::stdout();
        let mut out = stdout.lock();

        for line in stdin.lock().lines() {
            let line = match line {
                Ok(s) => s,
                Err(_) => break,
            };
            let trimmed = line.trim();
            if trimmed.is_empty() {
                continue;
            }
            let req: Request = match serde_json::from_str(trimmed) {
                Ok(r) => r,
                Err(e) => {
                    let resp = Response::err(Value::Null, -32700, format!("parse error: {}", e));
                    writeln!(out, "{}", serde_json::to_string(&resp)?)?;
                    out.flush()?;
                    continue;
                }
            };
            if let Some(resp) = self.handle(req) {
                writeln!(out, "{}", serde_json::to_string(&resp)?)?;
                out.flush()?;
            }
        }
        Ok(())
    }
}

fn tool_definitions() -> Vec<Value> {
    vec![
        json!({
            "name": "search_matches",
            "description": "Find matches by team, competition, season, or date range.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team": {"type": "string", "description": "Match where either side is this team"},
                    "home_team": {"type": "string"},
                    "away_team": {"type": "string"},
                    "competition": {"type": "string", "description": "Substring match (e.g. 'Brasileir', 'Copa do Brasil', 'Libertadores')"},
                    "season": {"type": "integer"},
                    "date_from": {"type": "string", "description": "YYYY-MM-DD"},
                    "date_to": {"type": "string", "description": "YYYY-MM-DD"},
                    "limit": {"type": "integer", "default": 50}
                }
            }
        }),
        json!({
            "name": "head_to_head",
            "description": "Head-to-head record between two teams across all competitions.",
            "inputSchema": {
                "type": "object",
                "required": ["team_a", "team_b"],
                "properties": {
                    "team_a": {"type": "string"},
                    "team_b": {"type": "string"}
                }
            }
        }),
        json!({
            "name": "team_stats",
            "description": "Win/loss/draw record and goal totals for a team, optionally filtered by season and competition.",
            "inputSchema": {
                "type": "object",
                "required": ["team"],
                "properties": {
                    "team": {"type": "string"},
                    "season": {"type": "integer"},
                    "competition": {"type": "string"}
                }
            }
        }),
        json!({
            "name": "standings",
            "description": "Compute a final league table for a season from match results.",
            "inputSchema": {
                "type": "object",
                "required": ["season"],
                "properties": {
                    "season": {"type": "integer"},
                    "competition": {"type": "string", "description": "Defaults to 'Brasileir'"},
                    "limit": {"type": "integer", "default": 20}
                }
            }
        }),
        json!({
            "name": "search_players",
            "description": "Find FIFA players by name, nationality, club, position, and minimum rating.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "nationality": {"type": "string"},
                    "club": {"type": "string"},
                    "position": {"type": "string"},
                    "min_overall": {"type": "integer"},
                    "limit": {"type": "integer", "default": 25}
                }
            }
        }),
        json!({
            "name": "biggest_wins",
            "description": "Largest victory margins, optionally filtered by competition.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "competition": {"type": "string"},
                    "limit": {"type": "integer", "default": 10}
                }
            }
        }),
        json!({
            "name": "overall_stats",
            "description": "Aggregate stats: matches, goals, home/away/draw rates, average goals per match.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "season": {"type": "integer"},
                    "competition": {"type": "string"}
                }
            }
        }),
    ]
}

fn dispatch_tool(ds: &Dataset, name: &str, args: Value) -> Result<(String, Value)> {
    match name {
        "search_matches" => {
            let q: MatchQuery = serde_json::from_value(args)?;
            let limit = q.limit.unwrap_or(50);
            let mut q2 = q.clone();
            q2.limit = Some(limit);
            let matches = q2.filter(ds);
            let text = if matches.is_empty() {
                "No matches found.".to_string()
            } else {
                let mut t = format!("Found {} match(es):\n", matches.len());
                t.push_str(&format_match_list(&matches, limit));
                t
            };
            let structured = json!({
                "count": matches.len(),
                "matches": matches,
            });
            Ok((text, structured))
        }
        "head_to_head" => {
            let a = args
                .get("team_a")
                .and_then(|v| v.as_str())
                .ok_or_else(|| anyhow!("missing team_a"))?;
            let b = args
                .get("team_b")
                .and_then(|v| v.as_str())
                .ok_or_else(|| anyhow!("missing team_b"))?;
            let h = head_to_head(ds, a, b);
            let text = format!(
                "{} vs {} — {} matches\n{}: {} wins ({} goals)\n{}: {} wins ({} goals)\nDraws: {}\n",
                h.team_a,
                h.team_b,
                h.matches,
                h.team_a,
                h.team_a_wins,
                h.team_a_goals,
                h.team_b,
                h.team_b_wins,
                h.team_b_goals,
                h.draws
            );
            Ok((text, serde_json::to_value(&h)?))
        }
        "team_stats" => {
            let team = args
                .get("team")
                .and_then(|v| v.as_str())
                .ok_or_else(|| anyhow!("missing team"))?;
            let season = args.get("season").and_then(|v| v.as_i64()).map(|v| v as i32);
            let competition = args.get("competition").and_then(|v| v.as_str());
            let s = team_stats(ds, team, season, competition);
            let text = format!(
                "{} — {}{}{}\nMatches: {}, Wins: {}, Draws: {}, Losses: {}\nGoals: {} for, {} against (diff {})\nHome: {}W-{}D-{}L ({} GF, {} GA)\nAway: {}W-{}D-{}L ({} GF, {} GA)\nPoints (3W+1D): {}\nWin rate: {:.1}%\n",
                team,
                season.map(|y| format!("season {} ", y)).unwrap_or_default(),
                competition.map(|c| format!("({}) ", c)).unwrap_or_default(),
                "",
                s.matches, s.wins, s.draws, s.losses,
                s.goals_for, s.goals_against, s.goals_for - s.goals_against,
                s.home_wins, s.home_draws, s.home_losses, s.home_goals_for, s.home_goals_against,
                s.away_wins, s.away_draws, s.away_losses, s.away_goals_for, s.away_goals_against,
                s.points(),
                s.win_rate() * 100.0,
            );
            Ok((text, serde_json::to_value(&s)?))
        }
        "standings" => {
            let season = args
                .get("season")
                .and_then(|v| v.as_i64())
                .ok_or_else(|| anyhow!("missing season"))?
                as i32;
            let comp = args.get("competition").and_then(|v| v.as_str());
            let comp = comp.or(Some("Brasileir"));
            let limit = args
                .get("limit")
                .and_then(|v| v.as_u64())
                .map(|v| v as usize)
                .unwrap_or(20);
            let table = standings(ds, season, comp);
            let mut text = format!(
                "{} season {} standings:\n",
                comp.unwrap_or(""),
                season
            );
            for row in table.iter().take(limit) {
                text.push_str(&format!(
                    "{:>2}. {:<30} {:>3} pts ({}W-{}D-{}L, GD {:+})\n",
                    row.rank,
                    truncate(&row.team, 30),
                    row.points,
                    row.wins,
                    row.draws,
                    row.losses,
                    row.goal_difference,
                ));
            }
            let truncated: Vec<_> = table.into_iter().take(limit).collect();
            Ok((text, serde_json::to_value(&truncated)?))
        }
        "search_players" => {
            let mut q: PlayerQuery = serde_json::from_value(args)?;
            if q.limit.is_none() {
                q.limit = Some(25);
            }
            let players = q.filter(ds);
            let mut text = format!("Found {} player(s):\n", players.len());
            for p in &players {
                text.push_str(&format!(
                    "- {} ({}) — Overall {}, Position {}, Club: {}\n",
                    p.name,
                    p.nationality,
                    p.overall.map(|v| v.to_string()).unwrap_or_else(|| "?".into()),
                    p.position.clone().unwrap_or_else(|| "?".into()),
                    p.club,
                ));
            }
            Ok((text, json!({ "count": players.len(), "players": players })))
        }
        "biggest_wins" => {
            let comp = args.get("competition").and_then(|v| v.as_str());
            let limit = args
                .get("limit")
                .and_then(|v| v.as_u64())
                .map(|v| v as usize)
                .unwrap_or(10);
            let rows = biggest_wins(ds, limit, comp);
            let mut text = String::from("Biggest victories:\n");
            for (i, r) in rows.iter().enumerate() {
                let date = r
                    .match_
                    .date_iso()
                    .unwrap_or_else(|| r.match_.date_raw.clone());
                text.push_str(&format!(
                    "{:>2}. {}: {} {}-{} {} ({}, margin {})\n",
                    i + 1,
                    date,
                    r.match_.home_team,
                    r.match_.home_goal.unwrap_or(0),
                    r.match_.away_goal.unwrap_or(0),
                    r.match_.away_team,
                    r.match_.competition,
                    r.margin,
                ));
            }
            Ok((text, serde_json::to_value(&rows)?))
        }
        "overall_stats" => {
            let season = args.get("season").and_then(|v| v.as_i64()).map(|v| v as i32);
            let comp = args.get("competition").and_then(|v| v.as_str());
            let s = overall_stats(ds, season, comp);
            let text = format!(
                "Aggregate over {} match(es){}{}\nGoals: {} (avg {:.2}/match)\nHome win rate: {:.1}%\nAway win rate: {:.1}%\nDraw rate: {:.1}%\n",
                s.matches,
                s.season.map(|y| format!(", season {}", y)).unwrap_or_default(),
                s.competition.clone().map(|c| format!(", competition {}", c)).unwrap_or_default(),
                s.goals,
                s.avg_goals_per_match,
                s.home_win_rate * 100.0,
                s.away_win_rate * 100.0,
                s.draw_rate * 100.0,
            );
            Ok((text, serde_json::to_value(&s)?))
        }
        other => Err(anyhow!("unknown tool: {}", other)),
    }
}

fn truncate(s: &str, n: usize) -> String {
    if s.chars().count() <= n {
        s.to_string()
    } else {
        let cut: String = s.chars().take(n.saturating_sub(1)).collect();
        format!("{}…", cut)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;

    fn make_server() -> Server {
        let dir = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("data/kaggle");
        Server::new(Dataset::load_from_dir(&dir).unwrap())
    }

    #[test]
    fn initialize_returns_protocol_version() {
        let s = make_server();
        let req = Request {
            _jsonrpc: Some("2.0".into()),
            id: Some(json!(1)),
            method: "initialize".into(),
            params: json!({}),
        };
        let resp = s.handle(req).unwrap();
        assert!(resp.error.is_none());
        let r = resp.result.unwrap();
        assert_eq!(r["protocolVersion"], json!(PROTOCOL_VERSION));
        assert!(r["capabilities"]["tools"].is_object());
    }

    #[test]
    fn tools_list_includes_expected() {
        let s = make_server();
        let req = Request {
            _jsonrpc: Some("2.0".into()),
            id: Some(json!(1)),
            method: "tools/list".into(),
            params: json!({}),
        };
        let resp = s.handle(req).unwrap();
        let r = resp.result.unwrap();
        let tools = r["tools"].as_array().unwrap();
        let names: Vec<&str> = tools.iter().map(|t| t["name"].as_str().unwrap()).collect();
        for n in [
            "search_matches",
            "head_to_head",
            "team_stats",
            "standings",
            "search_players",
            "biggest_wins",
            "overall_stats",
        ] {
            assert!(names.contains(&n), "missing tool {}", n);
        }
    }

    #[test]
    fn call_head_to_head() {
        let s = make_server();
        let req = Request {
            _jsonrpc: Some("2.0".into()),
            id: Some(json!(1)),
            method: "tools/call".into(),
            params: json!({
                "name": "head_to_head",
                "arguments": {"team_a": "Flamengo", "team_b": "Fluminense"}
            }),
        };
        let resp = s.handle(req).unwrap();
        assert!(resp.error.is_none(), "error: {:?}", resp.error);
        let r = resp.result.unwrap();
        let content = r["content"][0]["text"].as_str().unwrap();
        assert!(content.contains("Flamengo"));
        assert!(content.contains("matches"));
        assert!(r["structuredContent"]["matches"].as_u64().unwrap() > 0);
    }

    #[test]
    fn call_search_matches_by_team_year() {
        let s = make_server();
        let req = Request {
            _jsonrpc: Some("2.0".into()),
            id: Some(json!(1)),
            method: "tools/call".into(),
            params: json!({
                "name": "search_matches",
                "arguments": {"team": "Palmeiras", "season": 2023, "limit": 10}
            }),
        };
        let resp = s.handle(req).unwrap();
        assert!(resp.error.is_none());
        let r = resp.result.unwrap();
        assert!(r["structuredContent"]["count"].as_u64().unwrap() > 0);
    }

    #[test]
    fn call_standings_for_2019() {
        let s = make_server();
        let req = Request {
            _jsonrpc: Some("2.0".into()),
            id: Some(json!(1)),
            method: "tools/call".into(),
            params: json!({
                "name": "standings",
                "arguments": {"season": 2019, "limit": 5}
            }),
        };
        let resp = s.handle(req).unwrap();
        assert!(resp.error.is_none());
        let r = resp.result.unwrap();
        let text = r["content"][0]["text"].as_str().unwrap();
        assert!(text.to_lowercase().contains("flamengo"));
    }

    #[test]
    fn call_search_players_brazilian() {
        let s = make_server();
        let req = Request {
            _jsonrpc: Some("2.0".into()),
            id: Some(json!(1)),
            method: "tools/call".into(),
            params: json!({
                "name": "search_players",
                "arguments": {"nationality": "Brazil", "limit": 5}
            }),
        };
        let resp = s.handle(req).unwrap();
        assert!(resp.error.is_none());
        let r = resp.result.unwrap();
        assert_eq!(r["structuredContent"]["count"].as_u64().unwrap(), 5);
    }

    #[test]
    fn unknown_method_returns_error() {
        let s = make_server();
        let req = Request {
            _jsonrpc: Some("2.0".into()),
            id: Some(json!(1)),
            method: "no_such".into(),
            params: json!({}),
        };
        let resp = s.handle(req).unwrap();
        assert!(resp.error.is_some());
        assert_eq!(resp.error.unwrap().code, -32601);
    }

    #[test]
    fn notification_returns_none() {
        let s = make_server();
        let req = Request {
            _jsonrpc: Some("2.0".into()),
            id: None,
            method: "notifications/initialized".into(),
            params: json!({}),
        };
        assert!(s.handle(req).is_none());
    }
}
