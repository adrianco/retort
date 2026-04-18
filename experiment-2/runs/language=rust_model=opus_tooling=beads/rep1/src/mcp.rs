use serde_json::{json, Value};
use std::io::{BufRead, Write};

use crate::data::{Competition, Dataset};
use crate::query::{
    aggregate_stats, biggest_wins, find_matches, find_players, head_to_head, standings,
    team_stats, MatchFilter, PlayerFilter,
};

pub const PROTOCOL_VERSION: &str = "2024-11-05";
pub const SERVER_NAME: &str = "brazilian-soccer-mcp";
pub const SERVER_VERSION: &str = "0.1.0";

pub struct Server {
    pub ds: Dataset,
}

impl Server {
    pub fn new(ds: Dataset) -> Self { Server { ds } }

    pub fn handle_request(&self, req: &Value) -> Option<Value> {
        let id = req.get("id").cloned();
        let method = req.get("method").and_then(|v| v.as_str()).unwrap_or("");
        // Notifications have no id and expect no response.
        let is_notification = id.is_none();

        let result = match method {
            "initialize" => Ok(json!({
                "protocolVersion": PROTOCOL_VERSION,
                "serverInfo": { "name": SERVER_NAME, "version": SERVER_VERSION },
                "capabilities": { "tools": {} }
            })),
            "notifications/initialized" | "initialized" => return None,
            "ping" => Ok(json!({})),
            "tools/list" => Ok(json!({ "tools": tool_catalog() })),
            "tools/call" => self.tools_call(req.get("params").cloned().unwrap_or(Value::Null)),
            _ => Err((-32601, format!("Method not found: {}", method))),
        };

        if is_notification { return None; }

        match result {
            Ok(r) => Some(json!({ "jsonrpc": "2.0", "id": id, "result": r })),
            Err((code, msg)) => Some(json!({
                "jsonrpc": "2.0", "id": id,
                "error": { "code": code, "message": msg }
            })),
        }
    }

    fn tools_call(&self, params: Value) -> Result<Value, (i64, String)> {
        let name = params.get("name").and_then(|v| v.as_str()).unwrap_or("").to_string();
        let args = params.get("arguments").cloned().unwrap_or(Value::Null);
        let text = self.dispatch_tool(&name, &args)?;
        Ok(json!({
            "content": [ { "type": "text", "text": text } ]
        }))
    }

    pub fn dispatch_tool(&self, name: &str, args: &Value) -> Result<String, (i64, String)> {
        match name {
            "find_matches" => Ok(self.tool_find_matches(args)),
            "team_stats" => Ok(self.tool_team_stats(args)?),
            "head_to_head" => Ok(self.tool_head_to_head(args)?),
            "standings" => Ok(self.tool_standings(args)?),
            "find_players" => Ok(self.tool_find_players(args)),
            "biggest_wins" => Ok(self.tool_biggest_wins(args)),
            "aggregate_stats" => Ok(self.tool_aggregate(args)),
            _ => Err((-32601, format!("Unknown tool: {}", name))),
        }
    }

