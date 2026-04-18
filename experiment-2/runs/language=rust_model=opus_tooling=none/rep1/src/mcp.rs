use crate::data::{Competition, Dataset};
use crate::queries::Query;
use serde_json::{json, Value};

fn comp_from_str(s: &str) -> Option<Competition> {
    match s.to_lowercase().as_str() {
        "brasileirao" | "brasileirão" | "serie_a" => Some(Competition::Brasileirao),
        "copa_do_brasil" | "cup" => Some(Competition::CopaDoBrasil),
        "libertadores" => Some(Competition::Libertadores),
        "extended" => Some(Competition::ExtendedStats),
        "historical" => Some(Competition::HistoricalBrasileirao),
        _ => None,
    }
}

pub fn tools_list() -> Value {
    json!({
        "tools": [
            {"name": "matches_between", "description": "Find matches between two teams",
             "inputSchema": {"type": "object", "properties": {
                "team_a": {"type": "string"}, "team_b": {"type": "string"}},
                "required": ["team_a", "team_b"]}},
            {"name": "team_stats", "description": "Compute W/D/L/goals for a team",
             "inputSchema": {"type": "object", "properties": {
                "team": {"type": "string"}, "season": {"type": "integer"},
                "home_only": {"type": "boolean"}, "away_only": {"type": "boolean"}},
                "required": ["team"]}},
            {"name": "head_to_head", "description": "Head-to-head record",
             "inputSchema": {"type": "object", "properties": {
                "team_a": {"type": "string"}, "team_b": {"type": "string"}},
                "required": ["team_a", "team_b"]}},
            {"name": "standings", "description": "Calculated standings for a competition/season",
             "inputSchema": {"type": "object", "properties": {
                "competition": {"type": "string"}, "season": {"type": "integer"}},
                "required": ["competition", "season"]}},
            {"name": "search_players", "description": "Search FIFA players by name",
             "inputSchema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}},
            {"name": "players_by_nationality", "description": "Top players by nationality",
             "inputSchema": {"type": "object", "properties": {
                "nationality": {"type": "string"}, "limit": {"type": "integer"}},
                "required": ["nationality"]}},
            {"name": "players_by_club", "description": "Players at a club",
             "inputSchema": {"type": "object", "properties": {"club": {"type": "string"}}, "required": ["club"]}},
            {"name": "biggest_wins", "description": "Biggest wins across dataset",
             "inputSchema": {"type": "object", "properties": {"limit": {"type": "integer"}}}},
            {"name": "avg_goals_per_match", "description": "Average goals per match",
             "inputSchema": {"type": "object", "properties": {"competition": {"type": "string"}}}},
            {"name": "home_win_rate", "description": "Home win rate",
             "inputSchema": {"type": "object", "properties": {"competition": {"type": "string"}}}}
        ]
    })
}

pub fn call_tool(ds: &Dataset, name: &str, args: &Value) -> Value {
    let q = Query::new(ds);
    match name {
        "matches_between" => {
            let a = args.get("team_a").and_then(|v| v.as_str()).unwrap_or("");
            let b = args.get("team_b").and_then(|v| v.as_str()).unwrap_or("");
            let ms: Vec<_> = q.matches_between(a, b).into_iter().cloned().collect();
            json!({"count": ms.len(), "matches": ms})
        }
        "team_stats" => {
            let team = args.get("team").and_then(|v| v.as_str()).unwrap_or("");
            let season = args.get("season").and_then(|v| v.as_i64()).map(|v| v as i32);
            let home = args.get("home_only").and_then(|v| v.as_bool()).unwrap_or(false);
            let away = args.get("away_only").and_then(|v| v.as_bool()).unwrap_or(false);
            json!(q.team_stats(team, season, home, away))
        }
        "head_to_head" => {
            let a = args.get("team_a").and_then(|v| v.as_str()).unwrap_or("");
            let b = args.get("team_b").and_then(|v| v.as_str()).unwrap_or("");
            json!(q.head_to_head(a, b))
        }
        "standings" => {
            let comp = args
                .get("competition")
                .and_then(|v| v.as_str())
                .and_then(comp_from_str)
                .unwrap_or(Competition::Brasileirao);
            let season = args.get("season").and_then(|v| v.as_i64()).unwrap_or(0) as i32;
            json!(q.standings(comp, season))
        }
        "search_players" => {
            let n = args.get("name").and_then(|v| v.as_str()).unwrap_or("");
            let v: Vec<_> = q.search_players(n).into_iter().cloned().collect();
            json!(v)
        }
        "players_by_nationality" => {
            let n = args.get("nationality").and_then(|v| v.as_str()).unwrap_or("");
            let lim = args.get("limit").and_then(|v| v.as_u64()).unwrap_or(25) as usize;
            let v: Vec<_> = q.players_by_nationality(n, lim).into_iter().cloned().collect();
            json!(v)
        }
        "players_by_club" => {
            let c = args.get("club").and_then(|v| v.as_str()).unwrap_or("");
            let v: Vec<_> = q.players_by_club(c).into_iter().cloned().collect();
            json!(v)
        }
        "biggest_wins" => {
            let lim = args.get("limit").and_then(|v| v.as_u64()).unwrap_or(10) as usize;
            let v: Vec<_> = q.biggest_wins(lim).into_iter().cloned().collect();
            json!(v)
        }
        "avg_goals_per_match" => {
            let c = args.get("competition").and_then(|v| v.as_str()).and_then(comp_from_str);
            json!({"avg": q.average_goals_per_match(c)})
        }
        "home_win_rate" => {
            let c = args.get("competition").and_then(|v| v.as_str()).and_then(comp_from_str);
            json!({"rate": q.home_win_rate(c)})
        }
        _ => json!({"error": format!("unknown tool: {}", name)}),
    }
}

pub fn handle_request(ds: &Dataset, req: &Value) -> Value {
    let id = req.get("id").cloned().unwrap_or(Value::Null);
    let method = req.get("method").and_then(|v| v.as_str()).unwrap_or("");
    let result = match method {
        "initialize" => json!({
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "brazilian-soccer-mcp", "version": "0.1.0"}
        }),
        "tools/list" => tools_list(),
        "tools/call" => {
            let params = req.get("params").cloned().unwrap_or(Value::Null);
            let name = params.get("name").and_then(|v| v.as_str()).unwrap_or("");
            let args = params.get("arguments").cloned().unwrap_or(json!({}));
            let output = call_tool(ds, name, &args);
            json!({"content": [{"type": "text", "text": output.to_string()}]})
        }
        _ => json!({"error": "method not found"}),
    };
    json!({"jsonrpc": "2.0", "id": id, "result": result})
}
