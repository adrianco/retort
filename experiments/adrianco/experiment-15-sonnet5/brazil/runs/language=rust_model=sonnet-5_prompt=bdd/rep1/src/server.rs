//! MCP tool wiring: thin request/response translation between the
//! [`KnowledgeBase`] query API and the Model Context Protocol.

use std::sync::Arc;

use chrono::NaiveDate;
use rmcp::handler::server::router::tool::ToolRouter;
use rmcp::handler::server::wrapper::{Json, Parameters};
use rmcp::{ServerHandler, tool, tool_handler, tool_router};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

use crate::model::{Competition, Venue};
use crate::store::{
    CompetitionOverview, FindMatchesResult, HeadToHeadResult, KnowledgeBase, MatchFilter,
    MatchStats, PlayerFilter, PlayerSort, StandingRow, TeamRecordResult,
};

fn parse_date(raw: &Option<String>, field: &str) -> Result<Option<NaiveDate>, String> {
    match raw {
        None => Ok(None),
        Some(s) => NaiveDate::parse_from_str(s, "%Y-%m-%d")
            .map(Some)
            .map_err(|_| format!("{field} must be an ISO date (YYYY-MM-DD), got {s:?}")),
    }
}

#[derive(Debug, Deserialize, Serialize, JsonSchema)]
pub struct FindMatchesRequest {
    /// Team name (any spelling/state suffix, e.g. "Flamengo" or "Flamengo-RJ").
    pub team: Option<String>,
    /// Which side `team` must appear on. Defaults to either side.
    pub venue: Option<Venue>,
    /// A second team, to find matches between `team` and this opponent.
    pub opponent: Option<String>,
    /// Restrict to one competition/dataset.
    pub competition: Option<Competition>,
    /// Restrict to a single season (year).
    pub season: Option<i32>,
    /// Inclusive lower bound on season (year).
    pub season_from: Option<i32>,
    /// Inclusive upper bound on season (year).
    pub season_to: Option<i32>,
    /// Inclusive lower bound date, ISO format YYYY-MM-DD.
    pub date_from: Option<String>,
    /// Inclusive upper bound date, ISO format YYYY-MM-DD.
    pub date_to: Option<String>,
    /// Max matches to return (results are sorted newest first). Default 50.
    pub limit: Option<usize>,
}

#[derive(Debug, Deserialize, Serialize, JsonSchema)]
pub struct HeadToHeadRequest {
    /// First team name.
    pub team_a: String,
    /// Second team name.
    pub team_b: String,
    /// Restrict to one competition/dataset.
    pub competition: Option<Competition>,
    /// Restrict to a single season (year).
    pub season: Option<i32>,
    /// Max matches to include in the returned match list. Default 20.
    pub limit: Option<usize>,
}

#[derive(Debug, Deserialize, Serialize, JsonSchema)]
pub struct TeamRecordRequest {
    /// Team name (any spelling/state suffix).
    pub team: String,
    /// Restrict to one competition/dataset.
    pub competition: Option<Competition>,
    /// Restrict to a single season (year).
    pub season: Option<i32>,
    /// Restrict to home-only, away-only, or both (default) matches.
    pub venue: Option<Venue>,
}

#[derive(Debug, Deserialize, Serialize, JsonSchema)]
pub struct StandingsRequest {
    /// Competition/dataset to compute a table for. Defaults to Brasileirão.
    /// Meaningful for round-robin league competitions; knockout competitions
    /// (Copa do Brasil, Libertadores) will still produce a table but it does
    /// not represent an official bracket.
    pub competition: Option<Competition>,
    /// Season (year) to compute the table for.
    pub season: i32,
}

#[derive(Debug, Deserialize, Serialize, JsonSchema)]
pub struct BiggestWinsRequest {
    /// Restrict to one competition/dataset.
    pub competition: Option<Competition>,
    /// Restrict to a single season (year).
    pub season: Option<i32>,
    /// Max matches to return. Default 10.
    pub limit: Option<usize>,
}

#[derive(Debug, Deserialize, Serialize, JsonSchema)]
pub struct MatchStatsRequest {
    /// Restrict to one competition/dataset.
    pub competition: Option<Competition>,
    /// Restrict to a single season (year).
    pub season: Option<i32>,
}

