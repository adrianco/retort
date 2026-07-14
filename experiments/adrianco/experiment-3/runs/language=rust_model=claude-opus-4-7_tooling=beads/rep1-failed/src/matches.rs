//! Match lookup queries.
//!
//! Context: implements requirement category 1 ("Match Queries") from
//! `TASK.md` — finding matches by team, opponent, competition, season and
//! date range. Results are returned most-recent-first. Competition names are
//! matched loosely (accent-folded substring) so a query for "Brasileirao" or
//! "Libertadores" resolves to the canonical competition label.

use crate::data::Database;
use crate::model::Match;
use crate::normalize::{fold_accents, key_matches};

/// Criteria for [`find_matches`]. All set fields must be satisfied (AND).
#[derive(Debug, Default, Clone)]
pub struct MatchFilter {
    /// Club that played on either side.
    pub team: Option<String>,
    /// Second club; combined with `team` to find head-to-head fixtures.
    pub opponent: Option<String>,
    /// Club that played specifically at home.
    pub home_team: Option<String>,
    /// Club that played specifically away.
    pub away_team: Option<String>,
    /// Exact canonical competition label (already resolved by the caller).
    pub competition: Option<String>,
    pub season: Option<i32>,
    /// Inclusive ISO `YYYY-MM-DD` lower bound.
    pub date_from: Option<String>,
    /// Inclusive ISO `YYYY-MM-DD` upper bound.
    pub date_to: Option<String>,
}

/// Resolve a free-text competition query to exactly one canonical competition
/// label, or `None` when the query is empty, unknown or ambiguous.
///
/// Examples: "Brasileirao" / "serie a" -> "Brasileirão Série A";
/// "libertadores" -> "Copa Libertadores"; "cup" -> "Copa do Brasil".
pub fn canonical_competition(query: &str) -> Option<&'static str> {
    let q = fold_accents(query).to_lowercase();
    let q = q.split_whitespace().collect::<Vec<_>>().join(" ");
    if q.is_empty() {
        None
    } else if q.contains("libertadores") {
        Some("Copa Libertadores")
    } else if q.contains("copa do brasil") || q.contains("cup") {
        Some("Copa do Brasil")
    } else if q.contains("serie b") {
        Some("Brasileirão Série B")
    } else if q.contains("serie c") {
        Some("Brasileirão Série C")
    } else if q.contains("serie a") {
        Some("Brasileirão Série A")
    } else if q.contains("brasileir") {
        Some("Brasileirão Série A")
    } else {
        None
    }
}

/// Return every match satisfying `filter`, sorted most-recent first.
pub fn find_matches<'a>(db: &'a Database, filter: &MatchFilter) -> Vec<&'a Match> {
    let mut out: Vec<&Match> = db
        .matches
        .iter()
        .filter(|m| matches_filter(m, filter))
        .collect();
    out.sort_by(|a, b| b.date.cmp(&a.date));
    out
}

fn matches_filter(m: &Match, f: &MatchFilter) -> bool {
    if let Some(team) = &f.team {
        if !(key_matches(&m.home_key, team) || key_matches(&m.away_key, team)) {
            return false;
        }
    }
    if let Some(opp) = &f.opponent {
        if !(key_matches(&m.home_key, opp) || key_matches(&m.away_key, opp)) {
            return false;
        }
    }
    if let Some(home) = &f.home_team {
        if !key_matches(&m.home_key, home) {
            return false;
        }
    }
    if let Some(away) = &f.away_team {
        if !key_matches(&m.away_key, away) {
            return false;
        }
    }
    if let Some(comp) = &f.competition {
        if &m.competition != comp {
            return false;
        }
    }
    if let Some(season) = f.season {
        if m.season != season {
            return false;
        }
    }
    if let Some(from) = &f.date_from {
        if m.date.is_empty() || m.date.as_str() < from.as_str() {
            return false;
        }
    }
    if let Some(to) = &f.date_to {
        if m.date.is_empty() || m.date.as_str() > to.as_str() {
            return false;
        }
    }
    true
}

/// Render a list of matches as a numbered, human-readable block. At most
/// `limit` matches are shown; a trailing note reports any remainder.
pub fn format_matches(matches: &[&Match], limit: usize) -> String {
    if matches.is_empty() {
        return "No matches found for the given criteria.".to_string();
    }
    let mut out = String::new();
    for (i, m) in matches.iter().take(limit).enumerate() {
        out.push_str(&format!("{}. {}\n", i + 1, m.summary()));
    }
    if matches.len() > limit {
        out.push_str(&format!(
            "... ({} more match(es) in dataset)\n",
            matches.len() - limit
        ));
    }
    out
}
