// =============================================================================
// Context: Brazilian Soccer MCP Server
// File:    src/tools.rs
// Purpose: The MCP "tool" surface. Declares the JSON-Schema for each callable
//          tool exposed to an LLM and adapts incoming tool-call arguments into
//          `queries` invocations, formatting the results as readable text that
//          mirrors the answer formats in the specification.
//
//          Tools:
//            search_matches        - matches by team/opponent/competition/season/date
//            team_stats            - W/D/L, goals, win rate (optionally by venue)
//            head_to_head          - aggregated record between two clubs
//            search_players        - FIFA players by name/nationality/club/position/rating
//            competition_standings - league table computed from results
//            competition_stats     - avg goals, home-win rate, biggest victories
//            list_competitions     - distinct competitions + seasons available
// =============================================================================

use serde_json::{json, Value};

use crate::data::Database;
use crate::queries::{MatchQuery, PlayerQuery, Venue};

/// JSON-Schema descriptors for every tool, returned by `tools/list`.
pub fn tool_definitions() -> Value {
    json!([
        {
            "name": "search_matches",
            "description": "Search matches by team, opponent, competition, season and/or date range. Returns matching games sorted by date, plus a head-to-head summary when both team and opponent are given.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team": {"type": "string", "description": "Team name (matches home or away). Naming variants like 'Flamengo' / 'Flamengo-RJ' are handled."},
                    "opponent": {"type": "string", "description": "Restrict to matches that also involve this opponent."},
                    "competition": {"type": "string", "description": "Competition filter, e.g. 'Brasileirão', 'Copa do Brasil', 'Libertadores'."},
                    "season": {"type": "integer", "description": "Season year, e.g. 2019."},
                    "date_from": {"type": "string", "description": "Inclusive lower bound, ISO date YYYY-MM-DD."},
                    "date_to": {"type": "string", "description": "Inclusive upper bound, ISO date YYYY-MM-DD."},
                    "limit": {"type": "integer", "description": "Maximum number of matches to return (default 25)."}
                }
            }
        },
        {
            "name": "team_stats",
            "description": "Win/draw/loss record, goals for/against and win rate for a team, optionally filtered by season, competition and venue (home/away/all).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team": {"type": "string"},
                    "season": {"type": "integer"},
                    "competition": {"type": "string"},
                    "venue": {"type": "string", "enum": ["home", "away", "all"], "description": "Default 'all'."}
                },
                "required": ["team"]
            }
        },
        {
            "name": "head_to_head",
            "description": "Aggregated head-to-head record between two clubs across all competitions, with recent meetings.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team1": {"type": "string"},
                    "team2": {"type": "string"},
                    "limit": {"type": "integer", "description": "Recent meetings to list (default 10)."}
                },
                "required": ["team1", "team2"]
            }
        },
        {
            "name": "search_players",
            "description": "Search the FIFA player database by name, nationality, club, position and/or minimum overall rating. Sorted by rating.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "nationality": {"type": "string", "description": "e.g. 'Brazil'."},
                    "club": {"type": "string"},
                    "position": {"type": "string", "description": "Exact FIFA position code, e.g. 'GK', 'ST', 'LW'."},
                    "min_overall": {"type": "integer"},
                    "limit": {"type": "integer", "description": "Default 25."}
                }
            }
        },
        {
            "name": "competition_standings",
            "description": "Compute a league standings table from match results for a competition and season.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "competition": {"type": "string", "description": "Default 'Brasileirão'."},
                    "season": {"type": "integer"}
                },
                "required": ["season"]
            }
        },
        {
            "name": "competition_stats",
            "description": "Aggregate statistics for a competition/season: average goals per match, home-win rate, and the biggest victories.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "competition": {"type": "string"},
                    "season": {"type": "integer"}
                }
            }
        },
        {
            "name": "list_competitions",
            "description": "List the distinct competitions and the seasons available in the loaded data.",
            "inputSchema": {"type": "object", "properties": {}}
        }
    ])
}

fn str_arg<'a>(args: &'a Value, key: &str) -> Option<&'a str> {
    args.get(key).and_then(|v| v.as_str()).map(|s| s.trim()).filter(|s| !s.is_empty())
}

fn int_arg(args: &Value, key: &str) -> Option<i32> {
    args.get(key).and_then(|v| {
        v.as_i64().map(|n| n as i32).or_else(|| v.as_str().and_then(|s| s.parse().ok()))
    })
}

