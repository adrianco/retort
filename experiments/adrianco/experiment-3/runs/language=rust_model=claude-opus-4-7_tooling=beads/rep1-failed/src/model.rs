//! Core domain model.
//!
//! Context: every row from the five match datasets is normalized into a single
//! [`Match`] record, and every FIFA row into a [`Player`]. Storing a
//! pre-computed `match_key` for each club avoids re-normalizing names on every
//! query. Dates are normalized to ISO `YYYY-MM-DD` strings so range filters
//! and sorting work with plain lexical comparison.

/// Outcome of a match from one team's perspective.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Outcome {
    Win,
    Draw,
    Loss,
}

/// Optional extended per-match statistics (only present for rows sourced from
/// `BR-Football-Dataset.csv`).
#[derive(Debug, Clone, Default)]
pub struct MatchStats {
    pub home_corner: i32,
    pub away_corner: i32,
    pub home_shots: i32,
    pub away_shots: i32,
    pub home_attack: i32,
    pub away_attack: i32,
}

/// A single soccer match, unified across every source dataset.
#[derive(Debug, Clone)]
pub struct Match {
    pub competition: String,
    pub season: i32,
    pub round: Option<String>,
    pub stage: Option<String>,
    /// ISO `YYYY-MM-DD`, or empty when the source had no date.
    pub date: String,
    pub home_team: String,
    pub away_team: String,
    pub home_key: String,
    pub away_key: String,
    pub home_goal: i32,
    pub away_goal: i32,
    pub stadium: Option<String>,
    pub source: String,
    pub stats: Option<MatchStats>,
}

impl Match {
    /// Outcome for the team identified by `team_key`. Returns `None` if the
    /// team did not play in this match.
    pub fn outcome_for(&self, team_key: &str) -> Option<Outcome> {
        let home = self.home_key == team_key;
        let away = self.away_key == team_key;
        if !home && !away {
            return None;
        }
        let (gf, ga) = if home {
            (self.home_goal, self.away_goal)
        } else {
            (self.away_goal, self.home_goal)
        };
        Some(match gf.cmp(&ga) {
            std::cmp::Ordering::Greater => Outcome::Win,
            std::cmp::Ordering::Equal => Outcome::Draw,
            std::cmp::Ordering::Less => Outcome::Loss,
        })
    }

    /// True when both supplied keys are the two teams in this match.
    pub fn involves(&self, key_a: &str, key_b: &str) -> bool {
        (self.home_key == key_a && self.away_key == key_b)
            || (self.home_key == key_b && self.away_key == key_a)
    }

    /// Total goals scored in the match.
    pub fn total_goals(&self) -> i32 {
        self.home_goal + self.away_goal
    }

    /// Absolute goal margin.
    pub fn margin(&self) -> i32 {
        (self.home_goal - self.away_goal).abs()
    }

    /// One-line human-readable score line, e.g.
    /// `2023-09-03: Flamengo 2-1 Fluminense (Brasileirão Série A, Round 22)`.
    pub fn summary(&self) -> String {
        let date = if self.date.is_empty() {
            "(date n/a)".to_string()
        } else {
            self.date.clone()
        };
        let mut ctx = self.competition.clone();
        if let Some(r) = &self.round {
            if !r.is_empty() {
                ctx.push_str(&format!(", Round {r}"));
            }
        }
        if let Some(s) = &self.stage {
            if !s.is_empty() {
                ctx.push_str(&format!(", {s}"));
            }
        }
        ctx.push_str(&format!(", {}", self.season));
        format!(
            "{date}: {} {}-{} {} ({ctx})",
            self.home_team, self.home_goal, self.away_goal, self.away_team
        )
    }
}

/// A FIFA player record (subset of the columns most useful for queries).
#[derive(Debug, Clone)]
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
}

impl Player {
    /// One-line summary, e.g. `Neymar Jr — Overall 92, LW, Paris Saint-Germain`.
    pub fn summary(&self) -> String {
        let ovr = self
            .overall
            .map(|v| v.to_string())
            .unwrap_or_else(|| "?".into());
        let pos = if self.position.is_empty() {
            "?"
        } else {
            &self.position
        };
        let club = if self.club.is_empty() {
            "(no club)"
        } else {
            &self.club
        };
        format!("{} — Overall {ovr}, {pos}, {club}", self.name)
    }
}
