//! ============================================================================
//! Module: normalize
//! Project: Brazilian Soccer MCP Server (Rust)
//!
//! Context:
//!   The datasets are inconsistent about team names and dates. Team names may
//!   carry a state/country suffix ("Palmeiras-SP", "Nacional (URU)",
//!   "América - MG"), use full club names, or include accented Portuguese
//!   characters. Dates appear as ISO ("2023-09-24"), ISO-with-time
//!   ("2012-05-19 18:30:00") and Brazilian DD/MM/YYYY ("29/03/2003").
//!
//!   Naming has a crucial subtlety: the state suffix is part of a club's
//!   IDENTITY, not noise — "Atlético-MG" (Mineiro) and "Atlético-PR"
//!   (Paranaense) are different clubs. So `normalize_team` produces a canonical
//!   key that KEEPS the suffix (just folding accents/case/whitespace and
//!   unifying the suffix punctuation to "-xx"). Stripping it would merge
//!   distinct clubs and corrupt standings.
//!
//!   `base_team` is the suffix-stripped form, used only where we deliberately
//!   want to ignore the state (cross-source de-duplication). `team_matches`
//!   implements the loose "does this query refer to this team" check used by
//!   every query: a bare "Flamengo" still matches the key "flamengo-rj".
//! ============================================================================

/// Fold common Portuguese accented characters down to ASCII for matching.
fn fold_accents(s: &str) -> String {
    s.chars()
        .map(|c| match c {
            'á' | 'à' | 'â' | 'ã' | 'ä' => 'a',
            'é' | 'è' | 'ê' | 'ë' => 'e',
            'í' | 'ì' | 'î' | 'ï' => 'i',
            'ó' | 'ò' | 'ô' | 'õ' | 'ö' => 'o',
            'ú' | 'ù' | 'û' | 'ü' => 'u',
            'ç' => 'c',
            'ñ' => 'n',
            'Á' | 'À' | 'Â' | 'Ã' | 'Ä' => 'A',
            'É' | 'È' | 'Ê' | 'Ë' => 'E',
            'Í' | 'Ì' | 'Î' | 'Ï' => 'I',
            'Ó' | 'Ò' | 'Ô' | 'Õ' | 'Ö' => 'O',
            'Ú' | 'Ù' | 'Û' | 'Ü' => 'U',
            'Ç' => 'C',
            'Ñ' => 'N',
            other => other,
        })
        .collect()
}

/// Normalize a team name into a canonical comparison/grouping key, *keeping*
/// the state/country suffix (so distinct clubs stay distinct).
///
/// Steps: fold accents, lower-case, turn a parenthetical "(uru)" into "-uru",
/// unify " - xx" / "- xx" into "-xx", and collapse whitespace.
pub fn normalize_team(name: &str) -> String {
    let mut s = fold_accents(name).to_lowercase();

    // Convert parenthetical country/state codes "(uru)" -> "-uru".
    if let Some(open) = s.find('(') {
        if let Some(close_rel) = s[open..].find(')') {
            let close = open + close_rel;
            let inner = s[open + 1..close].trim().to_string();
            s.replace_range(open..=close, &format!("-{inner}"));
        }
    }

    // Unify spacing around a trailing hyphen suffix: "america - mg" -> "america-mg".
    let s = s.replace(" - ", "-").replace("- ", "-").replace(" -", "-");

    // Collapse internal whitespace.
    s.split_whitespace().collect::<Vec<_>>().join(" ")
}

/// The suffix-stripped base name: drops a trailing "-xx" (or trailing standalone
/// 2-4 letter token) state/country code. Used only for cross-source de-dup and
/// as a loose matching fallback — NOT for grouping, since it conflates clubs
/// that differ only by state.
pub fn base_team(name: &str) -> String {
    let key = normalize_team(name);
    // Strip a trailing "-xx" code.
    if let Some(idx) = key.rfind('-') {
        let tail = &key[idx + 1..];
        if (2..=4).contains(&tail.len()) && tail.chars().all(|c| c.is_ascii_alphabetic()) {
            return key[..idx].trim().to_string();
        }
    }
    // Strip a trailing standalone 2-letter token ("vasco da gama rj").
    if let Some(idx) = key.rfind(' ') {
        let tail = &key[idx + 1..];
        if tail.len() == 2 && tail.chars().all(|c| c.is_ascii_alphabetic()) {
            return key[..idx].trim().to_string();
        }
    }
    key
}

