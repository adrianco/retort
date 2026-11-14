//! MCP (Model Context Protocol) server: JSON-RPC 2.0 over stdio, newline-delimited.
use crate::data::{Competition, Db};
use crate::normalize::parse_date;
use crate::queries::{Filter, PlayerQuery, Venue};
use serde_json::{json, Map, Value};
use std::io::{BufRead, Write};

const PROTOCOL_VERSIONS: &[&str] = &["2025-06-18", "2025-03-26", "2024-11-05"];

fn tool(name: &str, desc: &str, props: &[(&str, &str, &str)], required: &[&str]) -> Value {
    let mut p = Map::new();
    for (n, ty, d) in props {
        p.insert(n.to_string(), json!({"type": ty, "description": d}));
    }
    json!({
        "name": name,
        "description": desc,
        "inputSchema": {"type": "object", "properties": p, "required": required}
    })
}

const TEAM: (&str, &str, &str) = ("team", "string", "Team name; any variation works (e.g. 'Flamengo', 'Flamengo-RJ', 'São Paulo FC')");
const COMP: (&str, &str, &str) = ("competition", "string", "One of: 'Brasileirão' (Série A), 'Série B', 'Série C', 'Copa do Brasil', 'Libertadores'. Omit for all");
const SEASON: (&str, &str, &str) = ("season", "integer", "Season year, e.g. 2019");
const VENUE: (&str, &str, &str) = ("venue", "string", "'home', 'away' or 'either' (default)");
const FROM: (&str, &str, &str) = ("date_from", "string", "Earliest date, YYYY-MM-DD or DD/MM/YYYY");
const TO: (&str, &str, &str) = ("date_to", "string", "Latest date, YYYY-MM-DD or DD/MM/YYYY");
const LIMIT: (&str, &str, &str) = ("limit", "integer", "Maximum rows to list (default 20)");

pub fn tool_definitions() -> Vec<Value> {
    vec![
        tool("search_matches", "Find matches by team, opponent, venue, competition, season, stage/round and date range. Results are newest first, so limit=1 answers 'when did X last play Y'. With both team and opponent a head-to-head summary is appended.",
            &[TEAM, ("opponent", "string", "Opposing team name"), VENUE, COMP, SEASON, ("stage", "string", "Stage or round: 'final', 'semifinals', 'quarterfinals', 'round of 16', 'group stage', or a round number"), FROM, TO, LIMIT], &[]),
        tool("head_to_head", "Compare two teams head-to-head: wins, draws, goals, home/away split and recent meetings.",
            &[("team_a", "string", "First team"), ("team_b", "string", "Second team"), COMP, SEASON, FROM, TO, LIMIT], &["team_a", "team_b"]),
        tool("team_stats", "Win/draw/loss record, goals for/against and win rate for a team, optionally restricted by season, competition and venue; includes home/away and per-competition breakdowns.",
            &[TEAM, SEASON, COMP, VENUE, FROM, TO], &["team"]),
        tool("team_profile", "Cross-dataset profile of a club: overall match record, competitions played, derbies, latest match and its FIFA squad.",
            &[TEAM], &["team"]),
        tool("team_competitions", "List the competitions (and seasons) a team appears in, with its record in each.",
            &[TEAM], &["team"]),
        tool("standings", "League table for a season calculated from match results (champion and relegation zone flagged). Default competition: Brasileirão Série A.",
            &[SEASON, COMP], &["season"]),
        tool("competition_bracket", "Round-by-round results of a competition season (e.g. Copa Libertadores or Copa do Brasil knockout bracket, including the final).",
            &[COMP, SEASON], &["competition", "season"]),
        tool("league_stats", "Aggregate statistics: matches, goals, average goals per match, home win/draw/away win rates, highest-scoring match, corners and shots where available.",
            &[COMP, SEASON, TEAM, FROM, TO], &[]),
        tool("biggest_wins", "Largest victories by goal margin, optionally filtered by competition, season or team.",
            &[COMP, SEASON, TEAM, FROM, TO, LIMIT], &[]),
        tool("rank_teams", "Rank teams by a metric (best home record, best away record, most goals scored, ...).",
            &[("metric", "string", "win_rate (default), points, points_per_match, goals_for, goals_against, goal_diff or wins"), VENUE, COMP, SEASON, ("min_matches", "integer", "Minimum matches to qualify (default 10)"), FROM, TO, LIMIT], &[]),
        tool("compare_seasons", "Compare two seasons of a competition: goals per match, result distribution, table leader, top-scoring team.",
            &[("season_a", "integer", "First season"), ("season_b", "integer", "Second season"), COMP], &["season_a", "season_b"]),
        tool("find_derbies", "List matches between traditional rivals (Fla-Flu, Derby Paulista, Gre-Nal, ...), optionally by season, competition or team.",
            &[SEASON, COMP, TEAM, FROM, TO, LIMIT], &[]),
        tool("search_players", "Search the FIFA player database by name, nationality, club and position; sorted by overall rating.",
            &[("name", "string", "Player name or part of it"), ("nationality", "string", "Country, e.g. 'Brazil'"), ("club", "string", "Club name, e.g. 'Santos'"), ("position", "string", "FIFA code (ST, GK, CDM...) or group: forwards, midfielders, defenders, goalkeepers"), ("min_overall", "integer", "Minimum overall rating"), ("max_age", "integer", "Maximum age"), LIMIT], &[]),
        tool("player_details", "Full profile of one player (ratings, physical attributes, skills, club) by name or FIFA ID.",
            &[("player", "string", "Player name or numeric FIFA ID")], &["player"]),
        tool("players_by_club", "Count players per club with average rating, optionally for one nationality and/or only clubs that appear in the Brazilian match data.",
            &[("nationality", "string", "Country, e.g. 'Brazil'"), ("brazilian_clubs_only", "boolean", "Only clubs present in the Brazilian competitions data"), LIMIT], &[]),
        tool("data_summary", "Overview of the loaded datasets: files, row counts, competitions, season ranges.", &[], &[]),
    ]
}

