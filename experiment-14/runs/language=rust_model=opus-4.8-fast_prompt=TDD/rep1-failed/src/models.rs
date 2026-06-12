//! Core domain types shared across the knowledge base: [`Competition`],
//! [`Match`], [`Player`] and the small parsing helpers used while loading the
//! CSV datasets.

use crate::normalize;
use serde::Serialize;

/// A competition a match belongs to.
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Competition {
    Brasileirao,
    CopaDoBrasil,
    Libertadores,
    /// Any other competition named in the extended-statistics dataset.
    Other(String),
}

impl Competition {
    /// Human-facing competition name.
    pub fn display_name(&self) -> String {
        match self {
            Competition::Brasileirao => "Brasileirão".to_string(),
            Competition::CopaDoBrasil => "Copa do Brasil".to_string(),
            Competition::Libertadores => "Copa Libertadores".to_string(),
            Competition::Other(name) => name.clone(),
        }
    }

    /// Classify a free-text tournament label (from `BR-Football-Dataset.csv`)
    /// into a known competition where possible.
    pub fn from_tournament(label: &str) -> Competition {
        let key = normalize::normalize_key(label);
        if key.contains("libertadores") {
            Competition::Libertadores
        } else if key.contains("copa do brasil") {
            Competition::CopaDoBrasil
        } else if key.contains("brasileir") || key.contains("serie a") {
            Competition::Brasileirao
        } else {
            Competition::Other(label.trim().to_string())
        }
    }
}

/// The outcome of a match from the home team's perspective.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Outcome {
    HomeWin,
    AwayWin,
    Draw,
}

/// A single match result.
#[derive(Debug, Clone, Serialize)]
pub struct Match {
    pub competition: Competition,
    /// Display name of the home team (state/country suffix removed).
    pub home_team: String,
    /// Display name of the away team.
    pub away_team: String,
    pub home_goal: u32,
    pub away_goal: u32,
    /// Season year.
    pub season: i32,
    /// Match date in ISO `YYYY-MM-DD` form, when known.
    pub date: Option<String>,
    /// Round label (league round number or cup round), when known.
    pub round: Option<String>,
    /// Tournament stage (Libertadores group stage / knockout), when known.
    pub stage: Option<String>,
}

impl Match {
    /// Canonical lookup key for the home team.
    pub fn home_key(&self) -> String {
        normalize::normalize_key(&self.home_team)
    }

    /// Canonical lookup key for the away team.
    pub fn away_key(&self) -> String {
        normalize::normalize_key(&self.away_team)
    }

    /// True when the given normalized key is the home or away team.
    pub fn involves(&self, key: &str) -> bool {
        self.home_key() == key || self.away_key() == key
    }

    /// The outcome from the home team's perspective.
    pub fn outcome(&self) -> Outcome {
        use std::cmp::Ordering::*;
        match self.home_goal.cmp(&self.away_goal) {
            Greater => Outcome::HomeWin,
            Less => Outcome::AwayWin,
            Equal => Outcome::Draw,
        }
    }

    /// Total goals scored in the match.
    pub fn total_goals(&self) -> u32 {
        self.home_goal + self.away_goal
    }

    /// Goal difference, absolute value (margin of victory).
    pub fn margin(&self) -> u32 {
        self.home_goal.abs_diff(self.away_goal)
    }
}

/// A FIFA player record.
#[derive(Debug, Clone, Serialize)]
pub struct Player {
    pub id: u64,
    pub name: String,
    pub age: Option<u32>,
    pub nationality: String,
    pub overall: Option<u32>,
    pub potential: Option<u32>,
    pub club: String,
    pub position: String,
}

