//! MCP tool surface: JSON schemas, argument parsing and dispatch.
//!
//! Each tool returns a [`ToolOutput`] carrying both a natural-language answer
//! (what an LLM reads back to the user) and a structured JSON payload (what a
//! program consumes). Argument errors and unresolvable club names come back as
//! `Err(String)` and are surfaced to the client as tool errors, never panics.

use serde_json::{json, Map, Value};

use crate::format;
use crate::graph::{KnowledgeGraph, NodeRef, Relation, Resolution};
use crate::model::{Competition, Date, Source};
use crate::queries::{self, MatchQuery, Metric, PlayerQuery, PlayerSort, Venue};

/// Text + structured content returned by a tool call.
pub struct ToolOutput {
    pub text: String,
    pub data: Value,
}

impl ToolOutput {
    fn new(text: impl Into<String>, data: Value) -> ToolOutput {
        ToolOutput {
            text: text.into(),
            data,
        }
    }
}

/// Static description of one tool, as advertised by `tools/list`.
pub struct ToolSpec {
    pub name: &'static str,
    pub description: &'static str,
    pub schema: fn() -> Value,
}

fn string_prop(description: &str) -> Value {
    json!({ "type": "string", "description": description })
}

fn integer_prop(description: &str) -> Value {
    json!({ "type": "integer", "description": description })
}

fn boolean_prop(description: &str) -> Value {
    json!({ "type": "boolean", "description": description })
}

fn schema(properties: Vec<(&str, Value)>, required: Vec<&str>) -> Value {
    let mut map = Map::new();
    for (name, value) in properties {
        map.insert(name.to_string(), value);
    }
    json!({
        "type": "object",
        "properties": Value::Object(map),
        "required": required,
        "additionalProperties": false,
    })
}

fn competition_prop() -> Value {
    json!({
        "type": "string",
        "description": "Competition name: 'Serie A'/'Brasileirão', 'Serie B', 'Serie C', 'Copa do Brasil' or 'Libertadores'",
    })
}

fn include_all_sources_prop() -> Value {
    boolean_prop(
        "Include rows from overlapping source files (default false). When false only the canonical file per competition/season is used, so fixtures are never double-counted.",
    )
}

