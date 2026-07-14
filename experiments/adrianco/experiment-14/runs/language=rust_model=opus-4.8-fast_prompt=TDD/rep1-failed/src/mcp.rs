//! Model Context Protocol server.
//!
//! Speaks JSON-RPC 2.0 over stdio using newline-delimited messages (the MCP
//! stdio transport). Implements `initialize`, `tools/list` and `tools/call`,
//! exposing the [`crate::query`] engine as nine tools. Tool results are
//! human-readable text formatted in the style of the specification examples.

use crate::data::Database;
use crate::models::Competition;
use crate::query::{self, MatchFilter, PlayerFilter};
use serde_json::{json, Value};
use std::io::{BufRead, Write};

/// Protocol version advertised to clients.
const PROTOCOL_VERSION: &str = "2024-11-05";

/// An MCP server wrapping a loaded [`Database`].
pub struct McpServer {
    db: Database,
}

impl McpServer {
    pub fn new(db: Database) -> Self {
        McpServer { db }
    }

    /// Run the blocking stdio request loop.
    pub fn run(&self) -> std::io::Result<()> {
        let stdin = std::io::stdin();
        let stdout = std::io::stdout();
        let mut out = stdout.lock();
        for line in stdin.lock().lines() {
            let line = line?;
            if line.trim().is_empty() {
                continue;
            }
            if let Some(resp) = self.handle_line(&line) {
                writeln!(out, "{}", resp)?;
                out.flush()?;
            }
        }
        Ok(())
    }

    /// Handle one line of input, returning the JSON response line (or `None`
    /// for notifications and unparseable input).
    pub fn handle_line(&self, line: &str) -> Option<String> {
        let req: Value = serde_json::from_str(line).ok()?;
        let resp = self.handle_request(&req)?;
        serde_json::to_string(&resp).ok()
    }

    /// Dispatch a parsed JSON-RPC request. Returns `None` for notifications
    /// (requests without an `id`), which must not produce a response.
    pub fn handle_request(&self, req: &Value) -> Option<Value> {
        let method = req.get("method").and_then(Value::as_str).unwrap_or("");
        let id = req.get("id").cloned();

        // Notifications have no id and expect no response.
        if id.is_none() {
            return None;
        }
        let id = id.unwrap();

        match method {
            "initialize" => Some(ok(
                id,
                json!({
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": { "tools": {} },
                    "serverInfo": { "name": "brazilian-soccer-mcp", "version": env!("CARGO_PKG_VERSION") }
                }),
            )),
            "ping" => Some(ok(id, json!({}))),
            "tools/list" => Some(ok(id, json!({ "tools": tool_definitions() }))),
            "tools/call" => {
                let params = req.get("params").cloned().unwrap_or(json!({}));
                let name = params.get("name").and_then(Value::as_str).unwrap_or("");
                let args = params.get("arguments").cloned().unwrap_or(json!({}));
                match self.call_tool(name, &args) {
                    Ok(text) => Some(ok(
                        id,
                        json!({ "content": [ { "type": "text", "text": text } ] }),
                    )),
                    Err(msg) => Some(ok(
                        id,
                        json!({
                            "content": [ { "type": "text", "text": format!("Error: {msg}") } ],
                            "isError": true
                        }),
                    )),
                }
            }
            _ => Some(err(id, -32601, &format!("Method not found: {method}"))),
        }
    }

    /// Execute a named tool against the database, returning formatted text.
    fn call_tool(&self, name: &str, args: &Value) -> Result<String, String> {
        match name {
            "find_matches" => Ok(self.tool_find_matches(args)),
            "head_to_head" => self.tool_head_to_head(args),
            "team_record" => self.tool_team_record(args),
            "find_players" => Ok(self.tool_find_players(args)),
            "standings" => self.tool_standings(args),
            "goal_stats" => Ok(self.tool_goal_stats(args)),
            "biggest_wins" => Ok(self.tool_biggest_wins(args)),
            "team_rankings" => Ok(self.tool_team_rankings(args)),
            "competitions_for_team" => self.tool_competitions_for_team(args),
            other => Err(format!("Unknown tool: {other}")),
        }
    }

