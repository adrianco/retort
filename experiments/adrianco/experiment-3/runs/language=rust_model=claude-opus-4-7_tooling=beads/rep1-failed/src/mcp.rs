//! JSON-RPC 2.0 / MCP protocol server.
//!
//! Context: implements the Model Context Protocol over the stdio transport
//! (newline-delimited JSON-RPC messages). It advertises eight query tools
//! covering all five capability categories from `TASK.md` — matches, teams,
//! players, competitions and statistics — and dispatches `tools/call`
//! requests to the query modules. All protocol output goes to stdout; the
//! caller keeps stderr free for diagnostics.

use std::io::{self, BufRead, Write};

use serde_json::{json, Value};

use crate::competitions;
use crate::data::Database;
use crate::matches::{self, canonical_competition, MatchFilter};
use crate::players::{self, PlayerFilter};
use crate::stats;
use crate::teams::{self, Venue};

/// Human-readable list of the competitions this server understands.
const COMPETITION_HINT: &str =
    "known competitions: Brasileirão Série A/B/C, Copa do Brasil, Copa Libertadores";

const PROTOCOL_VERSION: &str = "2024-11-05";
const SERVER_NAME: &str = "brazilian-soccer-mcp";
const SERVER_VERSION: &str = "0.1.0";

/// Run the MCP server loop on stdin/stdout until end-of-input.
pub fn serve(db: &Database) -> io::Result<()> {
    let stdin = io::stdin();
    let stdout = io::stdout();
    let mut out = stdout.lock();

    for line in stdin.lock().lines() {
        let line = line?;
        if line.trim().is_empty() {
            continue;
        }
        let msg: Value = match serde_json::from_str(&line) {
            Ok(v) => v,
            Err(e) => {
                write_msg(
                    &mut out,
                    &error_response(Value::Null, -32700, &format!("parse error: {e}")),
                )?;
                continue;
            }
        };
        if let Some(response) = handle_message(db, &msg) {
            write_msg(&mut out, &response)?;
        }
    }
    Ok(())
}

/// Handle one decoded JSON-RPC message, returning a response when one is due.
///
/// Notifications (messages without an `id`) never produce a response.
pub fn handle_message(db: &Database, msg: &Value) -> Option<Value> {
    let method = msg.get("method")?.as_str()?;
    let id = msg.get("id").cloned();
    let params = msg.get("params").cloned().unwrap_or_else(|| json!({}));
    let is_notification = id.is_none();

    match method {
        "initialize" => Some(result_response(id?, initialize_result(&params))),
        "ping" => Some(result_response(id?, json!({}))),
        "tools/list" => Some(result_response(id?, json!({ "tools": tool_definitions() }))),
        "tools/call" => Some(result_response(id?, handle_tools_call(db, &params))),
        m if m.starts_with("notifications/") => None,
        _ => {
            if is_notification {
                None
            } else {
                Some(error_response(
                    id.unwrap_or(Value::Null),
                    -32601,
                    &format!("method not found: {method}"),
                ))
            }
        }
    }
}

fn initialize_result(params: &Value) -> Value {
    // Echo the client's protocol version when present for compatibility.
    let version = params
        .get("protocolVersion")
        .and_then(|v| v.as_str())
        .unwrap_or(PROTOCOL_VERSION);
    json!({
        "protocolVersion": version,
        "capabilities": { "tools": { "listChanged": false } },
        "serverInfo": { "name": SERVER_NAME, "version": SERVER_VERSION },
        "instructions": "Knowledge-graph server for Brazilian soccer. Tools cover \
matches, team records, head-to-head, FIFA players, league standings and \
aggregate statistics. Call tools/list for details."
    })
}

fn handle_tools_call(db: &Database, params: &Value) -> Value {
    let name = params.get("name").and_then(|v| v.as_str()).unwrap_or("");
    let args = params
        .get("arguments")
        .cloned()
        .unwrap_or_else(|| json!({}));
    match call_tool(db, name, &args) {
        Ok(text) => json!({
            "content": [ { "type": "text", "text": text } ],
            "isError": false
        }),
        Err(text) => json!({
            "content": [ { "type": "text", "text": format!("Error: {text}") } ],
            "isError": true
        }),
    }
}

/// Dispatch a single tool call. Exposed so tests can exercise tools directly.
pub fn call_tool(db: &Database, name: &str, args: &Value) -> Result<String, String> {
    match name {
        "find_matches" => tool_find_matches(db, args),
        "head_to_head" => tool_head_to_head(db, args),
        "team_record" => tool_team_record(db, args),
        "find_players" => tool_find_players(db, args),
        "competition_standings" => tool_competition_standings(db, args),
        "match_statistics" => tool_match_statistics(db, args),
        "team_rankings" => tool_team_rankings(db, args),
        "list_competitions" => tool_list_competitions(db, args),
        other => Err(format!("unknown tool: {other}")),
    }
}

