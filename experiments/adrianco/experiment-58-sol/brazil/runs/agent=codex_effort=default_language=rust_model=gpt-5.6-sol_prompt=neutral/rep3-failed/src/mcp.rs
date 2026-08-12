use crate::model::MatchFilter;
use crate::normalize::parse_date;
use crate::store::{format_matches, SoccerStore};
use serde_json::{json, Map, Value};

pub struct McpServer {
    store: SoccerStore,
}

impl McpServer {
    pub fn new(store: SoccerStore) -> Self {
        Self { store }
    }
    pub fn store(&self) -> &SoccerStore {
        &self.store
    }

    /// Handles one JSON-RPC message. Notifications intentionally produce no response.
    pub fn handle(&self, request: Value) -> Option<Value> {
        let id = request.get("id").cloned()?;
        let method = request.get("method").and_then(Value::as_str).unwrap_or("");
        let result = match method {
            "initialize" => Ok(json!({
                "protocolVersion": request.pointer("/params/protocolVersion").and_then(Value::as_str).unwrap_or("2025-06-18"),
                "capabilities": { "tools": { "listChanged": false } },
                "serverInfo": { "name": "brasileirao-mcp", "version": env!("CARGO_PKG_VERSION") },
                "instructions": "Query the bundled Brazilian soccer match and FIFA player datasets. Use structured filters; team names and accents are normalized automatically."
            })),
            "ping" => Ok(json!({})),
            "tools/list" => Ok(json!({ "tools": tool_definitions() })),
            "tools/call" => self.call_tool(request.get("params").unwrap_or(&Value::Null)),
            _ => {
                return Some(error_response(
                    id,
                    -32601,
                    format!("method not found: {method}"),
                ))
            }
        };
        Some(match result {
            Ok(value) => json!({"jsonrpc":"2.0", "id":id, "result":value}),
            Err(message) => error_response(id, -32602, message),
        })
    }

    fn call_tool(&self, params: &Value) -> Result<Value, String> {
        let name = required_str(params, "name")?;
        let args = params
            .get("arguments")
            .and_then(Value::as_object)
            .cloned()
            .unwrap_or_default();
        match name {
            "dataset_summary" => tool_result(json!({"datasets": self.store.counts()}), format!(
                "Loaded {} match rows ({} unique matches) and {} players from all 6 required CSV files.",
                self.store.counts().total_matches, self.store.counts().unique_matches, self.store.counts().total_players)),
            "search_matches" => {
                let start = optional_date(&args, "start_date")?; let end = optional_date(&args, "end_date")?;
                if matches!((start, end), (Some(a), Some(b)) if a > b) { return Err("start_date must not be after end_date".into()); }
                let filter = MatchFilter {
                    team: str_arg(&args, "team"), opponent: str_arg(&args, "opponent"), competition: str_arg(&args, "competition"),
                    season: u16_arg(&args, "season")?, start_date: start, end_date: end, stage: str_arg(&args, "stage"), source: str_arg(&args, "source"),
                };
                let rows = self.store.search_matches(&filter, limit_arg(&args, 50)?);
                let text = format_matches(&rows);
                tool_result(json!({"count":rows.len(), "matches":rows}), text)
            }
            "team_statistics" => {
                let team = req_arg(&args, "team")?;
                let stats = self.store.team_statistics(team, u16_arg(&args, "season")?, str_arg(&args, "competition"), str_arg(&args, "venue"));
                let text = format!("{} record: {} matches, {}W-{}D-{}L, {} goals for, {} against, {} points, {:.1}% win rate.", stats.team, stats.matches, stats.wins, stats.draws, stats.losses, stats.goals_for, stats.goals_against, stats.points, stats.win_rate());
                tool_result(json!({"statistics":stats}), text)
            }
            "head_to_head" => {
                let a = req_arg(&args, "team_a")?; let b = req_arg(&args, "team_b")?;
                let (summary, matches) = self.store.head_to_head(a, b, u16_arg(&args, "season")?, str_arg(&args, "competition"));
                let text = format!("{} vs {}: {} matches — {} wins {}, {} wins {}, draws {}.\n{}", a, b, summary.matches, a, summary.team_a_wins, b, summary.team_b_wins, summary.draws, format_matches(&matches));
                tool_result(json!({"summary":summary, "matches":matches}), text)
            }
            "search_players" => {
                let min = u8_arg(&args, "min_overall")?;
                let rows = self.store.search_players(str_arg(&args, "name"), str_arg(&args, "nationality"), str_arg(&args, "club"), str_arg(&args, "position"), min, limit_arg(&args, 50)?);
                let text = if rows.is_empty() { "No matching players were found in the FIFA dataset.".into() } else { rows.iter().map(|p| format!("{} — overall {}, {}, {}", p.name, p.overall.map(|n| n.to_string()).unwrap_or_else(|| "n/a".into()), p.position.as_deref().unwrap_or("position unknown"), p.club.as_deref().unwrap_or("no club"))).collect::<Vec<_>>().join("\n") };
                tool_result(json!({"count":rows.len(), "players":rows}), text)
            }
            "standings" => {
                let season = required_u16(&args, "season")?; let competition = str_arg(&args, "competition").unwrap_or("Brasileirão");
                let rows = self.store.standings(season, competition);
                let text = if rows.is_empty() { format!("No standings data found for {competition} {season}.") } else { rows.iter().map(|s| format!("{}. {} — {} pts ({}W {}D {}L, GD {:+})", s.position, s.team, s.stats.points, s.stats.wins, s.stats.draws, s.stats.losses, s.stats.goal_difference())).collect::<Vec<_>>().join("\n") };
                tool_result(json!({"season":season, "competition":competition, "standings":rows}), text)
            }
            "competition_statistics" => {
                let competition = req_arg(&args, "competition")?;
                let stats = self.store.competition_statistics(competition, u16_arg(&args, "season")?);
                let text = format!("{}: {} matches, {} goals ({:.2} per match); {} home wins, {} away wins, {} draws; home win rate {:.1}%.", stats.competition, stats.matches, stats.goals, stats.goals_per_match, stats.home_wins, stats.away_wins, stats.draws, stats.home_win_rate);
                tool_result(json!({"statistics":stats}), text)
            }
            "biggest_wins" => {
                let rows = self.store.biggest_wins(str_arg(&args, "competition"), u16_arg(&args, "season")?, limit_arg(&args, 10)?);
                let text = format_matches(&rows); tool_result(json!({"matches":rows}), text)
            }
            "team_overview" => {
                let team = req_arg(&args, "team")?; let overview = self.store.team_overview(team, u16_arg(&args, "season")?);
                let text = format!("{}: {} matches across {}; {} FIFA players linked to this club.\nRecent matches:\n{}", team, overview.statistics.matches, overview.competitions.join(", "), overview.players.len(), format_matches(&overview.recent_matches));
                tool_result(json!({"overview":overview}), text)
            }
            _ => Ok(tool_error(format!("unknown tool: {name}"))),
        }
    }
}