    fn match_filter(&self, args: &Value) -> MatchFilter {
        MatchFilter {
            team: str_arg(args, "team"),
            opponent: str_arg(args, "opponent"),
            home_only: bool_arg(args, "home_only"),
            away_only: bool_arg(args, "away_only"),
            competition: str_arg(args, "competition").and_then(|s| parse_competition(&s)),
            season: int_arg(args, "season").map(|v| v as i32),
            date_from: str_arg(args, "date_from"),
            date_to: str_arg(args, "date_to"),
            limit: int_arg(args, "limit").map(|v| v as usize),
        }
    }

    fn tool_find_matches(&self, args: &Value) -> String {
        let mut filter = self.match_filter(args);
        let display_limit = filter.limit.unwrap_or(20);
        filter.limit = None;
        let matches = query::find_matches(&self.db, &filter);
        if matches.is_empty() {
            return "No matches found for the given criteria.".to_string();
        }
        let total = matches.len();
        let mut lines = vec![format!("Found {total} match(es):")];
        for m in matches.iter().take(display_limit) {
            lines.push(format!("- {}", format_match(m)));
        }
        if total > display_limit {
            lines.push(format!("- ... ({} more)", total - display_limit));
        }
        // Head-to-head summary when two named teams were given.
        if let (Some(a), Some(b)) = (&filter.team, &filter.opponent) {
            let h = query::head_to_head(&self.db, a, b);
            lines.push(String::new());
            lines.push(format!(
                "Head-to-head: {} {} wins, {} {} wins, {} draws",
                h.team_a, h.team_a_wins, h.team_b, h.team_b_wins, h.draws
            ));
        }
        lines.join("\n")
    }

    fn tool_head_to_head(&self, args: &Value) -> Result<String, String> {
        let a = str_arg(args, "team_a").ok_or("missing 'team_a'")?;
        let b = str_arg(args, "team_b").ok_or("missing 'team_b'")?;
        let h = query::head_to_head(&self.db, &a, &b);
        if h.total == 0 {
            return Ok(format!("No matches found between {} and {}.", h.team_a, h.team_b));
        }
        Ok(format!(
            "{} vs {} (head-to-head in dataset):\n\
             - Matches: {}\n\
             - {} wins: {}\n\
             - {} wins: {}\n\
             - Draws: {}\n\
             - Goals: {} {}, {} {}",
            h.team_a, h.team_b, h.total, h.team_a, h.team_a_wins, h.team_b, h.team_b_wins, h.draws,
            h.team_a, h.team_a_goals, h.team_b, h.team_b_goals
        ))
    }

    fn tool_team_record(&self, args: &Value) -> Result<String, String> {
        if str_arg(args, "team").is_none() {
            return Err("missing 'team'".into());
        }
        let filter = self.match_filter(args);
        let r = query::team_record(&self.db, &filter);
        let mut scope = Vec::new();
        if let Some(c) = &filter.competition {
            scope.push(c.display_name());
        }
        if let Some(s) = filter.season {
            scope.push(s.to_string());
        }
        if filter.home_only {
            scope.push("home".into());
        }
        if filter.away_only {
            scope.push("away".into());
        }
        let scope = if scope.is_empty() {
            String::new()
        } else {
            format!(" ({})", scope.join(" "))
        };
        Ok(format!(
            "{} record{}:\n\
             - Matches: {}\n\
             - Wins: {}, Draws: {}, Losses: {}\n\
             - Goals For: {}, Goals Against: {}\n\
             - Win rate: {:.1}%",
            r.team, scope, r.matches, r.wins, r.draws, r.losses, r.goals_for, r.goals_against,
            r.win_rate * 100.0
        ))
    }