/// Every tool exposed over MCP.
pub const TOOLS: &[ToolSpec] = &[
    ToolSpec {
        name: "search_matches",
        description: "Find matches by team, opponent, competition, season, date range or stage. Returns match lines plus a head-to-head tally when two teams are given.",
        schema: || schema(
            vec![
                ("team", string_prop("Club name; matches where this club played home or away")),
                ("opponent", string_prop("Second club, to restrict to meetings between the two")),
                ("home_team", string_prop("Club that must be the home side")),
                ("away_team", string_prop("Club that must be the away side")),
                ("competition", competition_prop()),
                ("season", integer_prop("Season year, e.g. 2019")),
                ("date_from", string_prop("Earliest match date, YYYY-MM-DD")),
                ("date_to", string_prop("Latest match date, YYYY-MM-DD")),
                ("stage", string_prop("Round or stage substring, e.g. 'final', 'group stage', '22'")),
                ("limit", integer_prop("Maximum matches to return (default 20, 0 = no limit)")),
                ("oldest_first", boolean_prop("Sort chronologically instead of most recent first")),
                ("include_all_sources", include_all_sources_prop()),
            ],
            vec![],
        ),
    },
    ToolSpec {
        name: "head_to_head",
        description: "Compare two clubs: matches played, wins each way, draws, goals, per-competition split and recent meetings.",
        schema: || schema(
            vec![
                ("team_a", string_prop("First club")),
                ("team_b", string_prop("Second club")),
                ("competition", competition_prop()),
                ("season", integer_prop("Restrict to a single season")),
                ("recent", integer_prop("How many recent meetings to list (default 5)")),
                ("include_all_sources", include_all_sources_prop()),
            ],
            vec!["team_a", "team_b"],
        ),
    },
    ToolSpec {
        name: "team_stats",
        description: "Wins, draws, losses, goals, points and win rate for a club, optionally restricted to a season, competition and home/away split.",
        schema: || schema(
            vec![
                ("team", string_prop("Club name")),
                ("season", integer_prop("Season year")),
                ("competition", competition_prop()),
                ("venue", string_prop("'home', 'away' or 'all' (default all)")),
                ("include_all_sources", include_all_sources_prop()),
            ],
            vec!["team"],
        ),
    },
    ToolSpec {
        name: "team_profile",
        description: "Which competitions and seasons a club appears in, its overall record, name variants and linked FIFA squad.",
        schema: || schema(
            vec![
                ("team", string_prop("Club name")),
                ("include_all_sources", include_all_sources_prop()),
            ],
            vec!["team"],
        ),
    },
    ToolSpec {
        name: "standings",
        description: "League table for a competition and season, calculated from match results (3 points per win), with champion and relegation when the season is complete.",
        schema: || schema(
            vec![
                ("competition", competition_prop()),
                ("season", integer_prop("Season year, e.g. 2019")),
                ("limit", integer_prop("Rows to return (default all)")),
                ("include_all_sources", include_all_sources_prop()),
            ],
            vec!["season"],
        ),
    },
    ToolSpec {
        name: "competition_stats",
        description: "Aggregate statistics for a competition: goals per match, home/draw/away split, per-season breakdown, highest scoring match. Pass two seasons to compare them.",
        schema: || schema(
            vec![
                ("competition", competition_prop()),
                ("season", integer_prop("Single season to summarise")),
                ("seasons", json!({
                    "type": "array",
                    "items": { "type": "integer" },
                    "description": "Seasons to include, e.g. [2018, 2019] to compare two seasons",
                })),
                ("include_all_sources", include_all_sources_prop()),
            ],
            vec![],
        ),
    },
    ToolSpec {
        name: "team_rankings",
        description: "Rank clubs by a metric (points, wins, win_rate, goals_for, goals_against, goal_difference, clean_sheets) with an optional home/away filter. Answers 'which team scored the most goals' or 'best away record'.",
        schema: || schema(
            vec![
                ("metric", string_prop("Ranking metric (default win_rate)")),
                ("competition", competition_prop()),
                ("season", integer_prop("Season year")),
                ("venue", string_prop("'home', 'away' or 'all' (default all)")),
                ("min_matches", integer_prop("Minimum matches for a club to be ranked (default 5)")),
                ("limit", integer_prop("Rows to return (default 10)")),
                ("include_all_sources", include_all_sources_prop()),
            ],
            vec![],
        ),
    },
    ToolSpec {
        name: "biggest_wins",
        description: "Largest winning margins in the data, optionally scoped to a competition, season or club.",
        schema: || schema(
            vec![
                ("competition", competition_prop()),
                ("season", integer_prop("Season year")),
                ("team", string_prop("Only wins by this club")),
                ("limit", integer_prop("Rows to return (default 10)")),
                ("include_all_sources", include_all_sources_prop()),
            ],
            vec![],
        ),
    },
    ToolSpec {
        name: "search_players",
        description: "Search the FIFA player database by name, nationality, club, position, rating and age.",
        schema: || schema(
            vec![
                ("name", string_prop("Player name or fragment")),
                ("nationality", string_prop("Nationality, e.g. 'Brazil'")),
                ("club", string_prop("Club name; Brazilian clubs are matched through the same aliases as match data")),
                ("position", string_prop("FIFA position code, e.g. ST, LW, GK, CB")),
                ("min_overall", integer_prop("Minimum FIFA overall rating")),
                ("min_age", integer_prop("Minimum age")),
                ("max_age", integer_prop("Maximum age")),
                ("brazilian_clubs_only", boolean_prop("Only players whose club also appears in the Brazilian match data")),
                ("sort_by", string_prop("'overall' (default), 'potential', 'age' or 'name'")),
                ("limit", integer_prop("Players to return (default 20)")),
            ],
            vec![],
        ),
    },
    ToolSpec {
        name: "player_profile",
        description: "Full profile of one player: ratings, attributes, club and whether that club appears in the Brazilian match data.",
        schema: || schema(
            vec![("name", string_prop("Player name"))],
            vec!["name"],
        ),
    },
    ToolSpec {
        name: "club_players",
        description: "Squad of a club in the FIFA database with average rating, plus the club's match-data footprint. Explains the gap when a club is not licensed in FIFA 19.",
        schema: || schema(
            vec![
                ("club", string_prop("Club name")),
                ("limit", integer_prop("Players to list (default 20)")),
            ],
            vec!["club"],
        ),
    },
    ToolSpec {
        name: "find_team",
        description: "Resolve a club name to its canonical entry in the knowledge graph, listing every spelling used across the datasets. Use when a name is ambiguous, e.g. 'Atlético'.",
        schema: || schema(
            vec![
                ("query", string_prop("Club name or fragment")),
                ("limit", integer_prop("Candidates to return (default 10)")),
            ],
            vec!["query"],
        ),
    },
    ToolSpec {
        name: "graph_neighbors",
        description: "Traverse the knowledge graph from a node (team, competition, player or match) and list its edges.",
        schema: || schema(
            vec![
                ("node_type", string_prop("'team', 'competition', 'player' or 'match'")),
                ("name", string_prop("Node name (team/competition/player) or numeric match id")),
                ("limit", integer_prop("Edges per relation (default 10)")),
            ],
            vec!["node_type", "name"],
        ),
    },
    ToolSpec {
        name: "dataset_overview",
        description: "What is loaded: source files, licenses, row counts, competitions, season coverage, graph size and known data caveats.",
        schema: || schema(vec![], vec![]),
    },
];

