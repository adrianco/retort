//! Core data structures for matches and players.

use crate::normalize::{canon, normalize_club};

/// A single match, unified across all of the provided CSV schemas.
#[derive(Clone, Debug)]
pub struct Match {
    pub competition: String,
    /// ISO date `YYYY-MM-DD` (empty when unknown).
    pub date: String,
    pub season: Option<i32>,
    pub round: Option<String>,
    pub stage: Option<String>,
    /// Raw home/away names as found in the source file.
    pub home_team: String,
    pub away_team: String,
    /// Canonical lookup keys (accent-free, lower-case).
    pub home_key: String,
    pub away_key: String,
    /// Canonical display names.
    pub home_display: String,
    pub away_display: String,
    pub home_goal: i32,
    pub away_goal: i32,
    pub source: String,
    // Optional extended statistics (only present in BR-Football-Dataset).
    pub home_shots: Option<f64>,
    pub away_shots: Option<f64>,
    pub home_corner: Option<f64>,
    pub away_corner: Option<f64>,
}

impl Match {
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        competition: impl Into<String>,
        date: String,
        season: Option<i32>,
        home_team: impl Into<String>,
        away_team: impl Into<String>,
        home_goal: i32,
        away_goal: i32,
        source: impl Into<String>,
    ) -> Self {
        let home_team = home_team.into();
        let away_team = away_team.into();
        let home = canon(&home_team);
        let away = canon(&away_team);
        Match {
            competition: competition.into(),
            date,
            season,
            round: None,
            stage: None,
            home_team,
            away_team,
            home_key: home.key,
            away_key: away.key,
            home_display: home.display,
            away_display: away.display,
            home_goal,
            away_goal,
            source: source.into(),
            home_shots: None,
            away_shots: None,
            home_corner: None,
            away_corner: None,
        }
    }

    /// Stable key used to deduplicate the same real-world match that appears
    /// in more than one dataset.
    /// Key used to merge the same fixture appearing in several datasets.
    ///
    /// Deliberately excludes the match date: the BR-Football dataset records
    /// some matches a day off (timezone shift) from the other sources. Within a
    /// single competition + season a given (home, away, score) fixture is
    /// effectively unique, so this still merges duplicates without collapsing
    /// the home and away legs of a tie (their orientation differs).
    pub fn dedup_key(&self) -> String {
        format!(
            "{}|{}|{}|{}|{}|{}",
            self.competition,
            self.season.unwrap_or(0),
            self.home_key,
            self.away_key,
            self.home_goal,
            self.away_goal
        )
    }

    /// Does this match involve the club with canonical key `team_key`?
    pub fn involves(&self, team_key: &str) -> bool {
        self.home_key == team_key || self.away_key == team_key
    }

    pub fn total_goals(&self) -> i32 {
        self.home_goal + self.away_goal
    }
}

/// A FIFA player record.
#[derive(Clone, Debug)]
pub struct Player {
    pub id: String,
    pub name: String,
    pub age: Option<i32>,
    pub nationality: String,
    pub overall: Option<i32>,
    pub potential: Option<i32>,
    pub club: String,
    pub club_norm: String,
    pub position: String,
    pub jersey: Option<String>,
    pub height: String,
    pub weight: String,
}

impl Player {
    pub fn with_norms(mut self) -> Self {
        self.club_norm = normalize_club(&self.club);
        self
    }
}
