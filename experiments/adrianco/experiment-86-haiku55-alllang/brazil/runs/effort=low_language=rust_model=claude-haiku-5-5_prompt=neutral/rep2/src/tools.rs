//! Context: the MCP tool surface. Each tool validates JSON arguments, runs a
//! query from `query.rs`, and returns plain text formatted for an LLM to quote.

use std::fmt::Write as _;

use serde_json::{json, Value};

use crate::data::{Dataset, Match, Player};
use crate::query::{
    average_goals, biggest_wins, club_summary, find_matches, head_to_head, home_win_rate,
    resolve_team, search_players, standings, team_record, venue_ranking, MatchFilter, PlayerFilter,
    Record, Venue,
};

const DEFAULT_LIMIT: usize = 20;
const MAX_LIMIT: usize = 200;
const DEFAULT_COMPETITION: &str = "Brasileirão Série A";

/// Errors returned to the client as tool results with `isError: true`.
pub type ToolResult = Result<String, String>;

/// JSON descriptions of every tool, in MCP `tools/list` format.
pub fn tool_definitions() -> Value {
    json!([
        {
            "name": "search_matches",
            "description": "Find matches between teams across Brasileirão, Copa do Brasil and Copa Libertadores data. Team names accept state suffixes and accents.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team": {"type": "string", "description": "Team name, e.g. 'Flamengo'"},
                    "opponent": {"type": "string", "description": "Second team; restricts to matches between the two"},
                    "venue": {"type": "string", "enum": ["any", "home", "away"], "description": "Venue of 'team'"},
                    "competition": {"type": "string", "description": "Competition name or part, e.g. 'Copa do Brasil'"},
                    "season": {"type": "integer", "description": "Season year, e.g. 2023"},
                    "round": {"type": "string", "description": "Round number or stage, e.g. '8'; 'final' selects the last round of each competition-season"},
                    "start_date": {"type": "string", "description": "Inclusive start, YYYY-MM-DD"},
                    "end_date": {"type": "string", "description": "Inclusive end, YYYY-MM-DD"},
                    "limit": {"type": "integer", "description": "Max matches to return (default 20)"}
                }
            }
        },
        {
            "name": "team_record",
            "description": "Win/draw/loss record, goals for and against, and win rate for one team.",
            "inputSchema": {
                "type": "object",
                "required": ["team"],
                "properties": {
                    "team": {"type": "string"},
                    "venue": {"type": "string", "enum": ["any", "home", "away"]},
                    "competition": {"type": "string"},
                    "season": {"type": "integer"},
                    "start_date": {"type": "string"},
                    "end_date": {"type": "string"}
                }
            }
        },
        {
            "name": "head_to_head",
            "description": "Head-to-head record between two teams in the dataset, with recent results.",
            "inputSchema": {
                "type": "object",
                "required": ["team", "opponent"],
                "properties": {
                    "team": {"type": "string"},
                    "opponent": {"type": "string"},
                    "competition": {"type": "string"},
                    "season": {"type": "integer"},
                    "limit": {"type": "integer", "description": "Recent matches to list (default 20)"}
                }
            }
        },
        {
            "name": "standings",
            "description": "League table for one season calculated from match results (3 points for a win, 1 for a draw).",
            "inputSchema": {
                "type": "object",
                "required": ["season"],
                "properties": {
                    "season": {"type": "integer"},
                    "competition": {"type": "string", "description": "Default 'Brasileirão Série A'"}
                }
            }
        },
        {
            "name": "aggregate_stats",
            "description": "Aggregate statistics: average_goals, home_win_rate, biggest_wins, or best_venue_record (team win rate ranking in a venue).",
            "inputSchema": {
                "type": "object",
                "required": ["metric"],
                "properties": {
                    "metric": {"type": "string", "enum": ["average_goals", "home_win_rate", "biggest_wins", "best_venue_record"]},
                    "team": {"type": "string", "description": "Optional team filter for average_goals, home_win_rate and biggest_wins"},
                    "competition": {"type": "string"},
                    "season": {"type": "integer"},
                    "venue": {"type": "string", "enum": ["any", "home", "away"], "description": "For best_venue_record (default home)"},
                    "min_matches": {"type": "integer", "description": "For best_venue_record: minimum games (default 10)"},
                    "limit": {"type": "integer", "description": "Rows to return (default 10)"}
                }
            }
        },
        {
            "name": "search_players",
            "description": "Search FIFA player data by name, nationality, club, position or position group (forward, midfielder, defender, goalkeeper), and minimum overall rating.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "nationality": {"type": "string", "description": "e.g. 'Brazil'"},
                    "club": {"type": "string", "description": "e.g. 'Flamengo'"},
                    "position": {"type": "string", "description": "Position code (ST, CM) or group (forward, midfielder, defender, goalkeeper)"},
                    "min_overall": {"type": "integer"},
                    "limit": {"type": "integer", "description": "Default 20"}
                }
            }
        },
        {
            "name": "club_summary",
            "description": "For one nationality (default Brazil), list clubs with player counts and average overall rating.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "nationality": {"type": "string"},
                    "limit": {"type": "integer", "description": "Default 20"}
                }
            }
        }
    ])
}

