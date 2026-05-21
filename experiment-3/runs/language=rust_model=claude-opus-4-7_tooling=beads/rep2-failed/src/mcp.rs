//! MCP (Model Context Protocol) JSON-RPC handling and tool dispatch.
//!
//! Implements the server side of the MCP stdio transport: newline-delimited
//! JSON-RPC 2.0 messages. The `handle` entry point answers `initialize`,
//! `tools/list`, `tools/call` and `ping`, ignoring notifications. Each tool
//! turns a `Database` query into human-readable text — the format mirrors the
//! example answers in `TASK.md` so an LLM client can relay them directly.

use serde_json::{json, Value};

use crate::data::{parse_date, Database};
use crate::models::Match;
use crate::queries::{
    self, MatchFilter, PlayerFilter, PlayerSort, Venue,
};

/// MCP protocol version advertised when a client does not request one.
const DEFAULT_PROTOCOL: &str = "2024-11-05";
const SERVER_NAME: &str = "brazilian-soccer-mcp";
const SERVER_VERSION: &str = "0.1.0";

/// Handle one parsed JSON-RPC message.
///
/// Returns `Some(response)` for requests (messages carrying an `id`) and
/// `None` for notifications, which receive no reply.
pub fn handle(db: &Database, req: &Value) -> Option<Value> {
    let id = req.get("id").cloned();
    let method = req.get("method").and_then(Value::as_str).unwrap_or("");
    let params = req.get("params").cloned().unwrap_or_else(|| json!({}));

    // Notifications (no `id`) are processed silently.
    let id = id?;

    let outcome: Result<Value, (i64, String)> = match method {
        "initialize" => Ok(initialize_result(&params)),
        "tools/list" => Ok(tools_list()),
        "tools/call" => tools_call(db, &params),
        "ping" => Ok(json!({})),
        other => Err((-32601, format!("Method not found: {other}"))),
    };

    Some(match outcome {
        Ok(result) => json!({"jsonrpc": "2.0", "id": id, "result": result}),
        Err((code, message)) => {
            json!({"jsonrpc": "2.0", "id": id, "error": {"code": code, "message": message}})
        }
    })
}

fn initialize_result(params: &Value) -> Value {
    let protocol = params
        .get("protocolVersion")
        .and_then(Value::as_str)
        .unwrap_or(DEFAULT_PROTOCOL);
    json!({
        "protocolVersion": protocol,
        "capabilities": { "tools": {} },
        "serverInfo": { "name": SERVER_NAME, "version": SERVER_VERSION }
    })
}

