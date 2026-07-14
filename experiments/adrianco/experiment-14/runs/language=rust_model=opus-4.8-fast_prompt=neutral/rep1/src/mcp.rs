//! ============================================================================
//! Module: mcp
//!
//! Context
//! -------
//! Implements the Model Context Protocol (JSON-RPC 2.0 over stdio) on top of the
//! `Database` query engine. This module is transport-agnostic: it parses a
//! request `Value`, dispatches to the right query, and returns a response
//! `Value`. `main.rs` owns the stdio read/write loop.
//!
//! Exposed tools (the verbs an LLM can call):
//!   find_matches, head_to_head, team_record, standings, search_players,
//!   league_stats, biggest_wins, team_competitions, list_competitions
//!
//! Each tool returns a human-readable text block in the MCP `content` form,
//! formatted to match the answer styles in the specification.
//! ============================================================================

use serde_json::{json, Value};

use crate::db::{Database, MatchFilter, PlayerFilter};

const PROTOCOL_VERSION: &str = "2024-11-05";
const SERVER_NAME: &str = "brazilian-soccer-mcp";
const SERVER_VERSION: &str = env!("CARGO_PKG_VERSION");

/// MCP server bound to a loaded database.
pub struct Server {
    db: Database,
}

impl Server {
    pub fn new(db: Database) -> Self {
        Server { db }
    }

    pub fn db(&self) -> &Database {
        &self.db
    }

    /// Handle a single JSON-RPC request. Returns `None` for notifications
    /// (requests without an `id`), which require no response.
    pub fn handle(&self, req: &Value) -> Option<Value> {
        let id = req.get("id").cloned();
        let method = req.get("method").and_then(|m| m.as_str()).unwrap_or("");
        let params = req.get("params").cloned().unwrap_or(Value::Null);

        // Notifications carry no id and expect no reply.
        let id = id?;

        match method {
            "initialize" => Some(ok(
                id,
                json!({
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": { "tools": {} },
                    "serverInfo": { "name": SERVER_NAME, "version": SERVER_VERSION }
                }),
            )),
            "ping" => Some(ok(id, json!({}))),
            "tools/list" => Some(ok(id, json!({ "tools": tool_definitions() }))),
            "tools/call" => {
                let name = params.get("name").and_then(|n| n.as_str()).unwrap_or("");
                let args = params.get("arguments").cloned().unwrap_or(json!({}));
                match self.call_tool(name, &args) {
                    Ok(text) => Some(ok(
                        id,
                        json!({ "content": [{ "type": "text", "text": text }] }),
                    )),
                    Err(msg) => Some(ok(
                        id,
                        json!({ "content": [{ "type": "text", "text": msg }], "isError": true }),
                    )),
                }
            }
            other => Some(err(id, -32601, &format!("Method not found: {}", other))),
        }
    }

    /// Dispatch a tool call to the query engine and format the answer.
    pub fn call_tool(&self, name: &str, args: &Value) -> Result<String, String> {
        match name {
            "find_matches" => Ok(self.tool_find_matches(args)),
            "head_to_head" => Ok(self.tool_head_to_head(args)),
            "team_record" => Ok(self.tool_team_record(args)),
            "standings" => Ok(self.tool_standings(args)),
            "search_players" => Ok(self.tool_search_players(args)),
            "league_stats" => Ok(self.tool_league_stats(args)),
            "biggest_wins" => Ok(self.tool_biggest_wins(args)),
            "team_competitions" => Ok(self.tool_team_competitions(args)),
            "list_competitions" => Ok(self.tool_list_competitions()),
            other => Err(format!("Unknown tool: {}", other)),
        }
    }

    // -- individual tool implementations ------------------------------------

