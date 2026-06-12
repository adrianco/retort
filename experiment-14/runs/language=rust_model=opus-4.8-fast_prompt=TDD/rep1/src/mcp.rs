// mcp - the Model Context Protocol server (JSON-RPC 2.0 over stdio).
//
// This module is a thin, well-tested formatting layer over `query::Database`.
// It speaks the MCP stdio transport: newline-delimited JSON-RPC messages on
// stdin/stdout. It answers `initialize`, `tools/list` and `tools/call`, and
// exposes eight tools covering the spec's five capability areas (match, team,
// player, competition and statistical queries).
//
// `handle_message` (pure: Value -> Option<Value>) and `call_tool` (name+args
// -> formatted text) are the unit-tested seams; `main.rs` only wires them to
// real stdin/stdout.

use serde_json::{json, Value};

use crate::model::{Competition, Match, Player};
use crate::query::{Database, MatchFilter};

/// The MCP protocol revision we advertise.
const PROTOCOL_VERSION: &str = "2024-11-05";

/// Wraps the dataset and turns MCP requests into answers.
pub struct McpServer {
    db: Database,
}

impl McpServer {
    pub fn new(db: Database) -> Self {
        McpServer { db }
    }

    /// Handle one JSON-RPC message. Returns `Some(response)` for requests and
    /// `None` for notifications (messages without an `id`).
    pub fn handle_message(&self, msg: &Value) -> Option<Value> {
        let id = msg.get("id").cloned();
        let method = msg.get("method").and_then(|m| m.as_str()).unwrap_or("");

        // Notifications carry no id and expect no reply.
        let id = id?;

        match method {
            "initialize" => Some(ok(
                id,
                json!({
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": { "tools": {} },
                    "serverInfo": {
                        "name": "brazilian-soccer-mcp",
                        "version": env!("CARGO_PKG_VERSION"),
                    }
                }),
            )),
            "ping" => Some(ok(id, json!({}))),
            "tools/list" => Some(ok(id, json!({ "tools": tool_definitions() }))),
            "tools/call" => {
                let params = msg.get("params").cloned().unwrap_or(Value::Null);
                let name = params.get("name").and_then(|n| n.as_str()).unwrap_or("");
                let args = params
                    .get("arguments")
                    .cloned()
                    .unwrap_or_else(|| json!({}));
                match self.call_tool(name, &args) {
                    Ok(text) => Some(ok(id, tool_text(&text, false))),
                    Err(text) => Some(ok(id, tool_text(&text, true))),
                }
            }
            _ => Some(err(id, -32601, &format!("Method not found: {}", method))),
        }
    }

    /// Dispatch a tool call to the query engine and format the answer.
    /// `Err` carries a user-facing error message (surfaced via `isError`).
    pub fn call_tool(&self, name: &str, args: &Value) -> Result<String, String> {
        match name {
            "find_matches" => self.tool_find_matches(args),
            "team_record" => self.tool_team_record(args),
            "head_to_head" => self.tool_head_to_head(args),
            "standings" => self.tool_standings(args),
            "search_players" => self.tool_search_players(args),
            "top_players" => self.tool_top_players(args),
            "competition_stats" => self.tool_competition_stats(args),
            "last_match" => self.tool_last_match(args),
            other => Err(format!("Unknown tool: {}", other)),
        }
    }

    // ---- Individual tools ----------------------------------------------

    fn tool_find_matches(&self, args: &Value) -> Result<String, String> {
        let team = require_str(args, "team")?;
        let mut filter = MatchFilter::new().team(&team);
        if let Some(opp) = get_str(args, "opponent") {
            filter = filter.opponent(&opp);
        }
        if let Some(s) = get_i64(args, "season") {
            filter = filter.season(s as i32);
        }
        if let Some(c) = get_competition(args, "competition") {
            filter = filter.competition(c);
        }
        let limit = get_i64(args, "limit").unwrap_or(20).max(1) as usize;

        let mut matches = self.db.find_matches(&filter);
        matches.sort_by(|a, b| a.date.cmp(&b.date));
        let total = matches.len();
        if total == 0 {
            return Ok(format!("No matches found for {}.", team));
        }

        let mut out = String::new();
        let header = match get_str(args, "opponent") {
            Some(opp) => format!("{} vs {} — {} match(es) in dataset:\n", team, opp, total),
            None => format!("{} — {} match(es) in dataset:\n", team, total),
        };
        out.push_str(&header);
        for m in matches.iter().take(limit) {
            out.push_str("- ");
            out.push_str(&format_match(m));
            out.push('\n');
        }
        if total > limit {
            out.push_str(&format!("... ({} more not shown)\n", total - limit));
        }

        // When an opponent is named, append the head-to-head summary.
        if let Some(opp) = get_str(args, "opponent") {
            let h = self.db.head_to_head(&team, &opp, &filter);
            out.push_str(&format!(
                "\nHead-to-head: {} {} wins, {} {} wins, {} draws.",
                team, h.a_wins, opp, h.b_wins, h.draws
            ));
        }
        Ok(out)
    }