/// The static tool catalogue advertised to clients.
fn tools_list() -> Value {
    json!({
        "tools": [
            {
                "name": "find_matches",
                "description": "Search soccer matches by team, opponent, competition, season or date range. Returns dates, scores and competitions, most recent first.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "team": {"type": "string", "description": "Team name (e.g. 'Flamengo'). State suffixes are handled automatically."},
                        "team2": {"type": "string", "description": "Optional second team — restricts to fixtures between the two clubs."},
                        "competition": {"type": "string", "description": "Competition filter: 'Brasileirao', 'Copa do Brasil', 'Libertadores', 'Serie B', etc."},
                        "season": {"type": "integer", "description": "Season year, e.g. 2019."},
                        "date_from": {"type": "string", "description": "Earliest date, YYYY-MM-DD."},
                        "date_to": {"type": "string", "description": "Latest date, YYYY-MM-DD."},
                        "venue": {"type": "string", "enum": ["home", "away", "either"], "description": "For a single team, restrict to home or away matches."},
                        "limit": {"type": "integer", "description": "Maximum matches to list (default 25)."}
                    }
                }
            },
            {
                "name": "team_stats",
                "description": "Win/draw/loss record, goals for/against and win rate for a team, optionally scoped to a season, competition and venue.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "team": {"type": "string", "description": "Team name."},
                        "season": {"type": "integer", "description": "Optional season year."},
                        "competition": {"type": "string", "description": "Optional competition filter."},
                        "venue": {"type": "string", "enum": ["home", "away", "either"], "description": "Restrict to home or away record."}
                    },
                    "required": ["team"]
                }
            },
            {
                "name": "head_to_head",
                "description": "Head-to-head record between two teams: wins each way, draws, goals and the full match list.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "team1": {"type": "string", "description": "First team."},
                        "team2": {"type": "string", "description": "Second team."},
                        "limit": {"type": "integer", "description": "Maximum matches to list (default 20)."}
                    },
                    "required": ["team1", "team2"]
                }
            },
            {
                "name": "find_players",
                "description": "Search the FIFA player database by name, nationality, club, position or minimum overall rating.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Player name substring."},
                        "nationality": {"type": "string", "description": "Nationality, e.g. 'Brazil'."},
                        "club": {"type": "string", "description": "Club name substring, e.g. 'Flamengo'."},
                        "position": {"type": "string", "description": "Position code, e.g. 'GK', 'ST', 'CB'."},
                        "min_overall": {"type": "integer", "description": "Minimum FIFA overall rating."},
                        "sort_by": {"type": "string", "enum": ["overall", "potential", "age", "name"], "description": "Sort order (default overall)."},
                        "limit": {"type": "integer", "description": "Maximum players to list (default 20)."}
                    }
                }
            },
            {
                "name": "competition_standings",
                "description": "League table for a competition and season, calculated from match results (3 points per win).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "competition": {"type": "string", "description": "Competition, e.g. 'Brasileirao', 'Copa do Brasil', 'Libertadores'."},
                        "season": {"type": "integer", "description": "Season year."}
                    },
                    "required": ["competition", "season"]
                }
            },
            {
                "name": "competition_stats",
                "description": "Aggregate statistics: average goals per match, home/away/draw split, biggest wins and top scoring teams. Scope with competition and/or season.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "competition": {"type": "string", "description": "Optional competition filter."},
                        "season": {"type": "integer", "description": "Optional season year."}
                    }
                }
            },
            {
                "name": "list_competitions",
                "description": "List every competition in the loaded data with match counts and the range of seasons covered.",
                "inputSchema": {"type": "object", "properties": {}}
            }
        ]
    })
}

fn tools_call(db: &Database, params: &Value) -> Result<Value, (i64, String)> {
    let name = params
        .get("name")
        .and_then(Value::as_str)
        .ok_or((-32602, "tools/call: missing 'name'".to_string()))?;
    let args = params
        .get("arguments")
        .cloned()
        .unwrap_or_else(|| json!({}));

    let text = match name {
        "find_matches" => tool_find_matches(db, &args),
        "team_stats" => tool_team_stats(db, &args),
        "head_to_head" => tool_head_to_head(db, &args),
        "find_players" => tool_find_players(db, &args),
        "competition_standings" => tool_standings(db, &args),
        "competition_stats" => tool_competition_stats(db, &args),
        "list_competitions" => tool_list_competitions(db),
        other => {
            return Ok(tool_error(format!("Unknown tool: {other}")));
        }
    };

    Ok(json!({
        "content": [{"type": "text", "text": text}],
        "isError": false
    }))
}

fn tool_error(message: String) -> Value {
    json!({
        "content": [{"type": "text", "text": message}],
        "isError": true
    })
}

// ---------------------------------------------------------------------------
// Argument helpers
// ---------------------------------------------------------------------------

/// Extract a non-empty string argument.
fn arg_str(args: &Value, key: &str) -> Option<String> {
    args.get(key)
        .and_then(Value::as_str)
        .map(str::trim)
        .filter(|s| !s.is_empty())
        .map(str::to_string)
}

