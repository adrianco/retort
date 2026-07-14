use std::io::{BufRead, Write};

use anyhow::Result;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};

use crate::data::Competition;
use crate::queries::{
    self, club_averages_by_nationality, head_to_head, search_matches, search_players,
    season_standings, team_stats, top_players, MatchFilter, PlayerFilter,
};
use crate::store::Store;

const PROTOCOL_VERSION: &str = "2024-11-05";
const SERVER_NAME: &str = "brazilian-soccer-mcp";
const SERVER_VERSION: &str = env!("CARGO_PKG_VERSION");

#[derive(Debug, Deserialize)]
struct Request {
    jsonrpc: String,
    #[serde(default)]
    id: Option<Value>,
    method: String,
    #[serde(default)]
    params: Option<Value>,
}

#[derive(Debug, Serialize)]
struct ResponseOk {
    jsonrpc: &'static str,
    id: Value,
    result: Value,
}

#[derive(Debug, Serialize)]
struct ResponseErr {
    jsonrpc: &'static str,
    id: Value,
    error: ErrorObj,
}

#[derive(Debug, Serialize)]
struct ErrorObj {
    code: i32,
    message: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    data: Option<Value>,
}

pub struct Server {
    store: Store,
}

impl Server {
    pub fn new(store: Store) -> Self {
        Server { store }
    }

    /// Drive the JSON-RPC loop until stdin closes.
    pub fn run_stdio(&self) -> Result<()> {
        let stdin = std::io::stdin();
        let stdout = std::io::stdout();
        let mut out = stdout.lock();
        let mut line = String::new();
        let mut handle = stdin.lock();
        loop {
            line.clear();
            let n = handle.read_line(&mut line)?;
            if n == 0 {
                return Ok(());
            }
            let trimmed = line.trim();
            if trimmed.is_empty() {
                continue;
            }
            let resp = self.dispatch_line(trimmed);
            if let Some(s) = resp {
                writeln!(out, "{}", s)?;
                out.flush()?;
            }
        }
    }

    pub fn dispatch_line(&self, line: &str) -> Option<String> {
        let req: Request = match serde_json::from_str(line) {
            Ok(r) => r,
            Err(e) => {
                let err = ResponseErr {
                    jsonrpc: "2.0",
                    id: Value::Null,
                    error: ErrorObj {
                        code: -32700,
                        message: format!("Parse error: {}", e),
                        data: None,
                    },
                };
                return Some(serde_json::to_string(&err).unwrap());
            }
        };
        if req.jsonrpc != "2.0" {
            let err = ResponseErr {
                jsonrpc: "2.0",
                id: req.id.unwrap_or(Value::Null),
                error: ErrorObj {
                    code: -32600,
                    message: "Invalid JSON-RPC version".to_string(),
                    data: None,
                },
            };
            return Some(serde_json::to_string(&err).unwrap());
        }
        // Notifications: no id → no response
        let is_notification = req.id.is_none();
        let result = self.handle(&req.method, req.params.as_ref());
        if is_notification {
            return None;
        }
        let id = req.id.unwrap_or(Value::Null);
        let resp = match result {
            Ok(v) => serde_json::to_string(&ResponseOk {
                jsonrpc: "2.0",
                id,
                result: v,
            })
            .unwrap(),
            Err((code, msg)) => serde_json::to_string(&ResponseErr {
                jsonrpc: "2.0",
                id,
                error: ErrorObj {
                    code,
                    message: msg,
                    data: None,
                },
            })
            .unwrap(),
        };
        Some(resp)
    }

    fn handle(&self, method: &str, params: Option<&Value>) -> Result<Value, (i32, String)> {
        match method {
            "initialize" => Ok(json!({
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": { "tools": {} },
                "serverInfo": { "name": SERVER_NAME, "version": SERVER_VERSION }
            })),
            "ping" => Ok(json!({})),
            "notifications/initialized" => Ok(Value::Null),
            "tools/list" => Ok(json!({ "tools": tool_definitions() })),
            "tools/call" => {
                let params = params.ok_or((-32602, "missing params".into()))?;
                let name = params
                    .get("name")
                    .and_then(|v| v.as_str())
                    .ok_or((-32602, "missing tool name".into()))?;
                let empty = json!({});
                let args = params.get("arguments").unwrap_or(&empty);
                self.call_tool(name, args)
            }
            "resources/list" => Ok(json!({ "resources": [] })),
            "prompts/list" => Ok(json!({ "prompts": [] })),
            other => Err((
                -32601,
                format!("Method not found: {}", other),
            )),
        }
    }

