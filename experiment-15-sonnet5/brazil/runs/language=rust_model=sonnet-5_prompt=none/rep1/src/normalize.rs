//! Team name normalization and flexible date parsing.
//!
//! The provided datasets spell the same club in several different ways
//! (state suffixes, accented vs. unaccented characters, punctuation in
//! abbreviations). [`normalize_team_name`] folds all of these down to a
//! single comparison key so matches/teams can be joined across files.

use chrono::NaiveDate;
use unicode_normalization::UnicodeNormalization;

/// Produce a canonical comparison key for a team name: strip a trailing
/// state-abbreviation suffix (e.g. `-SP`, `- MG`), strip diacritics, drop
/// punctuation, lowercase, and collapse whitespace.
///
/// Note this key alone is ambiguous for the handful of base names shared by
/// multiple real clubs in different states (e.g. "Atletico" is used by
/// Atletico-MG, Atletico-GO, Atletico-PR, ...). Callers that need a unique
/// team identity (as opposed to a loose search key) should combine this
/// with [`extract_state_suffix`] - see `Store::team_identity`.
pub fn normalize_team_name(raw: &str) -> String {
    let (base, _state) = split_state_suffix(raw.trim());
    fold_text(base)
}

/// Extract the trailing two-letter Brazilian state abbreviation from a team
/// name, if the datasets embedded one directly in the name (as
/// `Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`, and
/// `novo_campeonato_brasileiro.csv` do).
pub fn extract_state_suffix(raw: &str) -> Option<String> {
    split_state_suffix(raw.trim()).1.map(|s| s.to_uppercase())
}

fn fold_text(text: &str) -> String {
    let decomposed: String = text.nfd().collect();
    let mut out = String::with_capacity(decomposed.len());
    for ch in decomposed.chars() {
        // Drop combining diacritical marks produced by NFD decomposition.
        if ('\u{0300}'..='\u{036f}').contains(&ch) {
            continue;
        }
        if ch.is_alphanumeric() {
            out.extend(ch.to_lowercase());
        } else if ch.is_whitespace() || ch == '-' {
            out.push(' ');
        }
        // other punctuation (periods, parens, apostrophes) is dropped
    }
    out.split_whitespace().collect::<Vec<_>>().join(" ")
}

/// Split a trailing " - XX" / "-XX" / " XX" two-letter Brazilian state
/// abbreviation off a team name, if present.
fn split_state_suffix(name: &str) -> (&str, Option<&str>) {
    const STATES: &[&str] = &[
        "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB",
        "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
    ];
    let trimmed = name.trim_end();
    let char_count = trimmed.chars().count();
    if char_count < 3 {
        return (trimmed, None);
    }
    let last_two: String = trimmed.chars().skip(char_count - 2).collect();
    let Some(&state) = STATES.iter().find(|s| s.eq_ignore_ascii_case(&last_two)) else {
        return (trimmed, None);
    };
    // Byte offset of the state-code start; safe because we index by char
    // position rather than assuming 1-byte-per-char.
    let split_at = trimmed
        .char_indices()
        .nth(char_count - 2)
        .map(|(i, _)| i)
        .unwrap_or(trimmed.len());
    let prefix = &trimmed[..split_at];
    let stripped = prefix.trim_end_matches(|c: char| c == '-' || c.is_whitespace());
    if stripped.is_empty() {
        (trimmed, None)
    } else {
        (stripped, Some(state))
    }
}

/// Parse a date value that may be in one of several formats used across the
/// datasets: `YYYY-MM-DD HH:MM:SS`, `YYYY-MM-DD`, or `DD/MM/YYYY`.
pub fn parse_flexible_date(raw: &str) -> Option<NaiveDate> {
    let raw = raw.trim();
    if raw.is_empty() {
        return None;
    }
    if let Ok(dt) = chrono::NaiveDateTime::parse_from_str(raw, "%Y-%m-%d %H:%M:%S") {
        return Some(dt.date());
    }
    if let Ok(d) = NaiveDate::parse_from_str(raw, "%Y-%m-%d") {
        return Some(d);
    }
    if let Ok(d) = NaiveDate::parse_from_str(raw, "%d/%m/%Y") {
        return Some(d);
    }
    None
}

/// Parse an integer goal count, treating common "no result" sentinels
/// (`NA`, `-`, empty string) as `None` rather than an error.
pub fn parse_goal(raw: &str) -> Option<i32> {
    let raw = raw.trim();
    if raw.is_empty() || raw.eq_ignore_ascii_case("na") || raw == "-" {
        return None;
    }
    raw.parse::<f64>().ok().map(|v| v.round() as i32)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn strips_state_suffix_variants() {
        assert_eq!(normalize_team_name("Palmeiras-SP"), "palmeiras");
        assert_eq!(normalize_team_name("Flamengo-RJ"), "flamengo");
        assert_eq!(normalize_team_name("América - MG"), "america");
        assert_eq!(normalize_team_name("America - MG"), "america");
    }

    #[test]
    fn folds_accents_and_punctuation() {
        assert_eq!(normalize_team_name("Grêmio"), "gremio");
        assert_eq!(normalize_team_name("Avaí"), "avai");
        assert_eq!(normalize_team_name("A.b.c. - RN"), "abc");
        assert_eq!(normalize_team_name("ABC - RN"), "abc");
    }

    #[test]
    fn extracts_state_suffix() {
        assert_eq!(extract_state_suffix("Atletico-MG"), Some("MG".to_string()));
        assert_eq!(extract_state_suffix("Atletico-GO"), Some("GO".to_string()));
        assert_eq!(extract_state_suffix("América - MG"), Some("MG".to_string()));
        assert_eq!(extract_state_suffix("Sao Paulo"), None);
    }

    #[test]
    fn parses_dates() {
        assert_eq!(
            parse_flexible_date("2012-05-19 18:30:00"),
            NaiveDate::from_ymd_opt(2012, 5, 19)
        );
        assert_eq!(
            parse_flexible_date("2023-09-24"),
            NaiveDate::from_ymd_opt(2023, 9, 24)
        );
        assert_eq!(
            parse_flexible_date("29/03/2003"),
            NaiveDate::from_ymd_opt(2003, 3, 29)
        );
        assert_eq!(parse_flexible_date(""), None);
    }

    #[test]
    fn parses_goals_with_sentinels() {
        assert_eq!(parse_goal("2"), Some(2));
        assert_eq!(parse_goal("2.0"), Some(2));
        assert_eq!(parse_goal("NA"), None);
        assert_eq!(parse_goal("-"), None);
        assert_eq!(parse_goal(""), None);
    }
}