/// Dispatch a `tools/call` request. Returns the textual answer or an error
/// string describing why the call could not be served.
pub fn call_tool(db: &Database, name: &str, args: &Value) -> Result<String, String> {
    match name {
        "search_matches" => Ok(handle_search_matches(db, args)),
        "team_stats" => handle_team_stats(db, args),
        "head_to_head" => handle_head_to_head(db, args),
        "search_players" => Ok(handle_search_players(db, args)),
        "competition_standings" => handle_standings(db, args),
        "competition_stats" => Ok(handle_competition_stats(db, args)),
        "list_competitions" => Ok(handle_list_competitions(db)),
        other => Err(format!("Unknown tool: {other}")),
    }
}

fn fmt_match(m: &crate::model::Match) -> String {
    let date = m.date.as_deref().unwrap_or("date unknown");
    let mut ctx = m.competition.clone();
    if let Some(r) = &m.round {
        ctx.push_str(&format!(" Round {r}"));
    }
    if let Some(s) = &m.stage {
        ctx.push_str(&format!(" — {s}"));
    }
    format!("- {date}: {} ({ctx})", m.scoreline())
}

fn handle_search_matches(db: &Database, args: &Value) -> String {
    let q = MatchQuery {
        team: str_arg(args, "team").map(String::from),
        opponent: str_arg(args, "opponent").map(String::from),
        competition: str_arg(args, "competition").map(String::from),
        season: int_arg(args, "season"),
        date_from: str_arg(args, "date_from").map(String::from),
        date_to: str_arg(args, "date_to").map(String::from),
        limit: Some(int_arg(args, "limit").map(|n| n.max(1) as usize).unwrap_or(25)),
    };
    let matches = db.search_matches(&q);
    if matches.is_empty() {
        return "No matches found for the given criteria.".to_string();
    }

    let mut out = String::new();
    let header = match (&q.team, &q.opponent) {
        (Some(t), Some(o)) => format!("{t} vs {o} matches:"),
        (Some(t), None) => format!("Matches involving {t}:"),
        _ => "Matches:".to_string(),
    };
    out.push_str(&header);
    out.push('\n');
    for m in &matches {
        out.push_str(&fmt_match(m));
        out.push('\n');
    }

    // Head-to-head summary when two teams were specified.
    if let (Some(t), Some(o)) = (&q.team, &q.opponent) {
        let (h2h, _) = db.head_to_head(t, o);
        out.push_str(&format!(
            "\nHead-to-head in dataset: {} {} wins, {} {} wins, {} draws ({} meetings).",
            t, h2h.team1_wins, o, h2h.team2_wins, h2h.draws, h2h.total_matches
        ));
    }
    out
}

fn handle_team_stats(db: &Database, args: &Value) -> Result<String, String> {
    let team = str_arg(args, "team").ok_or("Missing required 'team'")?;
    let season = int_arg(args, "season");
    let competition = str_arg(args, "competition");
    let venue = match str_arg(args, "venue").map(|s| s.to_lowercase()).as_deref() {
        Some("home") => Venue::Home,
        Some("away") => Venue::Away,
        _ => Venue::All,
    };
    let rec = db.team_record(team, season, competition, venue);
    if rec.matches == 0 {
        return Ok(format!("No matches found for {team} with the given filters."));
    }
    let venue_label = match venue {
        Venue::Home => "home ",
        Venue::Away => "away ",
        Venue::All => "",
    };
    let scope = match (season, competition) {
        (Some(s), Some(c)) => format!(" ({s} {c})"),
        (Some(s), None) => format!(" ({s})"),
        (None, Some(c)) => format!(" ({c})"),
        (None, None) => String::new(),
    };
    Ok(format!(
        "{team} {venue_label}record{scope}:\n- Matches: {}\n- Wins: {}, Draws: {}, Losses: {}\n- Goals For: {}, Goals Against: {} (GD {:+})\n- Points: {}\n- Win rate: {:.1}%",
        rec.matches,
        rec.wins,
        rec.draws,
        rec.losses,
        rec.goals_for,
        rec.goals_against,
        rec.goal_difference(),
        rec.points(),
        rec.win_rate()
    ))
}

fn handle_head_to_head(db: &Database, args: &Value) -> Result<String, String> {
    let team1 = str_arg(args, "team1").ok_or("Missing required 'team1'")?;
    let team2 = str_arg(args, "team2").ok_or("Missing required 'team2'")?;
    let limit = int_arg(args, "limit").map(|n| n.max(1) as usize).unwrap_or(10);
    let (h2h, matches) = db.head_to_head(team1, team2);
    if h2h.total_matches == 0 {
        return Ok(format!("No matches between {team1} and {team2} in the dataset."));
    }
    let mut out = format!(
        "{team1} vs {team2} — head-to-head ({} meetings):\n- {team1} wins: {}\n- {team2} wins: {}\n- Draws: {}\n- Goals: {} - {}\n\nRecent meetings:\n",
        h2h.total_matches, h2h.team1_wins, h2h.team2_wins, h2h.draws, h2h.team1_goals, h2h.team2_goals
    );
    for m in matches.iter().take(limit) {
        out.push_str(&fmt_match(m));
        out.push('\n');
    }
    Ok(out)
}

