//! MCP tool definitions, argument parsing and plain-text result formatting.
//!
//! Results are human-readable text so the connected LLM can quote them
//! directly. Argument errors come back as `Err(message)`, which the MCP layer
//! reports as a tool error.

use std::fmt::Write as _;

use serde_json::{json, Map, Value};

use crate::data::{parse_date, Competition, Dataset, Match};
use crate::query::{self, MatchFilter, PlayerFilter};

const DEFAULT_MATCH_LIMIT: usize = 20;
const MAX_LIMIT: usize = 200;
const DEFAULT_PLAYER_LIMIT: usize = 10;

/// The tool list advertised by `tools/list`.
pub fn definitions() -> Value {
    json!([
        {
            "name": "search_matches",
            "description": "Find Brazilian football matches. Filter by team, opponent (with team: head-to-head), competition, season and date range. Returns most recent first.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team": {"type": "string", "description": "Team name, e.g. 'Flamengo', 'Palmeiras-SP'"},
                    "opponent": {"type": "string", "description": "Second team; only matches between the two"},
                    "competition": competition_schema(),
                    "season": {"type": "integer", "description": "Year, e.g. 2023"},
                    "date_from": {"type": "string", "description": "Inclusive start date (YYYY-MM-DD or DD/MM/YYYY)"},
                    "date_to": {"type": "string", "description": "Inclusive end date (YYYY-MM-DD or DD/MM/YYYY)"},
                    "limit": {"type": "integer", "description": "Max matches to return (default 20, max 200)"}
                }
            }
        },
        {
            "name": "team_stats",
            "description": "Win/draw/loss record, goals and win rate for a team, overall and home/away, optionally by competition and season.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team": {"type": "string"},
                    "competition": competition_schema(),
                    "season": {"type": "integer"}
                },
                "required": ["team"]
            }
        },
        {
            "name": "head_to_head",
            "description": "Head-to-head record between two teams across all competitions in the dataset (or one competition).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_a": {"type": "string"},
                    "team_b": {"type": "string"},
                    "competition": competition_schema()
                },
                "required": ["team_a", "team_b"]
            }
        },
        {
            "name": "standings",
            "description": "League table calculated from match results for one competition and season (3 points for a win, 1 for a draw).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "season": {"type": "integer"},
                    "competition": competition_schema()
                },
                "required": ["season"]
            }
        },
        {
            "name": "league_stats",
            "description": "Aggregate statistics: match count, average goals per match, home/draw/away rates and the biggest wins.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "competition": competition_schema(),
                    "season": {"type": "integer"}
                }
            }
        },
        {
            "name": "search_players",
            "description": "Search FIFA player ratings by name, nationality, club, position or minimum overall. Sorted by overall rating.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Part of the player's name, e.g. 'Gabriel'"},
                    "nationality": {"type": "string", "description": "Exact nationality, e.g. 'Brazil'"},
                    "club": {"type": "string", "description": "Part of the club name, e.g. 'Flamengo'"},
                    "position": {"type": "string", "description": "Position code, e.g. 'ST', 'GK', 'CDM'"},
                    "min_overall": {"type": "integer"},
                    "limit": {"type": "integer", "description": "Default 10, max 200"}
                }
            }
        },
        {
            "name": "dataset_info",
            "description": "List the loaded data files with the number of rows loaded and skipped.",
            "inputSchema": {"type": "object", "properties": {}}
        }
    ])
}

fn competition_schema() -> Value {
    json!({
        "type": "string",
        "enum": Competition::ALL.iter().map(|c| c.slug()).collect::<Vec<_>>(),
        "description": "brasileirao, copa_do_brasil, libertadores, serie_b or serie_c"
    })
}

/// Runs a tool call and returns its text output.
pub fn call(ds: &Dataset, name: &str, args: &Value) -> Result<String, String> {
    let args = match args {
        Value::Object(map) => map.clone(),
        Value::Null => Map::new(),
        _ => return Err("arguments must be an object".into()),
    };
    match name {
        "search_matches" => search_matches(ds, &args),
        "team_stats" => team_stats(ds, &args),
        "head_to_head" => head_to_head(ds, &args),
        "standings" => standings(ds, &args),
        "league_stats" => league_stats(ds, &args),
        "search_players" => search_players(ds, &args),
        "dataset_info" => Ok(dataset_info(ds)),
        other => Err(format!("unknown tool: {other}")),
    }
}

