//! ============================================================================
//! Module: normalize
//!
//! Context
//! -------
//! Brazilian soccer datasets use many naming conventions for the same club:
//!   * with a state suffix:   "Palmeiras-SP", "Flamengo-RJ"
//!   * with a spaced suffix:  "América - MG"
//!   * with a country tag:    "Nacional (URU)"
//!   * with accents:          "São Paulo", "Grêmio", "Avaí"
//!   * full legal names:      "Sport Club Corinthians Paulista"
//!
//! To answer cross-dataset questions ("What competitions has Palmeiras played
//! in?") every team name is reduced to a *normalization key*: lower-case,
//! accent-free, suffix-free, whitespace-collapsed. Two raw names that share a
//! key are treated as the same club. Display names keep their original, most
//! human-readable form.
//! ============================================================================

/// Replace common Latin-1 / Portuguese accented characters with their ASCII
/// equivalents so that "São Paulo" and "Sao Paulo" collapse to one key.
fn strip_accents(input: &str) -> String {
    input
        .chars()
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

/// Two-letter Brazilian state abbreviations used as team-name suffixes.
const BR_STATES: &[&str] = &[
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR",
    "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
];

/// Base club names that recur across several Brazilian states and therefore
/// MUST keep their state code to stay distinct (Atlético-MG / -GO / -PR all play
/// in the same Série A season; América-MG / -RN likewise).
const AMBIGUOUS_BASES: &[&str] = &["atletico", "america", "botafogo"];

/// Full normalized names that map to a `<base> <state>` canonical key, used to
/// reconcile the long-form spellings in BR-Football-Dataset.csv with the
/// dash-suffixed spellings elsewhere ("Atletico Mineiro" == "Atletico-MG").
fn regional_alias(norm: &str) -> Option<&'static str> {
    Some(match norm {
        "atletico mineiro" => "atletico mg",
        "atletico goianiense" => "atletico go",
        "atletico paranaense" => "atletico pr",
        "america mineiro" => "america mg",
        "america de natal" | "america rn" => "america rn",
        _ => return None,
    })
}

/// Simpler one-to-one name aliases (multi-word legal name -> common short key).
fn simple_alias(norm: &str) -> Option<&'static str> {
    Some(match norm {
        "vasco da gama" => "vasco",
        _ => return None,
    })
}

/// Strip a trailing parenthesised tag such as "(URU)".
fn strip_parens(name: &str) -> &str {
    let s = name.trim();
    if let Some(open) = s.rfind('(') {
        if s.ends_with(')') {
            return s[..open].trim();
        }
    }
    s
}

/// Split a raw name into `(base, Option<state_code_lowercase>)`, recognising
/// both the "Flamengo-RJ" dash form and the "Botafogo RJ" trailing-space form.
fn split_state(name: &str) -> (String, Option<String>) {
    let s = strip_parens(name).trim();

    // Dash form: "Atletico-MG", "Barcelona-EQU".
    if let Some(dash) = s.rfind('-') {
        let suffix = s[dash + 1..].trim();
        if suffix.len() >= 2 && suffix.len() <= 3 && suffix.chars().all(|c| c.is_alphabetic()) {
            let state = suffix.to_uppercase();
            let st = if BR_STATES.contains(&state.as_str()) {
                Some(state.to_lowercase())
            } else {
                None // country code (e.g. URU): drop it, don't treat as state
            };
            return (s[..dash].trim().to_string(), st);
        }
    }

    // Trailing-space form: "Botafogo RJ", "Vasco Da Gama RJ".
    if let Some(space) = s.rfind(' ') {
        let suffix = &s[space + 1..];
        if suffix.len() == 2 && BR_STATES.contains(&suffix.to_uppercase().as_str()) {
            return (s[..space].trim().to_string(), Some(suffix.to_lowercase()));
        }
    }

    (s.to_string(), None)
}

