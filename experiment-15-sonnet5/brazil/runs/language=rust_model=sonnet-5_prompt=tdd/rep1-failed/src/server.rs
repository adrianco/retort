use std::sync::Arc;

use rmcp::{
    ErrorData as McpError, ServerHandler,
    handler::server::{router::tool::ToolRouter, wrapper::Parameters},
    model::{CallToolResult, ContentBlock, Implementation, ProtocolVersion, ServerCapabilities, ServerInfo},
    schemars, tool, tool_handler, tool_router,
};

use crate::format;
use crate::models::parse_competition;
use crate::queries;
use crate::store::Store;

fn default_limit() -> usize {
    20
}

#[derive(Debug, serde::Deserialize, schemars::JsonSchema)]
pub struct SearchMatchesArgs {
    /// Team name to filter by (matches either home or away side); omit for all teams.
    pub team: Option<String>,
    /// Competition name: "brasileirao", "serie b", "serie c", "copa do brasil", or "libertadores".
    pub competition: Option<String>,
    /// Season year, e.g. 2023.
    pub season: Option<i32>,
    /// Inclusive start date in YYYY-MM-DD format.
    pub start_date: Option<String>,
    /// Inclusive end date in YYYY-MM-DD format.
    pub end_date: Option<String>,
    /// Maximum number of matches to return (default 20).
    #[serde(default = "default_limit")]
    pub limit: usize,
}

#[derive(Debug, serde::Deserialize, schemars::JsonSchema)]
pub struct HeadToHeadArgs {
    pub team_a: String,
    pub team_b: String,
}

#[derive(Debug, serde::Deserialize, schemars::JsonSchema)]
pub struct TeamRecordArgs {
    pub team: String,
    /// Season year, e.g. 2022. Omit for the team's all-time record.
    pub season: Option<i32>,
    /// Competition name: "brasileirao", "serie b", "serie c", "copa do brasil", or "libertadores".
    pub competition: Option<String>,
    /// If true, only home matches. If false, only away matches. Omit for both.
    pub home_only: Option<bool>,
}

#[derive(Debug, serde::Deserialize, schemars::JsonSchema)]
pub struct StandingsArgs {
    /// Competition name: "brasileirao", "serie b", "serie c", "copa do brasil", or "libertadores".
    pub competition: String,
    pub season: i32,
}

#[derive(Debug, serde::Deserialize, schemars::JsonSchema)]
pub struct BiggestWinsArgs {
    /// Competition name to filter by; omit for all competitions.
    pub competition: Option<String>,
    /// Season year to filter by; omit for all seasons.
    pub season: Option<i32>,
    #[serde(default = "default_limit")]
    pub limit: usize,
}

#[derive(Debug, serde::Deserialize, schemars::JsonSchema)]
pub struct MatchStatsArgs {
    /// Competition name to filter by; omit for all competitions.
    pub competition: Option<String>,
    /// Season year to filter by; omit for all seasons.
    pub season: Option<i32>,
}

#[derive(Debug, serde::Deserialize, schemars::JsonSchema)]
pub struct PlayerNameArgs {
    pub query: String,
}

#[derive(Debug, serde::Deserialize, schemars::JsonSchema)]
pub struct NationalityArgs {
    pub nationality: String,
}

#[derive(Debug, serde::Deserialize, schemars::JsonSchema)]
pub struct ClubArgs {
    pub club: String,
}

#[derive(Debug, serde::Deserialize, schemars::JsonSchema)]
pub struct TopRatedPlayersArgs {
    /// Filter to players of this nationality, e.g. "Brazil".
    pub nationality: Option<String>,
    /// Filter to players whose club name contains this substring.
    pub club: Option<String>,
    #[serde(default = "default_limit")]
    pub limit: usize,
}

fn text_result(text: String) -> Result<CallToolResult, McpError> {
    Ok(CallToolResult::success(vec![ContentBlock::text(text)]))
}