/// Parse the many date encodings in the datasets into ISO `YYYY-MM-DD`.
///
/// Accepts:
///   * `"2023-09-24"`            (already ISO)
///   * `"2012-05-19 18:30:00"`   (ISO with time)
///   * `"29/03/2003"`            (Brazilian DD/MM/YYYY)
///
/// Returns `None` for empty or unrecognizable input.
pub fn parse_date(raw: &str) -> Option<String> {
    let s = raw.trim();
    if s.is_empty() {
        return None;
    }
    // ISO, optionally with a trailing time component.
    if let Some(date_part) = s.split([' ', 'T']).next() {
        if is_iso_date(date_part) {
            return Some(date_part.to_string());
        }
    }
    // Brazilian DD/MM/YYYY.
    let parts: Vec<&str> = s.split('/').collect();
    if parts.len() == 3 {
        let (d, m, y) = (parts[0], parts[1], parts[2]);
        if d.len() <= 2 && m.len() <= 2 && y.len() == 4 && parts.iter().all(|p| all_digits(p)) {
            return Some(format!(
                "{:04}-{:02}-{:02}",
                y.parse::<u32>().ok()?,
                m.parse::<u32>().ok()?,
                d.parse::<u32>().ok()?
            ));
        }
    }
    None
}

fn all_digits(s: &str) -> bool {
    !s.is_empty() && s.chars().all(|c| c.is_ascii_digit())
}

fn is_iso_date(s: &str) -> bool {
    let parts: Vec<&str> = s.split('-').collect();
    parts.len() == 3
        && parts[0].len() == 4
        && all_digits(parts[0])
        && all_digits(parts[1])
        && all_digits(parts[2])
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn competition_display_names() {
        assert_eq!(Competition::Brasileirao.display_name(), "Brasileirão");
        assert_eq!(Competition::CopaDoBrasil.display_name(), "Copa do Brasil");
        assert_eq!(Competition::Libertadores.display_name(), "Copa Libertadores");
        assert_eq!(
            Competition::Other("Friendly".into()).display_name(),
            "Friendly"
        );
    }

    #[test]
    fn classifies_tournament_labels() {
        assert_eq!(
            Competition::from_tournament("Copa Libertadores"),
            Competition::Libertadores
        );
        assert_eq!(
            Competition::from_tournament("Copa do Brasil"),
            Competition::CopaDoBrasil
        );
        assert_eq!(
            Competition::from_tournament("Brasileirão Série A"),
            Competition::Brasileirao
        );
        assert_eq!(
            Competition::from_tournament("Some Cup"),
            Competition::Other("Some Cup".into())
        );
    }

    fn sample_match(h: &str, a: &str, hg: u32, ag: u32) -> Match {
        Match {
            competition: Competition::Brasileirao,
            home_team: h.into(),
            away_team: a.into(),
            home_goal: hg,
            away_goal: ag,
            season: 2019,
            date: Some("2019-10-27".into()),
            round: Some("30".into()),
            stage: None,
        }
    }

    #[test]
    fn match_outcome_and_helpers() {
        let m = sample_match("Flamengo-RJ", "Grêmio-RS", 5, 0);
        assert_eq!(m.outcome(), Outcome::HomeWin);
        assert_eq!(m.total_goals(), 5);
        assert_eq!(m.margin(), 5);
        assert_eq!(m.home_key(), "flamengo");
        assert_eq!(m.away_key(), "gremio");
        assert!(m.involves("flamengo"));
        assert!(m.involves("gremio"));
        assert!(!m.involves("santos"));

        assert_eq!(sample_match("A", "B", 1, 2).outcome(), Outcome::AwayWin);
        assert_eq!(sample_match("A", "B", 2, 2).outcome(), Outcome::Draw);
    }

    #[test]
    fn parses_iso_date() {
        assert_eq!(parse_date("2023-09-24"), Some("2023-09-24".to_string()));
    }

    #[test]
    fn parses_iso_datetime() {
        assert_eq!(
            parse_date("2012-05-19 18:30:00"),
            Some("2012-05-19".to_string())
        );
    }

    #[test]
    fn parses_brazilian_date() {
        assert_eq!(parse_date("29/03/2003"), Some("2003-03-29".to_string()));
        assert_eq!(parse_date("1/1/2010"), Some("2010-01-01".to_string()));
    }

    #[test]
    fn rejects_bad_dates() {
        assert_eq!(parse_date(""), None);
        assert_eq!(parse_date("not a date"), None);
    }
}