#[derive(Debug, Deserialize, Serialize, JsonSchema)]
pub struct ListTeamsRequest {
    /// Restrict to one competition/dataset.
    pub competition: Option<Competition>,
    /// Restrict to a single season (year).
    pub season: Option<i32>,
}

#[derive(Debug, Deserialize, Serialize, JsonSchema)]
pub struct SearchPlayersRequest {
    /// Substring to search for in the player's name.
    pub name: Option<String>,
    /// Nationality, e.g. "Brazil".
    pub nationality: Option<String>,
    /// Club name, e.g. "Flamengo".
    pub club: Option<String>,
    /// Playing position, e.g. "ST", "GK", substring-matched.
    pub position: Option<String>,
    /// Only include players with at least this FIFA overall rating.
    pub min_overall: Option<u32>,
    /// Field to sort by. Defaults to overall rating.
    pub sort_by: Option<PlayerSortField>,
    /// Sort descending (default true, i.e. highest/oldest first).
    pub descending: Option<bool>,
    /// Max players to return. Default 20.
    pub limit: Option<usize>,
}

#[derive(Debug, Clone, Copy, Deserialize, Serialize, JsonSchema)]
#[serde(rename_all = "snake_case")]
pub enum PlayerSortField {
    Overall,
    Potential,
    Age,
    Name,
}

impl From<PlayerSortField> for PlayerSort {
    fn from(value: PlayerSortField) -> Self {
        match value {
            PlayerSortField::Overall => PlayerSort::Overall,
            PlayerSortField::Potential => PlayerSort::Potential,
            PlayerSortField::Age => PlayerSort::Age,
            PlayerSortField::Name => PlayerSort::Name,
        }
    }
}

#[derive(Debug, Serialize, JsonSchema)]
pub struct ListTeamsResult {
    pub teams: Vec<String>,
    pub count: usize,
}

#[derive(Debug, Serialize, JsonSchema)]
pub struct SearchPlayersResult {
    pub players: Vec<crate::model::PlayerRecord>,
    pub total_count: usize,
}

#[derive(Debug, Serialize, JsonSchema)]
pub struct StandingsResult {
    pub competition: Competition,
    pub season: i32,
    pub table: Vec<StandingRow>,
}

#[derive(Debug, Serialize, JsonSchema)]
pub struct BiggestWinsResult {
    pub matches: Vec<crate::model::MatchRecord>,
}

#[derive(Debug, Serialize, JsonSchema)]
pub struct CompetitionsOverviewResult {
    pub competitions: Vec<CompetitionOverview>,
}

/// The MCP server: a thin, stateless-per-call wrapper around a shared,
/// read-only [`KnowledgeBase`] built once at startup.
#[derive(Clone)]
pub struct BrazilianSoccerServer {
    kb: Arc<KnowledgeBase>,
    tool_router: ToolRouter<Self>,
}

impl BrazilianSoccerServer {
    pub fn new(kb: KnowledgeBase) -> Self {
        Self {
            kb: Arc::new(kb),
            tool_router: Self::tool_router(),
        }
    }
}

#[tool_router]
impl BrazilianSoccerServer {
    /// Find matches by team, opponent, competition, season, and/or date
    /// range. Team names are matched flexibly (state suffixes, accents,
    /// and abbreviated vs. full legal names are all handled). Results are
    /// sorted most-recent first; `total_count` reports how many matches
    /// satisfied the filter even if truncated by `limit`.
    #[tool]
    pub async fn find_matches(
        &self,
        Parameters(req): Parameters<FindMatchesRequest>,
    ) -> Result<Json<FindMatchesResult>, String> {
        let date_from = parse_date(&req.date_from, "date_from")?;
        let date_to = parse_date(&req.date_to, "date_to")?;
        let filter = MatchFilter {
            team: req.team.as_deref(),
            venue: req.venue.unwrap_or_default(),
            opponent: req.opponent.as_deref(),
            competition: req.competition,
            season: req.season,
            season_from: req.season_from,
            season_to: req.season_to,
            date_from,
            date_to,
        };
        let limit = req.limit.unwrap_or(50);
        Ok(Json(self.kb.find_matches(&filter, limit)))
    }

    /// Compute head-to-head history between two teams: win/draw/loss
    /// tallies, aggregate goals, and the matches themselves (newest first).
    #[tool]
    pub async fn head_to_head(
        &self,
        Parameters(req): Parameters<HeadToHeadRequest>,
    ) -> Json<HeadToHeadResult> {
        let limit = req.limit.unwrap_or(20);
        Json(
            self.kb
                .head_to_head(&req.team_a, &req.team_b, req.competition, req.season, limit),
        )
    }

