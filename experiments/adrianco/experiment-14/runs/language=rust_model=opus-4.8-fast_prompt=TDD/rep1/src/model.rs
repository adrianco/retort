// model - core domain types shared across the loaders and query engine.
//
// A `Match` is the unified representation of one game drawn from any of the
// five match datasets; a `Player` is one row of the FIFA player database.
// `Competition` distinguishes the tournaments, and `parse_date` reconciles the
// several date formats the datasets use into a single ISO `YYYY-MM-DD` string.

use crate::normalize::{canonical_id, normalize_team};

/// The competitions represented across the datasets.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Competition {
    Brasileirao,
    CopaDoBrasil,
    Libertadores,
    /// Any other tournament label (from the extended BR-Football dataset).
    Other(String),
}

impl Competition {
    /// Human-readable competition name.
    pub fn display_name(&self) -> String {
        match self {
            Competition::Brasileirao => "Brasileirão".to_string(),
            Competition::CopaDoBrasil => "Copa do Brasil".to_string(),
            Competition::Libertadores => "Copa Libertadores".to_string(),
            Competition::Other(s) => s.clone(),
        }
    }

    /// Best-effort classification of a free-text tournament label.
    pub fn from_label(label: &str) -> Competition {
        let l = label.to_lowercase();
        if l.contains("libertadores") {
            Competition::Libertadores
        } else if l.contains("copa do brasil") || l.contains("brazilian cup") {
            Competition::CopaDoBrasil
        } else if l.contains("brasileir") || l.contains("serie a") || l.contains("série a") {
            Competition::Brasileirao
        } else {
            Competition::Other(label.to_string())
        }
    }
}

/// The result of a match from the home team's perspective.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MatchResult {
    HomeWin,
    AwayWin,
    Draw,
}

/// A single match, unified across all match datasets.
#[derive(Debug, Clone)]
pub struct Match {
    pub competition: Competition,
    pub season: i32,
    /// ISO date `YYYY-MM-DD` when known.
    pub date: Option<String>,
    pub round: Option<String>,
    pub stage: Option<String>,
    pub home_team: String,
    pub away_team: String,
    pub home_state: Option<String>,
    pub away_state: Option<String>,
    pub home_goal: u32,
    pub away_goal: u32,
    /// Provenance priority used for de-duplication: lower wins. The cleanest,
    /// most complete dataset for a given competition+season gets the lowest
    /// number, so overlapping rows from secondary datasets are dropped.
    pub source_priority: u8,
}

impl Match {
    /// Canonical key for the home team.
    pub fn home_key(&self) -> String {
        normalize_team(&self.home_team)
    }

    /// Canonical key for the away team.
    pub fn away_key(&self) -> String {
        normalize_team(&self.away_team)
    }

    /// Strict club identity for the home team (state code retained).
    pub fn home_id(&self) -> String {
        canonical_id(&self.home_team)
    }

    /// Strict club identity for the away team (state code retained).
    pub fn away_id(&self) -> String {
        canonical_id(&self.away_team)
    }

    /// True if the given (already-normalized) team key played in this match.
    pub fn involves(&self, team_key: &str) -> bool {
        self.home_key() == team_key || self.away_key() == team_key
    }

    /// Result from the home team's perspective.
    pub fn result(&self) -> MatchResult {
        if self.home_goal > self.away_goal {
            MatchResult::HomeWin
        } else if self.away_goal > self.home_goal {
            MatchResult::AwayWin
        } else {
            MatchResult::Draw
        }
    }

    /// Total goals scored in the match.
    pub fn total_goals(&self) -> u32 {
        self.home_goal + self.away_goal
    }
}

/// One row of the FIFA player database (subset of the many columns).
#[derive(Debug, Clone)]
pub struct Player {
    pub id: i64,
    pub name: String,
    pub age: Option<u32>,
    pub nationality: String,
    pub overall: u32,
    pub potential: u32,
    pub club: String,
    pub position: String,
}

