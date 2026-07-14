//! ============================================================================
//! Module: model
//!
//! Context
//! -------
//! Core domain types for the Brazilian Soccer knowledge graph. A `Match` is the
//! central edge connecting two team nodes within a competition/season; a
//! `Player` is a node sourced from the FIFA database. Both carry a normalized
//! key (see `normalize`) alongside their original display strings so that
//! queries can match loosely while output stays human-readable.
//! ============================================================================

use serde::Serialize;

/// Optional extended statistics available only for the BR-Football dataset.
#[derive(Debug, Clone, Serialize, Default)]
pub struct MatchExtras {
    pub home_shots: Option<f64>,
    pub away_shots: Option<f64>,
    pub home_corner: Option<f64>,
    pub away_corner: Option<f64>,
    pub total_corners: Option<f64>,
}

impl MatchExtras {
    pub fn is_empty(&self) -> bool {
        self.home_shots.is_none()
            && self.away_shots.is_none()
            && self.home_corner.is_none()
            && self.away_corner.is_none()
            && self.total_corners.is_none()
    }
}

/// A single soccer match (one edge in the knowledge graph).
#[derive(Debug, Clone, Serialize)]
pub struct Match {
    /// Competition display name, e.g. "Brasileirão Série A".
    pub competition: String,
    /// Season year (e.g. 2019). 0 when unknown.
    pub season: i32,
    /// Round number or tournament stage label ("Round 22", "group stage").
    pub stage: String,
    /// ISO-ish date string ("2019-10-27"). Empty when unavailable.
    pub date: String,
    /// Original home-team display name.
    pub home_team: String,
    /// Original away-team display name.
    pub away_team: String,
    /// Normalized matching key for the home team.
    #[serde(skip)]
    pub home_key: String,
    /// Normalized matching key for the away team.
    #[serde(skip)]
    pub away_key: String,
    pub home_goal: i32,
    pub away_goal: i32,
    /// Source CSV file this record was loaded from.
    pub source: String,
    /// Extended stats (shots/corners), present only for some datasets.
    #[serde(skip_serializing_if = "MatchExtras::is_empty")]
    pub extras: MatchExtras,
}

/// Outcome of a match relative to a given team.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Outcome {
    Win,
    Draw,
    Loss,
}

impl Match {
    /// Total goals scored in the match.
    pub fn total_goals(&self) -> i32 {
        self.home_goal + self.away_goal
    }

    /// Absolute goal difference.
    pub fn margin(&self) -> i32 {
        (self.home_goal - self.away_goal).abs()
    }

    /// Does the match involve the team identified by `key` (home or away)?
    pub fn involves(&self, key: &str) -> bool {
        self.home_key == key || self.away_key == key
    }

    /// Outcome from the perspective of the team identified by `key`.
    /// Returns `None` if the team did not play in this match.
    pub fn outcome_for(&self, key: &str) -> Option<Outcome> {
        let scored;
        let conceded;
        if self.home_key == key {
            scored = self.home_goal;
            conceded = self.away_goal;
        } else if self.away_key == key {
            scored = self.away_goal;
            conceded = self.home_goal;
        } else {
            return None;
        }
        Some(if scored > conceded {
            Outcome::Win
        } else if scored < conceded {
            Outcome::Loss
        } else {
            Outcome::Draw
        })
    }

    /// One-line human-readable summary, e.g.
    /// "2019-10-27: Flamengo 5-0 Grêmio (Brasileirão Série A, Round 31)".
    pub fn summary(&self) -> String {
        let date = if self.date.is_empty() {
            "????-??-??".to_string()
        } else {
            self.date.clone()
        };
        let stage = if self.stage.is_empty() {
            self.competition.clone()
        } else {
            format!("{}, {}", self.competition, self.stage)
        };
        format!(
            "{}: {} {}-{} {} ({})",
            date, self.home_team, self.home_goal, self.away_goal, self.away_team, stage
        )
    }
}

/// A player node sourced from the FIFA database.
#[derive(Debug, Clone, Serialize)]
pub struct Player {
    pub id: String,
    pub name: String,
    pub age: Option<i32>,
    pub nationality: String,
    pub overall: Option<i32>,
    pub potential: Option<i32>,
    pub club: String,
    pub position: String,
    pub jersey: String,
    pub height: String,
    pub weight: String,
    /// Normalized keys for case/accent-insensitive search.
    #[serde(skip)]
    pub name_key: String,
    #[serde(skip)]
    pub nationality_key: String,
    #[serde(skip)]
    pub club_key: String,
}

impl Player {
    pub fn summary(&self) -> String {
        let overall = self
            .overall
            .map(|o| o.to_string())
            .unwrap_or_else(|| "?".to_string());
        let pos = if self.position.is_empty() {
            "?".to_string()
        } else {
            self.position.clone()
        };
        let club = if self.club.is_empty() {
            "Free agent".to_string()
        } else {
            self.club.clone()
        };
        format!(
            "{} - Overall: {}, Position: {}, Club: {}, Nationality: {}",
            self.name, overall, pos, club, self.nationality
        )
    }
}