    fn tool_find_matches(&self, args: &Value) -> String {
        let limit = arg_usize(args, "limit").unwrap_or(20);
        let mut filter = MatchFilter::default();

        let mut team_disp = None;
        if let Some(t) = arg_str(args, "team") {
            match self.db.resolve_team(t) {
                Some((key, disp)) => {
                    filter.team = Some(key);
                    team_disp = Some(disp);
                }
                None => return format!("No team matching \"{}\" found in the dataset.", t),
            }
        }
        let mut opp_disp = None;
        if let Some(o) = arg_str(args, "opponent") {
            match self.db.resolve_team(o) {
                Some((key, disp)) => {
                    filter.opponent = Some(key);
                    opp_disp = Some(disp);
                }
                None => return format!("No team matching \"{}\" found in the dataset.", o),
            }
        }
        filter.competition = arg_str(args, "competition").map(|s| s.to_string());
        filter.season = arg_i32(args, "season");
        filter.date_from = arg_str(args, "date_from").map(|s| s.to_string());
        filter.date_to = arg_str(args, "date_to").map(|s| s.to_string());
        filter.venue = arg_str(args, "venue").map(|s| s.to_lowercase());

        let matches = self.db.find_matches(&filter);
        if matches.is_empty() {
            return "No matches found for the given criteria.".to_string();
        }

        let mut header = String::new();
        if let (Some(a), Some(b)) = (&team_disp, &opp_disp) {
            header = format!("{} vs {} matches:\n", a, b);
        } else if let Some(a) = &team_disp {
            header = format!("Matches involving {}:\n", a);
        }

        let total = matches.len();
        let shown: Vec<String> = matches
            .iter()
            .take(limit)
            .map(|m| format!("- {}", m.summary()))
            .collect();

        let mut body = format!("{}{}", header, shown.join("\n"));
        if total > limit {
            body.push_str(&format!("\n... ({} more matches in dataset)", total - limit));
        }

        // Append head-to-head if exactly two teams were specified.
        if let (Some(ta), Some(tb)) = (&filter.team, &filter.opponent) {
            let h = self.db.head_to_head(ta, tb);
            body.push_str(&format!(
                "\n\nHead-to-head in dataset: {} {} wins, {} {} wins, {} draws",
                h.team_a, h.a_wins, h.team_b, h.b_wins, h.draws
            ));
        }
        body
    }

    fn tool_head_to_head(&self, args: &Value) -> String {
        let (a, b) = match (arg_str(args, "team_a"), arg_str(args, "team_b")) {
            (Some(a), Some(b)) => (a, b),
            _ => return "Both 'team_a' and 'team_b' are required.".to_string(),
        };
        let ka = match self.db.resolve_team(a) {
            Some((k, _)) => k,
            None => return format!("No team matching \"{}\".", a),
        };
        let kb = match self.db.resolve_team(b) {
            Some((k, _)) => k,
            None => return format!("No team matching \"{}\".", b),
        };
        let h = self.db.head_to_head(&ka, &kb);
        if h.total == 0 {
            return format!("No matches between {} and {} in the dataset.", h.team_a, h.team_b);
        }
        format!(
            "{} vs {} — head-to-head ({} matches):\n- {} wins: {}\n- {} wins: {}\n- Draws: {}\n- Goals: {} {} - {} {}",
            h.team_a, h.team_b, h.total,
            h.team_a, h.a_wins,
            h.team_b, h.b_wins,
            h.draws,
            h.team_a, h.a_goals, h.b_goals, h.team_b
        )
    }

    fn tool_team_record(&self, args: &Value) -> String {
        let team = match arg_str(args, "team") {
            Some(t) => t,
            None => return "'team' is required.".to_string(),
        };
        let (key, disp) = match self.db.resolve_team(team) {
            Some(v) => v,
            None => return format!("No team matching \"{}\".", team),
        };
        let mut filter = MatchFilter {
            team: Some(key),
            ..Default::default()
        };
        filter.season = arg_i32(args, "season");
        filter.competition = arg_str(args, "competition").map(|s| s.to_string());
        filter.venue = arg_str(args, "venue").map(|s| s.to_lowercase());

        let rec = self.db.team_record(&filter);
        if rec.matches == 0 {
            return format!("No matches found for {} with those filters.", disp);
        }

        let mut scope = disp.clone();
        if let Some(v) = &filter.venue {
            scope = format!("{} {}", scope, v);
        }
        let mut qualifiers = Vec::new();
        if let Some(s) = filter.season {
            qualifiers.push(s.to_string());
        }
        if let Some(c) = &filter.competition {
            qualifiers.push(c.clone());
        }
        let qual = if qualifiers.is_empty() {
            "all competitions".to_string()
        } else {
            qualifiers.join(" ")
        };

        format!(
            "{} record ({}):\n- Matches: {}\n- Wins: {}, Draws: {}, Losses: {}\n- Goals For: {}, Goals Against: {}\n- Win rate: {:.1}%",
            scope, qual, rec.matches, rec.wins, rec.draws, rec.losses,
            rec.goals_for, rec.goals_against, rec.win_rate()
        )
    }

    fn tool_standings(&self, args: &Value) -> String {
        let competition = arg_str(args, "competition").unwrap_or("Brasileirão Série A");
        let season = match arg_i32(args, "season") {
            Some(s) => s,
            None => return "'season' is required for standings.".to_string(),
        };
        let limit = arg_usize(args, "limit").unwrap_or(20);
        let rows = self.db.standings(competition, season);
        if rows.is_empty() {
            return format!("No data for {} {}.", competition, season);
        }
        let mut out = format!(
            "{} {} Final Standings (calculated from matches):\n",
            competition, season
        );
        for (i, row) in rows.iter().take(limit).enumerate() {
            out.push_str(&format!(
                "{:>2}. {} - {} pts ({}W, {}D, {}L), GF {} GA {} (GD {:+})\n",
                i + 1,
                row.team,
                row.record.points(),
                row.record.wins,
                row.record.draws,
                row.record.losses,
                row.record.goals_for,
                row.record.goals_against,
                row.record.goal_diff(),
            ));
        }
        out.trim_end().to_string()
    }

