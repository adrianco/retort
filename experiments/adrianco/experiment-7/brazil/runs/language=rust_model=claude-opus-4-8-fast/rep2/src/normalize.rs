// =============================================================================
// Context
// -----------------------------------------------------------------------------
// Module:  normalize
// Purpose: Normalisation helpers for the messy, multi-source Brazilian soccer
//          datasets. Team names appear with state suffixes ("Palmeiras-SP"),
//          country codes ("Nacional (URU)"), full legal names ("Sport Club
//          Corinthians Paulista") and with Portuguese accents ("Grêmio",
//          "São Paulo", "Avaí"). Dates appear in ISO, ISO+time and Brazilian
//          DD/MM/YYYY forms.
//
//          This module turns all of those into:
//            * a `display_team`  -> a clean human readable team name
//            * a `team_key`      -> an accent-folded, lower-cased, suffix-free
//                                   key used for fuzzy matching
//            * an ISO `date`     -> always "YYYY-MM-DD"
//
// Used by: data.rs (during load) and queries.rs (when matching user input).
// =============================================================================

/// Fold a single Unicode character to its closest ASCII equivalent so that
/// "São Paulo", "Sao Paulo" and "SAO PAULO" all compare equal. Only the
/// characters that actually occur in Brazilian Portuguese club/city names are
/// handled; anything else is passed through unchanged.
fn fold_char(c: char) -> char {
    match c {
        'á' | 'à' | 'â' | 'ã' | 'ä' | 'å' => 'a',
        'é' | 'è' | 'ê' | 'ë' => 'e',
        'í' | 'ì' | 'î' | 'ï' => 'i',
        'ó' | 'ò' | 'ô' | 'õ' | 'ö' => 'o',
        'ú' | 'ù' | 'û' | 'ü' => 'u',
        'ç' => 'c',
        'ñ' => 'n',
        'ý' | 'ÿ' => 'y',
        other => other,
    }
}

/// Accent-fold and lowercase a string.
pub fn fold(s: &str) -> String {
    s.chars()
        .flat_map(|c| c.to_lowercase())
        .map(fold_char)
        .collect()
}

/// Strip a trailing state/country qualifier from a team name.
///
/// Handles the forms produced by the various datasets:
///   "Palmeiras-SP"                -> "Palmeiras"
///   "América - MG"                -> "América"
///   "Nacional (URU)"              -> "Nacional"
///   "Boavista Sport Club - RJ"    -> "Boavista Sport Club"
fn strip_suffix(name: &str) -> String {
    let mut s = name.trim();

    // Remove a trailing parenthetical country/state code, e.g. "(URU)".
    if let Some(open) = s.rfind('(') {
        if s.ends_with(')') {
            let inside = &s[open + 1..s.len() - 1];
            if !inside.is_empty()
                && inside.len() <= 4
                && inside.chars().all(|c| c.is_ascii_alphabetic())
            {
                s = s[..open].trim_end();
            }
        }
    }

    // Remove a trailing " - XX" / "-XX" state or country code (2-3 letters).
    if let Some(dash) = s.rfind('-') {
        let tail = s[dash + 1..].trim();
        let head = s[..dash].trim();
        if !head.is_empty()
            && (2..=3).contains(&tail.chars().count())
            && tail.chars().all(|c| c.is_ascii_alphabetic())
        {
            s = head;
        }
    }

    s.trim().to_string()
}

/// Produce the clean, human-readable display name for a team.
pub fn display_team(raw: &str) -> String {
    let cleaned = strip_suffix(raw);
    if cleaned.is_empty() {
        raw.trim().to_string()
    } else {
        cleaned
    }
}

/// Produce the canonical match key for a team: accent-folded, lower-cased,
/// suffix-free, with internal whitespace collapsed.
pub fn team_key(raw: &str) -> String {
    let display = display_team(raw);
    let folded = fold(&display);
    folded.split_whitespace().collect::<Vec<_>>().join(" ")
}

/// Decide whether a dataset team name matches a user-supplied query name.
///
/// Matching is intentionally forgiving: it succeeds when either normalised key
/// contains the other. This lets "Flamengo" match "Flamengo-RJ" and lets
/// "Corinthians" match "Sport Club Corinthians Paulista", while still keeping
/// distinct clubs apart.
pub fn team_matches(dataset_name: &str, query: &str) -> bool {
    let a = team_key(dataset_name);
    let b = team_key(query);
    if a.is_empty() || b.is_empty() {
        return false;
    }
    a == b || a.contains(&b) || b.contains(&a)
}

