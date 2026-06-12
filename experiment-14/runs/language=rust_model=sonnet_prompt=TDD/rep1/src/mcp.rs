use anyhow::Result;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};

use crate::data::Database;
use crate::models::Competition;
use crate::query::{
    biggest_wins, goals_per_match, head_to_head, home_win_rate, search_matches, search_players,
    standings, team_stats, MatchFilter,
};

// --- JSON-RPC types ---

#[derive(Debug, Deserialize)]
pub struct JsonRpcRequest {
    pub jsonrpc: String,
    pub id: Option<Value>,
    pub method: String,
    pub params: Option<Value>,
}

#[derive(Debug, Serialize)]
pub struct JsonRpcResponse {
    pub jsonrpc: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub id: Option<Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub result: Option<Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<JsonRpcError>,
}

#[derive(Debug, Serialize)]
pub struct JsonRpcError {
    pub code: i32,
    pub message: String,
}

impl JsonRpcResponse {
    pub fn success(id: Option<Value>, result: Value) -> Self {
        JsonRpcResponse {
            jsonrpc: "2.0".to_string(),
            id,
            result: Some(result),
            error: None,
        }
    }

    pub fn error(id: Option<Value>, code: i32, message: String) -> Self {
        JsonRpcResponse {
            jsonrpc: "2.0".to_string(),
            id,
            result: None,
            error: Some(JsonRpcError { code, message }),
        }
    }
}

// --- MCP tool definitions ---

pub fn tool_definitions() -> Value {
    json!([
        {
            "name": "search_matches",
            "description": "Search for matches by team, season, competition, or date range. Returns match results with scores.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team": {
                        "type": "string",
                        "description": "Team name to search for (home or away)"
                    },
                    "home_team": {
                        "type": "string",
                        "description": "Specific home team name"
                    },
                    "away_team": {
                        "type": "string",
                        "description": "Specific away team name"
                    },
                    "season": {
                        "type": "integer",
                        "description": "Season year (e.g. 2023)"
                    },
                    "competition": {
                        "type": "string",
                        "enum": ["brasileirao", "copa_do_brasil", "libertadores", "extended", "historical"],
                        "description": "Competition name"
                    },
                    "date_from": {
                        "type": "string",
                        "description": "Start date filter (YYYY-MM-DD)"
                    },
                    "date_to": {
                        "type": "string",
                        "description": "End date filter (YYYY-MM-DD)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default 20)"
                    }
                }
            }
        },
        {
            "name": "head_to_head",
            "description": "Get head-to-head record between two teams.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_a": {
                        "type": "string",
                        "description": "First team name"
                    },
                    "team_b": {
                        "type": "string",
                        "description": "Second team name"
                    },
                    "season": {
                        "type": "integer",
                        "description": "Optional: filter by season"
                    },
                    "competition": {
                        "type": "string",
                        "description": "Optional: filter by competition"
                    }
                },
                "required": ["team_a", "team_b"]
            }
        },
        {
            "name": "team_stats",
            "description": "Get win/loss/draw statistics for a team.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team": {
                        "type": "string",
                        "description": "Team name"
                    },
                    "season": {
                        "type": "integer",
                        "description": "Optional: filter by season"
                    },
                    "competition": {
                        "type": "string",
                        "description": "Optional: filter by competition"
                    }
                },
                "required": ["team"]
            }
        },
        {
            "name": "competition_standings",
            "description": "Get standings table for a competition and season.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "season": {
                        "type": "integer",
                        "description": "Season year"
                    },
                    "competition": {
                        "type": "string",
                        "enum": ["brasileirao", "copa_do_brasil", "libertadores", "historical"],
                        "description": "Competition"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of teams to show (default 20)"
                    }
                },
                "required": ["season"]
            }
        },
        {
            "name": "search_players",
            "description": "Search for players by name, nationality, or club.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Player name search (partial match)"
                    },
                    "nationality": {
                        "type": "string",
                        "description": "Player nationality (e.g. 'Brazil')"
                    },
                    "club": {
                        "type": "string",
                        "description": "Club name search"
                    },
                    "min_overall": {
                        "type": "integer",
                        "description": "Minimum FIFA overall rating"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum results to return (default 20)"
                    }
                }
            }
        },
        {
            "name": "statistics",
            "description": "Get aggregate statistics like average goals, home win rate, or biggest wins.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "stat_type": {
                        "type": "string",
                        "enum": ["goals_per_match", "home_win_rate", "biggest_wins"],
                        "description": "Type of statistic"
                    },
                    "season": {
                        "type": "integer",
                        "description": "Optional: filter by season"
                    },
                    "competition": {
                        "type": "string",
                        "description": "Optional: filter by competition"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "For biggest_wins: how many to return (default 10)"
                    }
                },
                "required": ["stat_type"]
            }
        }
    ])
}