// --- argument helpers -------------------------------------------------------

fn arg_str(args: &Value, key: &str) -> Option<String> {
    match args.get(key) {
        Some(Value::String(s)) if !s.trim().is_empty() => Some(s.trim().to_string()),
        Some(Value::Number(n)) => Some(n.to_string()),
        _ => None,
    }
}

fn arg_i32(args: &Value, key: &str) -> Option<i32> {
    match args.get(key) {
        Some(Value::Number(n)) => n.as_i64().map(|v| v as i32),
        Some(Value::String(s)) => s.trim().parse::<i32>().ok(),
        _ => None,
    }
}

fn arg_usize(args: &Value, key: &str, default: usize) -> usize {
    arg_i32(args, key)
        .filter(|&v| v > 0)
        .map(|v| v as usize)
        .unwrap_or(default)
}

fn arg_bool(args: &Value, key: &str, default: bool) -> bool {
    match args.get(key) {
        Some(Value::Bool(b)) => *b,
        Some(Value::String(s)) => s.eq_ignore_ascii_case("true"),
        _ => default,
    }
}

fn arg_venue(args: &Value) -> Venue {
    args.get("venue")
        .and_then(|v| v.as_str())
        .map(Venue::parse)
        .unwrap_or(Venue::All)
}

// --- tool implementations ---------------------------------------------------

fn tool_find_matches(db: &Database, args: &Value) -> Result<String, String> {
    let filter = MatchFilter {
        team: arg_str(args, "team"),
        opponent: arg_str(args, "opponent"),
        home_team: arg_str(args, "home_team"),
        away_team: arg_str(args, "away_team"),
        competition: arg_str(args, "competition"),
        season: arg_i32(args, "season"),
        date_from: arg_str(args, "date_from"),
        date_to: arg_str(args, "date_to"),
    };
    let empty = filter.team.is_none()
        && filter.opponent.is_none()
        && filter.home_team.is_none()
        && filter.away_team.is_none()
        && filter.competition.is_none()
        && filter.season.is_none()
        && filter.date_from.is_none()
        && filter.date_to.is_none();
    if empty {
        return Err("provide at least one search criterion (team, competition, season, ...)".into());
    }
    let limit = arg_usize(args, "limit", 25).min(200);
    let results = matches::find_matches(db, &filter);
    if results.is_empty() {
        return Ok("No matches found for the given criteria.".into());
    }
    Ok(format!(
        "Found {} match(es):\n{}",
        results.len(),
        matches::format_matches(&results, limit)
    ))
}

fn tool_head_to_head(db: &Database, args: &Value) -> Result<String, String> {
    let a = arg_str(args, "team_a").ok_or("team_a is required")?;
    let b = arg_str(args, "team_b").ok_or("team_b is required")?;
    let limit = arg_usize(args, "limit", 20).min(200);
    match teams::head_to_head(db, &a, &b) {
        Some(h) => Ok(teams::format_head_to_head(&h, limit)),
        None => Err(format!(
            "could not resolve one or both teams: '{a}' / '{b}'"
        )),
    }
}

fn tool_team_record(db: &Database, args: &Value) -> Result<String, String> {
    let team = arg_str(args, "team").ok_or("team is required")?;
    let season = arg_i32(args, "season");
    let competition = arg_str(args, "competition");
    let venue = arg_venue(args);
    match teams::team_stats(db, &team, season, competition.as_deref(), venue) {
        Some((display, rec)) => {
            if rec.played == 0 {
                Ok(format!(
                    "{display} has no matches in the dataset for the given filters."
                ))
            } else {
                Ok(teams::format_record(
                    &display,
                    &rec,
                    season,
                    competition.as_deref(),
                    venue,
                ))
            }
        }
        None => Err(format!("could not resolve team '{team}'")),
    }
}

fn tool_find_players(db: &Database, args: &Value) -> Result<String, String> {
    let filter = PlayerFilter {
        name: arg_str(args, "name"),
        nationality: arg_str(args, "nationality"),
        club: arg_str(args, "club"),
        position: arg_str(args, "position"),
        min_overall: arg_i32(args, "min_overall"),
    };
    let empty = filter.name.is_none()
        && filter.nationality.is_none()
        && filter.club.is_none()
        && filter.position.is_none()
        && filter.min_overall.is_none();
    if empty {
        return Err("provide at least one filter (name, nationality, club, position, min_overall)".into());
    }
    let limit = arg_usize(args, "limit", 20).min(200);
    let results = players::find_players(db, &filter);
    Ok(players::format_players(&results, limit))
}

