//! Context: MCP (Model Context Protocol) JSON-RPC layer over stdio.
//!
//! Implements `initialize`, `ping`, `tools/list` and `tools/call`. Each tool
//! turns a query from `query.rs` into a short plain-text answer the LLM can
//! quote, in the layout shown in the specification.

use serde_json::{Map, Value, json};

use crate::data::{Dataset, Match, Player};
use crate::query::{self, LeagueStats, MatchFilter, PlayerFilter, StandingRow, Venue};

pub const PROTOCOL_VERSION: &str = "2024-11-05";
const DEFAULT_LIMIT: usize = 20;

/// Handles one JSON-RPC message. Returns `None` for notifications, which
/// must not be answered.
pub fn handle_message(ds: &Dataset, line: &str) -> Option<Value> {
    let msg: Value = match serde_json::from_str(line) {
        Ok(v) => v,
        Err(e) => {
            return Some(error_response(
                Value::Null,
                -32700,
                &format!("parse error: {e}"),
            ));
        }
    };
    let id = msg.get("id").cloned();
    let method = msg.get("method").and_then(Value::as_str).unwrap_or("");
    let params = msg.get("params").cloned().unwrap_or(Value::Null);

    // Notifications carry no id and get no reply.
    let id = id?;

    let result = match method {
        "initialize" => Ok(json!({
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": { "tools": {} },
            "serverInfo": { "name": "brazilian-soccer-mcp", "version": env!("CARGO_PKG_VERSION") },
        })),
        "ping" => Ok(json!({})),
        "tools/list" => Ok(json!({ "tools": tool_definitions() })),
        "tools/call" => Ok(call_tool(ds, &params)),
        other => Err((-32601, format!("method not found: {other}"))),
    };
    Some(match result {
        Ok(v) => json!({ "jsonrpc": "2.0", "id": id, "result": v }),
        Err((code, message)) => error_response(id, code, &message),
    })
}

fn error_response(id: Value, code: i64, message: &str) -> Value {
    json!({ "jsonrpc": "2.0", "id": id, "error": { "code": code, "message": message } })
}

/// Tool schemas advertised to the client.
pub fn tool_definitions() -> Value {
    json!([
        {
            "name": "search_matches",
            "description": "Find matches by team (either side), opponent, competition, season and date range. Most recent first.",
            "inputSchema": object_schema(&[
                ("team", "string", "Team name, e.g. Flamengo or Palmeiras-SP"),
                ("opponent", "string", "Second team; with team, only meetings between the two"),
                ("competition", "string", "Brasileirão Série A/B/C, Copa do Brasil or Copa Libertadores"),
                ("season", "integer", "Season year, e.g. 2023"),
                ("date_from", "string", "Inclusive start date YYYY-MM-DD"),
                ("date_to", "string", "Inclusive end date YYYY-MM-DD"),
                ("limit", "integer", "Maximum matches to return (default 20)"),
            ], &[]),
        },
        {
            "name": "team_record",
            "description": "Win/draw/loss record, goals for and against, and win rate for a team.",
            "inputSchema": object_schema(&[
                ("team", "string", "Team name"),
                ("season", "integer", "Season year"),
                ("competition", "string", "Competition name"),
                ("venue", "string", "any (default), home or away"),
            ], &["team"]),
        },
        {
            "name": "head_to_head",
            "description": "Head-to-head record and meetings between two teams.",
            "inputSchema": object_schema(&[
                ("team_a", "string", "First team"),
                ("team_b", "string", "Second team"),
                ("competition", "string", "Optional competition filter"),
            ], &["team_a", "team_b"]),
        },
        {
            "name": "standings",
            "description": "League table for a Brasileirão division and season, calculated from match results.",
            "inputSchema": object_schema(&[
                ("competition", "string", "Brasileirão Série A, B or C"),
                ("season", "integer", "Season year"),
            ], &["competition", "season"]),
        },
        {
            "name": "league_stats",
            "description": "Goals per match, home/draw/away percentages and biggest wins for a competition.",
            "inputSchema": object_schema(&[
                ("competition", "string", "Competition name (optional: all competitions)"),
                ("season", "integer", "Season year (optional)"),
            ], &[]),
        },
        {
            "name": "search_players",
            "description": "Search FIFA player data by name, nationality, club, position and minimum overall rating.",
            "inputSchema": object_schema(&[
                ("name", "string", "Name substring, e.g. Gabriel Barbosa"),
                ("nationality", "string", "Nationality, e.g. Brazil"),
                ("club", "string", "Club name substring, e.g. Flamengo"),
                ("position", "string", "Position code, e.g. ST, GK"),
                ("min_overall", "integer", "Minimum overall rating"),
                ("limit", "integer", "Maximum players to return (default 20)"),
            ], &[]),
        }
    ])
}

fn object_schema(props: &[(&str, &str, &str)], required: &[&str]) -> Value {
    let mut properties = Map::new();
    for (name, ty, desc) in props {
        properties.insert(
            (*name).to_string(),
            json!({ "type": ty, "description": desc }),
        );
    }
    json!({ "type": "object", "properties": properties, "required": required })
}

