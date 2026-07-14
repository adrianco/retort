/// Normalize a team string into a stable key suitable for both substring
/// matching ("flamengo" matches "flamengo-rj") and exact grouping
/// ("atletico-mg" stays distinct from "atletico-go").
///
/// The state suffix and country tag are preserved when present, because they
/// are the only thing telling apart same-named Brazilian clubs in different
/// states (Atlético-MG vs Atlético-GO, Nacional-AM vs Nacional URU).
pub fn normalize_team(name: &str) -> String {
    let s = name.trim();

    // "America - MG" -> "America-MG" (the historic-style files use " - ")
    let s = s.replace(" - ", "-");

    // "Nacional (URU)" -> "Nacional-URU"
    let s = if let (Some(lp), Some(rp)) = (s.find('('), s.find(')')) {
        if rp > lp {
            let inside = s[lp + 1..rp].trim().to_string();
            let head = s[..lp].trim();
            let tail = s[rp + 1..].trim();
            let mut joined = head.to_string();
            if !inside.is_empty() {
                joined.push('-');
                joined.push_str(&inside);
            }
            if !tail.is_empty() {
                joined.push(' ');
                joined.push_str(tail);
            }
            joined
        } else {
            s
        }
    } else {
        s
    };

    let lowered = s.to_lowercase();
    let unaccented = strip_accents(&lowered);

    // Collapse whitespace, then re-join with single spaces.
    unaccented.split_whitespace().collect::<Vec<_>>().join(" ")
}

pub fn normalize_simple(s: &str) -> String {
    let lowered = s.trim().to_lowercase();
    strip_accents(&lowered)
        .split_whitespace()
        .collect::<Vec<_>>()
        .join(" ")
}

pub fn strip_accents(s: &str) -> String {
    s.chars()
        .map(|c| match c {
            'á' | 'à' | 'ã' | 'â' | 'ä' | 'å' => 'a',
            'Á' | 'À' | 'Ã' | 'Â' | 'Ä' | 'Å' => 'A',
            'é' | 'è' | 'ê' | 'ë' => 'e',
            'É' | 'È' | 'Ê' | 'Ë' => 'E',
            'í' | 'ì' | 'î' | 'ï' => 'i',
            'Í' | 'Ì' | 'Î' | 'Ï' => 'I',
            'ó' | 'ò' | 'õ' | 'ô' | 'ö' => 'o',
            'Ó' | 'Ò' | 'Õ' | 'Ô' | 'Ö' => 'O',
            'ú' | 'ù' | 'û' | 'ü' => 'u',
            'Ú' | 'Ù' | 'Û' | 'Ü' => 'U',
            'ç' => 'c',
            'Ç' => 'C',
            'ñ' => 'n',
            'Ñ' => 'N',
            _ => c,
        })
        .collect()
}

/// Does the query match the candidate team? Uses substring match on
/// normalized forms so "Flamengo" matches both "Flamengo" and "Flamengo-RJ".
pub fn team_matches(query: &str, candidate_norm: &str) -> bool {
    let q = normalize_team(query);
    if q.is_empty() {
        return false;
    }
    candidate_norm.contains(&q) || q.contains(candidate_norm)
}

/// Does the player/club query string match the candidate?
pub fn text_contains(query: &str, candidate: &str) -> bool {
    let q = normalize_simple(query);
    let c = normalize_simple(candidate);
    if q.is_empty() {
        return false;
    }
    c.contains(&q)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn normalize_preserves_state_suffix() {
        assert_eq!(normalize_team("Palmeiras-SP"), "palmeiras-sp");
        assert_eq!(normalize_team("Flamengo-RJ"), "flamengo-rj");
    }

    #[test]
    fn normalize_distinguishes_same_name_different_states() {
        assert_ne!(normalize_team("Atletico-MG"), normalize_team("Atletico-GO"));
        assert_ne!(normalize_team("Atlético-MG"), normalize_team("Atlético-PR"));
    }

    #[test]
    fn normalize_handles_accents() {
        assert_eq!(normalize_team("São Paulo"), "sao paulo");
        assert_eq!(normalize_team("Grêmio"), "gremio");
        assert_eq!(normalize_team("Avaí-SC"), "avai-sc");
    }

    #[test]
    fn normalize_collapses_country_parenthetical() {
        assert_eq!(normalize_team("Nacional (URU)"), "nacional-uru");
    }

    #[test]
    fn normalize_collapses_dash_space_form() {
        assert_eq!(normalize_team("América - MG"), "america-mg");
        assert_eq!(normalize_team("Criciúma - SC"), "criciuma-sc");
    }

    #[test]
    fn team_matches_finds_substring_across_state_suffixes() {
        // The query "Flamengo" should match the fully-suffixed candidate.
        assert!(team_matches("Flamengo", &normalize_team("Flamengo-RJ")));
        // And the bare form too.
        assert!(team_matches("Flamengo", &normalize_team("Flamengo")));
        assert!(!team_matches("Santos", "fluminense"));
    }
}