/// Normalize one of the dataset date formats into ISO `YYYY-MM-DD`.
///
/// Accepts:
///   "2023-09-24"            -> "2023-09-24"
///   "2012-05-19 18:30:00"   -> "2012-05-19"
///   "29/03/2003"            -> "2003-03-29"
/// Returns `None` if the input does not match a recognised shape.
pub fn parse_date(raw: &str) -> Option<String> {
    let raw = raw.trim();
    if raw.is_empty() {
        return None;
    }
    // Drop any time component separated by a space.
    let date_part = raw.split_whitespace().next().unwrap_or(raw);

    if date_part.contains('/') {
        // DD/MM/YYYY
        let parts: Vec<&str> = date_part.split('/').collect();
        if parts.len() == 3 {
            let (d, m, y) = (parts[0], parts[1], parts[2]);
            if d.len() <= 2 && m.len() <= 2 && y.len() == 4 && all_digits(&[d, m, y]) {
                return Some(format!("{}-{:0>2}-{:0>2}", y, m, d));
            }
        }
        return None;
    }

    if date_part.contains('-') {
        // YYYY-MM-DD
        let parts: Vec<&str> = date_part.split('-').collect();
        if parts.len() == 3 {
            let (y, m, d) = (parts[0], parts[1], parts[2]);
            if y.len() == 4 && all_digits(&[y, m, d]) {
                return Some(format!("{}-{:0>2}-{:0>2}", y, m, d));
            }
        }
        return None;
    }

    None
}

fn all_digits(parts: &[&str]) -> bool {
    parts
        .iter()
        .all(|p| !p.is_empty() && p.chars().all(|c| c.is_ascii_digit()))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn competition_display_and_classification() {
        assert_eq!(Competition::Brasileirao.display_name(), "Brasileirão");
        assert_eq!(
            Competition::from_label("Copa Libertadores 2018"),
            Competition::Libertadores
        );
        assert_eq!(
            Competition::from_label("Copa do Brasil"),
            Competition::CopaDoBrasil
        );
        assert_eq!(
            Competition::from_label("Campeonato Brasileiro Série A"),
            Competition::Brasileirao
        );
        assert_eq!(
            Competition::from_label("Recopa"),
            Competition::Other("Recopa".to_string())
        );
    }

    fn sample_match(hg: u32, ag: u32) -> Match {
        Match {
            competition: Competition::Brasileirao,
            season: 2019,
            date: Some("2019-10-27".to_string()),
            round: Some("30".to_string()),
            stage: None,
            home_team: "Flamengo-RJ".to_string(),
            away_team: "Grêmio".to_string(),
            home_state: Some("RJ".to_string()),
            away_state: Some("RS".to_string()),
            home_goal: hg,
            away_goal: ag,
            source_priority: 0,
        }
    }

    #[test]
    fn match_result_classification() {
        assert_eq!(sample_match(5, 0).result(), MatchResult::HomeWin);
        assert_eq!(sample_match(0, 2).result(), MatchResult::AwayWin);
        assert_eq!(sample_match(1, 1).result(), MatchResult::Draw);
    }

    #[test]
    fn match_keys_are_normalized() {
        let m = sample_match(2, 1);
        assert_eq!(m.home_key(), "flamengo");
        assert_eq!(m.away_key(), "gremio");
        assert!(m.involves("flamengo"));
        assert!(m.involves("gremio"));
        assert!(!m.involves("santos"));
    }

    #[test]
    fn total_goals_sums() {
        assert_eq!(sample_match(3, 2).total_goals(), 5);
    }

    #[test]
    fn parse_iso_date() {
        assert_eq!(parse_date("2023-09-24").as_deref(), Some("2023-09-24"));
    }

    #[test]
    fn parse_iso_datetime_drops_time() {
        assert_eq!(
            parse_date("2012-05-19 18:30:00").as_deref(),
            Some("2012-05-19")
        );
    }

    #[test]
    fn parse_brazilian_date() {
        assert_eq!(parse_date("29/03/2003").as_deref(), Some("2003-03-29"));
        // single-digit day/month get zero-padded
        assert_eq!(parse_date("1/4/2005").as_deref(), Some("2005-04-01"));
    }

    #[test]
    fn parse_rejects_garbage() {
        assert_eq!(parse_date(""), None);
        assert_eq!(parse_date("not a date"), None);
    }
}
