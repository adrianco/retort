//! ============================================================================
//! Context
//! ----------------------------------------------------------------------------
//! Module:   normalize
//! Purpose:  Canonicalization helpers used across the whole crate so that the
//!           messy, multi-source Kaggle data can be matched consistently.
//!
//! The provided datasets are inconsistent in three ways that this module
//! papers over:
//!   * Team names carry state/country suffixes ("Palmeiras-SP",
//!     "Nacional (URU)", "América - MG") and accents ("Grêmio", "São Paulo").
//!   * Competition names appear under several aliases ("Serie A" vs
//!     "Brasileirão", "Cup" vs "Copa do Brasil").
//!   * Dates come in ISO ("2023-09-24"), ISO+time ("2012-05-19 18:30:00")
//!     and Brazilian ("29/03/2003") formats.
//!
//! Everything here is pure (no I/O) and unit tested at the bottom of the file.
//! ============================================================================

use std::cmp::Ordering;

/// A calendar date without a timezone. Kept deliberately tiny so the crate has
/// no `chrono` dependency. Ordered chronologically.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Date {
    pub year: i32,
    pub month: u32,
    pub day: u32,
}

impl Date {
    pub fn new(year: i32, month: u32, day: u32) -> Self {
        Date { year, month, day }
    }
}

impl std::fmt::Display for Date {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{:04}-{:02}-{:02}", self.year, self.month, self.day)
    }
}