// ---- argument helpers -------------------------------------------------------

fn args_object(args: &Value) -> Result<&Map<String, Value>, String> {
    match args {
        Value::Object(map) => Ok(map),
        Value::Null => Err("missing arguments object".to_string()),
        _ => Err("arguments must be a JSON object".to_string()),
    }
}

fn opt_str(args: &Map<String, Value>, key: &str) -> Result<Option<String>, String> {
    match args.get(key) {
        None | Some(Value::Null) => Ok(None),
        Some(Value::String(value)) if value.trim().is_empty() => Ok(None),
        Some(Value::String(value)) => Ok(Some(value.trim().to_string())),
        Some(other) => Err(format!("'{key}' must be a string, got {other}")),
    }
}

fn req_str(args: &Map<String, Value>, key: &str) -> Result<String, String> {
    opt_str(args, key)?.ok_or_else(|| format!("'{key}' is required"))
}

fn opt_i64(args: &Map<String, Value>, key: &str) -> Result<Option<i64>, String> {
    match args.get(key) {
        None | Some(Value::Null) => Ok(None),
        Some(Value::Number(number)) => number
            .as_i64()
            .map(Some)
            .ok_or_else(|| format!("'{key}' must be an integer")),
        Some(Value::String(value)) => value
            .trim()
            .parse::<i64>()
            .map(Some)
            .map_err(|_| format!("'{key}' must be an integer, got '{value}'")),
        Some(other) => Err(format!("'{key}' must be an integer, got {other}")),
    }
}

fn opt_bool(args: &Map<String, Value>, key: &str) -> Result<Option<bool>, String> {
    match args.get(key) {
        None | Some(Value::Null) => Ok(None),
        Some(Value::Bool(value)) => Ok(Some(*value)),
        Some(other) => Err(format!("'{key}' must be a boolean, got {other}")),
    }
}

fn limit_of(args: &Map<String, Value>, default: usize) -> Result<usize, String> {
    Ok(opt_i64(args, "limit")?
        .map(|value| value.max(0) as usize)
        .unwrap_or(default))
}

fn include_all(args: &Map<String, Value>) -> Result<bool, String> {
    Ok(opt_bool(args, "include_all_sources")?.unwrap_or(false))
}

fn opt_competition(args: &Map<String, Value>, key: &str) -> Result<Option<Competition>, String> {
    match opt_str(args, key)? {
        None => Ok(None),
        Some(raw) => Competition::parse(&raw).map(Some).ok_or_else(|| {
            format!(
                "unknown competition '{raw}'. Known competitions: {}.",
                Competition::ALL
                    .iter()
                    .map(|c| c.name())
                    .collect::<Vec<_>>()
                    .join(", ")
            )
        }),
    }
}