/// Extract an integer argument, tolerating numbers passed as strings.
fn arg_int(args: &Value, key: &str) -> Option<i64> {
    args.get(key).and_then(|v| {
        v.as_i64()
            .or_else(|| v.as_f64().map(|f| f as i64))
            .or_else(|| v.as_str().and_then(|s| s.trim().parse().ok()))
    })
}

fn arg_limit(args: &Value, default: usize) -> usize {
    arg_int(args, "limit")
        .filter(|&n| n > 0)
        .map(|n| n as usize)
        .unwrap_or(default)
}

// ---------------------------------------------------------------------------
// Tools
// ---------------------------------------------------------------------------

fn tool_find_matches(db: &Database, args: &Value) -> String {
    let filter = MatchFilter {
        team: arg_str(args, "team"),
        team2: arg_str(args, "team2"),
        competition: arg_str(args, "competition"),
        season: arg_int(args, "season").map(|n| n as i32),
        date_from: arg_str(args, "date_from").as_deref().and_then(parse_date),
        date_to: arg_str(args, "date_to").as_deref().and_then(parse_date),
        venue: Some(Venue::parse(arg_str(args, "venue").as_deref())),
    };
    let limit = arg_limit(args, 25);

    let matches = queries::find_matches(db, &filter);
    if matches.is_empty() {
        return "No matches found for the given criteria.".to_string();
    }

    let mut out = String::new();
    out.push_str(&format!("Found {} match(es)", matches.len()));
    if let (Some(t1), Some(t2)) = (&filter.team, &filter.team2) {
        out.push_str(&format!(" between {t1} and {t2}"));
    } else if let Some(t) = &filter.team {
        out.push_str(&format!(" for {t}"));
    }
    out.push_str(":\n\n");

    for m in matches.iter().take(limit) {
        out.push_str(&format!(
            "- {} | {} | {}{}\n",
            m.date_str(),
            m.competition,
            m.score_line(),
            round_or_stage(m),
        ));
    }
    if matches.len() > limit {
        out.push_str(&format!(
            "\n(showing {limit} of {} — raise 'limit' to see more)\n",
            matches.len()
        ));
    }

    // When two teams are given, append the head-to-head summary.
    if let (Some(t1), Some(t2)) = (&filter.team, &filter.team2) {
        let h = queries::head_to_head(db, t1, t2);
        out.push_str(&format!(
            "\nHead-to-head: {} {} wins, {} {} wins, {} draws (goals {}-{}).\n",
            queries::canonical_team_name(db, t1),
            h.team1_wins,
            queries::canonical_team_name(db, t2),
            h.team2_wins,
            h.draws,
            h.team1_goals,
            h.team2_goals,
        ));
    }
    out
}

fn round_or_stage(m: &Match) -> String {
    if let Some(r) = &m.round {
        format!(" (Round {r})")
    } else if let Some(s) = &m.stage {
        format!(" ({s})")
    } else {
        String::new()
    }
}

fn tool_team_stats(db: &Database, args: &Value) -> String {
    let Some(team) = arg_str(args, "team") else {
        return "team_stats: 'team' is required.".to_string();
    };
    let season = arg_int(args, "season").map(|n| n as i32);
    let competition = arg_str(args, "competition");
    let venue = Venue::parse(arg_str(args, "venue").as_deref());

    let stats = queries::team_stats(db, &team, season, competition.as_deref(), venue);
    let display = queries::canonical_team_name(db, &team);

    if stats.matches == 0 {
        return format!("No matches found for {display} with the given filters.");
    }

    let scope = {
        let mut parts = Vec::new();
        if let Some(s) = season {
            parts.push(s.to_string());
        }
        if let Some(c) = &competition {
            parts.push(c.clone());
        }
        parts.push(match venue {
            Venue::Home => "home matches".to_string(),
            Venue::Away => "away matches".to_string(),
            Venue::Either => "all matches".to_string(),
        });
        parts.join(", ")
    };

    format!(
        "{display} — {scope}\n\
         Matches: {} | Wins: {} | Draws: {} | Losses: {}\n\
         Goals For: {} | Goals Against: {} | Goal Diff: {:+}\n\
         Win rate: {:.1}% | Points: {} (3 per win)\n",
        stats.matches,
        stats.wins,
        stats.draws,
        stats.losses,
        stats.goals_for,
        stats.goals_against,
        stats.goal_diff(),
        stats.win_rate(),
        stats.points(),
    )
}

