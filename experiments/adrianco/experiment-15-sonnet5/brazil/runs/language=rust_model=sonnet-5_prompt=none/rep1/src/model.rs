//! Unified in-memory data model shared by every dataset loader.

use chrono::NaiveDate;

/// A single match, normalized from any of the five match-level datasets.
#[derive(Debug, Clone)]
pub struct MatchRecord {
    /// Which dataset file this record was loaded from (for provenance).
    pub source_file: &'static str,
    /// Competition/tournament label as given by the source dataset
    /// (e.g. "Brasileirao Serie A", "Copa do Brasil", "Copa Libertadores").
    pub competition: String,
    /// Match date, if parseable.
    pub date: Option<NaiveDate>,
    /// Raw date/time string for display purposes.
    pub date_display: String,
    pub season: Option<i32>,
    pub round: Option<String>,
    pub stage: Option<String>,
    pub venue: Option<String>,
    pub home_team: String,
    pub away_team: String,
    /// Loose, state-stripped comparison key (may be shared by distinct
    /// clubs, e.g. Atletico-MG and Atletico-GO both key to "atletico").
    /// Used for lenient search/browsing.
    pub home_team_key: String,
    pub away_team_key: String,
    /// Two-letter state code as embedded in the source dataset, if any.
    pub home_state: Option<String>,
    pub away_state: Option<String>,
    /// Unique team identity: same as `*_team_key` unless that key is
    /// ambiguous across states in the loaded data, in which case the state
    /// is folded back in. Set by `Store::load` once every dataset has been
    /// read. Used for aggregate stats (standings, records) where merging
    /// distinct clubs would silently corrupt the numbers.
    pub home_identity: String,
    pub away_identity: String,
    pub home_goal: Option<i32>,
    pub away_goal: Option<i32>,
}

impl MatchRecord {
    pub fn has_result(&self) -> bool {
        self.home_goal.is_some() && self.away_goal.is_some()
    }

    /// Outcome from the home team's perspective: 1 = win, 0 = draw, -1 = loss.
    pub fn home_outcome(&self) -> Option<i32> {
        match (self.home_goal, self.away_goal) {
            (Some(h), Some(a)) => Some((h - a).signum()),
            _ => None,
        }
    }

    pub fn goal_diff(&self) -> Option<i32> {
        match (self.home_goal, self.away_goal) {
            (Some(h), Some(a)) => Some((h - a).abs()),
            _ => None,
        }
    }
}

/// A player entry from the FIFA player dataset.
#[derive(Debug, Clone)]
pub struct Player {
    pub id: i64,
    pub name: String,
    pub age: Option<i32>,
    pub nationality: String,
    pub overall: Option<i32>,
    pub potential: Option<i32>,
    pub club: String,
    pub club_key: String,
    pub position: String,
}