    fn tool_find_players(&self, args: &Value) -> String {
        let filter = PlayerFilter {
            name: str_arg(args, "name"),
            nationality: str_arg(args, "nationality"),
            club: str_arg(args, "club"),
            position: str_arg(args, "position"),
            min_overall: int_arg(args, "min_overall").map(|v| v as u32),
            limit: int_arg(args, "limit").map(|v| v as usize),
        };
        let display_limit = filter.limit.unwrap_or(20);
        let mut filter = filter;
        filter.limit = None;
        let players = query::find_players(&self.db, &filter);
        if players.is_empty() {
            return "No players found for the given criteria.".to_string();
        }
        let total = players.len();
        let mut lines = vec![format!("Found {total} player(s):")];
        for (i, p) in players.iter().take(display_limit).enumerate() {
            lines.push(format!(
                "{}. {} - Overall: {}, Position: {}, Club: {}, Nationality: {}",
                i + 1,
                p.name,
                p.overall.map(|v| v.to_string()).unwrap_or_else(|| "?".into()),
                if p.position.is_empty() { "?" } else { &p.position },
                if p.club.is_empty() { "?" } else { &p.club },
                p.nationality
            ));
        }
        if total > display_limit {
            lines.push(format!("... ({} more)", total - display_limit));
        }
        lines.join("\n")
    }

    fn tool_standings(&self, args: &Value) -> Result<String, String> {
        let comp = str_arg(args, "competition")
            .and_then(|s| parse_competition(&s))
            .unwrap_or(Competition::Brasileirao);
        let season = int_arg(args, "season").ok_or("missing 'season'")? as i32;
        let table = query::standings(&self.db, &comp, season);
        if table.is_empty() {
            return Ok(format!(
                "No {} data found for {season}.",
                comp.display_name()
            ));
        }
        let mut lines = vec![format!(
            "{season} {} standings (calculated from matches):",
            comp.display_name()
        )];
        for r in &table {
            lines.push(format!(
                "{}. {} - {} pts ({}W {}D {}L, GD {:+})",
                r.rank, r.team, r.points, r.wins, r.draws, r.losses, r.goal_difference
            ));
        }
        Ok(lines.join("\n"))
    }

    fn tool_goal_stats(&self, args: &Value) -> String {
        let filter = self.match_filter(args);
        let s = query::goal_stats(&self.db, &filter);
        if s.matches == 0 {
            return "No matches found for the given criteria.".to_string();
        }
        format!(
            "Statistics over {} matches:\n\
             - Average goals per match: {:.2}\n\
             - Home wins: {} ({:.1}%)\n\
             - Away wins: {}\n\
             - Draws: {}\n\
             - Total goals: {}",
            s.matches,
            s.average_goals_per_match,
            s.home_wins,
            s.home_win_rate * 100.0,
            s.away_wins,
            s.draws,
            s.total_goals
        )
    }

    fn tool_biggest_wins(&self, args: &Value) -> String {
        let mut filter = self.match_filter(args);
        let limit = filter.limit.take().unwrap_or(10);
        let wins = query::biggest_wins(&self.db, &filter, limit);
        if wins.is_empty() {
            return "No matches found for the given criteria.".to_string();
        }
        let mut lines = vec!["Biggest victories:".to_string()];
        for (i, m) in wins.iter().enumerate() {
            lines.push(format!("{}. {}", i + 1, format_match(m)));
        }
        lines.join("\n")
    }

    fn tool_team_rankings(&self, args: &Value) -> String {
        let filter = self.match_filter(args);
        let min_matches = int_arg(args, "min_matches").map(|v| v as u32).unwrap_or(5);
        let limit = int_arg(args, "limit").map(|v| v as usize).unwrap_or(10);
        let ranks = query::team_rankings(&self.db, &filter, min_matches);
        if ranks.is_empty() {
            return "No matches found for the given criteria.".to_string();
        }
        let side = if filter.home_only {
            "home "
        } else if filter.away_only {
            "away "
        } else {
            ""
        };
        let mut lines = vec![format!("Team {side}rankings by win rate:")];
        for (i, r) in ranks.iter().take(limit).enumerate() {
            lines.push(format!(
                "{}. {} - {:.1}% ({}W {}D {}L over {} matches)",
                i + 1,
                r.team,
                r.win_rate * 100.0,
                r.wins,
                r.draws,
                r.losses,
                r.matches
            ));
        }
        lines.join("\n")
    }