fn tool_definitions() -> Vec<Value> {
    vec![
        tool("dataset_summary", "Report loading and coverage counts for all six required CSV datasets.", json!({"type":"object","properties":{},"additionalProperties":false})),
        tool("search_matches", "Find deduplicated matches by team, opponent, date range, competition, season, stage/round, or source file.", json!({"type":"object","properties":{
            "team":{"type":"string"}, "opponent":{"type":"string"}, "competition":{"type":"string"}, "season":{"type":"integer","minimum":1900,"maximum":2100},
            "start_date":{"type":"string","format":"date"}, "end_date":{"type":"string","format":"date"}, "stage":{"type":"string"}, "source":{"type":"string"}, "limit":{"type":"integer","minimum":1,"maximum":1000}
        },"additionalProperties":false})),
        tool("team_statistics", "Calculate wins, draws, losses, goals, points, and win rate for a team, optionally by season, competition, and home/away venue.", json!({"type":"object","required":["team"],"properties":{"team":{"type":"string"},"season":{"type":"integer"},"competition":{"type":"string"},"venue":{"type":"string","enum":["home","away"]}},"additionalProperties":false})),
        tool("head_to_head", "Compare two teams and list their meetings with aggregate wins, draws, and goals.", json!({"type":"object","required":["team_a","team_b"],"properties":{"team_a":{"type":"string"},"team_b":{"type":"string"},"season":{"type":"integer"},"competition":{"type":"string"}},"additionalProperties":false})),
        tool("search_players", "Search FIFA players by name, nationality, club, position, and minimum overall rating.", json!({"type":"object","properties":{"name":{"type":"string"},"nationality":{"type":"string"},"club":{"type":"string"},"position":{"type":"string"},"min_overall":{"type":"integer","minimum":0,"maximum":100},"limit":{"type":"integer","minimum":1,"maximum":1000}},"additionalProperties":false})),
        tool("standings", "Calculate a league table from match results using points, goal difference, and goals scored.", json!({"type":"object","required":["season"],"properties":{"season":{"type":"integer"},"competition":{"type":"string","default":"Brasileirão"}},"additionalProperties":false})),
        tool("competition_statistics", "Calculate match count, goals per match, draws, and home/away win rates for a competition.", json!({"type":"object","required":["competition"],"properties":{"competition":{"type":"string"},"season":{"type":"integer"}},"additionalProperties":false})),
        tool("biggest_wins", "Find the largest victory margins, optionally by competition and season.", json!({"type":"object","properties":{"competition":{"type":"string"},"season":{"type":"integer"},"limit":{"type":"integer","minimum":1,"maximum":100}},"additionalProperties":false})),
        tool("team_overview", "Cross-file team view joining match history, competitions, statistics, and FIFA club players.", json!({"type":"object","required":["team"],"properties":{"team":{"type":"string"},"season":{"type":"integer"}},"additionalProperties":false})),
    ]
}