fn opt_date(args: &Map<String, Value>, key: &str) -> Result<Option<Date>, String> {
    match opt_str(args, key)? {
        None => Ok(None),
        Some(raw) => Date::parse(&raw)
            .map(Some)
            .ok_or_else(|| format!("'{key}' must be a date such as 2023-09-24, got '{raw}'")),
    }
}

fn opt_venue(args: &Map<String, Value>) -> Result<Venue, String> {
    match opt_str(args, "venue")? {
        None => Ok(Venue::All),
        Some(raw) => Venue::parse(&raw)
            .ok_or_else(|| format!("'venue' must be 'home', 'away' or 'all', got '{raw}'")),
    }
}

fn resolve(graph: &KnowledgeGraph, name: &str) -> Result<usize, String> {
    graph.require_team(name)
}

// ---- dispatch ---------------------------------------------------------------

/// Runs a tool by name. `Err` carries a message meant for the model/user.
pub fn call(graph: &KnowledgeGraph, name: &str, args: &Value) -> Result<ToolOutput, String> {
    let empty = Map::new();
    let args = match args {
        Value::Null => &empty,
        other => args_object(other)?,
    };
    match name {
        "search_matches" => search_matches(graph, args),
        "head_to_head" => head_to_head(graph, args),
        "team_stats" => team_stats(graph, args),
        "team_profile" => team_profile(graph, args),
        "standings" => standings(graph, args),
        "competition_stats" => competition_stats(graph, args),
        "team_rankings" => team_rankings(graph, args),
        "biggest_wins" => biggest_wins(graph, args),
        "search_players" => search_players(graph, args),
        "player_profile" => player_profile(graph, args),
        "club_players" => club_players(graph, args),
        "find_team" => find_team(graph, args),
        "graph_neighbors" => graph_neighbors(graph, args),
        "dataset_overview" => dataset_overview(graph),
        other => Err(format!(
            "unknown tool '{other}'. Available tools: {}.",
            TOOLS
                .iter()
                .map(|tool| tool.name)
                .collect::<Vec<_>>()
                .join(", ")
        )),
    }
}

fn search_matches(graph: &KnowledgeGraph, args: &Map<String, Value>) -> Result<ToolOutput, String> {
    let mut query = MatchQuery::new();
    let mut described = Vec::new();

    if let Some(name) = opt_str(args, "team")? {
        let id = resolve(graph, &name)?;
        query.team = Some(id);
        described.push(graph.team(id).display());
    }
    if let Some(name) = opt_str(args, "opponent")? {
        let id = resolve(graph, &name)?;
        query.opponent = Some(id);
        described.push(format!("vs {}", graph.team(id).display()));
    }
    if let Some(name) = opt_str(args, "home_team")? {
        let id = resolve(graph, &name)?;
        query.home_team = Some(id);
        described.push(format!("home: {}", graph.team(id).display()));
    }
    if let Some(name) = opt_str(args, "away_team")? {
        let id = resolve(graph, &name)?;
        query.away_team = Some(id);
        described.push(format!("away: {}", graph.team(id).display()));
    }
    query.competition = opt_competition(args, "competition")?;
    if let Some(competition) = query.competition {
        described.push(competition.name().to_string());
    }
    query.season = opt_i64(args, "season")?.map(|value| value as i32);
    if let Some(season) = query.season {
        described.push(season.to_string());
    }
    query.date_from = opt_date(args, "date_from")?;
    query.date_to = opt_date(args, "date_to")?;
    if let Some(stage) = opt_str(args, "stage")? {
        described.push(format!("stage '{stage}'"));
        query.stage_contains = Some(stage);
    }
    query.limit = limit_of(args, 20)?;
    query.oldest_first = opt_bool(args, "oldest_first")?.unwrap_or(false);
    query.include_all_sources = include_all(args)?;

    let title = if described.is_empty() {
        "Matches in the datasets:".to_string()
    } else {
        format!("Matches — {}:", described.join(", "))
    };
    let search = queries::search_matches(graph, &query);
    let (text, data) = format::match_search(graph, &search, &title);
    Ok(ToolOutput::new(text, data))
}

