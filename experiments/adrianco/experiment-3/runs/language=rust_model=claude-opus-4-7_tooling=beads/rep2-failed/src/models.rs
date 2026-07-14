//! Domain models for the Brazilian Soccer MCP server.
//!
//! Defines the lightweight value types used across the crate: a dependency-free
//! `Date`, a `Match` record normalized from any of the five match CSVs, and a
//! `Player` record from the FIFA dataset. Keeping these free of external crates
//! (no `chrono`) keeps the build small and the data model easy to reason about.

/// A calendar date with no time component.
///
/// Field order (year, month, day) makes the derived `Ord` a correct
/// chronological ordering, which match queries rely on for date-range filters
/// and recency sorting.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct Date {
    pub year: i32,
    pub month: u32,
    pub day: u32,
}

impl Date {
    /// Render as an ISO-8601 `YYYY-MM-DD` string.
    pub fn iso(&self) -> String {
        format!("{:04}-{:02}-{:02}", self.year, self.month, self.day)
    }
}

/// The competition a match belongs to, after canonicalization.
pub mod competition {
    pub const SERIE_A: &str = "Brasileirão Série A";
    pub const SERIE_B: &str = "Brasileirão Série B";
    pub const SERIE_C: &str = "Brasileirão Série C";
    pub const COPA_DO_BRASIL: &str = "Copa do Brasil";
    pub const LIBERTADORES: &str = "Copa Libertadores";
}

/// A single soccer match, normalized from one of the match CSV files.
#[derive(Debug, Clone)]
pub struct Match {
    /// Canonical competition name (see `models::competition`).
    pub competition: String,
    /// Season year.
    pub season: i32,
    /// Kick-off date, if parseable from the source row.
    pub date: Option<Date>,
    /// League round number (when applicable), as a free-form string.
    pub round: Option<String>,
    /// Tournament stage, e.g. "group stage" / "final" (Libertadores).
    pub stage: Option<String>,
    /// Home team display name (state/country suffix stripped, accents kept).
    pub home: String,
    /// Away team display name.
    pub away: String,
    /// Normalized matching key for the home team (lower-case, accent-free).
    pub home_key: String,
    /// Normalized matching key for the away team.
    pub away_key: String,
    pub home_goal: i32,
    pub away_goal: i32,
    /// Source CSV file name — used to de-duplicate overlapping datasets.
    pub dataset: String,
}

/// Outcome of a match from the home team's perspective.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Outcome {
    HomeWin,
    AwayWin,
    Draw,
}

impl Match {
    /// The outcome of the match.
    pub fn outcome(&self) -> Outcome {
        if self.home_goal > self.away_goal {
            Outcome::HomeWin
        } else if self.away_goal > self.home_goal {
            Outcome::AwayWin
        } else {
            Outcome::Draw
        }
    }

    /// Total goals scored in the match.
    pub fn total_goals(&self) -> i32 {
        self.home_goal + self.away_goal
    }

    /// Absolute goal margin (size of the winning margin).
    pub fn margin(&self) -> i32 {
        (self.home_goal - self.away_goal).abs()
    }

    /// A compact one-line score string, e.g. `Flamengo 2-1 Fluminense`.
    pub fn score_line(&self) -> String {
        format!(
            "{} {}-{} {}",
            self.home, self.home_goal, self.away_goal, self.away
        )
    }

    /// ISO date string, or `"date unknown"` when the row had no usable date.
    pub fn date_str(&self) -> String {
        self.date
            .map(|d| d.iso())
            .unwrap_or_else(|| "date unknown".to_string())
    }
}

/// A FIFA player record (subset of the ~90 columns in `fifa_data.csv`).
#[derive(Debug, Clone)]
pub struct Player {
    pub id: i64,
    pub name: String,
    /// Normalized matching key for the name (lower-case, accent-free).
    pub name_key: String,
    pub age: i32,
    pub nationality: String,
    pub overall: i32,
    pub potential: i32,
    pub club: String,
    pub position: String,
    pub jersey: Option<i32>,
    pub height: String,
    pub weight: String,
    pub value: String,
}
