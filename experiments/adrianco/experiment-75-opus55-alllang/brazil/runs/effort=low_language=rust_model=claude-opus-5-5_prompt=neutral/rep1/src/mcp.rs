//! Minimal MCP (Model Context Protocol) server over JSON-RPC 2.0 / stdio.

use crate::data::Competition;
use crate::query::{Engine, MatchFilter};
use serde_json::{json, Value};

fn s(a: &Value, k: &str) -> Option<String> {
    match a.get(k)? {
        Value::String(v) if !v.trim().is_empty() => Some(v.clone()),
        Value::Number(n) => Some(n.to_string()),
        _ => None,
    }
}
fn n(a: &Value, k: &str) -> Option<i64> {
    a.get(k).and_then(|v| v.as_i64().or_else(|| v.as_str().and_then(|s| s.parse().ok())))
}

fn comp(a: &Value) -> Result<Option<Competition>, String> {
    match s(a, "competition") {
        None => Ok(None),
        Some(c) => Competition::parse(&c).map(Some).ok_or_else(|| format!("Unknown competition: {c}")),
    }
}

fn filter(a: &Value) -> Result<MatchFilter, String> {
    Ok(MatchFilter {
        team: s(a, "team"),
        opponent: s(a, "opponent"),
        venue: s(a, "venue"),
        competition: comp(a)?,
        season: n(a, "season").map(|v| v as i32),
        date_from: s(a, "date_from"),
        date_to: s(a, "date_to"),
        round: s(a, "round"),
    })
}

pub fn tool_definitions() -> Value {
    let str_ = |d: &str| json!({"type": "string", "description": d});
    let int_ = |d: &str| json!({"type": "integer", "description": d});
    let match_props = json!({
        "team": str_("Team name (any variant, e.g. 'Palmeiras', 'Palmeiras-SP')"),
        "opponent": str_("Opponent team name"),
        "venue": str_("'home', 'away' or omitted for either"),
        "competition": str_("Brasileirão / Serie A, Serie B, Serie C, Copa do Brasil, Libertadores"),
        "season": int_("Season year"),
        "date_from": str_("Start date YYYY-MM-DD"),
        "date_to": str_("End date YYYY-MM-DD"),
        "round": str_("Round/stage filter, e.g. 'final'"),
        "limit": int_("Max rows (default 20)")
    });
    json!([
        {"name": "search_matches", "description": "Find matches by team, opponent, venue, competition, season, date range or round.",
         "inputSchema": {"type": "object", "properties": match_props}},
        {"name": "head_to_head", "description": "Head-to-head record and match list between two teams.",
         "inputSchema": {"type": "object", "properties": {"team_a": str_("First team"), "team_b": str_("Second team"), "competition": str_("Optional competition"), "limit": int_("Max matches listed")}, "required": ["team_a", "team_b"]}},
        {"name": "team_stats", "description": "Win/draw/loss and goals record of a team, optionally by season, competition and venue.",
         "inputSchema": {"type": "object", "properties": match_props, "required": ["team"]}},
        {"name": "standings", "description": "League table for a season calculated from match results (champion, relegation).",
         "inputSchema": {"type": "object", "properties": {"season": int_("Season year"), "competition": str_("Default Brasileirão"), "limit": int_("Rows (default all)")}, "required": ["season"]}},
        {"name": "rank_teams", "description": "Rank teams by metric: win_rate, goals, defense, home, away.",
         "inputSchema": {"type": "object", "properties": {"metric": str_("win_rate | goals | defense | home | away"), "competition": str_("Competition"), "season": int_("Season"), "venue": str_("home/away"), "min_matches": int_("Minimum matches (default 10)"), "limit": int_("Rows (default 10)")}}},
        {"name": "biggest_wins", "description": "Largest victory margins, optionally filtered.",
         "inputSchema": {"type": "object", "properties": match_props}},
        {"name": "league_stats", "description": "Aggregate stats: goals per match, home/away win rates, per-season trend.",
         "inputSchema": {"type": "object", "properties": match_props}},
        {"name": "team_competitions", "description": "Which competitions a team has played in across all files.",
         "inputSchema": {"type": "object", "properties": {"team": str_("Team")}, "required": ["team"]}},
        {"name": "derbies", "description": "Traditional rivalry matches (Fla-Flu, Grenal, Derby Paulista, ...).",
         "inputSchema": {"type": "object", "properties": {"season": int_("Season"), "limit": int_("Max per derby (default 5)")}}},
        {"name": "search_players", "description": "Search FIFA player data by name, nationality, club, position (or forward/midfielder/defender/goalkeeper), min overall.",
         "inputSchema": {"type": "object", "properties": {"name": str_("Name substring"), "nationality": str_("e.g. Brazil"), "club": str_("Club"), "position": str_("Position code or group"), "min_overall": int_("Minimum overall"), "limit": int_("Max rows (default 20)")}}},
        {"name": "brazilian_club_players", "description": "Players at Brazilian clubs grouped by club, joined with each club's match record.",
         "inputSchema": {"type": "object", "properties": {"nationality": str_("Optional nationality filter")}}},
        {"name": "dataset_info", "description": "Summary of loaded datasets.", "inputSchema": {"type": "object", "properties": {}}}
    ])
}