fn head_to_head(graph: &KnowledgeGraph, args: &Map<String, Value>) -> Result<ToolOutput, String> {
    let team_a = resolve(graph, &req_str(args, "team_a")?)?;
    let team_b = resolve(graph, &req_str(args, "team_b")?)?;
    if team_a == team_b {
        return Err("team_a and team_b resolve to the same club".to_string());
    }
    let competition = opt_competition(args, "competition")?;
    let season = opt_i64(args, "season")?.map(|value| value as i32);
    let recent = opt_i64(args, "recent")?.unwrap_or(5).max(0) as usize;
    let h2h = queries::head_to_head(
        graph,
        team_a,
        team_b,
        competition,
        season,
        include_all(args)?,
    );
    let (text, data) = format::head_to_head(graph, &h2h, recent);
    Ok(ToolOutput::new(text, data))
}

fn team_stats(graph: &KnowledgeGraph, args: &Map<String, Value>) -> Result<ToolOutput, String> {
    let team = resolve(graph, &req_str(args, "team")?)?;
    let stats = queries::team_stats(
        graph,
        team,
        opt_competition(args, "competition")?,
        opt_i64(args, "season")?.map(|value| value as i32),
        opt_venue(args)?,
        include_all(args)?,
    );
    let (text, data) = format::team_stats(graph, &stats);
    Ok(ToolOutput::new(text, data))
}

fn team_profile(graph: &KnowledgeGraph, args: &Map<String, Value>) -> Result<ToolOutput, String> {
    let team = resolve(graph, &req_str(args, "team")?)?;
    let profile = queries::team_profile(graph, team, include_all(args)?);
    let (text, data) = format::team_profile(graph, &profile);
    Ok(ToolOutput::new(text, data))
}

fn standings(graph: &KnowledgeGraph, args: &Map<String, Value>) -> Result<ToolOutput, String> {
    let competition = opt_competition(args, "competition")?.unwrap_or(Competition::SerieA);
    let season = opt_i64(args, "season")?.ok_or("'season' is required")? as i32;
    let table = queries::standings(graph, competition, season, include_all(args)?);
    if table.rows.is_empty() {
        let seasons = graph.seasons(competition);
        return Err(format!(
            "no {} matches for season {season}. Seasons available: {}.",
            competition.name(),
            format::summarize_seasons(&seasons)
        ));
    }
    let (text, data) = format::standings(graph, &table, limit_of(args, 0)?);
    Ok(ToolOutput::new(text, data))
}

fn competition_stats(
    graph: &KnowledgeGraph,
    args: &Map<String, Value>,
) -> Result<ToolOutput, String> {
    let competition = opt_competition(args, "competition")?.unwrap_or(Competition::SerieA);
    let mut seasons: Vec<i32> = Vec::new();
    if let Some(Value::Array(values)) = args.get("seasons") {
        for value in values {
            match value.as_i64() {
                Some(year) => seasons.push(year as i32),
                None => return Err("'seasons' must be an array of integers".to_string()),
            }
        }
    }
    if let Some(season) = opt_i64(args, "season")? {
        seasons.push(season as i32);
    }
    let filter = if seasons.is_empty() {
        None
    } else {
        Some(seasons.as_slice())
    };
    let stats = queries::competition_stats(graph, competition, filter, include_all(args)?);
    if stats.total.matches == 0 {
        return Err(format!(
            "no matches for {} in {:?}. Seasons available: {}.",
            competition.name(),
            seasons,
            format::summarize_seasons(&graph.seasons(competition))
        ));
    }
    let (text, data) = format::competition_stats(graph, &stats);
    Ok(ToolOutput::new(text, data))
}

fn team_rankings(graph: &KnowledgeGraph, args: &Map<String, Value>) -> Result<ToolOutput, String> {
    let metric = match opt_str(args, "metric")? {
        None => Metric::WinRate,
        Some(raw) => Metric::parse(&raw).ok_or_else(|| {
            format!("unknown metric '{raw}'. Try points, wins, win_rate, goals_for, goals_against, goal_difference, clean_sheets.")
        })?,
    };
    let competition = opt_competition(args, "competition")?;
    let season = opt_i64(args, "season")?.map(|value| value as i32);
    let venue = opt_venue(args)?;
    let min_matches = opt_i64(args, "min_matches")?.unwrap_or(5) as i32;
    let limit = limit_of(args, 10)?;
    let ranked = queries::team_rankings(
        graph,
        &queries::RankingQuery {
            competition,
            season,
            venue,
            metric,
            min_matches,
            limit,
            include_all_sources: include_all(args)?,
        },
    );
    let title = format!(
        "Clubs ranked by {} ({}{}{}):",
        metric.label(),
        venue.label(),
        competition
            .map(|c| format!(", {}", c.name()))
            .unwrap_or_else(|| ", all competitions".to_string()),
        season
            .map(|s| format!(", {s}"))
            .unwrap_or_else(|| ", all seasons".to_string()),
    );
    let (text, data) = format::rankings(graph, &ranked, metric, &title);
    Ok(ToolOutput::new(text, data))
}

