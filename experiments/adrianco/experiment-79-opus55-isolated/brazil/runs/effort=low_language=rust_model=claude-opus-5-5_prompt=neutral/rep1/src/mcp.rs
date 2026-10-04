//! Minimal Model Context Protocol server: JSON-RPC 2.0, newline-delimited, over stdio.

use crate::data::{Competition, Database, Source};
use crate::queries::{MatchFilter, PlayerFilter, Venue};
use serde_json::{json, Map, Value};
use std::io::{BufRead, Write};

const PROTOCOL_VERSION: &str = "2024-11-05";
const DEFAULT_LIMIT: usize = 20;
const MAX_LIMIT: usize = 500;

/// (name, json type, description)
type Param = (&'static str, &'static str, &'static str);

const TEAM: Param = ("team", "string", "Team name; any spelling works (Flamengo, Flamengo-RJ, Atletico Mineiro, São Paulo)");
const OPPONENT: Param = ("opponent", "string", "Restrict to matches against this team");
const VENUE: Param = ("venue", "string", "home, away or either (default either), from the point of view of `team`");
const COMPETITION: Param = ("competition", "string", "Brasileirão / Serie A, Serie B, Serie C, Copa do Brasil or Libertadores");
const SEASON: Param = ("season", "integer", "Season year, e.g. 2019");
const DATE_FROM: Param = ("date_from", "string", "Earliest match date (YYYY-MM-DD or DD/MM/YYYY)");
const DATE_TO: Param = ("date_to", "string", "Latest match date (YYYY-MM-DD or DD/MM/YYYY)");
const STAGE: Param = ("stage", "string", "Stage (final, semifinals, quarterfinals, round of 16, group stage) or round number");
const SOURCE: Param = ("source", "string", "Query one CSV file only: brasileirao, cup, libertadores, br-football (has corners/shots/attacks), novo");
const LIMIT: Param = ("limit", "integer", "Maximum rows to list (default 20)");

struct Tool {
    name: &'static str,
    description: &'static str,
    params: &'static [Param],
    required: &'static [&'static str],
}

const TOOLS: &[Tool] = &[
    Tool {
        name: "search_matches",
        description: "Find matches by team, opponent, venue, competition, season, date range or stage. Most recent first. Answers 'What matches did Palmeiras play in 2023?', 'When did Flamengo last play Corinthians?', 'Find all Copa do Brasil finals' (competition=Copa do Brasil, stage=final).",
        params: &[TEAM, OPPONENT, VENUE, COMPETITION, SEASON, DATE_FROM, DATE_TO, STAGE, SOURCE, LIMIT],
        required: &[],
    },
    Tool {
        name: "head_to_head",
        description: "Head-to-head record and match list between two teams, e.g. Flamengo vs Fluminense or Palmeiras vs Santos.",
        params: &[("team_a", "string", "First team"), ("team_b", "string", "Second team"), COMPETITION, SEASON, LIMIT],
        required: &["team_a", "team_b"],
    },
    Tool {
        name: "team_stats",
        description: "Win/draw/loss record, goals for/against and win rate for a team, optionally filtered by season, competition, venue or dates, with a per-competition breakdown. Answers 'What is Corinthians' home record in 2022?'.",
        params: &[TEAM, VENUE, COMPETITION, SEASON, DATE_FROM, DATE_TO, SOURCE],
        required: &["team"],
    },
    Tool {
        name: "team_profile",
        description: "Cross-dataset profile of a team: competitions played with records, most recent result, and its players in the FIFA dataset.",
        params: &[TEAM],
        required: &["team"],
    },
    Tool {
        name: "standings",
        description: "League table for a Serie A/B/C season calculated from match results, with champion and relegated teams. Answers 'Who won the 2019 Brasileirão?' and 'Which teams were relegated in 2020?'.",
        params: &[COMPETITION, SEASON],
        required: &["season"],
    },
    Tool {
        name: "competition_summary",
        description: "Season summary for any competition: totals, champion, and for cups the bracket of knockout results by stage. Answers 'Show the 2018 Copa Libertadores bracket'.",
        params: &[COMPETITION, SEASON],
        required: &["competition", "season"],
    },
    Tool {
        name: "league_stats",
        description: "Aggregate statistics: goals per match, home/draw/away rates, highest scoring match. All filters optional.",
        params: &[COMPETITION, SEASON, TEAM, DATE_FROM, DATE_TO, SOURCE],
        required: &[],
    },
    Tool {
        name: "biggest_wins",
        description: "Largest winning margins, optionally filtered by competition, season or team.",
        params: &[COMPETITION, SEASON, TEAM, SOURCE, LIMIT],
        required: &[],
    },
    Tool {
        name: "team_rankings",
        description: "Rank teams by a metric. Answers 'Which team has the best home/away record?' (metric=win_rate, venue=home/away) and 'Which team scored the most goals in Serie A 2023?' (metric=goals_for).",
        params: &[
            ("metric", "string", "win_rate (default), points, points_per_game, goals_for, goals_against, goal_difference, wins"),
            VENUE, COMPETITION, SEASON,
            ("min_matches", "integer", "Minimum matches to qualify (default 5 with a season, otherwise 30)"),
            LIMIT,
        ],
        required: &[],
    },
    Tool {
        name: "compare_seasons",
        description: "Compare aggregate statistics and champions of two seasons of a competition.",
        params: &[COMPETITION, ("season_a", "integer", "First season"), ("season_b", "integer", "Second season")],
        required: &["season_a", "season_b"],
    },
    Tool {
        name: "derbies",
        description: "Matches between traditional rivals (Fla-Flu, Gre-Nal, Derby Paulista...), optionally by season, competition or team.",
        params: &[SEASON, COMPETITION, TEAM, LIMIT],
        required: &[],
    },
    Tool {
        name: "search_players",
        description: "Search the FIFA player database by name, nationality, club and position, sorted by overall rating. Answers 'Who are the top Brazilian players?', 'Which players play for Grêmio?', 'Show me all forwards from Santos'.",
        params: &[
            ("name", "string", "Player name or part of it"),
            ("nationality", "string", "Country, e.g. Brazil"),
            ("club", "string", "Club name or part of it"),
            ("position", "string", "Position code (ST, GK, CAM...) or group: forward, midfielder, defender, goalkeeper"),
            ("min_overall", "integer", "Minimum overall rating"),
            LIMIT,
        ],
        required: &[],
    },
    Tool {
        name: "player_details",
        description: "Full profile of one player: age, club, position, ratings, physical attributes and key skills. Answers 'Who is Gabriel Barbosa?'.",
        params: &[("name", "string", "Player name"), ("club", "string", "Club, to disambiguate")],
        required: &["name"],
    },
    Tool {
        name: "brazilian_clubs_players",
        description: "Player count and average rating per Brazilian club in the FIFA dataset, optionally restricted to a nationality.",
        params: &[("nationality", "string", "e.g. Brazil")],
        required: &[],
    },
    Tool {
        name: "list_teams",
        description: "List team names known to the match data, optionally filtered by a substring.",
        params: &[("query", "string", "Substring of the team name"), LIMIT],
        required: &[],
    },
    Tool {
        name: "dataset_info",
        description: "Describe the loaded datasets: files, row counts, competitions and seasons covered.",
        params: &[],
        required: &[],
    },
];