/// Run a tool by name with its JSON arguments.
pub fn call_tool(ds: &Dataset, name: &str, args: &Value) -> ToolResult {
    match name {
        "search_matches" => search_matches_tool(ds, args),
        "team_record" => team_record_tool(ds, args),
        "head_to_head" => head_to_head_tool(ds, args),
        "standings" => standings_tool(ds, args),
        "aggregate_stats" => aggregate_tool(ds, args),
        "search_players" => search_players_tool(ds, args),
        "club_summary" => club_summary_tool(ds, args),
        other => Err(format!("unknown tool '{other}'")),
    }
}

// ---------- argument helpers ----------

fn str_arg<'a>(args: &'a Value, key: &str) -> Option<&'a str> {
    args.get(key)
        .and_then(Value::as_str)
        .map(str::trim)
        .filter(|s| !s.is_empty())
}

fn int_arg(args: &Value, key: &str) -> Result<Option<i64>, String> {
    match args.get(key) {
        None | Some(Value::Null) => Ok(None),
        Some(v) => v
            .as_i64()
            .or_else(|| v.as_str().and_then(|s| s.trim().parse().ok()))
            .map(Some)
            .ok_or_else(|| format!("'{key}' must be an integer")),
    }
}

fn limit_arg(args: &Value) -> Result<usize, String> {
    let limit = int_arg(args, "limit")?.unwrap_or(DEFAULT_LIMIT as i64);
    if limit < 1 {
        return Err("'limit' must be at least 1".to_string());
    }
    Ok((limit as usize).min(MAX_LIMIT))
}

fn season_arg(args: &Value) -> Result<Option<i32>, String> {
    Ok(int_arg(args, "season")?.map(|s| s as i32))
}

fn date_arg(args: &Value, key: &str) -> Result<Option<String>, String> {
    match str_arg(args, key) {
        None => Ok(None),
        Some(raw) => crate::normalize::iso_date(raw)
            .map(Some)
            .ok_or_else(|| format!("'{key}' must be a date like 2023-09-24")),
    }
}

fn venue_arg(args: &Value) -> Result<Venue, String> {
    let raw = str_arg(args, "venue").unwrap_or("any");
    Venue::parse(raw).ok_or_else(|| format!("'venue' must be any, home or away (got '{raw}')"))
}

fn resolve_arg(ds: &Dataset, args: &Value, key: &str) -> Result<Option<String>, String> {
    str_arg(args, key).map(|q| resolve_team(ds, q)).transpose()
}

/// Build the shared filter from common match arguments.
fn common_filter(ds: &Dataset, args: &Value) -> Result<MatchFilter, String> {
    Ok(MatchFilter {
        team: resolve_arg(ds, args, "team")?,
        opponent: resolve_arg(ds, args, "opponent")?,
        venue: venue_arg(args)?,
        competition: str_arg(args, "competition").map(str::to_string),
        season: season_arg(args)?,
        round: str_arg(args, "round").map(str::to_string),
        start_date: date_arg(args, "start_date")?,
        end_date: date_arg(args, "end_date")?,
    })
}

// ---------- formatting ----------

fn describe_round(m: &Match) -> String {
    match m.round.as_deref() {
        Some(r) if r.chars().all(|c| c.is_ascii_digit()) => format!("Round {r}"),
        Some(r) => r.to_string(),
        None => String::new(),
    }
}

fn format_match(ds: &Dataset, m: &Match) -> String {
    let round = describe_round(m);
    let context = if round.is_empty() {
        m.competition.clone()
    } else {
        format!("{}, {round}", m.competition)
    };
    format!(
        "{}: {} {}-{} {} ({context})",
        m.date,
        ds.team_display(&m.home_key),
        m.home_goals,
        m.away_goals,
        ds.team_display(&m.away_key),
    )
}

fn format_record(record: &Record) -> String {
    format!(
        "- Matches: {}\n- Wins: {}, Draws: {}, Losses: {}\n- Goals For: {}, Goals Against: {}\n- Win rate: {:.1}%",
        record.played,
        record.wins,
        record.draws,
        record.losses,
        record.goals_for,
        record.goals_against,
        record.win_rate(),
    )
}