fn search_matches(ds: &Dataset, args: &Map<String, Value>) -> Result<String, String> {
    let filter = MatchFilter {
        team: text_arg(args, "team")?,
        opponent: text_arg(args, "opponent")?,
        competition: competition_arg(args)?,
        season: season_arg(args)?,
        date_from: date_arg(args, "date_from")?,
        date_to: date_arg(args, "date_to")?,
    };
    if filter.opponent.is_some() && filter.team.is_none() {
        return Err("'opponent' needs 'team' as well; use head_to_head for two teams".into());
    }
    let limit = limit_arg(args, DEFAULT_MATCH_LIMIT)?;
    let matches = query::find_matches(ds, &filter);
    if matches.is_empty() {
        return Ok("No matches found for those criteria.".into());
    }
    let mut out = String::new();
    for m in matches.iter().take(limit) {
        writeln!(out, "{}", match_line(m)).unwrap();
    }
    if matches.len() > limit {
        writeln!(out, "... ({} more matches in dataset)", matches.len() - limit).unwrap();
    } else {
        writeln!(out, "Total: {} matches", matches.len()).unwrap();
    }
    if let (Some(team), Some(opponent)) = (&filter.team, &filter.opponent) {
        let h2h = query::head_to_head(ds, team, opponent, filter.competition);
        writeln!(
            out,
            "\nHead-to-head in dataset: {team} {} wins, {} draws, {opponent} {} wins",
            h2h.first_wins, h2h.draws, h2h.second_wins
        )
        .unwrap();
    }
    Ok(out.trim_end().to_string())
}

fn match_line(m: &Match) -> String {
    let round = m.round.as_deref().map(|r| format!(" {r}")).unwrap_or_default();
    format!(
        "{}: {} {}-{} {} ({}{})",
        m.date,
        m.home.name,
        m.home_goals,
        m.away_goals,
        m.away.name,
        m.competition.label(),
        round
    )
}

fn team_stats(ds: &Dataset, args: &Map<String, Value>) -> Result<String, String> {
    let team = required_text(args, "team")?;
    let competition = competition_arg(args)?;
    let season = season_arg(args)?;
    let stats = query::team_stats(ds, &team, competition, season);
    let scope = scope_label(competition, season);
    if stats.overall.played == 0 {
        return Ok(format!("No matches found for {team}{scope}."));
    }
    let mut out = format!("{team} record{scope}:\n");
    out.push_str(&record_block(&stats.overall));
    out.push_str(&format!("\nHome: {}\n", record_summary(&stats.home)));
    out.push_str(&format!("Away: {}", record_summary(&stats.away)));
    Ok(out)
}

fn head_to_head(ds: &Dataset, args: &Map<String, Value>) -> Result<String, String> {
    let team_a = required_text(args, "team_a")?;
    let team_b = required_text(args, "team_b")?;
    let competition = competition_arg(args)?;
    let h2h = query::head_to_head(ds, &team_a, &team_b, competition);
    let total = h2h.first_wins + h2h.draws + h2h.second_wins;
    if total == 0 {
        return Ok(format!("No matches between {team_a} and {team_b} in the dataset."));
    }
    let scope = scope_label(competition, None);
    let mut out = format!(
        "{team_a} vs {team_b}{scope}:\n- Matches: {total}\n- {team_a} wins: {}, Draws: {}, {team_b} wins: {}\n- Goals: {team_a} {}, {team_b} {}",
        h2h.first_wins, h2h.draws, h2h.second_wins, h2h.first_goals, h2h.second_goals
    );
    out.push_str("\n\nMost recent:");
    for m in h2h.matches.iter().take(5) {
        out.push_str(&format!("\n- {}", match_line(m)));
    }
    Ok(out)
}

fn standings(ds: &Dataset, args: &Map<String, Value>) -> Result<String, String> {
    let season = season_arg(args)?.ok_or("'season' is required")?;
    let competition = competition_arg(args)?.unwrap_or(Competition::Brasileirao);
    let table = query::standings(ds, competition, season);
    if table.is_empty() {
        return Ok(format!("No {} matches in {season}.", competition.label()));
    }
    let mut out = format!("{season} {} final standings (calculated from matches):\n", competition.label());
    for (index, row) in table.iter().enumerate() {
        let r = &row.record;
        writeln!(
            out,
            "{}. {} - {} pts ({}W, {}D, {}L, GF {}, GA {}, GD {:+})",
            index + 1,
            row.team,
            r.points(),
            r.wins,
            r.draws,
            r.losses,
            r.goals_for,
            r.goals_against,
            row.goal_difference()
        )
        .unwrap();
    }
    Ok(out.trim_end().to_string())
}

fn league_stats(ds: &Dataset, args: &Map<String, Value>) -> Result<String, String> {
    let competition = competition_arg(args)?;
    let season = season_arg(args)?;
    let stats = query::league_stats(ds, competition, season);
    if stats.matches == 0 {
        return Ok("No matches for those criteria.".into());
    }
    let scope = scope_label(competition, season);
    let mut out = format!(
        "Statistics{scope}:\n- Matches: {}\n- Average goals per match: {:.2}\n- Home win rate: {:.1}%, Draw rate: {:.1}%, Away win rate: {:.1}%",
        stats.matches,
        stats.avg_goals_per_match,
        stats.home_win_rate() * 100.0,
        stats.draw_rate() * 100.0,
        stats.away_win_rate() * 100.0
    );
    if !stats.biggest_wins.is_empty() {
        out.push_str("\n\nBiggest wins:");
        for m in &stats.biggest_wins {
            out.push_str(&format!("\n- {}", match_line(m)));
        }
    }
    Ok(out)
}