    fn tool_team_record(&self, args: &Value) -> Result<String, String> {
        let team = require_str(args, "team")?;
        let mut filter = MatchFilter::new();
        if let Some(s) = get_i64(args, "season") {
            filter = filter.season(s as i32);
        }
        if let Some(c) = get_competition(args, "competition") {
            filter = filter.competition(c);
        }
        let venue = get_str(args, "venue").unwrap_or_else(|| "all".to_string());
        let (home_only, away_only) = match venue.to_lowercase().as_str() {
            "home" => (true, false),
            "away" => (false, true),
            _ => (false, false),
        };
        let rec = self.db.team_record(&team, &filter, home_only, away_only);
        if rec.played == 0 {
            return Ok(format!("No matches found for {} with those filters.", team));
        }
        let scope = describe_scope(args, &venue);
        Ok(format!(
            "{} record{}:\n- Matches: {}\n- Wins: {}, Draws: {}, Losses: {}\n- Goals For: {}, Goals Against: {}\n- Points: {}\n- Win rate: {:.1}%",
            team,
            scope,
            rec.played,
            rec.wins,
            rec.draws,
            rec.losses,
            rec.goals_for,
            rec.goals_against,
            rec.points(),
            rec.win_rate() * 100.0
        ))
    }

    fn tool_head_to_head(&self, args: &Value) -> Result<String, String> {
        let a = require_str(args, "team_a")?;
        let b = require_str(args, "team_b")?;
        let mut filter = MatchFilter::new();
        if let Some(s) = get_i64(args, "season") {
            filter = filter.season(s as i32);
        }
        if let Some(c) = get_competition(args, "competition") {
            filter = filter.competition(c);
        }
        let h = self.db.head_to_head(&a, &b, &filter);
        if h.total == 0 {
            return Ok(format!("No matches found between {} and {}.", a, b));
        }
        Ok(format!(
            "{} vs {} head-to-head ({} matches):\n- {} wins: {}\n- {} wins: {}\n- Draws: {}",
            a, b, h.total, a, h.a_wins, b, h.b_wins, h.draws
        ))
    }

    fn tool_standings(&self, args: &Value) -> Result<String, String> {
        let competition = get_competition(args, "competition").unwrap_or(Competition::Brasileirao);
        let season = require_i64(args, "season")? as i32;
        let table = self.db.standings(competition.clone(), season);
        if table.is_empty() {
            return Ok(format!(
                "No {} data for {}.",
                competition.display_name(),
                season
            ));
        }
        let mut out = format!(
            "{} {} final standings (calculated from matches):\n",
            season,
            competition.display_name()
        );
        for (i, row) in table.iter().enumerate() {
            let r = &row.record;
            out.push_str(&format!(
                "{}. {} - {} pts ({}W {}D {}L, GF {} GA {}, GD {:+})\n",
                i + 1,
                row.team,
                r.points(),
                r.wins,
                r.draws,
                r.losses,
                r.goals_for,
                r.goals_against,
                r.goal_difference()
            ));
        }
        Ok(out)
    }