fn tool_head_to_head(db: &Database, args: &Value) -> String {
    let (Some(t1), Some(t2)) = (arg_str(args, "team1"), arg_str(args, "team2")) else {
        return "head_to_head: both 'team1' and 'team2' are required.".to_string();
    };
    let limit = arg_limit(args, 20);

    let h = queries::head_to_head(db, &t1, &t2);
    let name1 = queries::canonical_team_name(db, &t1);
    let name2 = queries::canonical_team_name(db, &t2);

    if h.matches.is_empty() {
        return format!("No matches found between {name1} and {name2}.");
    }

    let mut out = format!("{name1} vs {name2} — head-to-head ({} matches)\n", h.matches.len());
    out.push_str(&format!(
        "{name1}: {} wins | {name2}: {} wins | Draws: {}\n",
        h.team1_wins, h.team2_wins, h.draws
    ));
    out.push_str(&format!(
        "Goals: {name1} {} — {} {name2}\n\n",
        h.team1_goals, h.team2_goals
    ));

    for m in h.matches.iter().take(limit) {
        out.push_str(&format!(
            "- {} | {} | {}{}\n",
            m.date_str(),
            m.competition,
            m.score_line(),
            round_or_stage(m),
        ));
    }
    if h.matches.len() > limit {
        out.push_str(&format!(
            "\n(showing {limit} of {} matches)\n",
            h.matches.len()
        ));
    }
    out
}

fn tool_find_players(db: &Database, args: &Value) -> String {
    let filter = PlayerFilter {
        name: arg_str(args, "name"),
        nationality: arg_str(args, "nationality"),
        club: arg_str(args, "club"),
        position: arg_str(args, "position"),
        min_overall: arg_int(args, "min_overall").map(|n| n as i32),
    };
    let sort = PlayerSort::parse(arg_str(args, "sort_by").as_deref());
    let limit = arg_limit(args, 20);

    let players = queries::find_players(db, &filter, sort);
    if players.is_empty() {
        return "No players found for the given criteria.".to_string();
    }

    let sort_label = match sort {
        PlayerSort::Overall => "overall rating",
        PlayerSort::Potential => "potential",
        PlayerSort::Age => "age",
        PlayerSort::Name => "name",
    };
    let mut out = format!(
        "Found {} player(s); showing top {} by {sort_label}:\n\n",
        players.len(),
        players.len().min(limit),
    );
    for (i, p) in players.iter().take(limit).enumerate() {
        out.push_str(&format!(
            "{:>3}. {} — Overall {}, Potential {}, {}, {}, {}, Age {}\n",
            i + 1,
            p.name,
            p.overall,
            p.potential,
            if p.position.is_empty() { "—" } else { &p.position },
            if p.club.is_empty() { "no club" } else { &p.club },
            p.nationality,
            p.age,
        ));
    }
    if players.len() > limit {
        out.push_str(&format!(
            "\n(showing {limit} of {} — raise 'limit' to see more)\n",
            players.len()
        ));
    }
    out
}