    pub fn call_tool(&self, name: &str, args: &Value) -> Result<Value, (i32, String)> {
        let text = match name {
            "search_matches" => self.tool_search_matches(args),
            "team_stats" => self.tool_team_stats(args),
            "head_to_head" => self.tool_head_to_head(args),
            "season_standings" => self.tool_season_standings(args),
            "biggest_wins" => self.tool_biggest_wins(args),
            "competition_stats" => self.tool_competition_stats(args),
            "search_players" => self.tool_search_players(args),
            "top_players" => self.tool_top_players(args),
            "brazilian_clubs_summary" => self.tool_brazilian_clubs(args),
            "team_competitions" => self.tool_team_competitions(args),
            other => {
                return Err((
                    -32602,
                    format!("Unknown tool: {}", other),
                ));
            }
        };
        let text = text.map_err(|e| (-32602, e))?;
        Ok(json!({
            "content": [{ "type": "text", "text": text }],
            "isError": false
        }))
    }

    // ---------- tool impls ----------

    fn tool_search_matches(&self, args: &Value) -> Result<String, String> {
        let team = args.get("team").and_then(|v| v.as_str());
        let opp = args.get("opponent").and_then(|v| v.as_str());
        let comp_str = args.get("competition").and_then(|v| v.as_str());
        let season = args.get("season").and_then(|v| v.as_i64()).map(|v| v as i32);
        let limit = args
            .get("limit")
            .and_then(|v| v.as_u64())
            .map(|v| v as usize)
            .unwrap_or(25);
        let competition = comp_str.and_then(Competition::parse);

        let filter = MatchFilter {
            team,
            opponent: opp,
            competition,
            season,
            ..Default::default()
        };
        let mut found = search_matches(&self.store, &filter);
        found.sort_by(|a, b| b.date.cmp(&a.date));
        let total = found.len();
        let take = found.iter().take(limit);
        let mut s = String::new();
        s.push_str(&format!("Matches found: {}\n", total));
        if let (Some(t), Some(o)) = (team, opp) {
            let h2h = head_to_head(&self.store, t, o);
            s.push_str(&format!(
                "Head-to-head ({} vs {}): {} wins {}, {} wins {}, draws {}\n",
                t, o, t, h2h.team1_wins, o, h2h.team2_wins, h2h.draws
            ));
        } else if let Some(t) = team {
            s.push_str(&format!("Filter: team={}\n", t));
        }
        if take.len() == 0 && total == 0 {
            s.push_str("(no matches)\n");
            return Ok(s);
        }
        s.push_str(&format!(
            "Showing {} of {} (most recent first):\n",
            limit.min(total),
            total
        ));
        for m in found.iter().take(limit) {
            s.push_str(&format!("- {}\n", m.score_line()));
        }
        Ok(s)
    }

    fn tool_team_stats(&self, args: &Value) -> Result<String, String> {
        let team = args
            .get("team")
            .and_then(|v| v.as_str())
            .ok_or("missing 'team'")?;
        let comp = args
            .get("competition")
            .and_then(|v| v.as_str())
            .and_then(Competition::parse);
        let season = args.get("season").and_then(|v| v.as_i64()).map(|v| v as i32);
        let home_only = args
            .get("home_only")
            .and_then(|v| v.as_bool())
            .unwrap_or(false);
        let away_only = args
            .get("away_only")
            .and_then(|v| v.as_bool())
            .unwrap_or(false);
        let filter = MatchFilter {
            competition: comp,
            season,
            home_only,
            away_only,
            ..Default::default()
        };
        let stats = team_stats(&self.store, team, &filter);
        let mut s = String::new();
        s.push_str(&format!("Team: {}\n", team));
        if let Some(c) = comp {
            s.push_str(&format!("Competition: {}\n", c.label()));
        }
        if let Some(y) = season {
            s.push_str(&format!("Season: {}\n", y));
        }
        if home_only {
            s.push_str("Venue: home only\n");
        }
        if away_only {
            s.push_str("Venue: away only\n");
        }
        s.push_str(&format!("Matches: {}\n", stats.played));
        s.push_str(&format!(
            "Wins: {}, Draws: {}, Losses: {}\n",
            stats.wins, stats.draws, stats.losses
        ));
        s.push_str(&format!(
            "Goals For: {}, Goals Against: {}, Goal Diff: {:+}\n",
            stats.goals_for,
            stats.goals_against,
            stats.goal_diff()
        ));
        s.push_str(&format!("Points: {}\n", stats.points()));
        s.push_str(&format!("Win rate: {:.1}%\n", stats.win_rate() * 100.0));
        Ok(s)
    }