/// Runs a `tools/call`. Tool failures are reported inside the result with
/// `isError: true`, as MCP specifies, not as JSON-RPC errors.
fn call_tool(ds: &Dataset, params: &Value) -> Value {
    let name = params.get("name").and_then(Value::as_str).unwrap_or("");
    let args = params
        .get("arguments")
        .cloned()
        .unwrap_or_else(|| json!({}));
    let outcome = match name {
        "search_matches" => search_matches_tool(ds, &args),
        "team_record" => team_record_tool(ds, &args),
        "head_to_head" => head_to_head_tool(ds, &args),
        "standings" => standings_tool(ds, &args),
        "league_stats" => league_stats_tool(ds, &args),
        "search_players" => search_players_tool(ds, &args),
        other => Err(format!("unknown tool `{other}`")),
    };
    match outcome {
        Ok(text) => json!({ "content": [{ "type": "text", "text": text }], "isError": false }),
        Err(text) => json!({ "content": [{ "type": "text", "text": text }], "isError": true }),
    }
}

fn str_arg(args: &Value, key: &str) -> Option<String> {
    args.get(key).and_then(Value::as_str).map(str::to_string)
}

fn int_arg(args: &Value, key: &str) -> Option<i64> {
    args.get(key).and_then(Value::as_i64)
}

fn require_str(args: &Value, key: &str) -> Result<String, String> {
    str_arg(args, key)
        .filter(|s| !s.trim().is_empty())
        .ok_or_else(|| format!("`{key}` is required"))
}

fn search_matches_tool(ds: &Dataset, args: &Value) -> Result<String, String> {
    let filter = MatchFilter {
        team: str_arg(args, "team"),
        opponent: str_arg(args, "opponent"),
        competition: str_arg(args, "competition"),
        season: int_arg(args, "season").map(|s| s as i32),
        date_from: str_arg(args, "date_from"),
        date_to: str_arg(args, "date_to"),
    };
    let limit = int_arg(args, "limit").map_or(DEFAULT_LIMIT, |l| l.max(1) as usize);
    let matches = query::search_matches(ds, &filter)?;
    if matches.is_empty() {
        return Ok("No matches found in the dataset for those criteria.".to_string());
    }
    let mut out = String::new();
    let header = match (&filter.team, &filter.opponent) {
        (Some(a), Some(b)) => format!("Matches between {a} and {b}:\n"),
        (Some(a), None) => format!("Matches involving {a}:\n"),
        (None, Some(b)) => format!("Matches involving {b}:\n"),
        (None, None) => "Matches:\n".to_string(),
    };
    out.push_str(&header);
    for m in matches.iter().take(limit) {
        out.push_str(&format!("- {}\n", format_match(m)));
    }
    if matches.len() > limit {
        out.push_str(&format!(
            "... ({} more matches in dataset)\n",
            matches.len() - limit
        ));
    }
    Ok(out.trim_end().to_string())
}

fn team_record_tool(ds: &Dataset, args: &Value) -> Result<String, String> {
    let team = require_str(args, "team")?;
    let venue = match str_arg(args, "venue")
        .as_deref()
        .map(str::to_lowercase)
        .as_deref()
    {
        None | Some("") | Some("any") => Venue::Any,
        Some("home") => Venue::Home,
        Some("away") => Venue::Away,
        Some(other) => return Err(format!("venue must be any, home or away, got `{other}`")),
    };
    let season = int_arg(args, "season").map(|s| s as i32);
    let competition = str_arg(args, "competition");
    let (team, rec) = query::team_record(ds, &team, season, competition.as_deref(), venue)?;
    let scope = [
        season.map(|s| s.to_string()),
        competition.clone(),
        match venue {
            Venue::Any => None,
            Venue::Home => Some("home".to_string()),
            Venue::Away => Some("away".to_string()),
        },
    ]
    .into_iter()
    .flatten()
    .collect::<Vec<_>>()
    .join(", ");
    let scope = if scope.is_empty() {
        "all data".to_string()
    } else {
        scope
    };
    if rec.played == 0 {
        return Ok(format!("No matches found for {} ({scope}).", team.name));
    }
    Ok(format!(
        "{} record ({scope}):\n- Matches: {}\n- Wins: {}, Draws: {}, Losses: {}\n- Goals For: {}, Goals Against: {}\n- Win rate: {:.1}%",
        team.name,
        rec.played,
        rec.wins,
        rec.draws,
        rec.losses,
        rec.goals_for,
        rec.goals_against,
        rec.win_rate()
    ))
}