    fn build_filter<'a>(&self, args: &'a Value) -> MatchFilter<'a> {
        let s = |k: &str| args.get(k).and_then(|v| v.as_str());
        let comp = args.get("competition").and_then(|v| v.as_str()).and_then(parse_competition);
        MatchFilter {
            team: s("team"),
            home_team: s("home_team"),
            away_team: s("away_team"),
            opponent: s("opponent"),
            season: args.get("season").and_then(|v| v.as_i64()).map(|i| i as i32),
            date_from: s("date_from"),
            date_to: s("date_to"),
            competition: comp,
        }
    }

    fn tool_find_matches(&self, args: &Value) -> String {
        let filter = self.build_filter(args);
        let limit = args.get("limit").and_then(|v| v.as_u64()).unwrap_or(25) as usize;
        let ms = find_matches(&self.ds, &filter);
        let total = ms.len();
        let mut lines = Vec::new();
        lines.push(format!("Found {} matches (showing up to {})", total, limit.min(total)));
        for m in ms.iter().take(limit) {
            let round = m.round.as_deref().map(|r| format!(" R{}", r)).unwrap_or_default();
            lines.push(format!(
                "- {} [{}{}]: {} {}-{} {}",
                m.date, m.competition.as_str(), round,
                m.home_team, m.home_goal, m.away_goal, m.away_team
            ));
        }
        lines.join("\n")
    }

    fn tool_team_stats(&self, args: &Value) -> Result<String, (i64, String)> {
        let team = args.get("team").and_then(|v| v.as_str())
            .ok_or((-32602, "missing 'team'".into()))?;
        let filter = self.build_filter(args);
        let ms = find_matches(&self.ds, &MatchFilter { team: Some(team), ..filter });
        let s = team_stats(&ms, team);
        let scope = describe_filter(&filter);
        Ok(format!(
            "{} stats{}:\n- Matches: {}\n- Wins/Draws/Losses: {}/{}/{}\n- Goals For/Against: {}/{}\n- Points: {}\n- Win rate: {:.1}%\n- Home: {}W {}D {}L ({}/{} matches)\n- Away: {}W {}D {}L ({}/{} matches)",
            team, scope, s.matches, s.wins, s.draws, s.losses,
            s.goals_for, s.goals_against, s.points(), s.win_rate() * 100.0,
            s.home_wins, s.home_draws, s.home_losses, s.home_matches, s.matches,
            s.away_wins, s.away_draws, s.away_losses, s.away_matches, s.matches,
        ))
    }

    fn tool_head_to_head(&self, args: &Value) -> Result<String, (i64, String)> {
        let a = args.get("team_a").and_then(|v| v.as_str())
            .ok_or((-32602, "missing 'team_a'".into()))?;
        let b = args.get("team_b").and_then(|v| v.as_str())
            .ok_or((-32602, "missing 'team_b'".into()))?;
        let h = head_to_head(&self.ds, a, b);
        Ok(format!(
            "Head-to-head {} vs {}:\n- Matches: {}\n- {} wins: {}\n- {} wins: {}\n- Draws: {}\n- Goals: {} {} - {} {}",
            a, b, h.matches, a, h.a_wins, b, h.b_wins, h.draws, a, h.a_goals, h.b_goals, b
        ))
    }

    fn tool_standings(&self, args: &Value) -> Result<String, (i64, String)> {
        let comp = args.get("competition").and_then(|v| v.as_str())
            .and_then(parse_competition)
            .unwrap_or(Competition::Brasileirao);
        let season = args.get("season").and_then(|v| v.as_i64())
            .ok_or((-32602, "missing 'season'".into()))? as i32;
        let limit = args.get("limit").and_then(|v| v.as_u64()).unwrap_or(20) as usize;
        let rows = standings(&self.ds, comp, season);
        if rows.is_empty() {
            return Ok(format!("No data for {} in {}", comp.as_str(), season));
        }
        let mut lines = Vec::new();
        lines.push(format!("{} {} Standings (calculated from matches):", season, comp.as_str()));
        for r in rows.iter().take(limit) {
            lines.push(format!(
                "{:>2}. {:<28} P{:>3} W{:>3} D{:>3} L{:>3} GF{:>3} GA{:>3} GD{:>+4} Pts{:>4}",
                r.position, truncate(&r.team, 28), r.played, r.wins, r.draws, r.losses,
                r.goals_for, r.goals_against, r.goal_diff, r.points
            ));
        }
        Ok(lines.join("\n"))
    }

    fn tool_find_players(&self, args: &Value) -> String {
        let s = |k: &str| args.get(k).and_then(|v| v.as_str());
        let filter = PlayerFilter {
            name_contains: s("name"),
            nationality: s("nationality"),
            club_contains: s("club"),
            position: s("position"),
            min_overall: args.get("min_overall").and_then(|v| v.as_i64()).map(|i| i as i32),
            limit: args.get("limit").and_then(|v| v.as_u64()).map(|i| i as usize).or(Some(25)),
            sort_by_overall_desc: args.get("sort_by_overall").and_then(|v| v.as_bool()).unwrap_or(true),
        };
        let ps = find_players(&self.ds, &filter);
        let mut lines = Vec::new();
        lines.push(format!("Found {} players", ps.len()));
        for p in &ps {
            lines.push(format!(
                "- {} (#{}) — Overall: {}, Pos: {}, Club: {}, Nat: {}, Age: {}",
                p.name,
                p.id,
                p.overall.map(|v| v.to_string()).unwrap_or_else(|| "-".into()),
                p.position, p.club, p.nationality,
                p.age.map(|v| v.to_string()).unwrap_or_else(|| "-".into())
            ));
        }
        lines.join("\n")
    }

    fn tool_biggest_wins(&self, args: &Value) -> String {
        let comp = args.get("competition").and_then(|v| v.as_str()).and_then(parse_competition);
        let limit = args.get("limit").and_then(|v| v.as_u64()).unwrap_or(10) as usize;
        let v = biggest_wins(&self.ds, comp, limit);
        let mut lines = Vec::new();
        lines.push("Biggest victories:".to_string());
        for (i, w) in v.iter().enumerate() {
            lines.push(format!(
                "{:>2}. {} [{}]: {} {}-{} {} (margin {})",
                i + 1, w.date, w.competition, w.home_team, w.home_goal, w.away_goal, w.away_team, w.margin
            ));
        }
        lines.join("\n")
    }

    fn tool_aggregate(&self, args: &Value) -> String {
        let filter = self.build_filter(args);
        let s = aggregate_stats(&self.ds, &filter);
        format!(
            "Aggregate stats{}:\n- Total matches: {}\n- Total goals: {}\n- Avg goals/match: {:.2}\n- Home wins: {} ({:.1}%)\n- Away wins: {}\n- Draws: {}",
            describe_filter(&filter), s.total_matches, s.total_goals, s.avg_goals_per_match,
            s.home_wins, s.home_win_rate * 100.0, s.away_wins, s.draws,
        )
    }
}

