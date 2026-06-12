//! Team-name normalization.
//!
//! The datasets describe the same club in several conventions:
//!   * with a Brazilian state suffix: `"Palmeiras-SP"`, `"Flamengo-RJ"`
//!   * with a spaced suffix:          `"América - MG"`
//!   * with a country code:           `"Nacional (URU)"`, `"Barcelona-EQU"`
//!   * accented vs. ASCII:            `"São Paulo"` vs `"Sao Paulo"`
//!
//! [`display_name`] produces a clean human-facing name (suffix removed) while
//! [`normalize_key`] produces a canonical lookup key (suffix removed, accents
//! folded, lower-cased, whitespace collapsed) used for matching user input
//! against the data regardless of which convention a given file uses.

/// Fold a single character to its closest ASCII equivalent, lower-cased.
fn fold_char(c: char) -> char {
    match c {
        'á' | 'à' | 'â' | 'ã' | 'ä' | 'å' | 'Á' | 'À' | 'Â' | 'Ã' | 'Ä' | 'Å' => 'a',
        'é' | 'è' | 'ê' | 'ë' | 'É' | 'È' | 'Ê' | 'Ë' => 'e',
        'í' | 'ì' | 'î' | 'ï' | 'Í' | 'Ì' | 'Î' | 'Ï' => 'i',
        'ó' | 'ò' | 'ô' | 'õ' | 'ö' | 'Ó' | 'Ò' | 'Ô' | 'Õ' | 'Ö' => 'o',
        'ú' | 'ù' | 'û' | 'ü' | 'Ú' | 'Ù' | 'Û' | 'Ü' => 'u',
        'ç' | 'Ç' => 'c',
        'ñ' | 'Ñ' => 'n',
        other => other.to_ascii_lowercase(),
    }
}

/// Remove a trailing state / country suffix from a team name.
///
/// Handles `"Palmeiras-SP"`, `"América - MG"` and `"Nacional (URU)"`.
/// Only strips a `(...)` group when it looks like a 2-4 letter code so that
/// descriptive parentheticals are preserved verbatim.
fn strip_suffix(name: &str) -> String {
    let mut s = name.trim();

    // Trailing "(URU)" / "(EQU)" style country codes.
    if let Some(open) = s.rfind('(') {
        if s.ends_with(')') {
            let inner = &s[open + 1..s.len() - 1];
            let is_code = (2..=4).contains(&inner.chars().count())
                && inner.chars().all(|c| c.is_ascii_alphabetic());
            if is_code {
                s = s[..open].trim_end();
            }
        }
    }

    // Trailing "-SP" / " - MG" style state suffixes.
    if let Some(dash) = s.rfind('-') {
        let tail = s[dash + 1..].trim();
        let head = s[..dash].trim_end();
        let is_state = (2..=3).contains(&tail.chars().count())
            && !tail.is_empty()
            && tail.chars().all(|c| c.is_ascii_alphabetic());
        // Only strip if there is a real name in front of the dash.
        if is_state && !head.is_empty() {
            s = head;
        }
    }

    s.trim().to_string()
}

/// A clean, human-facing team name with any state/country suffix removed.
pub fn display_name(name: &str) -> String {
    let stripped = strip_suffix(name);
    // Collapse internal whitespace runs to single spaces.
    stripped.split_whitespace().collect::<Vec<_>>().join(" ")
}

/// A canonical lookup key: suffix removed, accents folded, lower-cased,
/// whitespace collapsed. Two names referring to the same club produce the
/// same key.
pub fn normalize_key(name: &str) -> String {
    let display = display_name(name);
    let folded: String = display.chars().map(fold_char).collect();
    folded.split_whitespace().collect::<Vec<_>>().join(" ")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn strips_hyphen_state_suffix() {
        assert_eq!(display_name("Palmeiras-SP"), "Palmeiras");
        assert_eq!(display_name("Flamengo-RJ"), "Flamengo");
    }

    #[test]
    fn strips_spaced_state_suffix() {
        assert_eq!(display_name("América - MG"), "América");
    }

    #[test]
    fn strips_country_code_in_parens() {
        assert_eq!(display_name("Nacional (URU)"), "Nacional");
        assert_eq!(display_name("Barcelona-EQU"), "Barcelona");
    }

    #[test]
    fn keeps_descriptive_parenthetical() {
        let name = "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ";
        // The long descriptive group is kept; only the "- RJ" suffix is removed.
        assert_eq!(
            display_name(name),
            "Boavista Sport Club (antigo Esporte Clube Barreira)"
        );
    }

    #[test]
    fn does_not_strip_hyphen_in_real_name() {
        // "Vasco-da-Gama" style: the tail is not a 2-3 letter code, keep it.
        assert_eq!(display_name("Vitoria-Guimaraes"), "Vitoria-Guimaraes");
    }

    #[test]
    fn normalize_key_folds_accents_and_case() {
        assert_eq!(normalize_key("São Paulo"), "sao paulo");
        assert_eq!(normalize_key("Sao Paulo"), "sao paulo");
        assert_eq!(normalize_key("Grêmio"), "gremio");
        assert_eq!(normalize_key("Avaí"), "avai");
    }

    #[test]
    fn normalize_key_matches_across_conventions() {
        assert_eq!(normalize_key("Palmeiras-SP"), normalize_key("Palmeiras"));
        assert_eq!(normalize_key("Flamengo-RJ"), normalize_key("flamengo"));
        assert_eq!(normalize_key("América - MG"), normalize_key("america"));
    }

    #[test]
    fn collapses_whitespace() {
        assert_eq!(display_name("  Sport   Recife  "), "Sport Recife");
        assert_eq!(normalize_key("  Sport   Recife  "), "sport recife");
    }
}