fn tool_competition_standings(db: &Database, args: &Value) -> Result<String, String> {
    let competition = arg_str(args, "competition").ok_or("competition is required")?;
    let season = arg_i32(args, "season").ok_or("season is required")?;
    // Prefer the canonical competition label for display.
    let canonical = db
        .competitions()
        .into_iter()
        .find(|c| competition_matches(c, &competition))
        .unwrap_or_else(|| competition.clone());
    let rows = competitions::standings(db, &competition, season);
    Ok(competitions::format_standings(&rows, &canonical, season))
}

fn tool_match_statistics(db: &Database, args: &Value) -> Result<String, String> {
    let competition = arg_str(args, "competition");
    let season = arg_i32(args, "season");
    let aggregate = stats::aggregate(db, competition.as_deref(), season);
    let mut out = stats::format_aggregate(&aggregate, competition.as_deref(), season);
    if arg_bool(args, "include_biggest_wins", true) {
        let limit = arg_usize(args, "limit", 5).min(50);
        let wins = stats::biggest_wins(db, competition.as_deref(), season, limit);
        out.push_str("\n\n");
        out.push_str(&stats::format_biggest_wins(&wins));
    }
    Ok(out)
}

fn tool_team_rankings(db: &Database, args: &Value) -> Result<String, String> {
    let competition = arg_str(args, "competition");
    let season = arg_i32(args, "season");
    let venue = arg_venue(args);
    let min_played = arg_i32(args, "min_played").unwrap_or(5).max(1) as u32;
    let limit = arg_usize(args, "limit", 10).min(100);
    let ranked = stats::team_rankings(db, competition.as_deref(), season, venue, min_played);
    Ok(stats::format_rankings(&ranked, venue, limit))
}

fn tool_list_competitions(db: &Database, args: &Value) -> Result<String, String> {
    if let Some(team) = arg_str(args, "team") {
        let (key, display) = db
            .resolve_team(&team)
            .ok_or_else(|| format!("could not resolve team '{team}'"))?;
        let mut by_comp: std::collections::BTreeMap<String, (usize, i32, i32)> =
            std::collections::BTreeMap::new();
        for m in &db.matches {
            if m.home_key != key && m.away_key != key {
                continue;
            }
            let e = by_comp
                .entry(m.competition.clone())
                .or_insert((0, i32::MAX, i32::MIN));
            e.0 += 1;
            e.1 = e.1.min(m.season);
            e.2 = e.2.max(m.season);
        }
        if by_comp.is_empty() {
            return Ok(format!("{display} has no matches in the dataset."));
        }
        let mut out = format!("Competitions {display} appears in:\n");
        for (comp, (count, min_s, max_s)) in by_comp {
            out.push_str(&format!(
                "- {comp}: {count} match(es), seasons {min_s}-{max_s}\n"
            ));
        }
        Ok(out)
    } else {
        let mut out = String::from("Available competitions in the dataset:\n");
        for comp in db.competitions() {
            let seasons = db.seasons(Some(&comp));
            let count = db
                .matches
                .iter()
                .filter(|m| m.competition == comp)
                .count();
            let range = match (seasons.first(), seasons.last()) {
                (Some(a), Some(b)) => format!("{a}-{b}"),
                _ => "n/a".to_string(),
            };
            out.push_str(&format!(
                "- {comp}: {count} match(es), {} season(s) ({range})\n",
                seasons.len()
            ));
        }
        out.push_str(&format!(
            "\nTotal: {} matches, {} players loaded.",
            db.matches.len(),
            db.players.len()
        ));
        Ok(out)
    }
}

// --- tool schema definitions ------------------------------------------------

fn str_prop(desc: &str) -> Value {
    json!({ "type": "string", "description": desc })
}
fn int_prop(desc: &str) -> Value {
    json!({ "type": "integer", "description": desc })
}

fn tool(name: &str, description: &str, properties: Value, required: &[&str]) -> Value {
    json!({
        "name": name,
        "description": description,
        "inputSchema": {
            "type": "object",
            "properties": properties,
            "required": required,
        }
    })
}