fn truncate(s: &str, n: usize) -> String {
    let chars: Vec<char> = s.chars().collect();
    if chars.len() <= n { s.to_string() } else { chars[..n].iter().collect() }
}

fn describe_filter(f: &MatchFilter) -> String {
    let mut parts = Vec::new();
    if let Some(c) = f.competition { parts.push(format!("comp={}", c.as_str())); }
    if let Some(s) = f.season { parts.push(format!("season={}", s)); }
    if let Some(d) = f.date_from { parts.push(format!("from={}", d)); }
    if let Some(d) = f.date_to { parts.push(format!("to={}", d)); }
    if parts.is_empty() { String::new() } else { format!(" ({})", parts.join(", ")) }
}

pub fn parse_competition(s: &str) -> Option<Competition> {
    let l = s.to_lowercase();
    match l.as_str() {
        "brasileirao" | "brasileirão" | "serie_a" | "serie a" => Some(Competition::Brasileirao),
        "copa_do_brasil" | "copa do brasil" | "brazilian_cup" => Some(Competition::CopaDoBrasil),
        "libertadores" | "copa_libertadores" | "copa libertadores" => Some(Competition::Libertadores),
        _ => None,
    }
}

pub fn tool_catalog() -> Value {
    json!([
        {
            "name": "find_matches",
            "description": "Find matches filtered by team(s), season, competition, or date range.",
            "inputSchema": { "type": "object", "properties": {
                "team": { "type": "string", "description": "Match involves this team (home or away)" },
                "opponent": { "type": "string", "description": "Use with 'team' to restrict to team-vs-opponent" },
                "home_team": { "type": "string" },
                "away_team": { "type": "string" },
                "season": { "type": "integer" },
                "date_from": { "type": "string", "description": "ISO date YYYY-MM-DD inclusive" },
                "date_to": { "type": "string", "description": "ISO date YYYY-MM-DD inclusive" },
                "competition": { "type": "string", "enum": ["brasileirao", "copa_do_brasil", "libertadores"] },
                "limit": { "type": "integer", "default": 25 }
            } }
        },
        {
            "name": "team_stats",
            "description": "Aggregate wins/draws/losses, goals for/against, points, and home/away splits for a team.",
            "inputSchema": { "type": "object", "required": ["team"], "properties": {
                "team": { "type": "string" },
                "season": { "type": "integer" },
                "competition": { "type": "string" }
            } }
        },
        {
            "name": "head_to_head",
            "description": "Head-to-head record between two teams across all matches.",
            "inputSchema": { "type": "object", "required": ["team_a", "team_b"], "properties": {
                "team_a": { "type": "string" },
                "team_b": { "type": "string" }
            } }
        },
        {
            "name": "standings",
            "description": "Calculate final standings for a league season from match results.",
            "inputSchema": { "type": "object", "required": ["season"], "properties": {
                "competition": { "type": "string", "default": "brasileirao" },
                "season": { "type": "integer" },
                "limit": { "type": "integer", "default": 20 }
            } }
        },
        {
            "name": "find_players",
            "description": "Search the FIFA player database by name/nationality/club/position.",
            "inputSchema": { "type": "object", "properties": {
                "name": { "type": "string" },
                "nationality": { "type": "string" },
                "club": { "type": "string" },
                "position": { "type": "string" },
                "min_overall": { "type": "integer" },
                "sort_by_overall": { "type": "boolean", "default": true },
                "limit": { "type": "integer", "default": 25 }
            } }
        },
        {
            "name": "biggest_wins",
            "description": "Return the matches with the largest goal margins.",
            "inputSchema": { "type": "object", "properties": {
                "competition": { "type": "string" },
                "limit": { "type": "integer", "default": 10 }
            } }
        },
        {
            "name": "aggregate_stats",
            "description": "Aggregate match stats (total goals, averages, home-win rate) under the same filter as find_matches.",
            "inputSchema": { "type": "object", "properties": {
                "team": { "type": "string" },
                "season": { "type": "integer" },
                "competition": { "type": "string" },
                "date_from": { "type": "string" },
                "date_to": { "type": "string" }
            } }
        }
    ])
}

