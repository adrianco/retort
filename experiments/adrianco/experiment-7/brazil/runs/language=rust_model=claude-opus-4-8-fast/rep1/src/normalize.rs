// =============================================================================
// Context: Brazilian Soccer MCP Server
// File:    src/normalize.rs
// Purpose: Text normalization helpers used to reconcile the many naming and
//          encoding conventions found across the provided Kaggle datasets.
//
//          The datasets reference the same clubs in incompatible ways:
//            - With a state suffix:        "Palmeiras-SP", "Flamengo - RJ"
//            - With a country code:        "Nacional (URU)", "Barcelona-EQU"
//            - With accents / cedilla:     "São Paulo", "Grêmio", "Avaí"
//            - With long descriptive names "Sport Club Corinthians Paulista"
//
//          `normalize_key` reduces a raw team name to a canonical, accent-free,
//          punctuation-free lowercase key so that fuzzy, encoding-insensitive
//          matching is possible. `team_matches` performs the actual containment
//          based comparison used by the query layer.
// =============================================================================

/// Strip diacritics from common Brazilian Portuguese characters, lowercasing as
/// we go. We avoid pulling in a Unicode dependency by mapping the accents that
/// actually appear in the datasets (á à â ã ä, é ê, í, ó ô õ, ú, ç, ...).
pub fn strip_accents(input: &str) -> String {
    input
        .chars()
        .map(|c| match c {
            'á' | 'à' | 'â' | 'ã' | 'ä' | 'å' | 'Á' | 'À' | 'Â' | 'Ã' | 'Ä' | 'Å' => 'a',
            'é' | 'è' | 'ê' | 'ë' | 'É' | 'È' | 'Ê' | 'Ë' => 'e',
            'í' | 'ì' | 'î' | 'ï' | 'Í' | 'Ì' | 'Î' | 'Ï' => 'i',
            'ó' | 'ò' | 'ô' | 'õ' | 'ö' | 'Ó' | 'Ò' | 'Ô' | 'Õ' | 'Ö' => 'o',
            'ú' | 'ù' | 'û' | 'ü' | 'Ú' | 'Ù' | 'Û' | 'Ü' => 'u',
            'ç' | 'Ç' => 'c',
            'ñ' | 'Ñ' => 'n',
            other => other.to_ascii_lowercase(),
        })
        .collect()
}

/// Remove a trailing state / country qualifier such as "-SP", " - RJ" or
/// "(URU)" from a team name. Operates on the already-lowercased raw string.
fn strip_qualifier(name: &str) -> String {
    let mut s = name.trim().to_string();

    // Drop a trailing parenthetical, e.g. "nacional (uru)" -> "nacional".
    if let Some(open) = s.rfind('(') {
        if s.trim_end().ends_with(')') {
            s = s[..open].to_string();
        }
    }

    // Drop a trailing "- XX" / "-XX" suffix where the tail is a short token
    // (state abbreviation or country code: SP, RJ, MG, URU, EQU, ...).
    if let Some(dash) = s.rfind('-') {
        let tail = s[dash + 1..].trim();
        if !tail.is_empty() && tail.len() <= 3 && tail.chars().all(|c| c.is_alphabetic()) {
            s = s[..dash].to_string();
        }
    }

    s.trim().to_string()
}

/// Reduce a raw team name to a canonical matching key: accents removed, state /
/// country qualifiers removed, and every non-alphanumeric character dropped.
///
/// "Flamengo-RJ"               -> "flamengo"
/// "São Paulo"                 -> "saopaulo"
/// "Grêmio - RS"               -> "gremio"
/// "Nacional (URU)"            -> "nacionaluru" -> after qualifier strip "nacional"
pub fn normalize_key(raw: &str) -> String {
    let lowered = strip_accents(raw);
    let stripped = strip_qualifier(&lowered);
    let key: String = stripped.chars().filter(|c| c.is_alphanumeric()).collect();
    apply_aliases(&key)
}

/// Collapse spelling variants that survive the generic normalization but refer
/// to the same club. The datasets are internally inconsistent — for example
/// "Athletico Paranaense" and "Atletico Paranaense" both appear for the Curitiba
/// club — which would otherwise split a team across two standings rows.
fn apply_aliases(key: &str) -> String {
    key.replace("athletico", "atletico")
}

/// Decide whether a user-supplied query refers to the same club as `team`.
///
/// Matching is symmetric containment on the normalized keys: a short query such
/// as "flamengo" matches the longer "crflamengo", and a fully qualified
/// "saopaulosp" still matches a bare "saopaulo". Exact-equality short-circuits
/// for the common case.
pub fn team_matches(query: &str, team: &str) -> bool {
    let q = normalize_key(query);
    let t = normalize_key(team);
    if q.is_empty() || t.is_empty() {
        return false;
    }
    q == t || t.contains(&q) || q.contains(&t)
}

/// Loose case/accent-insensitive substring match used for player names, clubs
/// and nationalities.
pub fn loose_contains(haystack: &str, needle: &str) -> bool {
    let h = strip_accents(haystack);
    let n = strip_accents(needle);
    let n = n.trim();
    !n.is_empty() && h.contains(n)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn strips_state_suffix() {
        assert_eq!(normalize_key("Flamengo-RJ"), "flamengo");
        assert_eq!(normalize_key("Palmeiras-SP"), "palmeiras");
        assert_eq!(normalize_key("Grêmio - RS"), "gremio");
    }

    #[test]
    fn strips_country_parenthetical() {
        assert_eq!(normalize_key("Nacional (URU)"), "nacional");
    }

    #[test]
    fn strips_accents_consistently() {
        assert_eq!(normalize_key("São Paulo"), "saopaulo");
        assert_eq!(normalize_key("Sao Paulo"), "saopaulo");
        assert_eq!(strip_accents("Avaí"), "avai");
    }

    #[test]
    fn team_matches_variants() {
        assert!(team_matches("Flamengo", "Flamengo-RJ"));
        assert!(team_matches("flamengo", "CR Flamengo"));
        assert!(team_matches("São Paulo", "Sao Paulo-SP"));
        assert!(!team_matches("Flamengo", "Fluminense"));
    }
}