    fn tool_search_players(&self, args: &Value) -> Result<String, String> {
        let limit = get_i64(args, "limit").unwrap_or(20).max(1) as usize;
        let position = get_str(args, "position").map(|p| p.to_lowercase());

        // Start from the narrowest provided filter, then refine.
        let mut players: Vec<&Player> = if let Some(name) = get_str(args, "name") {
            self.db.players_by_name(&name)
        } else if let Some(club) = get_str(args, "club") {
            self.db.players_by_club(&club)
        } else if let Some(nat) = get_str(args, "nationality") {
            self.db.players_by_nationality(&nat)
        } else {
            return Err("Provide at least one of: name, club, nationality.".to_string());
        };

        if let Some(nat) = get_str(args, "nationality") {
            let nat = nat.to_lowercase();
            players.retain(|p| p.nationality.to_lowercase() == nat);
        }
        if let Some(club) = get_str(args, "club") {
            let club = club.to_lowercase();
            players.retain(|p| p.club.to_lowercase().contains(&club));
        }
        if let Some(pos) = &position {
            players.retain(|p| p.position.to_lowercase() == *pos);
        }

        if players.is_empty() {
            return Ok("No players matched those filters.".to_string());
        }
        players.sort_by(|a, b| b.overall.cmp(&a.overall).then(a.name.cmp(&b.name)));
        let total = players.len();
        let mut out = format!("{} player(s) found:\n", total);
        for (i, p) in players.iter().take(limit).enumerate() {
            out.push_str(&format!("{}. {}\n", i + 1, format_player(p)));
        }
        if total > limit {
            out.push_str(&format!("... ({} more not shown)\n", total - limit));
        }
        Ok(out)
    }

    fn tool_top_players(&self, args: &Value) -> Result<String, String> {
        let nationality = get_str(args, "nationality");
        let club = get_str(args, "club");
        let limit = get_i64(args, "limit").unwrap_or(10).max(1) as usize;
        let players = self
            .db
            .top_players(nationality.as_deref(), club.as_deref(), limit);
        if players.is_empty() {
            return Ok("No players matched those filters.".to_string());
        }
        let mut out = String::from("Top players:\n");
        for (i, p) in players.iter().enumerate() {
            out.push_str(&format!("{}. {}\n", i + 1, format_player(p)));
        }
        Ok(out)
    }

    fn tool_competition_stats(&self, args: &Value) -> Result<String, String> {
        let mut filter = MatchFilter::new();
        let mut scope = String::from("all matches");
        if let Some(c) = get_competition(args, "competition") {
            scope = c.display_name();
            filter = filter.competition(c);
        }
        if let Some(s) = get_i64(args, "season") {
            scope = format!("{} {}", s, scope);
            filter = filter.season(s as i32);
        }
        let count = self.db.find_matches(&filter).len();
        if count == 0 {
            return Ok(format!("No matches found for {}.", scope));
        }
        let avg = self.db.average_goals(&filter);
        let home_rate = self.db.home_win_rate(&filter);
        let mut out = format!(
            "Statistics for {} ({} matches):\n- Average goals per match: {:.2}\n- Home win rate: {:.1}%\n",
            scope, count, avg, home_rate * 100.0
        );
        if let Some((team, goals)) = self.db.most_goals_team(&filter) {
            out.push_str(&format!(
                "- Most goals scored: {} ({} goals)\n",
                team, goals
            ));
        }
        let biggest = self.db.biggest_wins(&filter, 5);
        if !biggest.is_empty() {
            out.push_str("- Biggest victories:\n");
            for m in biggest {
                out.push_str("  - ");
                out.push_str(&format_match(m));
                out.push('\n');
            }
        }
        Ok(out)
    }

    fn tool_last_match(&self, args: &Value) -> Result<String, String> {
        let a = require_str(args, "team_a")?;
        let b = require_str(args, "team_b")?;
        match self.db.last_match_between(&a, &b) {
            Some(m) => Ok(format!(
                "Most recent {} vs {} meeting:\n{}",
                a,
                b,
                format_match(m)
            )),
            None => Ok(format!("No matches found between {} and {}.", a, b)),
        }
    }
}

// ---- Formatting helpers -----------------------------------------------------

/// "2019-10-27: Flamengo-RJ 2-1 Fluminense-RJ (Brasileirão Round 22)".
pub fn format_match(m: &Match) -> String {
    let date = m.date.as_deref().unwrap_or("????-??-??");
    let qualifier = if let Some(r) = &m.round {
        format!(" Round {}", r)
    } else if let Some(s) = &m.stage {
        format!(" - {}", s)
    } else {
        String::new()
    };
    format!(
        "{}: {} {}-{} {} ({}{})",
        date,
        m.home_team,
        m.home_goal,
        m.away_goal,
        m.away_team,
        m.competition.display_name(),
        qualifier
    )
}