/// Normalise any of the supported date formats to ISO "YYYY-MM-DD".
///
/// Supported inputs:
///   "2023-09-24"            -> "2023-09-24"
///   "2012-05-19 18:30:00"   -> "2012-05-19"
///   "29/03/2003"            -> "2003-03-29"
/// Unrecognised input is returned trimmed and unchanged.
pub fn normalize_date(raw: &str) -> String {
    let s = raw.trim();
    if s.is_empty() {
        return String::new();
    }

    // ISO, possibly with a trailing time component.
    if let Some(date_part) = s.split([' ', 'T']).next() {
        if date_part.len() == 10 && date_part.as_bytes()[4] == b'-' {
            return date_part.to_string();
        }
    }

    // Brazilian DD/MM/YYYY.
    let parts: Vec<&str> = s.split('/').collect();
    if parts.len() == 3 {
        let (d, m, y) = (parts[0].trim(), parts[1].trim(), parts[2].trim());
        if y.len() == 4 && d.chars().all(|c| c.is_ascii_digit()) {
            return format!("{:0>4}-{:0>2}-{:0>2}", y, m, d);
        }
    }

    s.to_string()
}

/// Extract a 4-digit year from a (possibly already ISO) date string.
pub fn year_from_date(date: &str) -> Option<i32> {
    let iso = normalize_date(date);
    iso.split('-').next().and_then(|y| y.parse().ok())
}

// -----------------------------------------------------------------------------
// Canonicalizer: data-derived team-identity resolution
// -----------------------------------------------------------------------------
//
// The three Brasileirão sources spell the same club differently:
//   "Atletico-MG" / "Atlético-MG" / "Atletico Mineiro"   (one club)
//   "Atletico-PR" / "Athletico-PR" / "Athletico Paranaense" (a DIFFERENT club)
//   "Vasco" / "Vasco da Gama-RJ" / "Vasco Da Gama RJ"     (one club)
//
// A blind state-suffix strip would wrongly merge the two Atléticos (both ->
// "atletico"); not stripping at all would split "Flamengo" from "Flamengo-RJ".
//
// The `Canonicalizer` resolves this from the data itself: it strips a trailing
// 2-letter state code ONLY when the remaining stem is unambiguous (i.e. it never
// appears with more than one state across the dataset). Clubs like Atlético and
// América - which share a stem across multiple states - therefore keep their
// state, while clubs like Flamengo collapse to a single identity. A tiny alias
// table folds the remaining word-level spelling variants.

use std::collections::{HashMap, HashSet};

/// Collapse a name to a comparison "base form": accent-folded, lower-cased,
/// punctuation turned to spaces, whitespace collapsed.
fn base_form(raw: &str) -> String {
    let folded = fold(raw);
    let spaced: String = folded
        .chars()
        .map(|c| if matches!(c, '-' | '/' | '.' | ',' | '(' | ')') { ' ' } else { c })
        .collect();
    spaced.split_whitespace().collect::<Vec<_>>().join(" ")
}

/// Map word-level spelling variants onto a single canonical base form. Only the
/// variants that actually occur in the provided datasets are listed.
fn apply_alias(base: &str) -> &str {
    match base {
        "atletico mineiro" | "athletico mineiro" => "atletico mg",
        "atletico paranaense" | "athletico paranaense" | "athletico pr" => "atletico pr",
        "vasco da gama" | "vasco da gama rj" => "vasco",
        "ec bahia" => "bahia",
        "fortaleza fc" => "fortaleza",
        other => other,
    }
}

/// Split a trailing 2-letter state code off a base form.
/// "flamengo rj" -> ("flamengo", Some("rj")); "sao paulo" -> ("sao paulo", None).
fn split_state(base: &str) -> (&str, Option<&str>) {
    if let Some(pos) = base.rfind(' ') {
        let tail = &base[pos + 1..];
        if tail.len() == 2 && tail.chars().all(|c| c.is_ascii_alphabetic()) {
            return (&base[..pos], Some(tail));
        }
    }
    (base, None)
}