/// The full list of MCP tools advertised by this server.
pub fn tool_definitions() -> Vec<Value> {
    vec![
        tool(
            "find_matches",
            "Find soccer matches by team, opponent, home/away side, competition, \
season or date range. Returns matches most-recent first.",
            json!({
                "team": str_prop("Club that played on either side"),
                "opponent": str_prop("Second club, to find fixtures between two teams"),
                "home_team": str_prop("Club that played specifically at home"),
                "away_team": str_prop("Club that played specifically away"),
                "competition": str_prop("Competition name, e.g. 'Brasileirao', 'Copa do Brasil', 'Libertadores'"),
                "season": int_prop("Season year, e.g. 2019"),
                "date_from": str_prop("Inclusive start date (YYYY-MM-DD)"),
                "date_to": str_prop("Inclusive end date (YYYY-MM-DD)"),
                "limit": int_prop("Maximum matches to list (default 25)"),
            }),
            &[],
        ),
        tool(
            "head_to_head",
            "Compute the head-to-head record between two clubs: win/draw counts, \
goals and the list of fixtures.",
            json!({
                "team_a": str_prop("First club"),
                "team_b": str_prop("Second club"),
                "limit": int_prop("Maximum fixtures to list (default 20)"),
            }),
            &["team_a", "team_b"],
        ),
        tool(
            "team_record",
            "Win/draw/loss record, goals and win rate for a club, optionally \
filtered by season, competition and venue (home/away/all).",
            json!({
                "team": str_prop("Club name"),
                "season": int_prop("Season year to restrict to"),
                "competition": str_prop("Competition to restrict to"),
                "venue": json!({
                    "type": "string",
                    "enum": ["home", "away", "all"],
                    "description": "Which fixtures to count (default all)"
                }),
            }),
            &["team"],
        ),
        tool(
            "find_players",
            "Search the FIFA player database by name, nationality, club, position \
(code such as 'ST' or category such as 'forward') and minimum overall rating.",
            json!({
                "name": str_prop("Full or partial player name"),
                "nationality": str_prop("Nationality, e.g. 'Brazil' or 'Brazilian'"),
                "club": str_prop("Club name"),
                "position": str_prop("FIFA position code or category (forward/midfielder/defender/goalkeeper)"),
                "min_overall": int_prop("Minimum FIFA overall rating"),
                "limit": int_prop("Maximum players to list (default 20)"),
            }),
            &[],
        ),
        tool(
            "competition_standings",
            "Compute the final league table for a competition and season from \
match results (3 points per win, 1 per draw).",
            json!({
                "competition": str_prop("Competition name, e.g. 'Brasileirao'"),
                "season": int_prop("Season year, e.g. 2019"),
            }),
            &["competition", "season"],
        ),
        tool(
            "match_statistics",
            "Aggregate statistics over a competition/season scope: average goals \
per match, home/away win rates and the biggest victories.",
            json!({
                "competition": str_prop("Competition to restrict to (optional)"),
                "season": int_prop("Season year to restrict to (optional)"),
                "include_biggest_wins": json!({
                    "type": "boolean",
                    "description": "Append the biggest-margin victories (default true)"
                }),
                "limit": int_prop("How many biggest wins to list (default 5)"),
            }),
            &[],
        ),
        tool(
            "team_rankings",
            "Rank teams by win rate over a competition/season scope, optionally \
restricted to home or away fixtures. Useful for 'best home/away record'.",
            json!({
                "competition": str_prop("Competition to restrict to (optional)"),
                "season": int_prop("Season year to restrict to (optional)"),
                "venue": json!({
                    "type": "string",
                    "enum": ["home", "away", "all"],
                    "description": "Which fixtures to count (default all)"
                }),
                "min_played": int_prop("Minimum matches played to be ranked (default 5)"),
                "limit": int_prop("How many teams to list (default 10)"),
            }),
            &[],
        ),
        tool(
            "list_competitions",
            "List the competitions and seasons available in the dataset; with a \
team argument, list the competitions that club appears in.",
            json!({
                "team": str_prop("Optional club name to scope the listing"),
            }),
            &[],
        ),
    ]
}

// --- JSON-RPC plumbing ------------------------------------------------------

fn result_response(id: Value, result: Value) -> Value {
    json!({ "jsonrpc": "2.0", "id": id, "result": result })
}

fn error_response(id: Value, code: i32, message: &str) -> Value {
    json!({ "jsonrpc": "2.0", "id": id, "error": { "code": code, "message": message } })
}

fn write_msg<W: Write>(w: &mut W, msg: &Value) -> io::Result<()> {
    let line = serde_json::to_string(msg).unwrap_or_else(|_| "{}".to_string());
    w.write_all(line.as_bytes())?;
    w.write_all(b"\n")?;
    w.flush()
}