fn s<'a>(a: &'a Value, k: &str) -> Option<&'a str> {
    a.get(k).and_then(Value::as_str).map(str::trim).filter(|v| !v.is_empty())
}

fn int(a: &Value, k: &str) -> Result<Option<i64>, String> {
    match a.get(k) {
        None | Some(Value::Null) => Ok(None),
        Some(Value::Number(n)) => n.as_i64().or_else(|| n.as_f64().map(|f| f as i64)).map(Some).ok_or_else(|| format!("'{k}' must be an integer")),
        Some(Value::String(t)) if t.trim().is_empty() => Ok(None),
        Some(Value::String(t)) => t.trim().parse().map(Some).map_err(|_| format!("'{k}' must be an integer")),
        _ => Err(format!("'{k}' must be an integer")),
    }
}

fn req<'a>(a: &'a Value, k: &str) -> Result<&'a str, String> {
    s(a, k).ok_or_else(|| format!("missing required argument '{k}'"))
}

fn limit(a: &Value, default: usize) -> Result<usize, String> {
    Ok(int(a, "limit")?.map_or(default, |n| n.clamp(1, 500) as usize))
}

fn competition(a: &Value) -> Result<Option<Competition>, String> {
    match s(a, "competition") {
        None => Ok(None),
        Some(c) if matches!(c.to_lowercase().as_str(), "all" | "any") => Ok(None),
        Some(c) => Competition::parse(c).map(Some).ok_or_else(|| {
            format!("unknown competition '{c}' (use Brasileirão, Série B, Série C, Copa do Brasil or Libertadores)")
        }),
    }
}

fn date(a: &Value, k: &str) -> Result<Option<String>, String> {
    match s(a, k) {
        None => Ok(None),
        Some(d) => parse_date(d).map(Some).ok_or_else(|| format!("'{k}': cannot parse date '{d}'")),
    }
}

fn filter(db: &Db, a: &Value, team_key: &str, opp_key: &str) -> Result<Filter, String> {
    Ok(Filter {
        team: s(a, team_key).map(|t| db.resolve_team(t)).transpose()?,
        opponent: s(a, opp_key).map(|t| db.resolve_team(t)).transpose()?,
        venue: s(a, "venue").map(Venue::parse).transpose()?.unwrap_or_default(),
        competition: competition(a)?,
        season: int(a, "season")?.map(|v| v as i32),
        date_from: date(a, "date_from")?,
        date_to: date(a, "date_to")?,
        stage: s(a, "stage").map(String::from),
    })
}

