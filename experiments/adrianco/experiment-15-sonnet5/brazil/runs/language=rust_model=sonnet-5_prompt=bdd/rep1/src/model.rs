//! Unified domain model shared by all six source datasets.

use chrono::NaiveDate;
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

/// The competition/source dataset a match belongs to.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize, JsonSchema)]
#[serde(rename_all = "snake_case")]
pub enum Competition {
    /// `Brasileirao_Matches.csv` - Série A, 2012-2023.
    Brasileirao,
    /// `Brazilian_Cup_Matches.csv` - Copa do Brasil knockout matches.
    CopaDoBrasil,
    /// `Libertadores_Matches.csv` - Copa Libertadores.
    Libertadores,
    /// `BR-Football-Dataset.csv` - extended stats covering Série A/B/C and
    /// Copa do Brasil, with corners/shots detail. Use `tournament` on the
    /// match record to filter within this source.
    ExtendedStats,
    /// `novo_campeonato_brasileiro.csv` - historical Brasileirão, 2003-2019.
    HistoricalBrasileirao,
}

impl Competition {
    pub fn label(self) -> &'static str {
        match self {
            Competition::Brasileirao => "Brasileirão Série A",
            Competition::CopaDoBrasil => "Copa do Brasil",
            Competition::Libertadores => "Copa Libertadores",
            Competition::ExtendedStats => "Extended Match Statistics (Série A/B/C, Copa do Brasil)",
            Competition::HistoricalBrasileirao => "Historical Brasileirão (2003-2019)",
        }
    }
}

impl std::fmt::Display for Competition {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.label())
    }
}

/// Which side of the match a team filter should apply to.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Serialize, Deserialize, JsonSchema)]
#[serde(rename_all = "snake_case")]
pub enum Venue {
    #[default]
    Either,
    Home,
    Away,
}

/// The outcome of a match from the home team's perspective.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MatchOutcome {
    Home,
    Away,
    Draw,
}

/// A single match, normalized into a common shape regardless of which of
/// the five match datasets it originated from.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct MatchRecord {
    pub competition: Competition,
    /// Sub-tournament label, populated only for `ExtendedStats` rows
    /// (e.g. "Serie A", "Serie B", "Serie C", "Copa do Brasil").
    pub tournament: Option<String>,
    /// ISO date (YYYY-MM-DD), when parseable from the source dataset.
    #[schemars(with = "Option<String>")]
    pub date: Option<NaiveDate>,
    pub season: i32,
    pub round: Option<String>,
    /// Tournament stage, populated only for Libertadores rows.
    pub stage: Option<String>,
    pub home_team: String,
    pub away_team: String,
    /// Normalized lookup key for `home_team`, used internally for matching.
    #[serde(skip)]
    pub home_team_key: String,
    /// Normalized lookup key for `away_team`, used internally for matching.
    #[serde(skip)]
    pub away_team_key: String,
    pub home_goal: u32,
    pub away_goal: u32,
    /// Stadium name, populated only for `HistoricalBrasileirao` rows.
    pub venue: Option<String>,
    pub home_corners: Option<f64>,
    pub away_corners: Option<f64>,
    pub home_shots: Option<f64>,
    pub away_shots: Option<f64>,
}

impl MatchRecord {
    pub fn outcome(&self) -> MatchOutcome {
        use std::cmp::Ordering::*;
        match self.home_goal.cmp(&self.away_goal) {
            Greater => MatchOutcome::Home,
            Less => MatchOutcome::Away,
            Equal => MatchOutcome::Draw,
        }
    }

    pub fn goal_difference(&self) -> i32 {
        self.home_goal as i32 - self.away_goal as i32
    }

    pub fn total_goals(&self) -> u32 {
        self.home_goal + self.away_goal
    }
}

/// A player row from the FIFA player database.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct PlayerRecord {
    pub id: u64,
    pub name: String,
    pub age: Option<u32>,
    pub nationality: String,
    pub overall: Option<u32>,
    pub potential: Option<u32>,
    pub club: Option<String>,
    pub position: Option<String>,
    pub jersey_number: Option<u32>,
    pub height: Option<String>,
    pub weight: Option<String>,
    #[serde(skip)]
    pub nationality_key: String,
    #[serde(skip)]
    pub club_key: String,
    #[serde(skip)]
    pub name_key: String,
}
