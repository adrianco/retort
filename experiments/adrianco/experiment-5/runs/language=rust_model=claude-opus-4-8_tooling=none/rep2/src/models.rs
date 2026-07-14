//! ============================================================================
//! Context
//! ----------------------------------------------------------------------------
//! Module:   models
//! Purpose:  Core domain types for the knowledge graph: `Match` and `Player`.
//!           These are the normalized, in-memory representations that every
//!           CSV row is mapped onto, regardless of which of the six source
//!           files it came from.
//!
//! Design notes:
//!   * `Match` stores both the original team names (for display) and their
//!     normalized keys (for matching), computed once at load time.
//!   * Optionals are used everywhere a field may be missing in a given source
//!     file (e.g. Libertadores has no `round`, the cup has no `stage`).
//!
//! ============================================================================

use crate::normalize::{normalize_team, Date};

/// Result of a match from one team's point of view.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Outcome {
    Win,
    Draw,
    Loss,
}

/// A single soccer match, unified across all source datasets.
#[derive(Debug, Clone)]
pub struct Match {
    /// Canonical competition label, e.g. "Brasileirão", "Copa do Brasil".
    pub competition: String,
    /// Source CSV file the row came from (provenance).
    pub source: String,
    pub date: Option<Date>,
    pub season: Option<i32>,
    pub round: Option<String>,
    pub stage: Option<String>,
    pub home_team: String,
    pub away_team: String,
    pub home_team_norm: String,
    pub away_team_norm: String,
    pub home_goal: Option<u32>,
    pub away_goal: Option<u32>,
}

impl Match {
    /// Build a match, deriving the normalized team keys automatically.
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        competition: impl Into<String>,
        source: impl Into<String>,
        date: Option<Date>,
        season: Option<i32>,
        round: Option<String>,
        stage: Option<String>,
        home_team: impl Into<String>,
        away_team: impl Into<String>,
        home_goal: Option<u32>,
        away_goal: Option<u32>,
    ) -> Self {
        let home_team = home_team.into();
        let away_team = away_team.into();
        let home_team_norm = normalize_team(&home_team);
        let away_team_norm = normalize_team(&away_team);
        Match {
            competition: competition.into(),
            source: source.into(),
            date,
            season,
            round,
            stage,
            home_team,
            away_team,
            home_team_norm,
            away_team_norm,
            home_goal,
            away_goal,
        }
    }

    /// True when both scores are present.
    pub fn has_score(&self) -> bool {
        self.home_goal.is_some() && self.away_goal.is_some()
    }

    /// Whether this row comes from the "extended" BR-Football dataset, which
    /// overlaps (with divergent dates/scores/names) the curated league and cup
    /// files. Such rows are searchable but excluded from aggregates by default
    /// so league tables and statistics are not double-counted.
    pub fn is_extended(&self) -> bool {
        self.source == "BR-Football-Dataset.csv"
    }

    /// Total goals in the match, if scored.
    pub fn total_goals(&self) -> Option<u32> {
        Some(self.home_goal? + self.away_goal?)
    }

    /// Does the given normalized team key play in this match (either side)?
    pub fn involves(&self, team_norm: &str) -> bool {
        use crate::normalize::team_matches;
        team_matches(team_norm, &self.home_team_norm)
            || team_matches(team_norm, &self.away_team_norm)
    }

    /// Outcome from the perspective of `team_norm` (None if no score or the
    /// team is not in this match).
    pub fn outcome_for(&self, team_norm: &str) -> Option<Outcome> {
        use crate::normalize::team_matches;
        let (hg, ag) = (self.home_goal?, self.away_goal?);
        let is_home = team_matches(team_norm, &self.home_team_norm);
        let is_away = team_matches(team_norm, &self.away_team_norm);
        if !is_home && !is_away {
            return None;
        }
        let (gf, ga) = if is_home { (hg, ag) } else { (ag, hg) };
        Some(match gf.cmp(&ga) {
            std::cmp::Ordering::Greater => Outcome::Win,
            std::cmp::Ordering::Equal => Outcome::Draw,
            std::cmp::Ordering::Less => Outcome::Loss,
        })
    }

    /// A short, human-readable one-line summary of the match.
    pub fn summary(&self) -> String {
        let date = self
            .date
            .map(|d| d.to_string())
            .unwrap_or_else(|| "????-??-??".to_string());
        let score = match (self.home_goal, self.away_goal) {
            (Some(h), Some(a)) => format!("{} {}-{} {}", self.home_team, h, a, self.away_team),
            _ => format!("{} vs {}", self.home_team, self.away_team),
        };
        let mut ctx = vec![self.competition.clone()];
        if let Some(r) = &self.round {
            ctx.push(format!("Round {}", r));
        }
        if let Some(s) = &self.stage {
            ctx.push(s.clone());
        }
        format!("{}: {} ({})", date, score, ctx.join(", "))
    }
}

/// A FIFA-database player.
#[derive(Debug, Clone)]
pub struct Player {
    pub id: String,
    pub name: String,
    pub age: Option<u32>,
    pub nationality: String,
    pub overall: Option<u32>,
    pub potential: Option<u32>,
    pub club: String,
    pub position: String,
    pub jersey_number: Option<String>,
    pub height: String,
    pub weight: String,
}

impl Player {
    pub fn summary(&self) -> String {
        let ovr = self
            .overall
            .map(|o| o.to_string())
            .unwrap_or_else(|| "?".to_string());
        let club = if self.club.is_empty() {
            "Free agent".to_string()
        } else {
            self.club.clone()
        };
        format!(
            "{} - Overall: {}, Position: {}, Club: {}",
            self.name, ovr, self.position, club
        )
    }
}