    fn tool_head_to_head(&self, args: &Value) -> Result<String, String> {
        let team1 = args
            .get("team1")
            .and_then(|v| v.as_str())
            .ok_or("missing 'team1'")?;
        let team2 = args
            .get("team2")
            .and_then(|v| v.as_str())
            .ok_or("missing 'team2'")?;
        let h = head_to_head(&self.store, team1, team2);
        let total = h.team1_wins + h.team2_wins + h.draws;
        let mut s = String::new();
        s.push_str(&format!("Head-to-head: {} vs {}\n", team1, team2));
        s.push_str(&format!("Total meetings: {}\n", total));
        s.push_str(&format!(
            "{} wins: {}, {} wins: {}, draws: {}\n",
            team1, h.team1_wins, team2, h.team2_wins, h.draws
        ));
        s.push_str(&format!(
            "Goals: {} {} - {} {}\n",
            team1, h.team1_goals, h.team2_goals, team2
        ));
        Ok(s)
    }

    fn tool_season_standings(&self, args: &Value) -> Result<String, String> {
        let season = args
            .get("season")
            .and_then(|v| v.as_i64())
            .ok_or("missing 'season'")? as i32;
        let competition = args
            .get("competition")
            .and_then(|v| v.as_str())
            .and_then(Competition::parse)
            .unwrap_or(Competition::Brasileirao);
        let limit = args
            .get("limit")
            .and_then(|v| v.as_u64())
            .map(|v| v as usize)
            .unwrap_or(20);

        let rows = season_standings(&self.store, season, competition);
        let mut s = String::new();
        s.push_str(&format!(
            "{} {} Standings (calculated from matches):\n",
            season,
            competition.label()
        ));
        if rows.is_empty() {
            s.push_str("(no matches found for this season/competition)\n");
            return Ok(s);
        }
        for (i, r) in rows.iter().take(limit).enumerate() {
            s.push_str(&format!(
                "{:>2}. {} - {} pts ({}W {}D {}L, GF {} GA {} GD {:+})\n",
                i + 1,
                r.team,
                r.stats.points(),
                r.stats.wins,
                r.stats.draws,
                r.stats.losses,
                r.stats.goals_for,
                r.stats.goals_against,
                r.stats.goal_diff()
            ));
        }
        Ok(s)
    }

    fn tool_biggest_wins(&self, args: &Value) -> Result<String, String> {
        let comp = args
            .get("competition")
            .and_then(|v| v.as_str())
            .and_then(Competition::parse);
        let limit = args
            .get("limit")
            .and_then(|v| v.as_u64())
            .map(|v| v as usize)
            .unwrap_or(10);
        let matches = queries::biggest_wins(&self.store, comp, limit);
        let mut s = String::new();
        s.push_str(&format!(
            "Biggest victories{}:\n",
            comp.map(|c| format!(" ({})", c.label())).unwrap_or_default()
        ));
        for (i, m) in matches.iter().enumerate() {
            s.push_str(&format!("{:>2}. {}\n", i + 1, m.score_line()));
        }
        Ok(s)
    }