fn scope_label(filter: &MatchFilter) -> String {
    let mut parts = Vec::new();
    if let Some(c) = &filter.competition {
        parts.push(c.clone());
    }
    if let Some(s) = filter.season {
        parts.push(s.to_string());
    }
    if filter.venue != Venue::Any {
        parts.push(format!("{:?} games", filter.venue).to_lowercase());
    }
    if parts.is_empty() {
        "all competitions".to_string()
    } else {
        parts.join(", ")
    }
}

// ---------- tools ----------

fn search_matches_tool(ds: &Dataset, args: &Value) -> ToolResult {
    let filter = common_filter(ds, args)?;
    let limit = limit_arg(args)?;
    let all = find_matches(ds, &filter);
    if all.is_empty() {
        return Ok("No matches found for those criteria.".to_string());
    }
    let mut out = String::new();
    let _ = writeln!(
        out,
        "{} matches found ({} shown):",
        all.len(),
        all.len().min(limit)
    );
    for m in all.iter().take(limit) {
        let _ = writeln!(out, "- {}", format_match(ds, m));
    }
    if all.len() > limit {
        let _ = writeln!(out, "... ({} more matches in dataset)", all.len() - limit);
    }
    Ok(out.trim_end().to_string())
}

fn team_record_tool(ds: &Dataset, args: &Value) -> ToolResult {
    let filter = common_filter(ds, args)?;
    let team = filter.team.clone().ok_or("'team' is required")?;
    let record = team_record(ds, &team, &filter);
    if record.played == 0 {
        return Ok(format!(
            "{} has no matches in the dataset for {}.",
            ds.team_display(&team),
            scope_label(&filter)
        ));
    }
    Ok(format!(
        "{} record ({}):\n{}",
        ds.team_display(&team),
        scope_label(&filter),
        format_record(&record)
    ))
}

fn head_to_head_tool(ds: &Dataset, args: &Value) -> ToolResult {
    let filter = common_filter(ds, args)?;
    let limit = limit_arg(args)?;
    let (Some(a), Some(b)) = (filter.team.clone(), filter.opponent.clone()) else {
        return Err("'team' and 'opponent' are both required".to_string());
    };
    if a == b {
        return Err("'team' and 'opponent' must be different teams".to_string());
    }
    let record = head_to_head(ds, &a, &b, &filter);
    let name_a = ds.team_display(&a);
    let name_b = ds.team_display(&b);
    if record.played == 0 {
        return Ok(format!(
            "No matches between {name_a} and {name_b} in the dataset ({}).",
            scope_label(&filter)
        ));
    }
    let mut out = format!(
        "{name_a} vs {name_b} head-to-head ({}):\n- {name_a} wins: {}, {name_b} wins: {}, draws: {}\n- Goals: {name_a} {}, {name_b} {}\n\nMost recent matches:\n",
        scope_label(&filter),
        record.wins,
        record.losses,
        record.draws,
        record.goals_for,
        record.goals_against,
    );
    let mut matches = find_matches(ds, &filter);
    matches.truncate(limit);
    for m in matches {
        let _ = writeln!(out, "- {}", format_match(ds, m));
    }
    Ok(out.trim_end().to_string())
}

fn standings_tool(ds: &Dataset, args: &Value) -> ToolResult {
    let season = season_arg(args)?.ok_or("'season' is required")?;
    let competition = str_arg(args, "competition").unwrap_or(DEFAULT_COMPETITION);
    let filter = MatchFilter {
        season: Some(season),
        competition: Some(competition.to_string()),
        ..MatchFilter::default()
    };
    let table = standings(ds, &filter);
    if table.is_empty() {
        return Ok(format!(
            "No {competition} matches in the dataset for {season}."
        ));
    }
    let mut out = format!("{competition} {season} standings (calculated from matches):\n");
    for (i, row) in table.iter().enumerate() {
        let r = row.record;
        let _ = writeln!(
            out,
            "{}. {} - {} pts ({}W, {}D, {}L, GF {}, GA {}, GD {:+})",
            i + 1,
            ds.team_display(&row.team_key),
            r.points(),
            r.wins,
            r.draws,
            r.losses,
            r.goals_for,
            r.goals_against,
            r.goal_difference(),
        );
    }
    Ok(out.trim_end().to_string())
}