pub fn call_tool(e: &Engine, name: &str, a: &Value) -> Result<String, String> {
    let limit = |d: i64| n(a, "limit").unwrap_or(d).max(1) as usize;
    match name {
        "search_matches" => e.search_matches_text(&filter(a)?, limit(20)),
        "head_to_head" => {
            let ta = s(a, "team_a").ok_or("team_a required")?;
            let tb = s(a, "team_b").ok_or("team_b required")?;
            e.head_to_head_text(&ta, &tb, comp(a)?, limit(10))
        }
        "team_stats" => {
            let t = s(a, "team").ok_or("team required")?;
            e.team_stats_text(&t, &filter(a)?)
        }
        "standings" => {
            let season = n(a, "season").ok_or("season required")? as i32;
            e.standings_text(season, comp(a)?.unwrap_or(Competition::Brasileirao), limit(100))
        }
        "rank_teams" => {
            let metric = s(a, "metric").unwrap_or_else(|| "win_rate".into());
            e.rank_teams_text(&filter(a)?, &metric, n(a, "min_matches").unwrap_or(10) as u32, limit(10))
        }
        "biggest_wins" => e.biggest_wins_text(&filter(a)?, limit(10)),
        "league_stats" => e.league_stats_text(&filter(a)?),
        "team_competitions" => e.team_competitions_text(&s(a, "team").ok_or("team required")?),
        "derbies" => e.derbies_text(n(a, "season").map(|v| v as i32), limit(5)),
        "search_players" => {
            let ps = e.find_players(s(a, "name").as_deref(), s(a, "nationality").as_deref(), s(a, "club").as_deref(),
                s(a, "position").as_deref(), n(a, "min_overall").map(|v| v as u32));
            Ok(e.players_text(&ps, limit(20)))
        }
        "brazilian_club_players" => Ok(e.brazilian_clubs_players_text(s(a, "nationality").as_deref())),
        "dataset_info" => Ok(e.dataset_summary()),
        _ => Err(format!("Unknown tool: {name}")),
    }
}

/// Handle one JSON-RPC request; returns None for notifications.
pub fn handle(e: &Engine, req: &Value) -> Option<Value> {
    let id = req.get("id").cloned();
    let method = req.get("method").and_then(|m| m.as_str()).unwrap_or("");
    let result = match method {
        "initialize" => Ok(json!({
            "protocolVersion": req["params"]["protocolVersion"].as_str().unwrap_or("2024-11-05"),
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "brazilian-soccer-mcp", "version": env!("CARGO_PKG_VERSION")}
        })),
        "ping" => Ok(json!({})),
        "tools/list" => Ok(json!({"tools": tool_definitions()})),
        "tools/call" => {
            let p = &req["params"];
            let name = p["name"].as_str().unwrap_or("");
            let args = p.get("arguments").cloned().unwrap_or(json!({}));
            Ok(match call_tool(e, name, &args) {
                Ok(t) => json!({"content": [{"type": "text", "text": t}]}),
                Err(err) => json!({"content": [{"type": "text", "text": err}], "isError": true}),
            })
        }
        _ if id.is_none() => return None,
        _ => Err(json!({"code": -32601, "message": format!("Method not found: {method}")})),
    };
    let id = id?;
    Some(match result {
        Ok(r) => json!({"jsonrpc": "2.0", "id": id, "result": r}),
        Err(err) => json!({"jsonrpc": "2.0", "id": id, "error": err}),
    })
}