fn biggest_wins(graph: &KnowledgeGraph, args: &Map<String, Value>) -> Result<ToolOutput, String> {
    let competition = opt_competition(args, "competition")?;
    let season = opt_i64(args, "season")?.map(|value| value as i32);
    let team = match opt_str(args, "team")? {
        Some(name) => Some(resolve(graph, &name)?),
        None => None,
    };
    let limit = limit_of(args, 10)?;
    let ids = queries::biggest_wins(graph, competition, season, team, limit, include_all(args)?);
    let title = format!(
        "Biggest victories{}{}{}:",
        team.map(|id| format!(" by {}", graph.team(id).name))
            .unwrap_or_default(),
        competition
            .map(|c| format!(" in {}", c.name()))
            .unwrap_or_default(),
        season.map(|s| format!(" ({s})")).unwrap_or_default(),
    );
    let mut text = format!("{title}\n");
    for (idx, id) in ids.iter().enumerate() {
        text.push_str(&format!(
            "{}. {}\n",
            idx + 1,
            format::match_line(graph, *id)
        ));
    }
    if ids.is_empty() {
        text.push_str("No matches for those filters.\n");
    }
    let data = json!({
        "matches": ids.iter().map(|id| format::match_json(graph, *id)).collect::<Vec<_>>(),
    });
    Ok(ToolOutput::new(text, data))
}

fn search_players(graph: &KnowledgeGraph, args: &Map<String, Value>) -> Result<ToolOutput, String> {
    let mut query = PlayerQuery {
        limit: limit_of(args, 20)?,
        ..Default::default()
    };
    query.name = opt_str(args, "name")?;
    query.nationality = opt_str(args, "nationality")?;
    query.club = opt_str(args, "club")?;
    query.position = opt_str(args, "position")?;
    query.min_overall = opt_i64(args, "min_overall")?.map(|value| value as i32);
    query.min_age = opt_i64(args, "min_age")?.map(|value| value as i32);
    query.max_age = opt_i64(args, "max_age")?.map(|value| value as i32);
    query.brazilian_clubs_only = opt_bool(args, "brazilian_clubs_only")?.unwrap_or(false);
    query.sort_by = match opt_str(args, "sort_by")? {
        None => PlayerSort::Overall,
        Some(raw) => PlayerSort::parse(&raw).ok_or_else(|| {
            format!("unknown sort_by '{raw}'. Use overall, potential, age or name.")
        })?,
    };

    let mut described = Vec::new();
    if let Some(name) = &query.name {
        described.push(format!("name ~ '{name}'"));
    }
    if let Some(nationality) = &query.nationality {
        described.push(nationality.clone());
    }
    if let Some(club) = &query.club {
        described.push(format!("club {club}"));
    }
    if let Some(position) = &query.position {
        described.push(position.clone());
    }
    if let Some(min_overall) = query.min_overall {
        described.push(format!("overall >= {min_overall}"));
    }
    if query.brazilian_clubs_only {
        described.push("playing at a Brazilian club in the match data".to_string());
    }
    let title = if described.is_empty() {
        "Players in the FIFA dataset:".to_string()
    } else {
        format!("Players — {}:", described.join(", "))
    };

    let search = queries::search_players(graph, &query);
    let (mut text, data) = format::player_search(graph, &search, &title);
    if search.total == 0 && query.club.is_some() {
        text.push_str(
            "\nNote: the FIFA 19 database only contains officially licensed Brazilian clubs; several big clubs (Flamengo, Palmeiras, Corinthians, São Paulo, Vasco) are absent. Use club_players for the list of clubs that are present.\n",
        );
    }
    Ok(ToolOutput::new(text, data))
}