    fn tool_competition_stats(&self, args: &Value) -> Result<String, String> {
        let comp = args
            .get("competition")
            .and_then(|v| v.as_str())
            .and_then(Competition::parse);
        let season = args.get("season").and_then(|v| v.as_i64()).map(|v| v as i32);
        let s = queries::competition_stats(&self.store, comp, season);
        let mut out = String::new();
        out.push_str(&format!(
            "Stats{}{}:\n",
            comp.map(|c| format!(" — {}", c.label())).unwrap_or_default(),
            season.map(|y| format!(" — {}", y)).unwrap_or_default()
        ));
        out.push_str(&format!("Matches: {}\n", s.matches));
        out.push_str(&format!("Total goals: {}\n", s.total_goals));
        out.push_str(&format!("Average goals per match: {:.2}\n", s.average_goals()));
        out.push_str(&format!(
            "Home wins: {} ({:.1}%), Away wins: {}, Draws: {}\n",
            s.home_wins,
            s.home_win_rate() * 100.0,
            s.away_wins,
            s.draws
        ));
        Ok(out)
    }

    fn tool_search_players(&self, args: &Value) -> Result<String, String> {
        let f = PlayerFilter {
            name: args.get("name").and_then(|v| v.as_str()),
            nationality: args.get("nationality").and_then(|v| v.as_str()),
            club: args.get("club").and_then(|v| v.as_str()),
            position: args.get("position").and_then(|v| v.as_str()),
            min_overall: args
                .get("min_overall")
                .and_then(|v| v.as_i64())
                .map(|v| v as i32),
        };
        let limit = args
            .get("limit")
            .and_then(|v| v.as_u64())
            .map(|v| v as usize)
            .unwrap_or(20);
        let mut found = search_players(&self.store, &f);
        found.sort_by(|a, b| b.overall.unwrap_or(0).cmp(&a.overall.unwrap_or(0)));
        let total = found.len();
        let mut s = String::new();
        s.push_str(&format!("Players found: {}\n", total));
        s.push_str(&format!("Showing {} of {}:\n", limit.min(total), total));
        for (i, p) in found.iter().take(limit).enumerate() {
            s.push_str(&format!(
                "{:>3}. {} — Age {}, {}, Overall {}, Position {}, Club {}\n",
                i + 1,
                p.name,
                p.age.map(|x| x.to_string()).unwrap_or_else(|| "?".into()),
                p.nationality,
                p.overall.map(|x| x.to_string()).unwrap_or_else(|| "?".into()),
                p.position.as_deref().unwrap_or("?"),
                if p.club.is_empty() { "(free agent)" } else { &p.club }
            ));
        }
        Ok(s)
    }

    fn tool_top_players(&self, args: &Value) -> Result<String, String> {
        let nationality = args.get("nationality").and_then(|v| v.as_str());
        let club = args.get("club").and_then(|v| v.as_str());
        let limit = args
            .get("limit")
            .and_then(|v| v.as_u64())
            .map(|v| v as usize)
            .unwrap_or(10);
        let players = top_players(&self.store, nationality, club, limit);
        let mut s = String::new();
        let label = match (nationality, club) {
            (Some(n), Some(c)) => format!("{} players at {}", n, c),
            (Some(n), None) => format!("{} players", n),
            (None, Some(c)) => format!("players at {}", c),
            (None, None) => "players".into(),
        };
        s.push_str(&format!("Top {}:\n", label));
        for (i, p) in players.iter().enumerate() {
            s.push_str(&format!(
                "{:>2}. {} — Overall {}, Position {}, Club {}\n",
                i + 1,
                p.name,
                p.overall.map(|x| x.to_string()).unwrap_or_else(|| "?".into()),
                p.position.as_deref().unwrap_or("?"),
                if p.club.is_empty() { "(free agent)" } else { &p.club }
            ));
        }
        Ok(s)
    }

    fn tool_brazilian_clubs(&self, args: &Value) -> Result<String, String> {
        let limit = args
            .get("limit")
            .and_then(|v| v.as_u64())
            .map(|v| v as usize)
            .unwrap_or(15);
        let entries = club_averages_by_nationality(&self.store, "Brazil");
        let mut s = String::new();
        s.push_str("Brazilian players grouped by club (top by count):\n");
        for (club, n, avg) in entries.iter().take(limit) {
            s.push_str(&format!(
                "- {}: {} players (avg rating: {:.1})\n",
                club, n, avg
            ));
        }
        Ok(s)
    }