/// Resolves any raw team name to a canonical identity key.
#[derive(Debug, Default, Clone)]
pub struct Canonicalizer {
    /// Stems for which a trailing state code is a meaningful disambiguator and
    /// must be kept: the stem appears with more than one state AND never appears
    /// in bare (state-less) form. If the data ever uses the bare name, that bare
    /// form is treated as the canonical main club and all variants collapse to
    /// it (e.g. "Flamengo" / "Flamengo-RJ"). Clubs that always carry a state and
    /// span several of them (Atlético-MG vs Atlético-PR, América-MG vs -RN) are
    /// kept apart.
    keep_state_stems: HashSet<String>,
}

impl Canonicalizer {
    /// Build the canonicalizer by observing every raw team name in the data.
    pub fn build<'a, I: IntoIterator<Item = &'a str>>(names: I) -> Self {
        let mut stem_states: HashMap<String, HashSet<String>> = HashMap::new();
        let mut bare_stems: HashSet<String> = HashSet::new();
        for raw in names {
            let base = base_form(raw);
            let aliased = apply_alias(&base);
            match split_state(aliased) {
                (stem, Some(state)) => {
                    stem_states
                        .entry(stem.to_string())
                        .or_default()
                        .insert(state.to_string());
                }
                (stem, None) => {
                    bare_stems.insert(stem.to_string());
                }
            }
        }
        let keep_state_stems = stem_states
            .into_iter()
            .filter(|(stem, states)| states.len() > 1 && !bare_stems.contains(stem))
            .map(|(stem, _)| stem)
            .collect();
        Canonicalizer { keep_state_stems }
    }

    /// Canonical identity key for a raw team name.
    pub fn key(&self, raw: &str) -> String {
        let base = base_form(raw);
        let aliased = apply_alias(&base);
        match split_state(aliased) {
            (stem, Some(state)) if self.keep_state_stems.contains(stem) => {
                format!("{stem} {state}")
            }
            (stem, _) => stem.to_string(),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn folds_accents() {
        assert_eq!(fold("Grêmio"), "gremio");
        assert_eq!(fold("São Paulo"), "sao paulo");
        assert_eq!(fold("Avaí"), "avai");
    }

    #[test]
    fn strips_state_suffix() {
        assert_eq!(display_team("Palmeiras-SP"), "Palmeiras");
        assert_eq!(display_team("América - MG"), "América");
        assert_eq!(display_team("Nacional (URU)"), "Nacional");
    }

    #[test]
    fn matching_is_forgiving() {
        assert!(team_matches("Flamengo-RJ", "flamengo"));
        assert!(team_matches("Sport Club Corinthians Paulista", "Corinthians"));
        assert!(team_matches("São Paulo", "sao paulo"));
        assert!(!team_matches("Palmeiras", "Santos"));
    }

    #[test]
    fn canonicalizer_resolves_identities() {
        let names = [
            "Atletico-MG",
            "Atletico-PR",
            "Atletico Mineiro",
            "Athletico Paranaense",
            "Flamengo-RJ",
            "Flamengo",
            "Vasco",
            "Vasco da Gama-RJ",
            "Vasco Da Gama RJ",
            "Bahia-BA",
            "EC Bahia",
        ];
        let c = Canonicalizer::build(names.iter().copied());

        // Ambiguous stem "atletico" keeps its state -> MG and PR stay distinct.
        assert_ne!(c.key("Atletico-MG"), c.key("Atletico-PR"));
        assert_eq!(c.key("Atletico-MG"), c.key("Atletico Mineiro"));
        assert_eq!(c.key("Atletico-PR"), c.key("Athletico Paranaense"));

        // Unambiguous clubs collapse across spellings.
        assert_eq!(c.key("Flamengo"), c.key("Flamengo-RJ"));
        assert_eq!(c.key("Vasco"), c.key("Vasco Da Gama RJ"));
        assert_eq!(c.key("Bahia-BA"), c.key("EC Bahia"));

        // Different clubs stay different.
        assert_ne!(c.key("Flamengo"), c.key("Vasco"));
    }

    #[test]
    fn parses_dates() {
        assert_eq!(normalize_date("2012-05-19 18:30:00"), "2012-05-19");
        assert_eq!(normalize_date("29/03/2003"), "2003-03-29");
        assert_eq!(normalize_date("2023-09-24"), "2023-09-24");
        assert_eq!(year_from_date("29/03/2003"), Some(2003));
    }
}