fn player_profile(graph: &KnowledgeGraph, args: &Map<String, Value>) -> Result<ToolOutput, String> {
    let name = req_str(args, "name")?;
    let hits = graph.players_by_name(&name);
    let id = *hits.first().ok_or_else(|| {
        let suggestions = graph.similar_player_names(&name, 5);
        let mut message = format!(
            "'{name}' is not in the FIFA player file (a single 2019 snapshot, so later signings and unlicensed Brazilian squads are missing)."
        );
        if !suggestions.is_empty() {
            message.push_str(&format!(
                " Similar names: {}.",
                suggestions
                    .iter()
                    .map(|id| graph.player(*id).name.clone())
                    .collect::<Vec<_>>()
                    .join(", ")
            ));
        }
        message
    })?;
    let (mut text, data) = format::player_profile(graph, id);
    if hits.len() > 1 {
        text.push_str(&format!(
            "\nOther players matching '{name}': {}\n",
            hits.iter()
                .skip(1)
                .take(5)
                .map(|id| graph.player(*id).name.clone())
                .collect::<Vec<_>>()
                .join(", ")
        ));
    }
    Ok(ToolOutput::new(text, data))
}

fn club_players(graph: &KnowledgeGraph, args: &Map<String, Value>) -> Result<ToolOutput, String> {
    let club = req_str(args, "club")?;
    let limit = limit_of(args, 20)?;
    let squad = queries::club_squad(graph, &club);
    let (text, data) = format::club_squad(graph, &squad, limit);
    Ok(ToolOutput::new(text, data))
}

fn find_team(graph: &KnowledgeGraph, args: &Map<String, Value>) -> Result<ToolOutput, String> {
    let query = req_str(args, "query")?;
    let limit = limit_of(args, 10)?;
    let (status, ids) = match graph.resolve_team(&query) {
        Resolution::Unique(id) => ("unique", vec![id]),
        Resolution::Ambiguous(ids) => ("ambiguous", ids),
        Resolution::NotFound(ids) => ("not_found", ids),
    };
    let mut text = match status {
        "unique" => format!("'{query}' resolves to {}:\n", graph.team(ids[0]).display()),
        "ambiguous" => format!("'{query}' matches several clubs:\n"),
        _ => format!("No club named '{query}'. Closest entries:\n"),
    };
    for id in ids.iter().take(limit) {
        let team = graph.team(*id);
        text.push_str(&format!(
            "- {} [key {}], {} matches, spellings: {}\n",
            team.display(),
            team.key,
            graph.team_matches(*id).len(),
            team.aliases.join(" | ")
        ));
    }
    if ids.is_empty() {
        text.push_str("(no similar names found)\n");
    }
    let data = json!({
        "query": query,
        "status": status,
        "candidates": ids.iter().take(limit).map(|id| {
            let team = graph.team(*id);
            json!({
                "name": team.name,
                "key": team.key,
                "state": team.state,
                "country": team.country,
                "matches": graph.team_matches(*id).len(),
                "aliases": team.aliases,
            })
        }).collect::<Vec<_>>(),
    });
    Ok(ToolOutput::new(text, data))
}