/// Normalize a date string to canonical `YYYY-MM-DD`. Returns empty string if
/// it cannot be parsed.
pub fn normalize_date(raw: &str) -> String {
    let s = raw.trim();
    if s.is_empty() {
        return String::new();
    }

    // Brazilian format DD/MM/YYYY (optionally with time).
    if s.contains('/') {
        let date_part = s.split_whitespace().next().unwrap_or(s);
        let parts: Vec<&str> = date_part.split('/').collect();
        if parts.len() == 3 {
            let (d, m, y) = (parts[0], parts[1], parts[2]);
            if y.len() == 4 {
                return format!("{:0>4}-{:0>2}-{:0>2}", y, m, d);
            }
        }
        return String::new();
    }

    // ISO format (possibly with time component): take the first token.
    let date_part = s.split_whitespace().next().unwrap_or(s);
    let parts: Vec<&str> = date_part.split('-').collect();
    if parts.len() == 3 && parts[0].len() == 4 {
        return format!("{:0>4}-{:0>2}-{:0>2}", parts[0], parts[1], parts[2]);
    }
    String::new()
}

/// Extract the 4-digit year from a normalized or raw date, if present.
pub fn year_of(date: &str) -> Option<i32> {
    let norm = if date.len() >= 4 && date.as_bytes().get(4) == Some(&b'-') {
        date.to_string()
    } else {
        normalize_date(date)
    };
    norm.split('-').next().and_then(|y| y.parse().ok())
}

/// Does a user-supplied query name refer to the given normalized team key?
///
/// The key keeps its state suffix; the query may or may not. We match when:
///   - the normalized query equals the key, or is a substring of it
///     ("flamengo" ⊂ "flamengo-rj"), or vice-versa; or
///   - their suffix-stripped base names are equal AND the query carries no
///     suffix (so bare "atletico" stays ambiguous via substring, but a precise
///     "santos-sp" never leaks into "santos-fc").
pub fn team_matches(query: &str, team_key: &str) -> bool {
    let q = normalize_team(query);
    if q.is_empty() {
        return false;
    }
    if team_key == q || team_key.contains(&q) || q.contains(team_key) {
        return true;
    }
    // Loose fallback on base names (e.g. query "Vasco da Gama" vs key "vasco")
    // — but ONLY when the query itself carries no state suffix. A precise query
    // like "Atletico-MG" must never bleed into "atletico-pr".
    let qb = base_team(query);
    if qb == q {
        let kb = base_team(team_key);
        return !qb.is_empty() && (qb == kb || kb.contains(&qb) || qb.contains(&kb));
    }
    false
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn keeps_state_suffix_but_canonicalizes() {
        assert_eq!(normalize_team("Palmeiras-SP"), "palmeiras-sp");
        assert_eq!(normalize_team("Flamengo-RJ"), "flamengo-rj");
        assert_eq!(normalize_team("América - MG"), "america-mg");
    }

    #[test]
    fn distinguishes_clubs_by_state() {
        // The whole point: Mineiro and Paranaense must NOT collapse together.
        assert_ne!(normalize_team("Atlético-MG"), normalize_team("Atlético-PR"));
    }

    #[test]
    fn country_parens_become_suffix() {
        assert_eq!(normalize_team("Nacional (URU)"), "nacional-uru");
        assert_eq!(normalize_team("Barcelona-EQU"), "barcelona-equ");
    }

    #[test]
    fn folds_accents() {
        assert_eq!(normalize_team("São Paulo"), "sao paulo");
        assert_eq!(normalize_team("Grêmio-RS"), "gremio-rs");
    }

    #[test]
    fn base_strips_suffix() {
        assert_eq!(base_team("Flamengo-RJ"), "flamengo");
        assert_eq!(base_team("Vasco da Gama RJ"), "vasco da gama");
    }

    #[test]
    fn dates() {
        assert_eq!(normalize_date("2012-05-19 18:30:00"), "2012-05-19");
        assert_eq!(normalize_date("2023-09-24"), "2023-09-24");
        assert_eq!(normalize_date("29/03/2003"), "2003-03-29");
    }

    #[test]
    fn matching() {
        assert!(team_matches("Flamengo", &normalize_team("Flamengo-RJ")));
        assert!(team_matches("sao paulo", &normalize_team("São Paulo FC")));
        assert!(!team_matches("Santos", &normalize_team("Flamengo-RJ")));
        // A precise state query does not bleed across states.
        assert!(team_matches("Atletico-MG", &normalize_team("Atlético-MG")));
        assert!(!team_matches("Atletico-MG", &normalize_team("Atlético-PR")));
    }
}