/// Execute a tool by name. Returns the text answer or an error message.
pub fn call_tool(db: &Db, name: &str, a: &Value) -> Result<String, String> {
    let need_season = |k: &str| -> Result<i32, String> {
        int(a, k)?.map(|v| v as i32).ok_or_else(|| format!("missing required argument '{k}'"))
    };
    match name {
        "search_matches" => Ok(db.search_matches_text(&filter(db, a, "team", "opponent")?, limit(a, 20)?)),
        "head_to_head" => {
            req(a, "team_a")?;
            req(a, "team_b")?;
            db.head_to_head_text(&filter(db, a, "team_a", "team_b")?, limit(a, 10)?)
        }
        "team_stats" => {
            req(a, "team")?;
            db.team_stats_text(&filter(db, a, "team", "")?)
        }
        "team_profile" => db.team_profile_text(req(a, "team")?),
        "team_competitions" => Ok(db.team_competitions_text(&db.resolve_team(req(a, "team")?)?)),
        "standings" => Ok(db.standings_text(competition(a)?.unwrap_or(Competition::SerieA), need_season("season")?)),
        "competition_bracket" => {
            let c = competition(a)?.ok_or("missing required argument 'competition'")?;
            Ok(db.bracket_text(c, need_season("season")?))
        }
        "league_stats" => Ok(db.league_stats_text(&filter(db, a, "team", "")?)),
        "biggest_wins" => Ok(db.biggest_wins_text(&filter(db, a, "team", "")?, limit(a, 10)?)),
        "rank_teams" => {
            let f = filter(db, a, "", "")?;
            let min = int(a, "min_matches")?.map_or(10, |v| v.max(1) as u32);
            db.rank_teams_text(&f, s(a, "metric").unwrap_or("win_rate"), min, limit(a, 10)?)
        }
        "compare_seasons" => Ok(db.compare_seasons_text(
            competition(a)?.unwrap_or(Competition::SerieA),
            need_season("season_a")?,
            need_season("season_b")?,
        )),
        "find_derbies" => Ok(db.derbies_text(&filter(db, a, "team", "")?, limit(a, 30)?)),
        "search_players" => {
            let q = PlayerQuery {
                name: s(a, "name").map(String::from),
                nationality: s(a, "nationality").map(String::from),
                club: s(a, "club").map(String::from),
                position: s(a, "position").map(String::from),
                min_overall: int(a, "min_overall")?.map(|v| v.max(0) as u32),
                max_age: int(a, "max_age")?.map(|v| v.max(0) as u32),
            };
            Ok(db.search_players_text(&q, limit(a, 20)?))
        }
        "player_details" => Ok(db.player_details_text(req(a, "player")?)),
        "players_by_club" => Ok(db.players_by_club_text(
            s(a, "nationality"),
            a.get("brazilian_clubs_only").and_then(Value::as_bool).unwrap_or(false),
            limit(a, 20)?,
        )),
        "data_summary" => Ok(db.summary_text()),
        o => Err(format!("unknown tool '{o}'")),
    }
}

fn error(id: Value, code: i64, msg: &str) -> Value {
    json!({"jsonrpc": "2.0", "id": id, "error": {"code": code, "message": msg}})
}

/// Handle one JSON-RPC message; returns the response (None for notifications).
pub fn handle_message(db: &Db, line: &str) -> Option<String> {
    let msg: Value = match serde_json::from_str(line) {
        Ok(v) => v,
        Err(e) => return Some(error(Value::Null, -32700, &format!("parse error: {e}")).to_string()),
    };
    let Some(method) = msg.get("method").and_then(Value::as_str) else {
        // A response from the client, or garbage.
        return match msg.get("id") {
            Some(id) if msg.get("result").is_none() && msg.get("error").is_none() => {
                Some(error(id.clone(), -32600, "invalid request").to_string())
            }
            _ => None,
        };
    };
    let id = msg.get("id").filter(|i| !i.is_null()).cloned()?; // notifications get no reply
    let params = msg.get("params").cloned().unwrap_or(json!({}));
    let result = match method {
        "initialize" => {
            let asked = params.get("protocolVersion").and_then(Value::as_str).unwrap_or("");
            let version = if PROTOCOL_VERSIONS.contains(&asked) { asked } else { PROTOCOL_VERSIONS[0] };
            json!({
                "protocolVersion": version,
                "capabilities": {"tools": {"listChanged": false}},
                "serverInfo": {"name": "brazilian-soccer-mcp", "version": env!("CARGO_PKG_VERSION")},
                "instructions": "Knowledge base of Brazilian soccer: Brasileirão (2003-2023), Copa do Brasil, Copa Libertadores matches and FIFA player data. Team names are normalised, so any spelling variation works. All answers are computed from the bundled Kaggle datasets."
            })
        }
        "ping" => json!({}),
        "tools/list" => json!({"tools": tool_definitions()}),
        "tools/call" => {
            let Some(name) = params.get("name").and_then(Value::as_str) else {
                return Some(error(id, -32602, "missing tool name").to_string());
            };
            if !tool_definitions().iter().any(|t| t["name"] == name) {
                return Some(error(id, -32602, &format!("unknown tool: {name}")).to_string());
            }
            let args = params.get("arguments").cloned().unwrap_or(json!({}));
            match call_tool(db, name, &args) {
                Ok(text) => json!({"content": [{"type": "text", "text": text}], "isError": false}),
                Err(e) => json!({"content": [{"type": "text", "text": format!("Error: {e}")}], "isError": true}),
            }
        }
        "resources/list" => json!({"resources": []}),
        "prompts/list" => json!({"prompts": []}),
        _ => return Some(error(id, -32601, &format!("method not found: {method}")).to_string()),
    };
    Some(json!({"jsonrpc": "2.0", "id": id, "result": result}).to_string())
}

/// Serve newline-delimited JSON-RPC until EOF.
pub fn serve<R: BufRead, W: Write>(db: &Db, input: R, mut output: W) -> std::io::Result<()> {
    for line in input.lines() {
        let line = line?;
        if line.trim().is_empty() {
            continue;
        }
        if let Some(resp) = handle_message(db, &line) {
            writeln!(output, "{resp}")?;
            output.flush()?;
        }
    }
    Ok(())
}