    /// Compute a single team's win/draw/loss record, goals for/against, and
    /// win rate, optionally restricted to a competition, season, and/or
    /// home/away venue.
    #[tool]
    pub async fn team_record(
        &self,
        Parameters(req): Parameters<TeamRecordRequest>,
    ) -> Json<TeamRecordResult> {
        Json(self.kb.team_record(
            &req.team,
            req.competition,
            req.season,
            req.venue.unwrap_or_default(),
        ))
    }

    /// Compute a league table (points, goal difference, W/D/L) for a
    /// competition and season, calculated directly from match results.
    /// Ties are broken using official CBF criteria: points, then wins,
    /// then goal difference, then goals scored.
    #[tool]
    pub async fn standings(
        &self,
        Parameters(req): Parameters<StandingsRequest>,
    ) -> Json<StandingsResult> {
        let competition = req.competition.unwrap_or(Competition::Brasileirao);
        Json(StandingsResult {
            competition,
            season: req.season,
            table: self.kb.standings(competition, req.season),
        })
    }

    /// Find the biggest-margin wins, sorted by absolute goal difference
    /// (ties broken by total goals scored).
    #[tool]
    pub async fn biggest_wins(
        &self,
        Parameters(req): Parameters<BiggestWinsRequest>,
    ) -> Json<BiggestWinsResult> {
        let limit = req.limit.unwrap_or(10);
        Json(BiggestWinsResult {
            matches: self.kb.biggest_wins(req.competition, req.season, limit),
        })
    }

    /// Compute aggregate statistics across matches: average goals per match
    /// (total/home/away) and home-win/draw/away-win rates.
    #[tool]
    pub async fn match_stats(
        &self,
        Parameters(req): Parameters<MatchStatsRequest>,
    ) -> Json<MatchStats> {
        Json(self.kb.match_stats(req.competition, req.season))
    }

    /// List the distinct canonical team names known to the knowledge base,
    /// optionally restricted to a competition and/or season. Useful for
    /// discovering the exact spelling to pass to other tools.
    #[tool]
    pub async fn list_teams(
        &self,
        Parameters(req): Parameters<ListTeamsRequest>,
    ) -> Json<ListTeamsResult> {
        let teams = self.kb.list_teams(req.competition, req.season);
        Json(ListTeamsResult {
            count: teams.len(),
            teams,
        })
    }

    /// List the available competitions/datasets, their match counts, and
    /// the season range they cover.
    #[tool]
    pub async fn list_competitions(&self) -> Json<CompetitionsOverviewResult> {
        Json(CompetitionsOverviewResult {
            competitions: self.kb.competitions_overview(),
        })
    }

    /// Search FIFA player data by name, nationality, club, position, and/or
    /// minimum overall rating.
    #[tool]
    pub async fn search_players(
        &self,
        Parameters(req): Parameters<SearchPlayersRequest>,
    ) -> Json<SearchPlayersResult> {
        let sort_by = req
            .sort_by
            .map(PlayerSort::from)
            .unwrap_or(PlayerSort::Overall);
        let descending = req.descending.unwrap_or(true);
        let filter = PlayerFilter {
            name: req.name.as_deref(),
            nationality: req.nationality.as_deref(),
            club: req.club.as_deref(),
            position: req.position.as_deref(),
            min_overall: req.min_overall,
            limit: req.limit,
        };
        let (players, total_count) = self.kb.search_players(&filter, sort_by, descending);
        Json(SearchPlayersResult {
            players,
            total_count,
        })
    }
}

#[tool_handler(
    router = self.tool_router,
    name = "brazilian-soccer-mcp",
    version = "0.1.0",
    instructions = "Query Brazilian soccer data: matches (Brasileirão, Copa do Brasil, \
        Libertadores, extended stats, historical 2003-2019) and FIFA player data. Team \
        names are matched flexibly (state suffixes, accents, abbreviations). Use \
        list_teams/list_competitions to discover exact names, find_matches/head_to_head/\
        team_record/standings/biggest_wins/match_stats for match queries, and \
        search_players for player queries."
)]
impl ServerHandler for BrazilianSoccerServer {}