pub fn run_stdio(server: Server) -> std::io::Result<()> {
    let stdin = std::io::stdin();
    let stdout = std::io::stdout();
    let mut out = stdout.lock();
    for line in stdin.lock().lines() {
        let line = line?;
        if line.trim().is_empty() { continue; }
        let req: Value = match serde_json::from_str(&line) {
            Ok(v) => v,
            Err(e) => {
                let err = json!({
                    "jsonrpc": "2.0", "id": null,
                    "error": { "code": -32700, "message": format!("Parse error: {}", e) }
                });
                writeln!(out, "{}", err)?;
                out.flush()?;
                continue;
            }
        };
        if let Some(resp) = server.handle_request(&req) {
            writeln!(out, "{}", resp)?;
            out.flush()?;
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::data::Dataset;

    fn srv() -> Server {
        Server::new(Dataset::load_default("data/kaggle").unwrap())
    }

    #[test]
    fn initialize_handshake() {
        let s = srv();
        let req = json!({"jsonrpc":"2.0","id":1,"method":"initialize","params":{}});
        let resp = s.handle_request(&req).unwrap();
        assert_eq!(resp["result"]["serverInfo"]["name"], SERVER_NAME);
    }

    #[test]
    fn tools_list_returns_tools() {
        let s = srv();
        let req = json!({"jsonrpc":"2.0","id":2,"method":"tools/list"});
        let resp = s.handle_request(&req).unwrap();
        let tools = resp["result"]["tools"].as_array().unwrap();
        assert!(tools.len() >= 7);
    }

    #[test]
    fn find_matches_tool_call() {
        let s = srv();
        let req = json!({
            "jsonrpc":"2.0","id":3,"method":"tools/call",
            "params": { "name":"find_matches", "arguments": {
                "team":"Flamengo", "opponent":"Fluminense", "limit": 5
            } }
        });
        let resp = s.handle_request(&req).unwrap();
        let text = resp["result"]["content"][0]["text"].as_str().unwrap();
        assert!(text.contains("matches"));
    }

    #[test]
    fn standings_tool_call() {
        let s = srv();
        let req = json!({
            "jsonrpc":"2.0","id":4,"method":"tools/call",
            "params": { "name":"standings", "arguments": {
                "competition": "brasileirao", "season": 2019, "limit": 3
            } }
        });
        let resp = s.handle_request(&req).unwrap();
        let text = resp["result"]["content"][0]["text"].as_str().unwrap();
        assert!(text.to_lowercase().contains("flamengo"));
    }

    #[test]
    fn unknown_method_returns_error() {
        let s = srv();
        let req = json!({"jsonrpc":"2.0","id":5,"method":"does/not/exist"});
        let resp = s.handle_request(&req).unwrap();
        assert_eq!(resp["error"]["code"], -32601);
    }

    #[test]
    fn initialized_notification_no_response() {
        let s = srv();
        let req = json!({"jsonrpc":"2.0","method":"notifications/initialized"});
        assert!(s.handle_request(&req).is_none());
    }
}