fn parse_competition(s: &str) -> Option<Competition> {
    match s.to_lowercase().as_str() {
        "brasileirao" | "brasileirão" | "serie a" => Some(Competition::Brasileirao),
        "copa_do_brasil" | "copa do brasil" => Some(Competition::CopaDoBrasil),
        "libertadores" | "copa libertadores" => Some(Competition::Libertadores),
        "extended" => Some(Competition::Extended),
        "historical" => Some(Competition::Historical),
        _ => None,
    }
}

pub fn handle_tool_call(db: &Database, tool_name: &str, args: &Value) -> Result<Value> {
    match tool_name {
        "search_matches" => handle_search_matches(db, args),
        "head_to_head" => handle_head_to_head(db, args),
        "team_stats" => handle_team_stats(db, args),
        "competition_standings" => handle_standings(db, args),
        "search_players" => handle_search_players(db, args),
        "statistics" => handle_statistics(db, args),
        _ => Ok(json!({"error": format!("Unknown tool: {}", tool_name)})),
    }
}

fn handle_search_matches(db: &Database, args: &Value) -> Result<Value> {
    let team = args["team"].as_str();
    let home_team = args["home_team"].as_str();
    let away_team = args["away_team"].as_str();
    let season = args["season"].as_u64().map(|s| s as u32);
    let competition = args["competition"]
        .as_str()
        .and_then(parse_competition);
    let date_from = args["date_from"].as_str();
    let date_to = args["date_to"].as_str();
    let limit = args["limit"].as_u64().unwrap_or(20) as usize;

    let filter = MatchFilter {
        team,
        home_team,
        away_team,
        season,
        competition,
        date_from,
        date_to,
    };

    let results = search_matches(&db.matches, &filter);
    let total = results.len();
    let results: Vec<Value> = results
        .into_iter()
        .take(limit)
        .map(|m| {
            json!({
                "competition": m.competition.display_name(),
                "datetime": m.datetime,
                "home_team": m.home_team,
                "away_team": m.away_team,
                "home_goal": m.home_goal,
                "away_goal": m.away_goal,
                "season": m.season,
                "round": m.round,
                "stage": m.stage,
                "result": m.result_str(),
            })
        })
        .collect();

    Ok(json!({
        "total_found": total,
        "showing": results.len(),
        "matches": results
    }))
}

fn handle_head_to_head(db: &Database, args: &Value) -> Result<Value> {
    let team_a = args["team_a"].as_str().unwrap_or("");
    let team_b = args["team_b"].as_str().unwrap_or("");

    if team_a.is_empty() || team_b.is_empty() {
        return Ok(json!({"error": "team_a and team_b are required"}));
    }

    let mut matches: Vec<_> = head_to_head(&db.matches, team_a, team_b);

    // Optional season/competition filter
    if let Some(season) = args["season"].as_u64() {
        matches.retain(|m| m.season == season as u32);
    }
    if let Some(comp_str) = args["competition"].as_str() {
        if let Some(comp) = parse_competition(comp_str) {
            matches.retain(|m| m.competition == comp);
        }
    }

    let mut team_a_wins = 0u32;
    let mut team_b_wins = 0u32;
    let mut draws = 0u32;

    let match_list: Vec<Value> = matches
        .iter()
        .map(|m| {
            let winner = m.winner();
            let norm_a = crate::models::normalize_team_name(team_a);
            let norm_home = crate::models::normalize_team_name(&m.home_team);
            let is_a_home = norm_home.contains(&norm_a);

            if let Some(w) = winner {
                let norm_w = crate::models::normalize_team_name(w);
                if norm_w.contains(&norm_a) {
                    team_a_wins += 1;
                } else {
                    team_b_wins += 1;
                }
            } else {
                draws += 1;
            }

            let _ = is_a_home;
            json!({
                "datetime": m.datetime,
                "home_team": m.home_team,
                "away_team": m.away_team,
                "home_goal": m.home_goal,
                "away_goal": m.away_goal,
                "season": m.season,
                "competition": m.competition.display_name(),
                "result": m.result_str(),
            })
        })
        .collect();

    Ok(json!({
        "team_a": team_a,
        "team_b": team_b,
        "total_matches": match_list.len(),
        "team_a_wins": team_a_wins,
        "team_b_wins": team_b_wins,
        "draws": draws,
        "matches": match_list
    }))
}