pub fn tool_definitions() -> Value {
    let tools: Vec<Value> = TOOLS
        .iter()
        .map(|t| {
            let props: Map<String, Value> = t
                .params
                .iter()
                .map(|(n, ty, d)| (n.to_string(), json!({"type": ty, "description": d})))
                .collect();
            json!({
                "name": t.name,
                "description": t.description,
                "inputSchema": {"type": "object", "properties": props, "required": t.required}
            })
        })
        .collect();
    json!(tools)
}

struct Args<'a>(&'a Value);

impl Args<'_> {
    fn str(&self, key: &str) -> Option<String> {
        match self.0.get(key)? {
            Value::String(s) if !s.trim().is_empty() => Some(s.trim().to_string()),
            Value::Number(n) => Some(n.to_string()),
            _ => None,
        }
    }
    fn req(&self, key: &str) -> Result<String, String> {
        self.str(key).ok_or_else(|| format!("Missing required argument '{key}'."))
    }
    fn int(&self, key: &str) -> Result<Option<u64>, String> {
        match self.0.get(key) {
            None | Some(Value::Null) => Ok(None),
            Some(Value::String(s)) if s.trim().is_empty() => Ok(None),
            Some(v) => v
                .as_u64()
                .or_else(|| v.as_f64().filter(|f| *f >= 0.0 && f.fract() == 0.0).map(|f| f as u64))
                .or_else(|| v.as_str().and_then(|s| s.trim().parse().ok()))
                .map(Some)
                .ok_or_else(|| format!("Argument '{key}' must be a non-negative integer.")),
        }
    }
    fn season(&self, key: &str) -> Result<Option<u16>, String> {
        self.int(key)?
            .map(|v| u16::try_from(v).map_err(|_| format!("Argument '{key}' is not a valid year.")))
            .transpose()
    }
    fn limit(&self) -> Result<usize, String> {
        Ok(self.int("limit")?.map_or(DEFAULT_LIMIT, |v| (v as usize).clamp(1, MAX_LIMIT)))
    }
    fn competition(&self) -> Result<Option<Competition>, String> {
        self.str("competition").map(|c| Competition::parse(&c)).transpose()
    }
    fn filter(&self) -> Result<MatchFilter, String> {
        Ok(MatchFilter {
            team: self.str("team"),
            opponent: self.str("opponent"),
            venue: self.str("venue").map(|v| Venue::parse(&v)).transpose()?.unwrap_or_default(),
            competition: self.competition()?,
            season: self.season("season")?,
            date_from: self.str("date_from"),
            date_to: self.str("date_to"),
            stage: self.str("stage"),
            source: self.str("source").map(|s| Source::parse(&s)).transpose()?,
        })
    }
}