fn aggregate_tool(ds: &Dataset, args: &Value) -> ToolResult {
    let metric = str_arg(args, "metric").ok_or("'metric' is required")?;
    let filter = common_filter(ds, args)?;
    let scope = scope_label(&filter);
    match metric {
        "average_goals" => {
            let (n, avg) = average_goals(ds, &filter).ok_or("no matches for those criteria")?;
            Ok(format!(
                "Average goals per match ({scope}): {avg:.2} over {n} matches"
            ))
        }
        "home_win_rate" => {
            let (n, rate) = home_win_rate(ds, &filter).ok_or("no matches for those criteria")?;
            Ok(format!(
                "Home win rate ({scope}): {rate:.1}% over {n} matches"
            ))
        }
        "biggest_wins" => {
            let limit = limit_arg(args)?.min(50);
            let wins = biggest_wins(ds, &filter, limit);
            if wins.is_empty() {
                return Ok("No decisive matches for those criteria.".to_string());
            }
            let mut out = format!("Biggest wins ({scope}):\n");
            for (i, m) in wins.iter().enumerate() {
                let _ = writeln!(out, "{}. {}", i + 1, format_match(ds, m));
            }
            Ok(out.trim_end().to_string())
        }
        "best_venue_record" => {
            let venue = match venue_arg(args)? {
                Venue::Any => Venue::Home,
                v => v,
            };
            let min = int_arg(args, "min_matches")?.unwrap_or(10).max(1) as u32;
            let limit = limit_arg(args)?.min(50);
            let mut scoped = filter.clone();
            scoped.team = None;
            scoped.opponent = None;
            scoped.venue = Venue::Any;
            let ranking = venue_ranking(ds, venue, &scoped, min);
            if ranking.is_empty() {
                return Ok(format!(
                    "No team has at least {min} {venue:?} matches in scope ({scope})."
                ));
            }
            let label = format!("{venue:?}").to_lowercase();
            let mut out = format!("Best {label} win rates ({scope}, minimum {min} matches):\n");
            for (i, (key, r)) in ranking.iter().take(limit).enumerate() {
                let _ = writeln!(
                    out,
                    "{}. {} - {:.1}% ({}W {}D {}L in {} matches)",
                    i + 1,
                    ds.team_display(key),
                    r.win_rate(),
                    r.wins,
                    r.draws,
                    r.losses,
                    r.played,
                );
            }
            Ok(out.trim_end().to_string())
        }
        other => Err(format!("unknown metric '{other}'")),
    }
}

fn format_player(p: &Player) -> String {
    format!(
        "{} - Overall: {}, Potential: {}, Age: {}, Position: {}, Club: {}, Nationality: {}",
        p.name, p.overall, p.potential, p.age, p.position, p.club, p.nationality
    )
}

fn search_players_tool(ds: &Dataset, args: &Value) -> ToolResult {
    let filter = PlayerFilter {
        name: str_arg(args, "name").map(str::to_string),
        nationality: str_arg(args, "nationality").map(str::to_string),
        club: str_arg(args, "club").map(str::to_string),
        position: str_arg(args, "position").map(str::to_string),
        min_overall: int_arg(args, "min_overall")?.map(|v| v.max(0) as u32),
    };
    let limit = limit_arg(args)?;
    let found = search_players(ds, &filter, limit);
    if found.is_empty() {
        return Ok("No players found for those criteria.".to_string());
    }
    let mut out = format!("{} players found:\n", found.len());
    for p in found {
        let _ = writeln!(out, "- {}", format_player(p));
    }
    Ok(out.trim_end().to_string())
}

fn club_summary_tool(ds: &Dataset, args: &Value) -> ToolResult {
    let nationality = str_arg(args, "nationality").unwrap_or("Brazil");
    let limit = limit_arg(args)?;
    let rows = club_summary(ds, nationality);
    if rows.is_empty() {
        return Ok(format!(
            "No players with nationality '{nationality}' in the dataset."
        ));
    }
    let mut out = format!("{nationality} players by club (top {limit}):\n");
    for row in rows.iter().take(limit) {
        let _ = writeln!(
            out,
            "- {}: {} players (avg overall {:.1})",
            row.club, row.players, row.average_overall
        );
    }
    Ok(out.trim_end().to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn given_unknown_tool_when_called_then_error_names_it() {
        let ds = Dataset::default();
        let err = call_tool(&ds, "nope", &json!({})).unwrap_err();
        assert!(err.contains("nope"));
    }

    #[test]
    fn given_bad_limit_when_called_then_validation_error() {
        assert!(limit_arg(&json!({"limit": 0})).is_err());
        assert_eq!(limit_arg(&json!({"limit": 100000})).unwrap(), MAX_LIMIT);
        assert_eq!(limit_arg(&json!({})).unwrap(), DEFAULT_LIMIT);
    }
}