fn graph_neighbors(
    graph: &KnowledgeGraph,
    args: &Map<String, Value>,
) -> Result<ToolOutput, String> {
    let node_type = req_str(args, "node_type")?.to_lowercase();
    let name = req_str(args, "name")?;
    let limit = limit_of(args, 10)?;
    let node = match node_type.as_str() {
        "team" | "club" => NodeRef::Team(resolve(graph, &name)?),
        "competition" => NodeRef::Competition(
            Competition::parse(&name).ok_or_else(|| format!("unknown competition '{name}'"))?,
        ),
        "player" => NodeRef::Player(
            *graph
                .players_by_name(&name)
                .first()
                .ok_or_else(|| format!("no player named '{name}'"))?,
        ),
        "match" => {
            let id: usize = name.parse().map_err(|_| {
                "for node_type 'match', 'name' must be a numeric match id".to_string()
            })?;
            if id >= graph.matches.len() {
                return Err(format!("match id {id} is out of range"));
            }
            NodeRef::Match(id)
        }
        other => return Err(format!("unknown node_type '{other}'")),
    };
    let edges = graph.neighbors(node, limit);
    let mut text = format!("Node: {}\nEdges:\n", graph.node_label(node));
    for (relation, target) in &edges {
        text.push_str(&format!(
            "- {} -> {}\n",
            relation.name(),
            graph.node_label(*target)
        ));
    }
    if edges.is_empty() {
        text.push_str("(no edges)\n");
    }
    let data = json!({
        "node": graph.node_label(node),
        "edges": edges.iter().map(|(relation, target)| json!({
            "relation": relation.name(),
            "target": graph.node_label(*target),
            "target_type": match target {
                NodeRef::Team(_) => "team",
                NodeRef::Match(_) => "match",
                NodeRef::Player(_) => "player",
                NodeRef::Competition(_) => "competition",
            },
        })).collect::<Vec<_>>(),
        "relations_available": [
            Relation::Hosted.name(), Relation::Visited.name(), Relation::HomeTeam.name(),
            Relation::AwayTeam.name(), Relation::PartOf.name(), Relation::Includes.name(),
            Relation::PlaysFor.name(), Relation::HasPlayer.name(),
        ],
    });
    Ok(ToolOutput::new(text, data))
}

fn dataset_overview(graph: &KnowledgeGraph) -> Result<ToolOutput, String> {
    let stats = graph.stats();
    let mut text = String::from("Brazilian soccer knowledge graph\n\nSource files:\n");
    for report in &graph.reports {
        text.push_str(&format!(
            "- {} — {} rows loaded ({} skipped), license {}, {}\n",
            report.source.file_name(),
            report.rows_used,
            report.rows_skipped,
            report.source.license(),
            report.source.label()
        ));
    }
    text.push_str("\nCompetition coverage:\n");
    for competition in graph.competitions() {
        let seasons = graph.seasons(competition);
        let total = graph
            .competition_matches(competition)
            .iter()
            .filter(|id| graph.match_by_id(**id).canonical)
            .count();
        text.push_str(&format!(
            "- {}: {} matches, seasons {}\n",
            competition.name(),
            total,
            format::summarize_seasons(&seasons)
        ));
    }
    text.push_str(&format!(
        "\nGraph: {} teams, {} matches ({} canonical after de-duplication), {} players, {} edges. Loaded in {} ms.\n",
        stats.teams, stats.matches, stats.canonical_matches, stats.players, stats.edges, graph.load_millis
    ));
    text.push_str(
        "\nCaveats:\n\
         - Several files cover the same competition and season; the highest-priority file per season is marked canonical and aggregates use only those rows. Pass include_all_sources=true to see every row.\n\
         - The datasets contain no goalscorer or lineup data, so individual top-scorer questions cannot be answered; team scoring records can.\n\
         - The FIFA file is a single 2019 snapshot and only includes licensed Brazilian clubs.\n",
    );

    let data = json!({
        "sources": graph.reports.iter().map(|report| json!({
            "file": report.source.file_name(),
            "description": report.source.label(),
            "license": report.source.license(),
            "rows_read": report.rows_read,
            "rows_used": report.rows_used,
            "rows_skipped": report.rows_skipped,
        })).collect::<Vec<_>>(),
        "competitions": graph.competitions().iter().map(|competition| json!({
            "competition": competition.name(),
            "competition_id": competition.slug(),
            "seasons": graph.seasons(*competition),
            "matches": graph.competition_matches(*competition).len(),
        })).collect::<Vec<_>>(),
        "graph": {
            "teams": stats.teams,
            "matches": stats.matches,
            "canonical_matches": stats.canonical_matches,
            "duplicate_rows_dropped": graph.duplicate_rows_dropped,
            "players": stats.players,
            "edges": stats.edges,
            "load_millis": graph.load_millis,
        },
        "source_priority": Competition::ALL.iter().map(|competition| json!({
            "competition": competition.name(),
            "priority": Source::priority_for(*competition).iter().map(|s| s.file_name()).collect::<Vec<_>>(),
        })).collect::<Vec<_>>(),
    });
    Ok(ToolOutput::new(text, data))
}