fn handle_team_stats(db: &Database, args: &Value) -> Result<Value> {
    let team = args["team"].as_str().unwrap_or("");
    if team.is_empty() {
        return Ok(json!({"error": "team is required"}));
    }

    let mut matches: Vec<_> = db.matches.iter().collect();
    if let Some(season) = args["season"].as_u64() {
        matches.retain(|m| m.season == season as u32);
    }
    if let Some(comp_str) = args["competition"].as_str() {
        if let Some(comp) = parse_competition(comp_str) {
            matches.retain(|m| m.competition == comp);
        }
    }

    let filtered: Vec<_> = matches.into_iter().cloned().collect();
    let stats = team_stats(&filtered, team);

    Ok(json!({
        "team": stats.team,
        "matches": stats.matches,
        "wins": stats.wins,
        "draws": stats.draws,
        "losses": stats.losses,
        "goals_for": stats.goals_for,
        "goals_against": stats.goals_against,
        "goal_difference": stats.goal_difference(),
        "points": stats.points(),
        "win_rate_pct": format!("{:.1}", stats.win_rate()),
    }))
}

fn handle_standings(db: &Database, args: &Value) -> Result<Value> {
    let season = args["season"].as_u64().map(|s| s as u32);
    let competition = args["competition"].as_str().and_then(parse_competition);
    let limit = args["limit"].as_u64().unwrap_or(20) as usize;

    let filtered: Vec<_> = db
        .matches
        .iter()
        .filter(|m| {
            if let Some(s) = season {
                if m.season != s {
                    return false;
                }
            }
            if let Some(ref c) = competition {
                if &m.competition != c {
                    return false;
                }
            }
            true
        })
        .cloned()
        .collect();

    let table = standings(&filtered);
    let total = table.len();
    let table: Vec<Value> = table
        .into_iter()
        .take(limit)
        .enumerate()
        .map(|(i, s)| {
            json!({
                "position": i + 1,
                "team": s.team,
                "matches": s.matches,
                "wins": s.wins,
                "draws": s.draws,
                "losses": s.losses,
                "goals_for": s.goals_for,
                "goals_against": s.goals_against,
                "goal_difference": s.goal_difference(),
                "points": s.points(),
            })
        })
        .collect();

    Ok(json!({
        "season": season,
        "total_teams": total,
        "standings": table
    }))
}

fn handle_search_players(db: &Database, args: &Value) -> Result<Value> {
    let name = args["name"].as_str();
    let nationality = args["nationality"].as_str();
    let club = args["club"].as_str();
    let min_overall = args["min_overall"].as_u64().map(|v| v as u32);
    let limit = args["limit"].as_u64().unwrap_or(20) as usize;

    let mut results = search_players(&db.players, name, nationality, club, min_overall);
    results.sort_by(|a, b| b.overall.cmp(&a.overall));
    let total = results.len();
    let results: Vec<Value> = results
        .into_iter()
        .take(limit)
        .map(|p| {
            json!({
                "id": p.id,
                "name": p.name,
                "age": p.age,
                "nationality": p.nationality,
                "overall": p.overall,
                "potential": p.potential,
                "club": p.club,
                "position": p.position,
                "jersey_number": p.jersey_number,
            })
        })
        .collect();

    Ok(json!({
        "total_found": total,
        "showing": results.len(),
        "players": results
    }))
}