/// "Neymar Jr - Overall: 92, Position: LW, Club: Paris Saint-Germain (Brazil)".
pub fn format_player(p: &Player) -> String {
    let club = if p.club.trim().is_empty() {
        "Free agent".to_string()
    } else {
        p.club.clone()
    };
    format!(
        "{} - Overall: {}, Position: {}, Club: {} ({})",
        p.name, p.overall, p.position, club, p.nationality
    )
}

fn describe_scope(args: &Value, venue: &str) -> String {
    let mut parts = Vec::new();
    if let Some(s) = get_i64(args, "season") {
        parts.push(format!("{}", s));
    }
    if let Some(c) = get_competition(args, "competition") {
        parts.push(c.display_name());
    }
    match venue.to_lowercase().as_str() {
        "home" => parts.push("home".to_string()),
        "away" => parts.push("away".to_string()),
        _ => {}
    }
    if parts.is_empty() {
        String::new()
    } else {
        format!(" ({})", parts.join(" "))
    }
}

// ---- JSON-RPC + argument helpers -------------------------------------------

fn ok(id: Value, result: Value) -> Value {
    json!({ "jsonrpc": "2.0", "id": id, "result": result })
}

fn err(id: Value, code: i64, message: &str) -> Value {
    json!({ "jsonrpc": "2.0", "id": id, "error": { "code": code, "message": message } })
}

fn tool_text(text: &str, is_error: bool) -> Value {
    json!({
        "content": [ { "type": "text", "text": text } ],
        "isError": is_error,
    })
}

fn get_str(args: &Value, key: &str) -> Option<String> {
    args.get(key)
        .and_then(|v| v.as_str())
        .map(|s| s.trim().to_string())
        .filter(|s| !s.is_empty())
}

fn require_str(args: &Value, key: &str) -> Result<String, String> {
    get_str(args, key).ok_or_else(|| format!("Missing required argument: {}", key))
}

fn get_i64(args: &Value, key: &str) -> Option<i64> {
    match args.get(key) {
        Some(Value::Number(n)) => n.as_i64(),
        Some(Value::String(s)) => s.trim().parse::<i64>().ok(),
        _ => None,
    }
}

fn require_i64(args: &Value, key: &str) -> Result<i64, String> {
    get_i64(args, key).ok_or_else(|| format!("Missing required argument: {}", key))
}

fn get_competition(args: &Value, key: &str) -> Option<Competition> {
    get_str(args, key).map(|s| Competition::from_label(&s))
}

// ---- Tool schema definitions ------------------------------------------------

