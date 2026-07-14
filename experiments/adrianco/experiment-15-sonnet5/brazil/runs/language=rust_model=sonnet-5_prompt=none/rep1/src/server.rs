//! MCP tool surface: thin wrappers that expose [`crate::queries`] as MCP
//! tools over stdio.

use std::sync::Arc;

use rmcp::handler::server::router::tool::ToolRouter;
use rmcp::handler::server::wrapper::Parameters;
use rmcp::{ServerHandler, tool, tool_handler, tool_router};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

use crate::queries;
use crate::store::Store;

#[derive(Clone)]
pub struct SoccerServer {
    store: Arc<Store>,
    tool_router: ToolRouter<Self>,
}

impl SoccerServer {
    pub fn new(store: Arc<Store>) -> Self {
        Self {
            store,
            tool_router: Self::tool_router(),
        }
    }
}

fn opt_str(s: &Option<String>) -> &str {
    s.as_deref().unwrap_or("")
}

#[derive(Debug, Deserialize, Serialize, JsonSchema)]
pub struct SearchMatchesArgs {
    /// Team name to filter by (matches home or away side), e.g. "Flamengo".
    pub team: Option<String>,
    /// Opponent team name. If set together with `team`, returns head-to-head
    /// matches between the two teams plus a win/draw tally.
    pub opponent: Option<String>,
    /// Competition filter, e.g. "Brasileirao", "Copa do Brasil", "Copa Libertadores", "Serie B", "Serie C".
    pub competition: Option<String>,
    /// Season year to filter by, e.g. 2023.
    pub season: Option<i32>,
    /// Only include matches on or after this date (YYYY-MM-DD).
    pub date_from: Option<String>,
    /// Only include matches on or before this date (YYYY-MM-DD).
    pub date_to: Option<String>,
    /// Maximum number of matches to return (default 20).
    pub limit: Option<u32>,
}

#[derive(Debug, Deserialize, Serialize, JsonSchema)]
pub struct CompareTeamsArgs {
    /// First team name, e.g. "Palmeiras".
    pub team_a: String,
    /// Second team name, e.g. "Santos".
    pub team_b: String,
    /// Optional competition filter.
    pub competition: Option<String>,
    /// Optional season filter.
    pub season: Option<i32>,
}

#[derive(Debug, Deserialize, Serialize, JsonSchema)]
pub struct TeamRecordArgs {
    /// Team name, e.g. "Corinthians".
    pub team: String,
    /// Optional competition filter, e.g. "Brasileirao".
    pub competition: Option<String>,
    /// Optional season filter, e.g. 2022.
    pub season: Option<i32>,
    /// One of "home", "away", or "all" (default "all").
    pub venue: Option<String>,
}

#[derive(Debug, Deserialize, Serialize, JsonSchema)]
pub struct StandingsArgs {
    /// Competition name, e.g. "Brasileirao" or "Copa Libertadores".
    pub competition: String,
    /// Season year, e.g. 2019.
    pub season: i32,
}

#[derive(Debug, Deserialize, Serialize, JsonSchema)]
pub struct LeaderboardArgs {
    /// Competition filter, e.g. "Brasileirao".
    pub competition: Option<String>,
    /// Optional season filter.
    pub season: Option<i32>,
    /// Metric to rank by: "goals_for" (default), "goals_against", "goal_diff", "wins", or "win_rate".
    pub metric: Option<String>,
    /// One of "home", "away", or "all" (default "all") - used for e.g. best home/away record.
    pub venue: Option<String>,
    /// Maximum number of teams to return (default 10).
    pub limit: Option<u32>,
}

#[derive(Debug, Deserialize, Serialize, JsonSchema)]
pub struct BiggestWinsArgs {
    /// Optional competition filter.
    pub competition: Option<String>,
    /// Optional season filter.
    pub season: Option<i32>,
    /// Maximum number of matches to return (default 10).
    pub limit: Option<u32>,
}

#[derive(Debug, Deserialize, Serialize, JsonSchema)]
pub struct AverageStatsArgs {
    /// Optional competition filter, e.g. "Brasileirao".
    pub competition: Option<String>,
    /// Optional season filter.
    pub season: Option<i32>,
}

#[derive(Debug, Deserialize, Serialize, JsonSchema)]
pub struct DerbyArgs {
    /// Optional season filter, e.g. 2023.
    pub season: Option<i32>,
    /// Optional rivalry name filter, e.g. "Fla-Flu".
    pub rivalry: Option<String>,
}

#[derive(Debug, Deserialize, Serialize, JsonSchema)]
pub struct TeamCompetitionsArgs {
    /// Team name, e.g. "Palmeiras".
    pub team: String,
}

#[derive(Debug, Deserialize, Serialize, JsonSchema)]
pub struct SearchPlayersArgs {
    /// Player name substring to search for, e.g. "Neymar".
    pub name: Option<String>,
    /// Exact nationality to filter by, e.g. "Brazil".
    pub nationality: Option<String>,
    /// Club name to filter by (substring match), e.g. "Flamengo".
    pub club: Option<String>,
    /// Exact position code to filter by, e.g. "ST", "LW", "GK".
    pub position: Option<String>,
    /// Minimum FIFA overall rating.
    pub min_overall: Option<i32>,
    /// Maximum number of players to return (default 25), sorted by overall rating descending.
    pub limit: Option<u32>,
}

#[derive(Debug, Deserialize, Serialize, JsonSchema)]
pub struct ClubSquadsArgs {
    /// Maximum number of clubs to return (default 15).
    pub limit_clubs: Option<u32>,
}