fn handle_statistics(db: &Database, args: &Value) -> Result<Value> {
    let stat_type = args["stat_type"].as_str().unwrap_or("");

    let filtered: Vec<_> = db
        .matches
        .iter()
        .filter(|m| {
            if let Some(s) = args["season"].as_u64() {
                if m.season != s as u32 {
                    return false;
                }
            }
            if let Some(comp_str) = args["competition"].as_str() {
                if let Some(comp) = parse_competition(comp_str) {
                    if m.competition != comp {
                        return false;
                    }
                }
            }
            true
        })
        .cloned()
        .collect();

    match stat_type {
        "goals_per_match" => {
            let avg = goals_per_match(&filtered);
            Ok(json!({
                "stat": "goals_per_match",
                "value": format!("{:.2}", avg),
                "total_matches": filtered.len(),
                "total_goals": filtered.iter().map(|m| m.home_goal + m.away_goal).sum::<u32>()
            }))
        }
        "home_win_rate" => {
            let rate = home_win_rate(&filtered);
            let home_wins = filtered.iter().filter(|m| m.home_goal > m.away_goal).count();
            let away_wins = filtered.iter().filter(|m| m.away_goal > m.home_goal).count();
            let draws = filtered.iter().filter(|m| m.home_goal == m.away_goal).count();
            Ok(json!({
                "stat": "home_win_rate",
                "home_win_rate_pct": format!("{:.1}", rate),
                "home_wins": home_wins,
                "away_wins": away_wins,
                "draws": draws,
                "total_matches": filtered.len(),
            }))
        }
        "biggest_wins" => {
            let limit = args["limit"].as_u64().unwrap_or(10) as usize;
            let wins = biggest_wins(&filtered, limit);
            let results: Vec<Value> = wins
                .iter()
                .map(|m| {
                    let margin = (m.home_goal as i32 - m.away_goal as i32).abs();
                    json!({
                        "datetime": m.datetime,
                        "result": m.result_str(),
                        "competition": m.competition.display_name(),
                        "season": m.season,
                        "goal_margin": margin,
                    })
                })
                .collect();
            Ok(json!({ "biggest_wins": results }))
        }
        _ => Ok(json!({"error": format!("Unknown stat_type: {}", stat_type)})),
    }
}