/// Produce the canonical matching key for a raw team name.
///
/// Rules:
///   * accents are removed and the name lower-cased / whitespace-collapsed;
///   * a trailing state code is dropped for unambiguous clubs but RETAINED
///     (as "<base> <state>") for clubs that share a name across states;
///   * known long-form spellings are mapped to the canonical key via aliases.
pub fn team_key(raw: &str) -> String {
    let (base, state) = split_state(raw);
    let mut norm = strip_accents(&base)
        .split_whitespace()
        .collect::<Vec<_>>()
        .join(" ")
        .to_lowercase();
    // Unify the "Athletico"/"Atletico" spelling split.
    norm = norm.replace("athletico", "atletico");

    if let Some(canon) = regional_alias(&norm) {
        return canon.to_string();
    }
    if let Some(canon) = simple_alias(&norm) {
        norm = canon.to_string();
    }

    // Keep the state code only for ambiguous single-word bases.
    if let Some(st) = state {
        if AMBIGUOUS_BASES.contains(&norm.as_str()) {
            return format!("{} {}", norm, st);
        }
    }
    norm
}

/// Strip a trailing state/country suffix for display purposes (keeps accents).
fn strip_suffix(name: &str) -> String {
    let (base, _) = split_state(name);
    base
}

/// Normalize an arbitrary free-text token (player name, club, nationality) for
/// case- and accent-insensitive substring search.
pub fn search_key(raw: &str) -> String {
    strip_accents(raw.trim())
        .split_whitespace()
        .collect::<Vec<_>>()
        .join(" ")
        .to_lowercase()
}

/// A nicer display name: trims whitespace and removes a redundant state suffix
/// while preserving accents and capitalisation.
pub fn display_name(raw: &str) -> String {
    let trimmed = raw.trim();
    let stripped = strip_suffix(trimmed);
    if stripped.is_empty() {
        trimmed.to_string()
    } else {
        stripped
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn state_suffix_is_stripped_for_unambiguous_clubs() {
        assert_eq!(team_key("Palmeiras-SP"), "palmeiras");
        assert_eq!(team_key("Flamengo-RJ"), "flamengo");
    }

    #[test]
    fn state_suffix_is_kept_for_ambiguous_clubs() {
        // Atlético and América recur across states and must stay distinct.
        assert_eq!(team_key("Atletico-MG"), "atletico mg");
        assert_eq!(team_key("Atlético-GO"), "atletico go");
        assert_ne!(team_key("Atletico-MG"), team_key("Atletico-PR"));
        assert_eq!(team_key("América - MG"), "america mg");
    }

    #[test]
    fn cross_dataset_spellings_reconcile() {
        // Long-form (BR-Football) vs dash-form (Brasileirão) vs short (novo).
        assert_eq!(team_key("Atletico Mineiro"), team_key("Atletico-MG"));
        assert_eq!(team_key("Athletico Paranaense"), team_key("Atletico-PR"));
        assert_eq!(team_key("Vasco Da Gama RJ"), team_key("Vasco"));
        assert_eq!(team_key("Vasco da Gama-RJ"), team_key("Vasco"));
        assert_eq!(team_key("Botafogo RJ"), team_key("Botafogo-RJ"));
    }

    #[test]
    fn accents_collapse() {
        assert_eq!(team_key("São Paulo"), team_key("Sao Paulo"));
        assert_eq!(team_key("Grêmio"), "gremio");
        assert_eq!(team_key("Avaí-SC"), "avai");
    }

    #[test]
    fn country_tag_is_stripped() {
        assert_eq!(team_key("Nacional (URU)"), "nacional");
        assert_eq!(team_key("Barcelona-EQU"), "barcelona");
    }

    #[test]
    fn whitespace_collapses() {
        assert_eq!(team_key("  Sport   Recife "), "sport recife");
    }

    #[test]
    fn display_name_keeps_accents() {
        assert_eq!(display_name("São Paulo-SP"), "São Paulo");
        assert_eq!(display_name("Grêmio"), "Grêmio");
    }
}