fn tool_standings(db: &Database, args: &Value) -> String {
    let Some(comp_query) = arg_str(args, "competition") else {
        return "competition_standings: 'competition' is required.".to_string();
    };
    let Some(season) = arg_int(args, "season").map(|n| n as i32) else {
        return "competition_standings: 'season' is required.".to_string();
    };

    let Some(competition) = queries::resolve_competition(db, &comp_query) else {
        return format!("Unknown competition: '{comp_query}'. Use list_competitions to see options.");
    };

    let rows = queries::standings(db, &competition, season);
    if rows.is_empty() {
        let seasons = queries::seasons_for(db, &competition);
        let avail = if seasons.is_empty() {
            "none".to_string()
        } else {
            format!(
                "{}-{}",
                seasons.first().unwrap(),
                seasons.last().unwrap()
            )
        };
        return format!(
            "No {competition} data for season {season}. Available seasons: {avail}."
        );
    }

    let mut out = format!(
        "{season} {competition} — Standings (calculated from match results)\n\n"
    );
    out.push_str(&format!(
        "{:>3}  {:<26} {:>4} {:>4} {:>4} {:>4} {:>4} {:>5} {:>5} {:>5}\n",
        "#", "Team", "Pts", "P", "W", "D", "L", "GF", "GA", "GD"
    ));
    for (i, r) in rows.iter().enumerate() {
        out.push_str(&format!(
            "{:>3}  {:<26} {:>4} {:>4} {:>4} {:>4} {:>4} {:>5} {:>5} {:>+5}\n",
            i + 1,
            truncate(&r.team, 26),
            r.points(),
            r.played,
            r.wins,
            r.draws,
            r.losses,
            r.goals_for,
            r.goals_against,
            r.goal_diff(),
        ));
    }
    if let Some(champion) = rows.first() {
        out.push_str(&format!("\nLeader / champion: {}\n", champion.team));
    }
    out
}

fn tool_competition_stats(db: &Database, args: &Value) -> String {
    // Resolve the competition query to its canonical name so the report label
    // reads "Brasileirão Série A" rather than the user's loose spelling.
    let competition = arg_str(args, "competition")
        .map(|q| queries::resolve_competition(db, &q).unwrap_or(q));
    let season = arg_int(args, "season").map(|n| n as i32);

    let stats = queries::competition_stats(db, competition.as_deref(), season);
    if stats.matches == 0 {
        return "No matches found for the given scope.".to_string();
    }

    let mut out = format!("{} — Statistics\n", stats.label);
    out.push_str(&format!(
        "Matches: {} | Total goals: {} | Avg goals/match: {:.2}\n",
        stats.matches,
        stats.total_goals,
        stats.avg_goals(),
    ));
    out.push_str(&format!(
        "Home wins: {:.1}% | Draws: {:.1}% | Away wins: {:.1}%\n\n",
        stats.pct(stats.home_wins),
        stats.pct(stats.draws),
        stats.pct(stats.away_wins),
    ));

    out.push_str("Biggest victories:\n");
    for (i, m) in stats.biggest_wins.iter().take(5).enumerate() {
        out.push_str(&format!(
            "{:>2}. {} | {} | {} (margin {})\n",
            i + 1,
            m.date_str(),
            m.competition,
            m.score_line(),
            m.margin(),
        ));
    }

    out.push_str("\nTop scoring teams:\n");
    for (i, (team, goals)) in stats.top_scoring_teams.iter().take(5).enumerate() {
        out.push_str(&format!("{:>2}. {} — {} goals\n", i + 1, team, goals));
    }
    out
}

fn tool_list_competitions(db: &Database) -> String {
    let comps = queries::list_competitions(db);
    if comps.is_empty() {
        return "No competition data is loaded.".to_string();
    }
    let mut out = String::from("Competitions in the loaded data:\n\n");
    for c in &comps {
        out.push_str(&format!(
            "- {} — {} matches, seasons {}-{}\n",
            c.name, c.matches, c.first_season, c.last_season
        ));
    }
    out.push_str(&format!(
        "\nTotal players in FIFA database: {}\n",
        db.players.len()
    ));
    out
}

/// Truncate a string to `max` characters, appending an ellipsis if cut.
fn truncate(s: &str, max: usize) -> String {
    if s.chars().count() <= max {
        s.to_string()
    } else {
        let kept: String = s.chars().take(max.saturating_sub(1)).collect();
        format!("{kept}…")
    }
}