    fn tool_search_players(&self, args: &Value) -> String {
        let limit = arg_usize(args, "limit").unwrap_or(20);
        let filter = PlayerFilter {
            name: arg_str(args, "name").map(|s| s.to_string()),
            nationality: arg_str(args, "nationality").map(|s| s.to_string()),
            club: arg_str(args, "club").map(|s| s.to_string()),
            position: arg_str(args, "position").map(|s| s.to_string()),
            min_overall: arg_i32(args, "min_overall"),
        };
        let players = self.db.search_players(&filter);
        if players.is_empty() {
            return "No players found for the given criteria.".to_string();
        }
        let total = players.len();
        let mut out = format!("Found {} player(s):\n", total);
        for (i, p) in players.iter().take(limit).enumerate() {
            out.push_str(&format!("{:>2}. {}\n", i + 1, p.summary()));
        }
        if total > limit {
            out.push_str(&format!("... ({} more)\n", total - limit));
        }
        out.trim_end().to_string()
    }

    fn tool_league_stats(&self, args: &Value) -> String {
        let mut filter = MatchFilter {
            competition: arg_str(args, "competition").map(|s| s.to_string()),
            season: arg_i32(args, "season"),
            ..Default::default()
        };
        if let Some(t) = arg_str(args, "team") {
            match self.db.resolve_team(t) {
                Some((key, _)) => filter.team = Some(key),
                None => return format!("No team matching \"{}\".", t),
            }
        }
        let s = self.db.league_stats(&filter);
        if s.matches == 0 {
            return "No matches found for the given criteria.".to_string();
        }
        let mut scope = Vec::new();
        if let Some(c) = &filter.competition {
            scope.push(c.clone());
        }
        if let Some(season) = filter.season {
            scope.push(season.to_string());
        }
        let label = if scope.is_empty() {
            "All provided data".to_string()
        } else {
            scope.join(" ")
        };
        format!(
            "Statistics for {} ({} matches):\n- Total goals: {}\n- Average goals per match: {:.2}\n- Home wins: {} ({:.1}%)\n- Away wins: {}\n- Draws: {}",
            label, s.matches, s.total_goals, s.avg_goals_per_match,
            s.home_wins, s.home_win_rate, s.away_wins, s.draws
        )
    }

    fn tool_biggest_wins(&self, args: &Value) -> String {
        let limit = arg_usize(args, "limit").unwrap_or(10);
        let mut filter = MatchFilter {
            competition: arg_str(args, "competition").map(|s| s.to_string()),
            season: arg_i32(args, "season"),
            ..Default::default()
        };
        if let Some(t) = arg_str(args, "team") {
            match self.db.resolve_team(t) {
                Some((key, _)) => filter.team = Some(key),
                None => return format!("No team matching \"{}\".", t),
            }
        }
        let matches = self.db.biggest_wins(&filter, limit);
        if matches.is_empty() {
            return "No matches found for the given criteria.".to_string();
        }
        let mut out = "Biggest victories (by margin):\n".to_string();
        for (i, m) in matches.iter().enumerate() {
            out.push_str(&format!("{:>2}. {}\n", i + 1, m.summary()));
        }
        out.trim_end().to_string()
    }

    fn tool_team_competitions(&self, args: &Value) -> String {
        let team = match arg_str(args, "team") {
            Some(t) => t,
            None => return "'team' is required.".to_string(),
        };
        let (key, disp) = match self.db.resolve_team(team) {
            Some(v) => v,
            None => return format!("No team matching \"{}\".", team),
        };
        let comps = self.db.competitions_for_team(&key);
        if comps.is_empty() {
            return format!("No matches found for {}.", disp);
        }
        let mut out = format!("Competitions {} has played in (provided data):\n", disp);
        for (name, n) in comps {
            out.push_str(&format!("- {}: {} matches\n", name, n));
        }
        out.trim_end().to_string()
    }

    fn tool_list_competitions(&self) -> String {
        let comps = self.db.competitions();
        let mut out = format!(
            "Loaded {} matches and {} players across these competitions:\n",
            self.db.match_count(),
            self.db.player_count()
        );
        for (name, min, max, n) in comps {
            if min > 0 {
                out.push_str(&format!("- {} ({}–{}): {} matches\n", name, min, max, n));
            } else {
                out.push_str(&format!("- {}: {} matches\n", name, n));
            }
        }
        out.trim_end().to_string()
    }
}

// -- argument helpers -------------------------------------------------------