fn head_to_head_tool(ds: &Dataset, args: &Value) -> Result<String, String> {
    let a = require_str(args, "team_a")?;
    let b = require_str(args, "team_b")?;
    let competition = str_arg(args, "competition");
    let (ta, tb, meetings, rec) = query::head_to_head(ds, &a, &b, competition.as_deref())?;
    if meetings.is_empty() {
        return Ok(format!(
            "No meetings between {} and {} in the dataset.",
            ta.name, tb.name
        ));
    }
    let mut out = format!("{} vs {}:\n", ta.name, tb.name);
    for m in meetings.iter().take(DEFAULT_LIMIT) {
        out.push_str(&format!("- {}\n", format_match(m)));
    }
    if meetings.len() > DEFAULT_LIMIT {
        out.push_str(&format!(
            "... ({} more matches in dataset)\n",
            meetings.len() - DEFAULT_LIMIT
        ));
    }
    out.push_str(&format!(
        "\nHead-to-head in dataset: {} {} wins, {} {} wins, {} draws (goals {}-{})",
        ta.name, rec.wins, tb.name, rec.losses, rec.draws, rec.goals_for, rec.goals_against
    ));
    Ok(out)
}

fn standings_tool(ds: &Dataset, args: &Value) -> Result<String, String> {
    let competition = require_str(args, "competition")?;
    let season = int_arg(args, "season").ok_or("`season` is required")? as i32;
    let rows = query::standings(ds, &competition, season)?;
    if rows.is_empty() {
        return Ok(format!(
            "No {competition} matches for {season} in the dataset."
        ));
    }
    let mut out = format!("{competition} {season} standings (calculated from matches):\n");
    for (i, row) in rows.iter().enumerate() {
        out.push_str(&format_standing(i + 1, row));
        out.push('\n');
    }
    Ok(out.trim_end().to_string())
}

fn format_standing(position: usize, row: &StandingRow) -> String {
    format!(
        "{position}. {} - {} pts ({}W, {}D, {}L, GF {}, GA {}, GD {:+})",
        row.team,
        row.points,
        row.record.wins,
        row.record.draws,
        row.record.losses,
        row.record.goals_for,
        row.record.goals_against,
        row.goal_difference()
    )
}

fn league_stats_tool(ds: &Dataset, args: &Value) -> Result<String, String> {
    let competition = str_arg(args, "competition");
    let season = int_arg(args, "season").map(|s| s as i32);
    let stats = query::league_stats(ds, competition.as_deref(), season)?;
    if stats.matches == 0 {
        return Ok("No matches found for those criteria.".to_string());
    }
    Ok(format_league_stats(&stats, competition.as_deref(), season))
}

fn format_league_stats(
    stats: &LeagueStats,
    competition: Option<&str>,
    season: Option<i32>,
) -> String {
    let scope = match (competition, season) {
        (Some(c), Some(s)) => format!("{c} {s}"),
        (Some(c), None) => c.to_string(),
        (None, Some(s)) => format!("all competitions {s}"),
        (None, None) => "all competitions".to_string(),
    };
    let mut out = format!(
        "Statistics for {scope} ({} matches):\n- Average goals per match: {:.2}\n- Home win rate: {:.1}%\n- Draw rate: {:.1}%\n- Away win rate: {:.1}%\n",
        stats.matches, stats.avg_goals, stats.home_win_pct, stats.draw_pct, stats.away_win_pct
    );
    if !stats.biggest_wins.is_empty() {
        out.push_str("Biggest wins:\n");
        for m in &stats.biggest_wins {
            out.push_str(&format!("- {}\n", format_match(m)));
        }
    }
    out.trim_end().to_string()
}

fn search_players_tool(ds: &Dataset, args: &Value) -> Result<String, String> {
    let filter = PlayerFilter {
        name: str_arg(args, "name"),
        nationality: str_arg(args, "nationality"),
        club: str_arg(args, "club"),
        position: str_arg(args, "position"),
        min_overall: int_arg(args, "min_overall").map(|v| v.max(0) as u32),
    };
    let limit = int_arg(args, "limit").map_or(DEFAULT_LIMIT, |l| l.max(1) as usize);
    let players = query::search_players(ds, &filter);
    if players.is_empty() {
        return Ok("No players found for those criteria.".to_string());
    }
    let mut out = format!("{} players found (highest overall first):\n", players.len());
    for (i, p) in players.iter().take(limit).enumerate() {
        out.push_str(&format!("{}. {}\n", i + 1, format_player(p)));
    }
    if players.len() > limit {
        out.push_str(&format!(
            "... ({} more players in dataset)\n",
            players.len() - limit
        ));
    }
    Ok(out.trim_end().to_string())
}

fn format_player(p: &Player) -> String {
    format!(
        "{} - Overall: {}, Potential: {}, Age: {}, Nationality: {}, Position: {}, Club: {}",
        p.name,
        p.overall,
        p.potential,
        p.age,
        p.nationality,
        p.position.as_deref().unwrap_or("n/a"),
        p.club.as_deref().unwrap_or("n/a"),
    )
}

/// `Flamengo 2-1 Fluminense (2023-09-03, Brasileirão Série A, round 22)`.
pub fn format_match(m: &Match) -> String {
    let round = m
        .round
        .as_ref()
        .map(|r| format!(", round {r}"))
        .unwrap_or_default();
    format!(
        "{}: {} {}-{} {} ({}{})",
        m.date, m.home.name, m.home_goals, m.away_goals, m.away.name, m.competition, round
    )
}