    fn tool_competitions_for_team(&self, args: &Value) -> Result<String, String> {
        let team = str_arg(args, "team").ok_or("missing 'team'")?;
        let comps = query::competitions_for_team(&self.db, &team);
        if comps.is_empty() {
            return Ok(format!("No matches found for {team}."));
        }
        Ok(format!(
            "{team} has appeared in: {}",
            comps.join(", ")
        ))
    }
}

/// Build a JSON-RPC success response.
fn ok(id: Value, result: Value) -> Value {
    json!({ "jsonrpc": "2.0", "id": id, "result": result })
}

/// Build a JSON-RPC error response.
fn err(id: Value, code: i64, message: &str) -> Value {
    json!({ "jsonrpc": "2.0", "id": id, "error": { "code": code, "message": message } })
}

fn str_arg(args: &Value, key: &str) -> Option<String> {
    args.get(key)
        .and_then(Value::as_str)
        .map(|s| s.trim().to_string())
        .filter(|s| !s.is_empty())
}

fn int_arg(args: &Value, key: &str) -> Option<i64> {
    match args.get(key) {
        Some(Value::Number(n)) => n.as_i64(),
        Some(Value::String(s)) => s.trim().parse().ok(),
        _ => None,
    }
}

fn bool_arg(args: &Value, key: &str) -> bool {
    args.get(key).and_then(Value::as_bool).unwrap_or(false)
}

/// Map a free-text competition argument to a [`Competition`].
pub fn parse_competition(s: &str) -> Option<Competition> {
    let k = crate::normalize::normalize_key(s);
    match k.as_str() {
        _ if k.contains("libertadores") => Some(Competition::Libertadores),
        _ if k.contains("copa") || k.contains("cup") => Some(Competition::CopaDoBrasil),
        _ if k.contains("brasileir") || k.contains("serie a") || k == "league" => {
            Some(Competition::Brasileirao)
        }
        _ => None,
    }
}

/// Format a single match like `2019-10-27: Flamengo 5-0 Grêmio (Brasileirão Round 30)`.
fn format_match(m: &crate::models::Match) -> String {
    let date = m.date.as_deref().unwrap_or("date unknown");
    let mut suffix = m.competition.display_name();
    if let Some(r) = &m.round {
        suffix.push_str(&format!(" Round {r}"));
    } else if let Some(s) = &m.stage {
        suffix.push_str(&format!(" {s}"));
    }
    format!(
        "{}: {} {}-{} {} ({})",
        date, m.home_team, m.home_goal, m.away_goal, m.away_team, suffix
    )
}