impl PartialOrd for Date {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

impl Ord for Date {
    fn cmp(&self, other: &Self) -> Ordering {
        (self.year, self.month, self.day).cmp(&(other.year, other.month, other.day))
    }
}

/// Parse a date string in any of the formats present in the datasets.
///
/// Accepted shapes:
///   * `2023-09-24`            (ISO)
///   * `2012-05-19 18:30:00`   (ISO + time, time discarded)
///   * `29/03/2003`            (Brazilian DD/MM/YYYY)
pub fn parse_date(raw: &str) -> Option<Date> {
    let s = raw.trim();
    if s.is_empty() {
        return None;
    }
    // Drop any trailing time component ("... 18:30:00").
    let date_part = s.split_whitespace().next().unwrap_or(s);

    if let Some((y, m, d)) = split3(date_part, '-') {
        // ISO: YYYY-MM-DD
        return make_date(y, m, d);
    }
    if let Some((d, m, y)) = split3(date_part, '/') {
        // Brazilian: DD/MM/YYYY
        return make_date(y, m, d);
    }
    None
}

fn split3(s: &str, sep: char) -> Option<(&str, &str, &str)> {
    let mut it = s.split(sep);
    let a = it.next()?;
    let b = it.next()?;
    let c = it.next()?;
    if it.next().is_some() {
        return None;
    }
    Some((a, b, c))
}

fn make_date(y: &str, m: &str, d: &str) -> Option<Date> {
    let year: i32 = y.trim().parse().ok()?;
    let month: u32 = m.trim().parse().ok()?;
    let day: u32 = d.trim().parse().ok()?;
    if !(1..=12).contains(&month) || !(1..=31).contains(&day) {
        return None;
    }
    Some(Date::new(year, month, day))
}

/// Parse a goal count that may be quoted (`"2"`) or a float (`1.0`).
pub fn parse_goal(raw: &str) -> Option<u32> {
    let s = raw.trim().trim_matches('"').trim();
    if s.is_empty() {
        return None;
    }
    if let Ok(n) = s.parse::<u32>() {
        return Some(n);
    }
    // Handle "1.0" style floats.
    if let Ok(f) = s.parse::<f64>() {
        if f >= 0.0 {
            return Some(f.round() as u32);
        }
    }
    None
}

/// Fold common Latin-1 / Portuguese accented characters down to ASCII so that
/// "São Paulo" and "Sao Paulo" compare equal.
pub fn fold_accents(s: &str) -> String {
    s.chars()
        .map(|c| match c {
            'á' | 'à' | 'â' | 'ã' | 'ä' | 'å' => 'a',
            'Á' | 'À' | 'Â' | 'Ã' | 'Ä' | 'Å' => 'A',
            'é' | 'è' | 'ê' | 'ë' => 'e',
            'É' | 'È' | 'Ê' | 'Ë' => 'E',
            'í' | 'ì' | 'î' | 'ï' => 'i',
            'Í' | 'Ì' | 'Î' | 'Ï' => 'I',
            'ó' | 'ò' | 'ô' | 'õ' | 'ö' => 'o',
            'Ó' | 'Ò' | 'Ô' | 'Õ' | 'Ö' => 'O',
            'ú' | 'ù' | 'û' | 'ü' => 'u',
            'Ú' | 'Ù' | 'Û' | 'Ü' => 'U',
            'ç' => 'c',
            'Ç' => 'C',
            'ñ' => 'n',
            'Ñ' => 'N',
            other => other,
        })
        .collect()
}

/// Produce the canonical key for a team name. Idempotent.
///
/// Accents are folded, the name is lower-cased, and every run of
/// non-alphanumeric characters becomes a single space. Crucially the state /
/// country code is **kept as a trailing token** rather than discarded, so that
/// genuinely different clubs that share a base name stay distinct:
///
///   "Atletico-MG" -> "atletico mg"   (Atlético Mineiro)
///   "Atletico-GO" -> "atletico go"   (Atlético Goianiense)
///   "Palmeiras-SP" -> "palmeiras sp"
///   "São Paulo"   -> "sao paulo"
///   "Nacional (URU)" -> "nacional uru"
///
/// A bare query like "Palmeiras" still matches "palmeiras sp" via the
/// substring logic in [`team_matches`].
pub fn normalize_team(raw: &str) -> String {
    let folded = fold_accents(raw).to_lowercase();
    let mut out = String::with_capacity(folded.len());
    let mut prev_space = false;
    for c in folded.chars() {
        if c.is_alphanumeric() {
            out.push(c);
            prev_space = false;
        } else if !prev_space {
            out.push(' ');
            prev_space = true;
        }
    }
    out.trim().to_string()
}

/// Does a user-supplied team query match a normalized team key from the data?
/// Lenient on purpose: equality, or either string containing the other as a
/// substring. This lets "Flamengo" match "flamengo" and "Sao Paulo FC" match
/// "sao paulo".
pub fn team_matches(query_norm: &str, data_norm: &str) -> bool {
    // Both sides must be non-empty: an empty data key (e.g. a free-agent's
    // blank club) must never match, otherwise `query.contains("")` is always
    // true and every query would match it.
    if query_norm.is_empty() || data_norm.is_empty() {
        return false;
    }
    query_norm == data_norm
        || data_norm.contains(query_norm)
        || query_norm.contains(data_norm)
}

/// Normalize a competition label and resolve it to a canonical bucket so that
/// "Serie A", "brasileirao" and "Campeonato Brasileiro" all collapse together.
pub fn canonical_competition(raw: &str) -> String {
    let n = fold_accents(raw).to_lowercase();
    let n = n.trim();
    if n.contains("libertadores") {
        return "Copa Libertadores".to_string();
    }
    if n.contains("copa do brasil") || n == "cup" || n.contains("brazilian cup") {
        return "Copa do Brasil".to_string();
    }
    if n.contains("brasileir")
        || n.contains("serie a")
        || n.contains("série a")
        || n.contains("campeonato brasileiro")
    {
        return "Brasileirão".to_string();
    }
    // Fall back to a title-cased version of the raw label (e.g. "Serie B/C").
    raw.trim().to_string()
}

/// Does a competition filter (user input) match a stored competition label?
pub fn competition_matches(query: &str, stored: &str) -> bool {
    if query.trim().is_empty() {
        return true;
    }
    let q = canonical_competition(query);
    let s = canonical_competition(stored);
    if q == s {
        return true;
    }
    // Allow loose substring matching on the folded raw labels too.
    let qf = fold_accents(query).to_lowercase();
    let sf = fold_accents(stored).to_lowercase();
    sf.contains(qf.trim()) || qf.trim().contains(&sf)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn normalizes_state_suffixes_as_tokens() {
        // State codes are preserved as tokens so distinct clubs stay distinct.
        assert_eq!(normalize_team("Palmeiras-SP"), "palmeiras sp");
        assert_eq!(normalize_team("Flamengo-RJ"), "flamengo rj");
        assert_eq!(normalize_team("América - MG"), "america mg");
        assert_eq!(normalize_team("Nacional (URU)"), "nacional uru");
        assert_eq!(normalize_team("Barcelona-EQU"), "barcelona equ");
    }

    #[test]
    fn keeps_same_named_clubs_distinct() {
        // The three "Atlético"s are different teams and must not collapse.
        assert_ne!(normalize_team("Atletico-MG"), normalize_team("Atletico-GO"));
        assert_ne!(normalize_team("Atletico-MG"), normalize_team("Atletico-PR"));
    }

    #[test]
    fn folds_accents() {
        assert_eq!(normalize_team("São Paulo"), normalize_team("Sao Paulo"));
        assert_eq!(normalize_team("Grêmio"), "gremio");
        assert_eq!(normalize_team("Avaí"), "avai");
    }

    #[test]
    fn normalize_is_idempotent() {
        let once = normalize_team("Palmeiras-SP");
        assert_eq!(once, normalize_team(&once));
    }

    #[test]
    fn team_matching_is_lenient() {
        assert!(team_matches("flamengo", "flamengo"));
        assert!(team_matches(
            &normalize_team("Flamengo"),
            &normalize_team("Flamengo-RJ")
        ));
        assert!(team_matches(
            &normalize_team("Sao Paulo FC"),
            &normalize_team("São Paulo")
        ));
        assert!(!team_matches("flamengo", "fluminense"));
        // An empty data key (e.g. a free-agent's blank club) never matches.
        assert!(!team_matches("flamengo", ""));
        assert!(!team_matches("", "flamengo"));
    }

    #[test]
    fn parses_all_date_formats() {
        assert_eq!(parse_date("2023-09-24"), Some(Date::new(2023, 9, 24)));
        assert_eq!(
            parse_date("2012-05-19 18:30:00"),
            Some(Date::new(2012, 5, 19))
        );
        assert_eq!(parse_date("29/03/2003"), Some(Date::new(2003, 3, 29)));
        assert_eq!(parse_date(""), None);
    }

    #[test]
    fn dates_order_chronologically() {
        assert!(Date::new(2019, 1, 1) < Date::new(2019, 12, 31));
        assert!(Date::new(2018, 12, 31) < Date::new(2019, 1, 1));
    }

    #[test]
    fn parses_goal_variants() {
        assert_eq!(parse_goal("2"), Some(2));
        assert_eq!(parse_goal("\"2\""), Some(2));
        assert_eq!(parse_goal("1.0"), Some(1));
        assert_eq!(parse_goal(""), None);
    }

    #[test]
    fn competition_aliases_resolve() {
        assert_eq!(canonical_competition("Serie A"), "Brasileirão");
        assert_eq!(canonical_competition("brasileirao"), "Brasileirão");
        assert_eq!(canonical_competition("Cup"), "Copa do Brasil");
        assert_eq!(canonical_competition("libertadores"), "Copa Libertadores");
        assert!(competition_matches("libertadores", "Copa Libertadores"));
        assert!(competition_matches("serie a", "Brasileirão"));
        assert!(!competition_matches("libertadores", "Copa do Brasil"));
    }
}