    fn tool_team_competitions(&self, args: &Value) -> Result<String, String> {
        let team = args
            .get("team")
            .and_then(|v| v.as_str())
            .ok_or("missing 'team'")?;
        let team_norm = crate::normalize::normalize_team(team);
        let mut by_comp: std::collections::HashMap<Competition, u32> =
            std::collections::HashMap::new();
        for m in &self.store.matches {
            if m.home_team_norm.contains(&team_norm) || m.away_team_norm.contains(&team_norm) {
                *by_comp.entry(m.competition).or_insert(0) += 1;
            }
        }
        let mut entries: Vec<(Competition, u32)> = by_comp.into_iter().collect();
        entries.sort_by(|a, b| b.1.cmp(&a.1));
        let mut s = String::new();
        s.push_str(&format!("Competitions for {}:\n", team));
        if entries.is_empty() {
            s.push_str("(no matches found)\n");
        }
        for (c, n) in entries {
            s.push_str(&format!("- {}: {} matches\n", c.label(), n));
        }
        Ok(s)
    }
}

fn tool_definitions() -> Vec<Value> {
    vec![
        json!({
            "name": "search_matches",
            "description": "Search matches across all loaded datasets. Filter by team, opponent, competition, or season.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team": {"type": "string", "description": "Team name (normalized; accepts 'Flamengo' or 'Flamengo-RJ')"},
                    "opponent": {"type": "string", "description": "Opponent team name"},
                    "competition": {"type": "string", "description": "Brasileirão, Copa do Brasil, Libertadores"},
                    "season": {"type": "integer", "description": "Season year"},
                    "limit": {"type": "integer", "description": "Max matches to display (default 25)"}
                }
            }
        }),
        json!({
            "name": "team_stats",
            "description": "Win/loss/draw/goals record for a team. Filter by competition, season, or home-only/away-only.",
            "inputSchema": {
                "type": "object",
                "required": ["team"],
                "properties": {
                    "team": {"type": "string"},
                    "competition": {"type": "string"},
                    "season": {"type": "integer"},
                    "home_only": {"type": "boolean"},
                    "away_only": {"type": "boolean"}
                }
            }
        }),
        json!({
            "name": "head_to_head",
            "description": "Aggregate head-to-head record between two teams across all datasets.",
            "inputSchema": {
                "type": "object",
                "required": ["team1", "team2"],
                "properties": {
                    "team1": {"type": "string"},
                    "team2": {"type": "string"}
                }
            }
        }),
        json!({
            "name": "season_standings",
            "description": "Calculated end-of-season standings (3 pts/win, 1 pt/draw).",
            "inputSchema": {
                "type": "object",
                "required": ["season"],
                "properties": {
                    "season": {"type": "integer"},
                    "competition": {"type": "string", "description": "Default Brasileirão"},
                    "limit": {"type": "integer", "description": "Default 20"}
                }
            }
        }),
        json!({
            "name": "biggest_wins",
            "description": "Largest margin-of-victory matches.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "competition": {"type": "string"},
                    "limit": {"type": "integer", "description": "Default 10"}
                }
            }
        }),
        json!({
            "name": "competition_stats",
            "description": "Aggregate stats (match count, avg goals, home win rate) for a competition/season.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "competition": {"type": "string"},
                    "season": {"type": "integer"}
                }
            }
        }),
        json!({
            "name": "search_players",
            "description": "Search FIFA player data by name, nationality, club, position, or minimum rating.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "nationality": {"type": "string"},
                    "club": {"type": "string"},
                    "position": {"type": "string"},
                    "min_overall": {"type": "integer"},
                    "limit": {"type": "integer", "description": "Default 20"}
                }
            }
        }),
        json!({
            "name": "top_players",
            "description": "Top-rated players by FIFA Overall; optionally restrict by nationality or club.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "nationality": {"type": "string"},
                    "club": {"type": "string"},
                    "limit": {"type": "integer", "description": "Default 10"}
                }
            }
        }),
        json!({
            "name": "brazilian_clubs_summary",
            "description": "Number of Brazilian players and average rating per club.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Default 15"}
                }
            }
        }),
        json!({
            "name": "team_competitions",
            "description": "List which competitions a team appears in (across all datasets).",
            "inputSchema": {
                "type": "object",
                "required": ["team"],
                "properties": {
                    "team": {"type": "string"}
                }
            }
        }),
    ]
}