fn search_players(ds: &Dataset, args: &Map<String, Value>) -> Result<String, String> {
    let filter = PlayerFilter {
        name: text_arg(args, "name")?,
        nationality: text_arg(args, "nationality")?,
        club: text_arg(args, "club")?,
        position: text_arg(args, "position")?,
        min_overall: match args.get("min_overall") {
            None | Some(Value::Null) => None,
            Some(value) => Some(value.as_u64().ok_or("'min_overall' must be a non-negative integer")? as u32),
        },
    };
    let players = query::search_players(ds, &filter, limit_arg(args, DEFAULT_PLAYER_LIMIT)?);
    if players.is_empty() {
        return Ok("No players found for those criteria.".into());
    }
    let mut out = String::new();
    for p in players {
        let jersey = p.jersey_number.map(|n| format!(", #{n}")).unwrap_or_default();
        writeln!(
            out,
            "{} - Overall: {}, Potential: {}, Position: {}, Club: {}, Nationality: {}, Age: {}{jersey}",
            p.name,
            p.overall,
            p.potential,
            if p.position.is_empty() { "-" } else { &p.position },
            if p.club.is_empty() { "-" } else { &p.club },
            p.nationality,
            p.age
        )
        .unwrap();
    }
    Ok(out.trim_end().to_string())
}

fn dataset_info(ds: &Dataset) -> String {
    let mut out = format!("{} matches, {} players loaded.\n", ds.matches.len(), ds.players.len());
    for source in &ds.sources {
        writeln!(
            out,
            "- {}: {} loaded, {} duplicates, {} invalid, {} out of scope",
            source.file,
            source.rows_loaded,
            source.rows_duplicate,
            source.rows_invalid,
            source.rows_out_of_scope
        )
        .unwrap();
    }
    out.trim_end().to_string()
}

fn record_block(record: &query::Record) -> String {
    format!(
        "- Matches: {}\n- Wins: {}, Draws: {}, Losses: {}\n- Goals For: {}, Goals Against: {}\n- Win rate: {:.1}%",
        record.played,
        record.wins,
        record.draws,
        record.losses,
        record.goals_for,
        record.goals_against,
        record.win_rate() * 100.0
    )
}

fn record_summary(record: &query::Record) -> String {
    format!(
        "{}W {}D {}L, GF {} GA {} ({} matches)",
        record.wins, record.draws, record.losses, record.goals_for, record.goals_against, record.played
    )
}

fn scope_label(competition: Option<Competition>, season: Option<i32>) -> String {
    let mut parts = Vec::new();
    if let Some(c) = competition {
        parts.push(c.label().to_string());
    }
    if let Some(s) = season {
        parts.push(s.to_string());
    }
    if parts.is_empty() { String::new() } else { format!(" ({})", parts.join(" ")) }
}

fn text_arg(args: &Map<String, Value>, key: &str) -> Result<Option<String>, String> {
    match args.get(key) {
        None | Some(Value::Null) => Ok(None),
        Some(Value::String(text)) if !text.trim().is_empty() => Ok(Some(text.trim().to_string())),
        Some(Value::String(_)) => Ok(None),
        Some(_) => Err(format!("'{key}' must be a string")),
    }
}

fn required_text(args: &Map<String, Value>, key: &str) -> Result<String, String> {
    text_arg(args, key)?.ok_or_else(|| format!("'{key}' is required"))
}

fn season_arg(args: &Map<String, Value>) -> Result<Option<i32>, String> {
    match args.get("season") {
        None | Some(Value::Null) => Ok(None),
        Some(value) => value
            .as_i64()
            .and_then(|s| i32::try_from(s).ok())
            .map(Some)
            .ok_or_else(|| "'season' must be a year, e.g. 2023".to_string()),
    }
}

fn competition_arg(args: &Map<String, Value>) -> Result<Option<Competition>, String> {
    match text_arg(args, "competition")? {
        None => Ok(None),
        Some(text) => Competition::parse(&text)
            .map(Some)
            .ok_or_else(|| format!("unknown competition '{text}'; use brasileirao, copa_do_brasil, libertadores, serie_b or serie_c")),
    }
}

fn date_arg(args: &Map<String, Value>, key: &str) -> Result<Option<String>, String> {
    match text_arg(args, key)? {
        None => Ok(None),
        Some(text) => parse_date(&text)
            .map(Some)
            .ok_or_else(|| format!("'{key}' is not a valid date: {text}")),
    }
}

fn limit_arg(args: &Map<String, Value>, default: usize) -> Result<usize, String> {
    match args.get("limit") {
        None | Some(Value::Null) => Ok(default),
        Some(value) => {
            let limit = value.as_u64().ok_or("'limit' must be a positive integer")? as usize;
            if limit == 0 {
                Err("'limit' must be a positive integer".into())
            } else {
                Ok(limit.min(MAX_LIMIT))
            }
        }
    }
}
