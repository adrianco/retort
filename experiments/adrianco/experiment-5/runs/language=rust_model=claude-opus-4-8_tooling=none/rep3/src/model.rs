//! ============================================================================
//! Module: model
//! Project: Brazilian Soccer MCP Server (Rust)
//!
//! Context:
//!   Defines the core domain types used across the whole server: `Match` (a
//!   single game from any of the five match CSVs) and `Player` (a row from the
//!   FIFA player database). These structs are the normalized, in-memory
//!   representation that every query operates on. The raw CSVs use different
//!   column names, date formats, score encodings (int vs float vs quoted
//!   string) and team-name conventions; the loader (`loader.rs`) is responsible
//!   for converting all of that into the uniform shape declared here.
//!
//!   `Match` carries both the normalized team name (for matching/grouping) and
//!   the original raw name (for faithful display), plus a normalized ISO date
//!   and a `Competition` enum so cross-file queries are consistent.
//! ============================================================================

use serde::Serialize;

/// The competitions represented across the provided datasets.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
pub enum Competition {
    Brasileirao,
    CopaDoBrasil,
    Libertadores,
    SerieB,
    SerieC,
    /// Anything we could not classify into one of the above.
    Other,
}

impl Competition {
    /// Human-readable label used in formatted answers.
    pub fn label(&self) -> &'static str {
        match self {
            Competition::Brasileirao => "Brasileirão",
            Competition::CopaDoBrasil => "Copa do Brasil",
            Competition::Libertadores => "Copa Libertadores",
            Competition::SerieB => "Serie B",
            Competition::SerieC => "Serie C",
            Competition::Other => "Other",
        }
    }

    /// Classify a free-text competition/tournament string.
    pub fn from_text(s: &str) -> Competition {
        let l = s.to_lowercase();
        if l.contains("libertadores") {
            Competition::Libertadores
        } else if l.contains("copa do brasil") || l.contains("cup") {
            Competition::CopaDoBrasil
        } else if l.contains("serie b") {
            Competition::SerieB
        } else if l.contains("serie c") {
            Competition::SerieC
        } else if l.contains("serie a")
            || l.contains("brasileir")
            || l.contains("campeonato brasileiro")
        {
            Competition::Brasileirao
        } else {
            Competition::Other
        }
    }
}

/// A single match (game) from any of the match datasets, normalized.
#[derive(Debug, Clone, Serialize)]
pub struct Match {
    pub competition: Competition,
    /// Normalized date as `YYYY-MM-DD` (best effort; empty if unknown).
    pub date: String,
    /// Normalized (suffix-stripped) home team name, used for matching.
    pub home_team: String,
    /// Normalized away team name, used for matching.
    pub away_team: String,
    /// Original home team name as it appears in the source file.
    pub home_team_raw: String,
    /// Original away team name as it appears in the source file.
    pub away_team_raw: String,
    pub home_goal: i32,
    pub away_goal: i32,
    pub season: Option<i32>,
    /// Round / stage descriptor when available (e.g. "22", "group stage").
    pub round: Option<String>,
    /// Source CSV file the match was loaded from.
    pub source: &'static str,
}

impl Match {
    /// Returns the normalized winner: Some(team) or None for a draw.
    pub fn winner(&self) -> Option<&str> {
        if self.home_goal > self.away_goal {
            Some(&self.home_team)
        } else if self.away_goal > self.home_goal {
            Some(&self.away_team)
        } else {
            None
        }
    }

    /// Total goals in the match.
    pub fn total_goals(&self) -> i32 {
        self.home_goal + self.away_goal
    }
}

/// A player row from the FIFA dataset (subset of the many available columns).
#[derive(Debug, Clone, Serialize)]
pub struct Player {
    pub id: i64,
    pub name: String,
    pub age: Option<i32>,
    pub nationality: String,
    pub overall: i32,
    pub potential: i32,
    pub club: String,
    pub position: String,
    pub jersey_number: Option<i32>,
    pub height: String,
    pub weight: String,
}