/// JSON Schema definitions for all exposed tools.
fn tool_definitions() -> Vec<Value> {
    let team = json!({ "type": "string", "description": "Team name (any naming convention)" });
    let comp = json!({ "type": "string", "description": "Competition: brasileirao, copa_do_brasil or libertadores" });
    let season = json!({ "type": "integer", "description": "Season year, e.g. 2019" });
    vec![
        json!({
            "name": "find_matches",
            "description": "Find matches by team, opponent, competition, season or date range. Sorted most recent first.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team": team, "opponent": team, "competition": comp, "season": season,
                    "home_only": { "type": "boolean" }, "away_only": { "type": "boolean" },
                    "date_from": { "type": "string", "description": "ISO YYYY-MM-DD inclusive" },
                    "date_to": { "type": "string", "description": "ISO YYYY-MM-DD inclusive" },
                    "limit": { "type": "integer" }
                }
            }
        }),
        json!({
            "name": "head_to_head",
            "description": "Head-to-head win/draw/loss and goals record between two teams across all competitions.",
            "inputSchema": {
                "type": "object",
                "properties": { "team_a": team, "team_b": team },
                "required": ["team_a", "team_b"]
            }
        }),
        json!({
            "name": "team_record",
            "description": "A team's wins/draws/losses, goals and win rate, optionally scoped by competition, season and home/away.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team": team, "competition": comp, "season": season,
                    "home_only": { "type": "boolean" }, "away_only": { "type": "boolean" }
                },
                "required": ["team"]
            }
        }),
        json!({
            "name": "find_players",
            "description": "Search FIFA players by name, nationality, club, position or minimum overall rating. Sorted by rating.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": { "type": "string" }, "nationality": { "type": "string" },
                    "club": { "type": "string" }, "position": { "type": "string" },
                    "min_overall": { "type": "integer" }, "limit": { "type": "integer" }
                }
            }
        }),
        json!({
            "name": "standings",
            "description": "Calculated final league table for a competition season (3pts win, 1 draw).",
            "inputSchema": {
                "type": "object",
                "properties": { "competition": comp, "season": season },
                "required": ["season"]
            }
        }),
        json!({
            "name": "goal_stats",
            "description": "Aggregate goal and result statistics (avg goals/match, home win rate) over filtered matches.",
            "inputSchema": {
                "type": "object",
                "properties": { "competition": comp, "season": season, "team": team }
            }
        }),
        json!({
            "name": "biggest_wins",
            "description": "Largest-margin victories among matches, optionally filtered by competition/season/team.",
            "inputSchema": {
                "type": "object",
                "properties": { "competition": comp, "season": season, "team": team, "limit": { "type": "integer" } }
            }
        }),
        json!({
            "name": "team_rankings",
            "description": "Rank teams by win rate over filtered matches, with optional home_only/away_only and min_matches.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "competition": comp, "season": season,
                    "home_only": { "type": "boolean" }, "away_only": { "type": "boolean" },
                    "min_matches": { "type": "integer" }, "limit": { "type": "integer" }
                }
            }
        }),
        json!({
            "name": "competitions_for_team",
            "description": "List all competitions a team has appeared in within the datasets.",
            "inputSchema": {
                "type": "object",
                "properties": { "team": team },
                "required": ["team"]
            }
        }),
    ]
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::models::{Competition, Match, Player};

    fn mk(comp: Competition, h: &str, a: &str, hg: u32, ag: u32, season: i32, date: &str) -> Match {
        Match {
            competition: comp,
            home_team: h.into(),
            away_team: a.into(),
            home_goal: hg,
            away_goal: ag,
            season,
            date: Some(date.into()),
            round: Some("1".into()),
            stage: None,
        }
    }

    fn server() -> McpServer {
        let mut db = Database::new();
        db.matches = vec![
            mk(Competition::Brasileirao, "Flamengo", "Fluminense", 2, 1, 2023, "2023-09-03"),
            mk(Competition::Brasileirao, "Fluminense", "Flamengo", 1, 0, 2023, "2023-05-28"),
            mk(Competition::Brasileirao, "Flamengo", "Santos", 5, 0, 2023, "2023-07-01"),
        ];
        db.players = vec![Player {
            id: 1,
            name: "Gabriel Barbosa".into(),
            age: Some(27),
            nationality: "Brazil".into(),
            overall: Some(80),
            potential: Some(82),
            club: "Flamengo".into(),
            position: "ST".into(),
        }];
        McpServer::new(db)
    }

    #[test]
    fn initialize_returns_protocol_and_server_info() {
        let s = server();
        let req = json!({ "jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {} });
        let resp = s.handle_request(&req).unwrap();
        assert_eq!(resp["result"]["protocolVersion"], PROTOCOL_VERSION);
        assert_eq!(resp["result"]["serverInfo"]["name"], "brazilian-soccer-mcp");
        assert_eq!(resp["id"], 1);
    }

    #[test]
    fn notifications_get_no_response() {
        let s = server();
        let req = json!({ "jsonrpc": "2.0", "method": "notifications/initialized" });
        assert!(s.handle_request(&req).is_none());
    }

    #[test]
    fn tools_list_contains_all_tools() {
        let s = server();
        let req = json!({ "jsonrpc": "2.0", "id": 2, "method": "tools/list" });
        let resp = s.handle_request(&req).unwrap();
        let tools = resp["result"]["tools"].as_array().unwrap();
        assert_eq!(tools.len(), 9);
        let names: Vec<&str> = tools.iter().map(|t| t["name"].as_str().unwrap()).collect();
        assert!(names.contains(&"find_matches"));
        assert!(names.contains(&"standings"));
        assert!(names.contains(&"find_players"));
    }

    #[test]
    fn unknown_method_returns_error() {
        let s = server();
        let req = json!({ "jsonrpc": "2.0", "id": 3, "method": "no/such" });
        let resp = s.handle_request(&req).unwrap();
        assert_eq!(resp["error"]["code"], -32601);
    }

    #[test]
    fn call_find_matches_returns_text_content() {
        let s = server();
        let req = json!({
            "jsonrpc": "2.0", "id": 4, "method": "tools/call",
            "params": { "name": "find_matches", "arguments": { "team": "Flamengo", "opponent": "Fluminense" } }
        });
        let resp = s.handle_request(&req).unwrap();
        let text = resp["result"]["content"][0]["text"].as_str().unwrap();
        assert!(text.contains("Flamengo"));
        assert!(text.contains("Fluminense"));
        assert!(text.contains("Head-to-head"));
        // Most recent match listed first.
        let first_line = text.lines().find(|l| l.starts_with("- 2023")).unwrap();
        assert!(first_line.contains("2023-09-03"));
    }

    #[test]
    fn call_standings_calculates_table() {
        let s = server();
        let req = json!({
            "jsonrpc": "2.0", "id": 5, "method": "tools/call",
            "params": { "name": "standings", "arguments": { "competition": "brasileirao", "season": 2023 } }
        });
        let resp = s.handle_request(&req).unwrap();
        let text = resp["result"]["content"][0]["text"].as_str().unwrap();
        // Flamengo: 2 wins (vs Flu, vs Santos), 1 loss => 6 pts, top of table.
        assert!(text.contains("1. Flamengo - 6 pts"));
    }

    #[test]
    fn call_find_players_by_name() {
        let s = server();
        let req = json!({
            "jsonrpc": "2.0", "id": 6, "method": "tools/call",
            "params": { "name": "find_players", "arguments": { "name": "Gabriel" } }
        });
        let resp = s.handle_request(&req).unwrap();
        let text = resp["result"]["content"][0]["text"].as_str().unwrap();
        assert!(text.contains("Gabriel Barbosa"));
        assert!(text.contains("Overall: 80"));
    }

    #[test]
    fn call_unknown_tool_is_error() {
        let s = server();
        let req = json!({
            "jsonrpc": "2.0", "id": 7, "method": "tools/call",
            "params": { "name": "bogus", "arguments": {} }
        });
        let resp = s.handle_request(&req).unwrap();
        assert_eq!(resp["result"]["isError"], true);
    }

    #[test]
    fn missing_required_arg_is_error() {
        let s = server();
        let req = json!({
            "jsonrpc": "2.0", "id": 8, "method": "tools/call",
            "params": { "name": "head_to_head", "arguments": { "team_a": "Flamengo" } }
        });
        let resp = s.handle_request(&req).unwrap();
        assert_eq!(resp["result"]["isError"], true);
    }

    #[test]
    fn handle_line_roundtrip() {
        let s = server();
        let line = r#"{"jsonrpc":"2.0","id":9,"method":"ping"}"#;
        let out = s.handle_line(line).unwrap();
        assert!(out.contains("\"id\":9"));
    }

    #[test]
    fn parse_competition_variants() {
        assert_eq!(parse_competition("brasileirao"), Some(Competition::Brasileirao));
        assert_eq!(parse_competition("Brasileirão"), Some(Competition::Brasileirao));
        assert_eq!(parse_competition("copa_do_brasil"), Some(Competition::CopaDoBrasil));
        assert_eq!(parse_competition("libertadores"), Some(Competition::Libertadores));
        assert_eq!(parse_competition("xyz"), None);
    }
}