#[tool_router]
impl SoccerServer {
    #[tool(
        description = "Search Brazilian soccer matches across all loaded competitions (Brasileirao, Copa do Brasil, Copa Libertadores, Serie B/C) by team, opponent, competition, season, or date range. If both team and opponent are given, also returns a head-to-head tally."
    )]
    async fn search_matches(&self, Parameters(a): Parameters<SearchMatchesArgs>) -> String {
        queries::search_matches(
            &self.store,
            opt_str(&a.team),
            opt_str(&a.opponent),
            opt_str(&a.competition),
            a.season,
            opt_str(&a.date_from),
            opt_str(&a.date_to),
            a.limit.unwrap_or(0) as usize,
        )
    }

    #[tool(description = "Compare two teams head-to-head: full match history plus win/draw/loss tally.")]
    async fn compare_teams(&self, Parameters(a): Parameters<CompareTeamsArgs>) -> String {
        queries::compare_teams(&self.store, &a.team_a, &a.team_b, opt_str(&a.competition), a.season)
    }

    #[tool(
        description = "Get a team's win/draw/loss and goals record, optionally filtered by competition, season, and home/away venue."
    )]
    async fn team_record(&self, Parameters(a): Parameters<TeamRecordArgs>) -> String {
        queries::team_record(&self.store, &a.team, opt_str(&a.competition), a.season, opt_str(&a.venue))
    }

    #[tool(
        description = "Calculate the final league/competition standings table for a given competition and season from match results, including champion and (for Brasileirao) relegation zone."
    )]
    async fn standings(&self, Parameters(a): Parameters<StandingsArgs>) -> String {
        queries::standings(&self.store, &a.competition, a.season)
    }

    #[tool(
        description = "Rank teams by a statistic (goals scored, goals conceded, goal difference, wins, or win rate), optionally scoped to a competition/season and home-only or away-only matches. Use this for 'best home record', 'most goals', etc."
    )]
    async fn team_leaderboard(&self, Parameters(a): Parameters<LeaderboardArgs>) -> String {
        queries::team_leaderboard(
            &self.store,
            opt_str(&a.competition),
            a.season,
            opt_str(&a.metric),
            opt_str(&a.venue),
            a.limit.unwrap_or(0) as usize,
        )
    }

    #[tool(description = "Find the biggest victories (largest goal margins) in the dataset, optionally filtered by competition and season.")]
    async fn biggest_wins(&self, Parameters(a): Parameters<BiggestWinsArgs>) -> String {
        queries::biggest_wins(&self.store, opt_str(&a.competition), a.season, a.limit.unwrap_or(0) as usize)
    }

    #[tool(
        description = "Compute aggregate statistics for a competition/season: average goals per match, home win rate, draw rate, and away win rate."
    )]
    async fn average_stats(&self, Parameters(a): Parameters<AverageStatsArgs>) -> String {
        queries::average_stats(&self.store, opt_str(&a.competition), a.season)
    }

    #[tool(
        description = "Find matches between traditional rival teams (derbies), e.g. Fla-Flu (Flamengo vs Fluminense), Gre-Nal (Internacional vs Gremio), optionally filtered by season or rivalry name."
    )]
    async fn derby_matches(&self, Parameters(a): Parameters<DerbyArgs>) -> String {
        queries::derby_matches(&self.store, a.season, opt_str(&a.rivalry))
    }

    #[tool(description = "List which competitions and seasons a team has appeared in, with match counts, across all loaded datasets.")]
    async fn team_competitions(&self, Parameters(a): Parameters<TeamCompetitionsArgs>) -> String {
        queries::team_competitions(&self.store, &a.team)
    }

    #[tool(
        description = "Search FIFA player data by name, nationality, club, position, or minimum overall rating. Results are sorted by overall rating descending. Use this for 'Find all Brazilian players', 'top-rated players at Flamengo', etc."
    )]
    async fn search_players(&self, Parameters(a): Parameters<SearchPlayersArgs>) -> String {
        queries::search_players(
            &self.store,
            opt_str(&a.name),
            opt_str(&a.nationality),
            opt_str(&a.club),
            opt_str(&a.position),
            a.min_overall,
            a.limit.unwrap_or(0) as usize,
        )
    }

    #[tool(
        description = "Cross-file query: breaks down Brazilian (nationality) FIFA players by Brazilian club, with player counts and average rating. Brazilian clubs are resolved dynamically from the match datasets."
    )]
    async fn brazilian_club_squads(&self, Parameters(a): Parameters<ClubSquadsArgs>) -> String {
        queries::brazilian_club_squads(&self.store, a.limit_clubs.unwrap_or(0) as usize)
    }

    #[tool(description = "List the datasets loaded by this server and their row counts, for sanity-checking data coverage.")]
    async fn list_datasets(&self) -> String {
        queries::list_datasets(&self.store)
    }
}

#[tool_handler(
    router = self.tool_router,
    name = "brazilian-soccer-mcp",
    version = "0.1.0",
    instructions = "Knowledge graph over Brazilian soccer data (Brasileirao, Copa do Brasil, Copa Libertadores, extended match stats, and FIFA player ratings). Use the provided tools to answer natural-language questions about matches, teams, standings, and players. Team names are matched case/accent/state-suffix-insensitively (e.g. 'Palmeiras' matches 'Palmeiras-SP')."
)]
impl ServerHandler for SoccerServer {}