/// Execute a tool by name. `Err` carries a message suitable for the LLM.
pub fn call_tool(db: &Database, name: &str, args: &Value) -> Result<String, String> {
    let a = Args(args);
    let need_season = |k: &str| a.season(k)?.ok_or_else(|| format!("Missing required argument '{k}'."));
    match name {
        "search_matches" => db.search_matches(&a.filter()?, a.limit()?),
        "head_to_head" => db.head_to_head(&a.req("team_a")?, &a.req("team_b")?, a.competition()?, a.season("season")?, a.limit()?),
        "team_stats" => db.team_stats(&a.req("team")?, &a.filter()?),
        "team_profile" => db.team_profile(&a.req("team")?),
        "standings" => db.standings(a.competition()?.unwrap_or(Competition::SerieA), need_season("season")?),
        "competition_summary" => db.competition_summary(
            a.competition()?.ok_or("Missing required argument 'competition'.")?,
            need_season("season")?,
        ),
        "league_stats" => db.league_stats(&a.filter()?),
        "biggest_wins" => db.biggest_wins(&a.filter()?, a.limit()?),
        "team_rankings" => db.team_rankings(
            &a.str("metric").unwrap_or_default(),
            &a.filter()?,
            a.int("min_matches")?.map(|v| v.min(u32::MAX as u64) as u32),
            a.limit()?,
        ),
        "compare_seasons" => db.compare_seasons(
            a.competition()?.unwrap_or(Competition::SerieA),
            need_season("season_a")?,
            need_season("season_b")?,
        ),
        "derbies" => db.derbies(&a.filter()?, a.limit()?),
        "search_players" => db.search_players(
            &PlayerFilter {
                name: a.str("name"),
                nationality: a.str("nationality"),
                club: a.str("club"),
                position: a.str("position"),
                min_overall: a.int("min_overall")?.map(|v| v.min(u32::MAX as u64) as u32),
            },
            a.limit()?,
        ),
        "player_details" => db.player_details(&a.req("name")?, a.str("club").as_deref()),
        "brazilian_clubs_players" => db.brazilian_clubs_players(a.str("nationality").as_deref()),
        "list_teams" => db.list_teams(a.str("query").as_deref(), a.limit()?),
        "dataset_info" => db.dataset_info(),
        _ => Err(format!("Unknown tool '{name}'.")),
    }
}

fn error(id: Value, code: i64, message: &str) -> Value {
    json!({"jsonrpc": "2.0", "id": id, "error": {"code": code, "message": message}})
}

/// Handle one JSON-RPC message. Notifications yield `None`.
pub fn handle_message(db: &Database, msg: &Value) -> Option<Value> {
    let method = msg.get("method").and_then(Value::as_str);
    let id = match msg.get("id") {
        Some(id) if !id.is_null() => id.clone(),
        _ => {
            // Notification (or a response): nothing to answer unless it is malformed.
            return method.is_none().then(|| error(Value::Null, -32600, "Invalid Request"));
        }
    };
    let Some(method) = method else {
        return Some(error(id, -32600, "Invalid Request"));
    };
    let empty = json!({});
    let params = msg.get("params").unwrap_or(&empty);
    let result = match method {
        "initialize" => json!({
            "protocolVersion": params.get("protocolVersion").and_then(Value::as_str).unwrap_or(PROTOCOL_VERSION),
            "capabilities": {"tools": {"listChanged": false}},
            "serverInfo": {"name": "brazilian-soccer-mcp", "version": env!("CARGO_PKG_VERSION")},
            "instructions": "Knowledge base of Brazilian soccer: Brasileirão, Copa do Brasil and Libertadores matches plus FIFA player data. Call dataset_info for coverage."
        }),
        "ping" => json!({}),
        "tools/list" => json!({"tools": tool_definitions()}),
        "tools/call" => {
            let Some(name) = params.get("name").and_then(Value::as_str) else {
                return Some(error(id, -32602, "Missing tool name"));
            };
            if !TOOLS.iter().any(|t| t.name == name) {
                return Some(error(id, -32602, &format!("Unknown tool: {name}")));
            }
            let args = params.get("arguments").filter(|a| a.is_object()).unwrap_or(&empty);
            let (text, is_error) = match call_tool(db, name, args) {
                Ok(t) => (t, false),
                Err(e) => (e, true),
            };
            json!({"content": [{"type": "text", "text": text}], "isError": is_error})
        }
        _ => return Some(error(id, -32601, &format!("Method not found: {method}"))),
    };
    Some(json!({"jsonrpc": "2.0", "id": id, "result": result}))
}

/// Serve newline-delimited JSON-RPC until EOF.
pub fn serve<R: BufRead, W: Write>(db: &Database, input: R, mut output: W) -> std::io::Result<()> {
    for line in input.lines() {
        let line = line?;
        if line.trim().is_empty() {
            continue;
        }
        let response = match serde_json::from_str::<Value>(&line) {
            Ok(msg) => handle_message(db, &msg),
            Err(_) => Some(error(Value::Null, -32700, "Parse error")),
        };
        if let Some(r) = response {
            writeln!(output, "{r}")?;
            output.flush()?;
        }
    }
    Ok(())
}