/// The JSON schema advertised for each tool via `tools/list`.
pub fn tool_definitions() -> Vec<Value> {
    vec![
        json!({
            "name": "find_matches",
            "description": "Find matches involving a team, optionally vs an opponent, in a season and/or competition. Returns a chronological list plus a head-to-head summary when an opponent is given.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team": { "type": "string", "description": "Team name (any naming variant, e.g. 'Flamengo' or 'Flamengo-RJ')." },
                    "opponent": { "type": "string", "description": "Optional opponent team name." },
                    "season": { "type": "integer", "description": "Optional season year, e.g. 2019." },
                    "competition": { "type": "string", "description": "Optional: Brasileirao, Copa do Brasil, or Libertadores." },
                    "limit": { "type": "integer", "description": "Max matches to list (default 20)." }
                },
                "required": ["team"]
            }
        }),
        json!({
            "name": "team_record",
            "description": "Win/draw/loss and goals record for a team, optionally filtered by season, competition and venue (home/away).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team": { "type": "string" },
                    "season": { "type": "integer" },
                    "competition": { "type": "string" },
                    "venue": { "type": "string", "enum": ["home", "away", "all"], "description": "Restrict to home or away matches (default all)." }
                },
                "required": ["team"]
            }
        }),
        json!({
            "name": "head_to_head",
            "description": "Head-to-head record between two teams, optionally filtered by season and competition.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_a": { "type": "string" },
                    "team_b": { "type": "string" },
                    "season": { "type": "integer" },
                    "competition": { "type": "string" }
                },
                "required": ["team_a", "team_b"]
            }
        }),
        json!({
            "name": "standings",
            "description": "Calculated league table for a competition and season (3 points per win, 1 per draw), sorted by points then goal difference.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "competition": { "type": "string", "description": "Defaults to Brasileirao." },
                    "season": { "type": "integer" }
                },
                "required": ["season"]
            }
        }),
        json!({
            "name": "search_players",
            "description": "Search FIFA players by any combination of name, nationality, club and position. Sorted by Overall rating.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": { "type": "string" },
                    "nationality": { "type": "string", "description": "e.g. 'Brazil'." },
                    "club": { "type": "string" },
                    "position": { "type": "string", "description": "e.g. 'ST', 'GK'." },
                    "limit": { "type": "integer", "description": "Default 20." }
                }
            }
        }),
        json!({
            "name": "top_players",
            "description": "Highest-rated players, optionally filtered by nationality and/or club.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "nationality": { "type": "string" },
                    "club": { "type": "string" },
                    "limit": { "type": "integer", "description": "Default 10." }
                }
            }
        }),
        json!({
            "name": "competition_stats",
            "description": "Aggregate statistics (average goals per match, home win rate, top-scoring team, biggest victories) for a competition and/or season.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "competition": { "type": "string" },
                    "season": { "type": "integer" }
                }
            }
        }),
        json!({
            "name": "last_match",
            "description": "The most recent match between two teams.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_a": { "type": "string" },
                    "team_b": { "type": "string" }
                },
                "required": ["team_a", "team_b"]
            }
        }),
    ]
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::model::Competition::*;

    fn m(
        comp: Competition,
        season: i32,
        date: &str,
        home: &str,
        away: &str,
        hg: u32,
        ag: u32,
    ) -> Match {
        Match {
            competition: comp,
            season,
            date: Some(date.to_string()),
            round: Some("1".to_string()),
            stage: None,
            home_team: home.to_string(),
            away_team: away.to_string(),
            home_state: None,
            away_state: None,
            home_goal: hg,
            away_goal: ag,
            source_priority: 0,
        }
    }

    fn player(id: i64, name: &str, nat: &str, club: &str, overall: u32, pos: &str) -> Player {
        Player {
            id,
            name: name.to_string(),
            age: Some(25),
            nationality: nat.to_string(),
            overall,
            potential: overall,
            club: club.to_string(),
            position: pos.to_string(),
        }
    }

    fn server() -> McpServer {
        let matches = vec![
            m(
                Brasileirao,
                2019,
                "2019-05-01",
                "Flamengo-RJ",
                "Fluminense-RJ",
                2,
                1,
            ),
            m(
                Brasileirao,
                2019,
                "2019-09-01",
                "Fluminense-RJ",
                "Flamengo-RJ",
                0,
                0,
            ),
            m(
                Brasileirao,
                2019,
                "2019-07-01",
                "Flamengo-RJ",
                "Palmeiras-SP",
                3,
                0,
            ),
            m(
                Libertadores,
                2019,
                "2019-11-23",
                "Flamengo",
                "River Plate",
                2,
                1,
            ),
        ];
        let players = vec![
            player(1, "Gabriel Barbosa", "Brazil", "Flamengo", 80, "ST"),
            player(2, "Bruno Henrique", "Brazil", "Flamengo", 78, "LW"),
            player(3, "L. Messi", "Argentina", "FC Barcelona", 94, "RF"),
        ];
        McpServer::new(Database::new(matches, players))
    }

    #[test]
    fn initialize_returns_server_info() {
        let s = server();
        let req = json!({"jsonrpc":"2.0","id":1,"method":"initialize","params":{}});
        let resp = s.handle_message(&req).unwrap();
        assert_eq!(resp["result"]["protocolVersion"], PROTOCOL_VERSION);
        assert_eq!(resp["result"]["serverInfo"]["name"], "brazilian-soccer-mcp");
        assert_eq!(resp["id"], 1);
    }

    #[test]
    fn notifications_get_no_response() {
        let s = server();
        let note = json!({"jsonrpc":"2.0","method":"notifications/initialized"});
        assert!(s.handle_message(&note).is_none());
    }

    #[test]
    fn unknown_method_is_method_not_found() {
        let s = server();
        let req = json!({"jsonrpc":"2.0","id":7,"method":"does/not/exist"});
        let resp = s.handle_message(&req).unwrap();
        assert_eq!(resp["error"]["code"], -32601);
    }

    #[test]
    fn tools_list_advertises_all_tools() {
        let s = server();
        let req = json!({"jsonrpc":"2.0","id":2,"method":"tools/list"});
        let resp = s.handle_message(&req).unwrap();
        let tools = resp["result"]["tools"].as_array().unwrap();
        assert_eq!(tools.len(), 8);
        for t in tools {
            assert!(t["name"].is_string());
            assert_eq!(t["inputSchema"]["type"], "object");
        }
    }

    #[test]
    fn tools_call_find_matches_with_opponent() {
        let s = server();
        let req = json!({
            "jsonrpc":"2.0","id":3,"method":"tools/call",
            "params": { "name": "find_matches", "arguments": { "team": "Flamengo", "opponent": "Fluminense" } }
        });
        let resp = s.handle_message(&req).unwrap();
        assert_eq!(resp["result"]["isError"], false);
        let text = resp["result"]["content"][0]["text"].as_str().unwrap();
        assert!(text.contains("Flamengo"));
        assert!(text.contains("Head-to-head"));
        // Two Fla-Flu matches: one Flamengo win, one draw.
        assert!(text.contains("Flamengo 1 wins"));
        assert!(text.contains("1 draws"));
    }

    #[test]
    fn tools_call_unknown_tool_sets_is_error() {
        let s = server();
        let req = json!({
            "jsonrpc":"2.0","id":4,"method":"tools/call",
            "params": { "name": "bogus", "arguments": {} }
        });
        let resp = s.handle_message(&req).unwrap();
        assert_eq!(resp["result"]["isError"], true);
    }

    #[test]
    fn missing_required_argument_is_error() {
        let s = server();
        let out = s.call_tool("find_matches", &json!({}));
        assert!(out.is_err());
        assert!(out.unwrap_err().contains("team"));
    }

    #[test]
    fn team_record_tool_formats_record() {
        let s = server();
        let text = s
            .call_tool(
                "team_record",
                &json!({"team":"Flamengo","season":2019,"competition":"Brasileirao"}),
            )
            .unwrap();
        assert!(text.contains("Matches: 3"));
        assert!(text.contains("Wins: 2"));
        assert!(text.contains("Draws: 1"));
    }

    #[test]
    fn standings_tool_orders_and_formats() {
        let s = server();
        let text = s
            .call_tool(
                "standings",
                &json!({"competition":"Brasileirao","season":2019}),
            )
            .unwrap();
        // Flamengo leads (7 pts from 2W 1D).
        let first_line = text.lines().nth(1).unwrap();
        assert!(first_line.starts_with("1. Flamengo"));
        assert!(first_line.contains("7 pts"));
    }

    #[test]
    fn search_players_by_club_and_nationality() {
        let s = server();
        let text = s
            .call_tool(
                "search_players",
                &json!({"club":"Flamengo","nationality":"Brazil"}),
            )
            .unwrap();
        assert!(text.contains("Gabriel Barbosa"));
        assert!(text.contains("Bruno Henrique"));
        // Sorted by rating: Gabriel (80) before Bruno (78).
        let gpos = text.find("Gabriel").unwrap();
        let bpos = text.find("Bruno").unwrap();
        assert!(gpos < bpos);
    }

    #[test]
    fn top_players_filters_by_nationality() {
        let s = server();
        let text = s
            .call_tool("top_players", &json!({"nationality":"Argentina"}))
            .unwrap();
        assert!(text.contains("L. Messi"));
        assert!(!text.contains("Gabriel"));
    }

    #[test]
    fn competition_stats_reports_aggregates() {
        let s = server();
        let text = s
            .call_tool(
                "competition_stats",
                &json!({"competition":"Brasileirao","season":2019}),
            )
            .unwrap();
        assert!(text.contains("Average goals per match"));
        assert!(text.contains("Home win rate"));
        assert!(text.contains("Biggest victories"));
    }

    #[test]
    fn last_match_returns_latest() {
        let s = server();
        let text = s
            .call_tool(
                "last_match",
                &json!({"team_a":"Flamengo","team_b":"Fluminense"}),
            )
            .unwrap();
        assert!(text.contains("2019-09-01"));
    }

    #[test]
    fn format_match_shape() {
        let mm = m(
            Brasileirao,
            2019,
            "2019-05-01",
            "Flamengo-RJ",
            "Fluminense-RJ",
            2,
            1,
        );
        let s = format_match(&mm);
        assert_eq!(
            s,
            "2019-05-01: Flamengo-RJ 2-1 Fluminense-RJ (Brasileirão Round 1)"
        );
    }
}
