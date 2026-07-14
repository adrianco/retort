// normalize - canonical team-name keys for robust matching.
//
// The datasets name the same club many different ways:
//   "Palmeiras-SP", "Palmeiras", "São Paulo" vs "Sao Paulo",
//   "América - MG", "Nacional (URU)", "Barcelona-EQU".
// `normalize_team` folds all of these to a lowercase, accent-free, suffix-free
// key so a user query for "Flamengo" matches stored "Flamengo-RJ".

/// Strip the Portuguese/European accents we encounter to their ASCII base.
fn strip_accents(c: char) -> char {
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

/// Remove any parenthetical groups, e.g. "Nacional (URU)" -> "Nacional ".
fn remove_parentheticals(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    let mut depth = 0u32;
    for c in s.chars() {
        match c {
            '(' => depth += 1,
            ')' => depth = depth.saturating_sub(1),
            _ if depth == 0 => out.push(c),
            _ => {}
        }
    }
    out
}

/// Returns true if `tok` looks like a 2-3 letter state/country code (UF or
/// national abbreviation) that should be dropped from the end of a name.
fn is_region_code(tok: &str) -> bool {
    let len = tok.chars().count();
    (2..=3).contains(&len) && tok.chars().all(|c| c.is_ascii_alphabetic())
}

/// Drop a trailing state/country suffix attached with a hyphen, e.g.
/// "Palmeiras-SP" -> "Palmeiras", "América - MG" -> "América ".
fn strip_region_suffix(s: &str) -> String {
    match s.rfind('-') {
        Some(idx) => {
            let tail = s[idx + 1..].trim();
            if is_region_code(tail) {
                s[..idx].to_string()
            } else {
                s.to_string()
            }
        }
        None => s.to_string(),
    }
}

/// Collapse runs of whitespace to single spaces and trim.
fn collapse_ws(s: &str) -> String {
    s.split_whitespace().collect::<Vec<_>>().join(" ")
}

/// Unicode-lowercase (handles accented uppercase like 'Ê' -> 'ê') then fold
/// each accented char to its ASCII base.
fn fold(s: &str) -> String {
    s.to_lowercase().chars().map(strip_accents).collect()
}

/// Produce the **loose** matching key for a team name, used for user-facing
/// queries: the state/country suffix is dropped so "Flamengo" matches
/// "Flamengo-RJ". Note this deliberately merges same-named clubs from
/// different states (e.g. Atlético-MG and Atlético-PR) — use [`canonical_id`]
/// when distinct clubs must stay apart.
pub fn normalize_team(name: &str) -> String {
    let no_parens = remove_parentheticals(name);
    let no_suffix = strip_region_suffix(&no_parens);
    collapse_ws(&fold(&no_suffix))
}

/// Produce the **strict** club identity for a team name. Unlike
/// [`normalize_team`], the state/country code is retained (normalized to
/// `base-code`) so that Atlético-MG and Atlético-PR remain distinct. Used for
/// fixture de-duplication and standings, where merging two clubs would corrupt
/// the table.
pub fn canonical_id(name: &str) -> String {
    let folded = collapse_ws(&fold(&remove_parentheticals(name)));
    if let Some(idx) = folded.rfind('-') {
        let tail = folded[idx + 1..].trim();
        if is_region_code(tail) {
            return format!("{}-{}", folded[..idx].trim(), tail);
        }
    }
    folded
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn strips_state_suffix() {
        assert_eq!(normalize_team("Palmeiras-SP"), "palmeiras");
        assert_eq!(normalize_team("Flamengo-RJ"), "flamengo");
    }

    #[test]
    fn plain_name_unchanged_except_case() {
        assert_eq!(normalize_team("Palmeiras"), "palmeiras");
    }

    #[test]
    fn folds_accents() {
        assert_eq!(normalize_team("São Paulo"), "sao paulo");
        assert_eq!(normalize_team("Sao Paulo"), "sao paulo");
        assert_eq!(normalize_team("Grêmio"), "gremio");
        assert_eq!(normalize_team("Avaí"), "avai");
    }

    #[test]
    fn handles_spaced_dash_suffix() {
        assert_eq!(normalize_team("América - MG"), "america");
    }

    #[test]
    fn removes_country_parenthetical() {
        assert_eq!(normalize_team("Nacional (URU)"), "nacional");
        assert_eq!(normalize_team("Barcelona-EQU"), "barcelona");
    }

    #[test]
    fn trims_and_collapses_whitespace() {
        assert_eq!(normalize_team("  Grêmio  "), "gremio");
        assert_eq!(
            normalize_team("Red  Bull   Bragantino"),
            "red bull bragantino"
        );
    }

    #[test]
    fn distinct_clubs_stay_distinct() {
        // Atlético Mineiro vs Athletico Paranaense must not collide.
        assert_ne!(
            normalize_team("Atlético-MG"),
            normalize_team("Athletico-PR")
        );
    }

    #[test]
    fn canonical_id_keeps_state_to_separate_same_named_clubs() {
        // Loose matching merges these (both "atletico"), but the strict
        // canonical id must keep Atlético-MG and Atlético-PR distinct.
        assert_eq!(normalize_team("Atletico-MG"), normalize_team("Atletico-PR"));
        assert_ne!(canonical_id("Atletico-MG"), canonical_id("Atletico-PR"));
        assert_eq!(canonical_id("Atletico-MG"), "atletico-mg");
    }

    #[test]
    fn canonical_id_normalizes_formatting_and_accents() {
        // Same club written different ways within one source folds together.
        assert_eq!(canonical_id("Atlético - MG"), "atletico-mg");
        assert_eq!(canonical_id("Grêmio-RS"), "gremio-rs");
        // A club with no suffix keeps just its folded base.
        assert_eq!(canonical_id("Flamengo"), "flamengo");
    }

    #[test]
    fn handles_long_name_with_parens_and_suffix() {
        assert_eq!(
            normalize_team("Boavista Sport Club (antigo Esporte Clube Barreira) - RJ"),
            "boavista sport club"
        );
    }
}
