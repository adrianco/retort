// =============================================================================
// Context: Brazilian Soccer MCP Server
// File:    src/model.rs
// Purpose: Core domain types shared across the loader and query layers.
//
//          `Match` is a competition-agnostic representation of a single game,
//          unified from five differently-shaped CSV files. `Player` is a slim
//          projection of the FIFA player database keeping only the fields the
//          query tools expose. `MatchOutcome` and the small helpers on `Match`
//          centralise the win/draw/loss logic the statistics tools rely on.
// =============================================================================

use serde::Serialize;

/// The result of a match from the perspective of one of its teams.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MatchOutcome {
    Win,
    Draw,
    Loss,
}

/// A single match, normalized from any of the provided datasets.
#[derive(Debug, Clone, Serialize)]
pub struct Match {
    /// Canonical competition label (e.g. "Brasileirão Série A", "Copa do Brasil").
    pub competition: String,
    /// ISO date "YYYY-MM-DD" when derivable, otherwise None.
    pub date: Option<String>,
    /// Season year.
    pub season: i32,
    /// Round / matchday label when available.
    pub round: Option<String>,
    /// Tournament stage (group stage, knockout, ...) when available.
    pub stage: Option<String>,
    /// Home team as printed in the source file.
    pub home_team: String,
    /// Away team as printed in the source file.
    pub away_team: String,
    pub home_goal: i32,
    pub away_goal: i32,
    /// Stadium / arena when available.
    pub arena: Option<String>,
    /// Which CSV the record came from.
    pub source: String,
}

impl Match {
    /// Outcome for the home side.
    pub fn home_outcome(&self) -> MatchOutcome {
        match self.home_goal.cmp(&self.away_goal) {
            std::cmp::Ordering::Greater => MatchOutcome::Win,
            std::cmp::Ordering::Less => MatchOutcome::Loss,
            std::cmp::Ordering::Equal => MatchOutcome::Draw,
        }
    }

    /// Outcome for a given team key (must match one side of the fixture).
    pub fn outcome_for(&self, is_home: bool) -> MatchOutcome {
        let home = self.home_outcome();
        if is_home {
            home
        } else {
            match home {
                MatchOutcome::Win => MatchOutcome::Loss,
                MatchOutcome::Loss => MatchOutcome::Win,
                MatchOutcome::Draw => MatchOutcome::Draw,
            }
        }
    }

    /// A short human-readable scoreline, e.g. "Flamengo 2-1 Fluminense".
    pub fn scoreline(&self) -> String {
        format!(
            "{} {}-{} {}",
            self.home_team, self.home_goal, self.away_goal, self.away_team
        )
    }
}

/// A slim FIFA player record.
#[derive(Debug, Clone, Serialize)]
pub struct Player {
    pub id: String,
    pub name: String,
    pub age: Option<i32>,
    pub nationality: String,
    pub overall: i32,
    pub potential: i32,
    pub club: String,
    pub position: String,
    pub jersey_number: Option<String>,
    pub height: Option<String>,
    pub weight: Option<String>,
}