fn parse_optional_competition(
    name: Option<&str>,
) -> Result<Option<crate::models::Competition>, McpError> {
    match name {
        None => Ok(None),
        Some(name) => parse_competition(name)
            .map(Some)
            .ok_or_else(|| invalid_competition(name)),
    }
}

fn invalid_competition(name: &str) -> McpError {
    McpError::invalid_params(
        format!(
            "unrecognized competition \"{name}\"; expected one of: brasileirao, serie b, serie c, copa do brasil, libertadores"
        ),
        None,
    )
}

#[derive(Clone)]
pub struct SoccerServer {
    store: Arc<Store>,
    #[allow(dead_code)] // read by the generated `#[tool_handler]` dispatch, not visible to this lint
    tool_router: ToolRouter<SoccerServer>,
}

#[tool_router]
impl SoccerServer {
    pub fn new(store: Arc<Store>) -> Self {
        Self {
            store,
            tool_router: Self::tool_router(),
        }
    }

    #[tool(
        description = "Search Brazilian soccer matches across all provided datasets (Brasileirao, Copa do Brasil, Libertadores, and extended match stats). Filter by team, competition, season, and/or date range."
    )]
    async fn search_matches(
        &self,
        Parameters(args): Parameters<SearchMatchesArgs>,
    ) -> Result<CallToolResult, McpError> {
        let mut results: Vec<&crate::models::Match> = self.store.matches.iter().collect();

        if let Some(team) = &args.team {
            let key = crate::normalize::team_comparison_key(team);
            results.retain(|m| {
                crate::normalize::team_comparison_key(&m.home_team) == key
                    || crate::normalize::team_comparison_key(&m.away_team) == key
            });
        }
        if let Some(competition_name) = &args.competition {
            let competition = parse_competition(competition_name)
                .ok_or_else(|| invalid_competition(competition_name))?;
            results.retain(|m| m.competition == competition);
        }
        if let Some(season) = args.season {
            results.retain(|m| m.season == season);
        }
        if args.start_date.is_some() || args.end_date.is_some() {
            let start = args
                .start_date
                .as_deref()
                .and_then(crate::dates::parse_flexible_date)
                .unwrap_or(chrono::NaiveDate::MIN);
            let end = args
                .end_date
                .as_deref()
                .and_then(crate::dates::parse_flexible_date)
                .unwrap_or(chrono::NaiveDate::MAX);
            results.retain(|m| matches!(m.date, Some(d) if d >= start && d <= end));
        }

        results.sort_by_key(|m| m.date);
        let total = results.len();
        results.truncate(args.limit);
        let mut text = format::format_matches(&results);
        if total > results.len() {
            text.push_str(&format!("\n\n... ({} more matches in dataset)", total - results.len()));
        }
        text_result(text)
    }

    #[tool(
        description = "Get the head-to-head record and full match history between two teams."
    )]
    async fn head_to_head(
        &self,
        Parameters(args): Parameters<HeadToHeadArgs>,
    ) -> Result<CallToolResult, McpError> {
        let h2h = queries::head_to_head(&self.store.matches, &args.team_a, &args.team_b);
        text_result(format::format_head_to_head(&h2h, &args.team_a, &args.team_b))
    }

    #[tool(
        description = "Get a team's win/loss/draw record and goal statistics, optionally filtered by season, competition, and home/away."
    )]
    async fn team_record(
        &self,
        Parameters(args): Parameters<TeamRecordArgs>,
    ) -> Result<CallToolResult, McpError> {
        let competition = parse_optional_competition(args.competition.as_deref())?;
        let record = queries::team_record(
            &self.store.matches,
            &args.team,
            args.season,
            competition.as_ref(),
            args.home_only,
        );
        text_result(format::format_team_record(&record, &args.team))
    }

    #[tool(
        description = "Get the league standings/table for a competition and season, calculated from match results."
    )]
    async fn standings(
        &self,
        Parameters(args): Parameters<StandingsArgs>,
    ) -> Result<CallToolResult, McpError> {
        let competition =
            parse_competition(&args.competition).ok_or_else(|| invalid_competition(&args.competition))?;
        let table = queries::standings(&self.store.matches, &competition, args.season);
        text_result(format::format_standings(&table))
    }

    #[tool(
        description = "List the matches with the largest goal-difference margins (biggest wins), optionally filtered by competition and season."
    )]
    async fn biggest_wins(
        &self,
        Parameters(args): Parameters<BiggestWinsArgs>,
    ) -> Result<CallToolResult, McpError> {
        let competition = parse_optional_competition(args.competition.as_deref())?;

        let mut filtered: Vec<crate::models::Match> = self.store.matches.clone();
        if let Some(c) = &competition {
            filtered.retain(|m| &m.competition == c);
        }
        if let Some(season) = args.season {
            filtered.retain(|m| m.season == season);
        }
        let biggest = queries::biggest_wins(&filtered, args.limit);
        text_result(format::format_matches(&biggest))
    }

    #[tool(
        description = "Compute aggregate statistics (average goals per match and home win rate), optionally filtered by competition and season."
    )]
    async fn match_stats(
        &self,
        Parameters(args): Parameters<MatchStatsArgs>,
    ) -> Result<CallToolResult, McpError> {
        let competition = parse_optional_competition(args.competition.as_deref())?;

        let mut filtered: Vec<crate::models::Match> = self.store.matches.clone();
        if let Some(c) = &competition {
            filtered.retain(|m| &m.competition == c);
        }
        if let Some(season) = args.season {
            filtered.retain(|m| m.season == season);
        }

        let avg = queries::average_goals_per_match(&filtered);
        let home_rate = queries::home_win_rate(&filtered);
        text_result(format!(
            "Matches analyzed: {}\nAverage goals per match: {:.2}\nHome win rate: {:.1}%",
            filtered.len(),
            avg,
            home_rate * 100.0
        ))
    }

    #[tool(description = "Search FIFA player data by name (case-insensitive substring match).")]
    async fn players_by_name(
        &self,
        Parameters(args): Parameters<PlayerNameArgs>,
    ) -> Result<CallToolResult, McpError> {
        let players = queries::players_by_name(&self.store.players, &args.query);
        text_result(format::format_players(&players))
    }

    #[tool(description = "Find FIFA players by nationality, e.g. \"Brazil\".")]
    async fn players_by_nationality(
        &self,
        Parameters(args): Parameters<NationalityArgs>,
    ) -> Result<CallToolResult, McpError> {
        let players = queries::players_by_nationality(&self.store.players, &args.nationality);
        text_result(format::format_players(&players))
    }

    #[tool(description = "Find FIFA players whose club name contains the given text.")]
    async fn players_by_club(
        &self,
        Parameters(args): Parameters<ClubArgs>,
    ) -> Result<CallToolResult, McpError> {
        let players = queries::players_by_club(&self.store.players, &args.club);
        text_result(format::format_players(&players))
    }

    #[tool(
        description = "List the highest FIFA-overall-rated players, optionally filtered by nationality and/or club."
    )]
    async fn top_rated_players(
        &self,
        Parameters(args): Parameters<TopRatedPlayersArgs>,
    ) -> Result<CallToolResult, McpError> {
        let players = queries::top_rated_players(
            &self.store.players,
            args.nationality.as_deref(),
            args.club.as_deref(),
            args.limit,
        );
        text_result(format::format_players(&players))
    }
}

#[tool_handler]
impl ServerHandler for SoccerServer {
    fn get_info(&self) -> ServerInfo {
        ServerInfo::new(ServerCapabilities::builder().enable_tools().build())
            .with_server_info(Implementation::from_build_env())
            .with_protocol_version(ProtocolVersion::V_2024_11_05)
            .with_instructions(
                "Query Brazilian soccer match, team, player, and competition data. Tools: \
                 search_matches, head_to_head, team_record, standings, biggest_wins, \
                 match_stats, players_by_name, players_by_nationality, players_by_club, \
                 top_rated_players.",
            )
    }
}