fn handle_search_players(db: &Database, args: &Value) -> String {
    let q = PlayerQuery {
        name: str_arg(args, "name").map(String::from),
        nationality: str_arg(args, "nationality").map(String::from),
        club: str_arg(args, "club").map(String::from),
        position: str_arg(args, "position").map(String::from),
        min_overall: int_arg(args, "min_overall"),
        limit: Some(int_arg(args, "limit").map(|n| n.max(1) as usize).unwrap_or(25)),
    };
    let players = db.search_players(&q);
    if players.is_empty() {
        return "No players found for the given criteria.".to_string();
    }
    let mut out = format!("Found {} player(s):\n", players.len());
    for (i, p) in players.iter().enumerate() {
        let age = p.age.map(|a| format!(", Age: {a}")).unwrap_or_default();
        out.push_str(&format!(
            "{}. {} - Overall: {}, Potential: {}, Position: {}, Club: {}, Nationality: {}{age}\n",
            i + 1,
            p.name,
            p.overall,
            p.potential,
            if p.position.is_empty() { "?" } else { &p.position },
            if p.club.is_empty() { "Free agent" } else { &p.club },
            p.nationality,
        ));
    }
    out
}

fn handle_standings(db: &Database, args: &Value) -> Result<String, String> {
    let season = int_arg(args, "season").ok_or("Missing required 'season'")?;
    let competition = str_arg(args, "competition").unwrap_or("Brasileirão");
    let rows = db.standings(competition, season);
    if rows.is_empty() {
        return Ok(format!("No standings could be computed for {competition} {season}."));
    }
    let mut out = format!("{season} {competition} standings (computed from matches):\n");
    for row in &rows {
        out.push_str(&format!(
            "{}. {} - {} pts ({}W {}D {}L, GF {} GA {}, GD {:+})\n",
            row.position,
            row.team,
            row.points,
            row.record.wins,
            row.record.draws,
            row.record.losses,
            row.record.goals_for,
            row.record.goals_against,
            row.goal_difference,
        ));
    }
    Ok(out)
}

fn handle_competition_stats(db: &Database, args: &Value) -> String {
    let competition = str_arg(args, "competition");
    let season = int_arg(args, "season");
    let stats = db.competition_stats(competition, season);
    if stats.matches == 0 {
        return "No matches found for the given filters.".to_string();
    }
    let scope = match (&stats.competition, stats.season) {
        (Some(c), Some(s)) => format!("{c} {s}"),
        (Some(c), None) => c.clone(),
        (None, Some(s)) => format!("Season {s}"),
        (None, None) => "All competitions".to_string(),
    };
    let mut out = format!(
        "{scope} — aggregate statistics:\n- Matches: {}\n- Total goals: {}\n- Average goals per match: {:.2}\n- Home wins: {} ({:.1}%), Away wins: {}, Draws: {}\n\nBiggest victories:\n",
        stats.matches,
        stats.total_goals,
        stats.avg_goals_per_match,
        stats.home_wins,
        stats.home_win_rate,
        stats.away_wins,
        stats.draws,
    );
    for (i, m) in db.biggest_wins(competition, season, 5).iter().enumerate() {
        let date = m.date.as_deref().unwrap_or("date unknown");
        out.push_str(&format!(
            "{}. {date}: {} ({})\n",
            i + 1,
            m.scoreline(),
            m.competition
        ));
    }
    out
}

fn handle_list_competitions(db: &Database) -> String {
    use std::collections::BTreeMap;
    let mut comps: BTreeMap<String, (i32, i32, usize)> = BTreeMap::new();
    for m in &db.matches {
        let entry = comps.entry(m.competition.clone()).or_insert((i32::MAX, i32::MIN, 0));
        if m.season != 0 {
            entry.0 = entry.0.min(m.season);
            entry.1 = entry.1.max(m.season);
        }
        entry.2 += 1;
    }
    let mut out = format!(
        "Loaded {} matches and {} players across these competitions:\n",
        db.matches.len(),
        db.players.len()
    );
    for (comp, (min, max, count)) in comps {
        if min <= max {
            out.push_str(&format!("- {comp}: {count} matches ({min}–{max})\n"));
        } else {
            out.push_str(&format!("- {comp}: {count} matches\n"));
        }
    }
    out
}