fn arg_str<'a>(args: &'a Value, key: &str) -> Option<&'a str> {
    args.get(key).and_then(|v| v.as_str()).filter(|s| !s.trim().is_empty())
}

fn arg_i32(args: &Value, key: &str) -> Option<i32> {
    match args.get(key) {
        Some(Value::Number(n)) => n.as_i64().map(|v| v as i32),
        Some(Value::String(s)) => s.trim().parse::<i32>().ok(),
        _ => None,
    }
}

fn arg_usize(args: &Value, key: &str) -> Option<usize> {
    arg_i32(args, key).filter(|v| *v >= 0).map(|v| v as usize)
}

// -- JSON-RPC envelope helpers ----------------------------------------------

fn ok(id: Value, result: Value) -> Value {
    json!({ "jsonrpc": "2.0", "id": id, "result": result })
}

fn err(id: Value, code: i64, message: &str) -> Value {
    json!({ "jsonrpc": "2.0", "id": id, "error": { "code": code, "message": message } })
}

/// JSON-Schema definitions advertised via `tools/list`.
pub fn tool_definitions() -> Vec<Value> {
    let team = json!({ "type": "string", "description": "Team name; accepts variations like 'Palmeiras', 'Palmeiras-SP', 'São Paulo'." });
    let competition = json!({ "type": "string", "description": "Competition name or substring, e.g. 'Brasileirão', 'Copa do Brasil', 'Libertadores'." });
    let season = json!({ "type": "integer", "description": "Season year, e.g. 2019." });

    vec![
        json!({
            "name": "find_matches",
            "description": "Find matches by team, opponent, competition, season or date range. Returns a chronological list (newest first) and head-to-head totals when two teams are given.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team": team,
                    "opponent": { "type": "string", "description": "Optional second team to filter head-to-head fixtures." },
                    "competition": competition,
                    "season": season,
                    "date_from": { "type": "string", "description": "Inclusive ISO date lower bound (YYYY-MM-DD)." },
                    "date_to": { "type": "string", "description": "Inclusive ISO date upper bound (YYYY-MM-DD)." },
                    "venue": { "type": "string", "enum": ["home", "away"], "description": "Restrict 'team' to home or away fixtures." },
                    "limit": { "type": "integer", "description": "Max matches to list (default 20)." }
                }
            }
        }),
        json!({
            "name": "head_to_head",
            "description": "Summarise the all-time head-to-head record between two teams across all competitions in the dataset.",
            "inputSchema": {
                "type": "object",
                "properties": { "team_a": team, "team_b": team },
                "required": ["team_a", "team_b"]
            }
        }),
        json!({
            "name": "team_record",
            "description": "Compute a team's win/draw/loss record and goals, optionally scoped to a season, competition and/or home/away venue.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team": team,
                    "season": season,
                    "competition": competition,
                    "venue": { "type": "string", "enum": ["home", "away"] }
                },
                "required": ["team"]
            }
        }),
        json!({
            "name": "standings",
            "description": "Compute the league table for a competition and season from match results (3 pts win, 1 pt draw).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "competition": competition,
                    "season": season,
                    "limit": { "type": "integer", "description": "Number of table rows to return (default 20)." }
                },
                "required": ["season"]
            }
        }),
        json!({
            "name": "search_players",
            "description": "Search the FIFA player database by name, nationality, club, position and/or minimum overall rating. Results are sorted by rating.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": { "type": "string" },
                    "nationality": { "type": "string", "description": "e.g. 'Brazil'." },
                    "club": { "type": "string" },
                    "position": { "type": "string", "description": "Exact position code, e.g. 'GK', 'ST', 'LW'." },
                    "min_overall": { "type": "integer" },
                    "limit": { "type": "integer", "description": "Max players to list (default 20)." }
                }
            }
        }),
        json!({
            "name": "league_stats",
            "description": "Aggregate goal and result statistics (avg goals per match, home/away win rates) over a competition, season and/or team.",
            "inputSchema": {
                "type": "object",
                "properties": { "competition": competition, "season": season, "team": team }
            }
        }),
        json!({
            "name": "biggest_wins",
            "description": "List the largest-margin victories within an optional competition/season/team scope.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "competition": competition,
                    "season": season,
                    "team": team,
                    "limit": { "type": "integer", "description": "Number of matches to return (default 10)." }
                }
            }
        }),
        json!({
            "name": "team_competitions",
            "description": "List the competitions a team appears in, with match counts.",
            "inputSchema": {
                "type": "object",
                "properties": { "team": team },
                "required": ["team"]
            }
        }),
        json!({
            "name": "list_competitions",
            "description": "List all loaded competitions with their season ranges and match counts.",
            "inputSchema": { "type": "object", "properties": {} }
        }),
    ]
}