/// Process a single MCP JSON-RPC message.
pub fn process_message(db: &Database, input: &str) -> Option<String> {
    let req: JsonRpcRequest = match serde_json::from_str(input) {
        Ok(r) => r,
        Err(e) => {
            let resp = JsonRpcResponse::error(None, -32700, format!("Parse error: {}", e));
            return Some(serde_json::to_string(&resp).unwrap());
        }
    };

    let id = req.id.clone();
    let resp = match req.method.as_str() {
        "initialize" => {
            let result = json!({
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "brazilian-soccer-mcp",
                    "version": "0.1.0"
                }
            });
            JsonRpcResponse::success(id, result)
        }
        "initialized" => {
            // notification — no response
            return None;
        }
        "ping" => JsonRpcResponse::success(id, json!({})),
        "tools/list" => {
            let result = json!({ "tools": tool_definitions() });
            JsonRpcResponse::success(id, result)
        }
        "tools/call" => {
            let params = req.params.as_ref().and_then(|p| p.as_object());
            let tool_name = params
                .and_then(|p| p.get("name"))
                .and_then(|v| v.as_str())
                .unwrap_or("");
            let tool_args = params
                .and_then(|p| p.get("arguments"))
                .cloned()
                .unwrap_or(json!({}));

            match handle_tool_call(db, tool_name, &tool_args) {
                Ok(result) => {
                    let content = json!([{
                        "type": "text",
                        "text": serde_json::to_string_pretty(&result).unwrap_or_default()
                    }]);
                    JsonRpcResponse::success(id, json!({ "content": content }))
                }
                Err(e) => JsonRpcResponse::error(id, -32603, e.to_string()),
            }
        }
        "resources/list" => {
            JsonRpcResponse::success(id, json!({ "resources": [] }))
        }
        "prompts/list" => {
            JsonRpcResponse::success(id, json!({ "prompts": [] }))
        }
        _ => JsonRpcResponse::error(id, -32601, format!("Method not found: {}", req.method)),
    };

    Some(serde_json::to_string(&resp).unwrap())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::data::Database;
    use crate::models::{Competition, Match, Player};

    fn make_db() -> Database {
        let matches = vec![
            Match {
                competition: Competition::Brasileirao,
                datetime: "2023-05-01".to_string(),
                home_team: "Flamengo".to_string(),
                away_team: "Santos".to_string(),
                home_goal: 3,
                away_goal: 1,
                season: 2023,
                round: Some("5".to_string()),
                stage: None,
                arena: None,
            },
            Match {
                competition: Competition::Brasileirao,
                datetime: "2023-06-15".to_string(),
                home_team: "Palmeiras".to_string(),
                away_team: "Flamengo".to_string(),
                home_goal: 0,
                away_goal: 2,
                season: 2023,
                round: Some("10".to_string()),
                stage: None,
                arena: None,
            },
            Match {
                competition: Competition::CopaDoBrasil,
                datetime: "2022-09-01".to_string(),
                home_team: "Santos".to_string(),
                away_team: "Corinthians".to_string(),
                home_goal: 1,
                away_goal: 1,
                season: 2022,
                round: Some("Final".to_string()),
                stage: None,
                arena: None,
            },
        ];
        let players = vec![
            Player {
                id: 1,
                name: "Gabriel Barbosa".to_string(),
                age: 26,
                nationality: "Brazil".to_string(),
                overall: 83,
                potential: 85,
                club: "Flamengo".to_string(),
                position: "ST".to_string(),
                jersey_number: Some(9),
                height: "5'11".to_string(),
                weight: "176lbs".to_string(),
            },
            Player {
                id: 2,
                name: "Cristiano Ronaldo".to_string(),
                age: 34,
                nationality: "Portugal".to_string(),
                overall: 94,
                potential: 94,
                club: "Juventus".to_string(),
                position: "ST".to_string(),
                jersey_number: Some(7),
                height: "6'2".to_string(),
                weight: "183lbs".to_string(),
            },
        ];
        Database { matches, players }
    }

    #[test]
    fn process_initialize_returns_server_info() {
        let db = make_db();
        let input = r#"{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{}}}"#;
        let output = process_message(&db, input).unwrap();
        let resp: Value = serde_json::from_str(&output).unwrap();
        assert_eq!(resp["jsonrpc"], "2.0");
        assert_eq!(resp["id"], 1);
        assert!(resp["result"]["serverInfo"]["name"].is_string());
    }

    #[test]
    fn process_initialized_notification_no_response() {
        let db = make_db();
        let input = r#"{"jsonrpc":"2.0","method":"initialized","params":{}}"#;
        let output = process_message(&db, input);
        assert!(output.is_none());
    }

    #[test]
    fn process_tools_list_returns_tools() {
        let db = make_db();
        let input = r#"{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}"#;
        let output = process_message(&db, input).unwrap();
        let resp: Value = serde_json::from_str(&output).unwrap();
        let tools = &resp["result"]["tools"];
        assert!(tools.is_array());
        assert!(tools.as_array().unwrap().len() >= 6);
    }

    #[test]
    fn process_tool_call_search_matches_by_team() {
        let db = make_db();
        let input = r#"{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"search_matches","arguments":{"team":"Flamengo"}}}"#;
        let output = process_message(&db, input).unwrap();
        let resp: Value = serde_json::from_str(&output).unwrap();
        let text = resp["result"]["content"][0]["text"].as_str().unwrap();
        let data: Value = serde_json::from_str(text).unwrap();
        assert_eq!(data["total_found"], 2);
    }

    #[test]
    fn process_tool_call_head_to_head() {
        let db = make_db();
        let input = r#"{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"head_to_head","arguments":{"team_a":"Flamengo","team_b":"Santos"}}}"#;
        let output = process_message(&db, input).unwrap();
        let resp: Value = serde_json::from_str(&output).unwrap();
        let text = resp["result"]["content"][0]["text"].as_str().unwrap();
        let data: Value = serde_json::from_str(text).unwrap();
        assert_eq!(data["total_matches"], 1);
    }

    #[test]
    fn process_tool_call_team_stats() {
        let db = make_db();
        let input = r#"{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"team_stats","arguments":{"team":"Flamengo"}}}"#;
        let output = process_message(&db, input).unwrap();
        let resp: Value = serde_json::from_str(&output).unwrap();
        let text = resp["result"]["content"][0]["text"].as_str().unwrap();
        let data: Value = serde_json::from_str(text).unwrap();
        assert_eq!(data["matches"], 2);
        assert_eq!(data["wins"], 2);
    }

    #[test]
    fn process_tool_call_standings() {
        let db = make_db();
        let input = r#"{"jsonrpc":"2.0","id":6,"method":"tools/call","params":{"name":"competition_standings","arguments":{"season":2023,"competition":"brasileirao"}}}"#;
        let output = process_message(&db, input).unwrap();
        let resp: Value = serde_json::from_str(&output).unwrap();
        let text = resp["result"]["content"][0]["text"].as_str().unwrap();
        let data: Value = serde_json::from_str(text).unwrap();
        assert!(data["standings"].as_array().unwrap().len() > 0);
        // Flamengo has 2 wins = 6 pts, should be top
        assert_eq!(data["standings"][0]["team"], "Flamengo");
    }

    #[test]
    fn process_tool_call_search_players() {
        let db = make_db();
        let input = r#"{"jsonrpc":"2.0","id":7,"method":"tools/call","params":{"name":"search_players","arguments":{"nationality":"Brazil"}}}"#;
        let output = process_message(&db, input).unwrap();
        let resp: Value = serde_json::from_str(&output).unwrap();
        let text = resp["result"]["content"][0]["text"].as_str().unwrap();
        let data: Value = serde_json::from_str(text).unwrap();
        assert_eq!(data["total_found"], 1);
        assert_eq!(data["players"][0]["name"], "Gabriel Barbosa");
    }

    #[test]
    fn process_tool_call_statistics_goals() {
        let db = make_db();
        let input = r#"{"jsonrpc":"2.0","id":8,"method":"tools/call","params":{"name":"statistics","arguments":{"stat_type":"goals_per_match"}}}"#;
        let output = process_message(&db, input).unwrap();
        let resp: Value = serde_json::from_str(&output).unwrap();
        let text = resp["result"]["content"][0]["text"].as_str().unwrap();
        let data: Value = serde_json::from_str(text).unwrap();
        assert_eq!(data["total_matches"], 3);
    }

    #[test]
    fn process_invalid_json_returns_parse_error() {
        let db = make_db();
        let input = "not valid json";
        let output = process_message(&db, input).unwrap();
        let resp: Value = serde_json::from_str(&output).unwrap();
        assert!(resp["error"].is_object());
        assert_eq!(resp["error"]["code"], -32700);
    }

    #[test]
    fn process_unknown_method_returns_error() {
        let db = make_db();
        let input = r#"{"jsonrpc":"2.0","id":9,"method":"unknown/method","params":{}}"#;
        let output = process_message(&db, input).unwrap();
        let resp: Value = serde_json::from_str(&output).unwrap();
        assert!(resp["error"].is_object());
        assert_eq!(resp["error"]["code"], -32601);
    }

    #[test]
    fn process_statistics_home_win_rate() {
        let db = make_db();
        let input = r#"{"jsonrpc":"2.0","id":10,"method":"tools/call","params":{"name":"statistics","arguments":{"stat_type":"home_win_rate"}}}"#;
        let output = process_message(&db, input).unwrap();
        let resp: Value = serde_json::from_str(&output).unwrap();
        let text = resp["result"]["content"][0]["text"].as_str().unwrap();
        let data: Value = serde_json::from_str(text).unwrap();
        // 1 home win (Flamengo 3-1), 1 away win (Flamengo at Palmeiras 0-2), 1 draw
        assert_eq!(data["home_wins"], 1);
        assert_eq!(data["away_wins"], 1);
        assert_eq!(data["draws"], 1);
    }

    #[test]
    fn process_statistics_biggest_wins() {
        let db = make_db();
        let input = r#"{"jsonrpc":"2.0","id":11,"method":"tools/call","params":{"name":"statistics","arguments":{"stat_type":"biggest_wins","limit":3}}}"#;
        let output = process_message(&db, input).unwrap();
        let resp: Value = serde_json::from_str(&output).unwrap();
        let text = resp["result"]["content"][0]["text"].as_str().unwrap();
        let data: Value = serde_json::from_str(text).unwrap();
        // Biggest win: Flamengo 3-1 Santos (margin 2)
        assert_eq!(data["biggest_wins"][0]["goal_margin"], 2);
    }
}