fn tool(name: &str, description: &str, schema: Value) -> Value {
    json!({"name":name,"description":description,"inputSchema":schema})
}
fn tool_result(structured: Value, text: String) -> Result<Value, String> {
    Ok(
        json!({"content":[{"type":"text","text":text}],"structuredContent":structured,"isError":false}),
    )
}
fn tool_error(message: String) -> Value {
    json!({"content":[{"type":"text","text":message}],"isError":true})
}
fn error_response(id: Value, code: i32, message: String) -> Value {
    json!({"jsonrpc":"2.0","id":id,"error":{"code":code,"message":message}})
}
fn required_str<'a>(value: &'a Value, key: &str) -> Result<&'a str, String> {
    value
        .get(key)
        .and_then(Value::as_str)
        .ok_or_else(|| format!("missing or invalid {key}"))
}
fn req_arg<'a>(args: &'a Map<String, Value>, key: &str) -> Result<&'a str, String> {
    str_arg(args, key)
        .filter(|v| !v.trim().is_empty())
        .ok_or_else(|| format!("{key} is required"))
}
fn str_arg<'a>(args: &'a Map<String, Value>, key: &str) -> Option<&'a str> {
    args.get(key).and_then(Value::as_str)
}
fn required_u16(args: &Map<String, Value>, key: &str) -> Result<u16, String> {
    u16_arg(args, key)?.ok_or_else(|| format!("{key} is required"))
}
fn u16_arg(args: &Map<String, Value>, key: &str) -> Result<Option<u16>, String> {
    match args.get(key) {
        None => Ok(None),
        Some(v) => v
            .as_u64()
            .and_then(|n| u16::try_from(n).ok())
            .map(Some)
            .ok_or_else(|| format!("{key} must be a valid positive integer")),
    }
}
fn u8_arg(args: &Map<String, Value>, key: &str) -> Result<Option<u8>, String> {
    match args.get(key) {
        None => Ok(None),
        Some(v) => v
            .as_u64()
            .and_then(|n| u8::try_from(n).ok())
            .map(Some)
            .ok_or_else(|| format!("{key} must be an integer from 0 to 255")),
    }
}
fn limit_arg(args: &Map<String, Value>, default: usize) -> Result<usize, String> {
    match args.get("limit") {
        None => Ok(default),
        Some(v) => v
            .as_u64()
            .and_then(|n| usize::try_from(n).ok())
            .filter(|n| *n > 0)
            .ok_or_else(|| "limit must be a positive integer".into()),
    }
}
fn optional_date(
    args: &Map<String, Value>,
    key: &str,
) -> Result<Option<chrono::NaiveDate>, String> {
    match str_arg(args, key) {
        None => Ok(None),
        Some(value) => parse_date(value)
            .map(Some)
            .ok_or_else(|| format!("{key} must be a date in YYYY-MM-DD format")),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;

    fn server() -> McpServer {
        let path = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("data/kaggle");
        McpServer::new(SoccerStore::load(path).unwrap())
    }

    #[test]
    fn initializes_and_advertises_tools() {
        let server = server();
        let response = server.handle(json!({"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18"}})).unwrap();
        assert_eq!(
            response.pointer("/result/protocolVersion").unwrap(),
            "2025-06-18"
        );
        let response = server
            .handle(json!({"jsonrpc":"2.0","id":2,"method":"tools/list"}))
            .unwrap();
        assert!(
            response
                .pointer("/result/tools")
                .unwrap()
                .as_array()
                .unwrap()
                .len()
                >= 9
        );
    }

    #[test]
    fn calls_tools_with_structured_and_text_results() {
        let server = server();
        let response = server.handle(json!({"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"head_to_head","arguments":{"team_a":"Flamengo","team_b":"Fluminense"}}})).unwrap();
        assert_eq!(response.pointer("/result/isError").unwrap(), false);
        assert!(
            response
                .pointer("/result/structuredContent/summary/matches")
                .unwrap()
                .as_u64()
                .unwrap()
                > 0
        );
        assert!(response
            .pointer("/result/content/0/text")
            .unwrap()
            .as_str()
            .unwrap()
            .contains("Flamengo"));
    }
}
