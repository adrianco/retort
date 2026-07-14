//! Team-name normalization and club entity resolution.
//!
//! Context: the same club is named many different ways across the datasets:
//!  - `novo_campeonato_brasileiro.csv` uses short names ("Flamengo"), adding a
//!    state suffix only to disambiguate ("Atlético-MG").
//!  - `Brasileirao_Matches.csv` always appends the state ("Flamengo-RJ").
//!  - `BR-Football-Dataset.csv` uses long descriptive names ("Atletico
//!    Mineiro", "Vasco da Gama", "EC Bahia").
//!
//! Naive suffix stripping both *splits* one club into several keys and
//! *merges* distinct clubs that differ only by state (Atlético-MG vs
//! Atlético-GO). To resolve this we:
//!  1. derive a `lookup_key` (accent-folded, lower-cased, punctuation→spaces);
//!  2. consult a curated registry of Brazilian clubs that maps every known
//!     name variant to one canonical key + display name;
//!  3. fall back, for unregistered clubs, to the lookup key with a trailing
//!     state/country code removed.
//!
//! This makes the club key stable across files, which in turn lets matches
//! de-duplicate correctly (see `data::dedup_matches`).

use std::collections::HashMap;
use std::sync::OnceLock;

/// Brazilian state abbreviations plus South-American country codes that appear
/// as trailing suffixes (the latter in the Libertadores dataset).
const SUFFIX_CODES: &[&str] = &[
    "ac", "al", "ap", "am", "ba", "ce", "df", "es", "go", "ma", "mt", "ms", "mg", "pa", "pb",
    "pr", "pe", "pi", "rj", "rn", "rs", "ro", "rr", "sc", "sp", "se", "to", "uru", "arg", "equ",
    "par", "bol", "per", "col", "ven", "chi", "bra", "mex", "ury",
];

/// Curated club registry: `(canonical_key, display_name, [name variants])`.
///
/// Only clubs whose name genuinely varies *between* datasets need an entry —
/// clubs named consistently are handled by the suffix-stripping fallback. The
/// variant strings are written in `lookup_key` form (lower-case, no accents,
/// punctuation already turned into spaces).
const CLUBS: &[(&str, &str, &[&str])] = &[
    (
        "atletico-mg",
        "Atlético Mineiro",
        &["atletico mg", "atletico mineiro", "clube atletico mineiro"],
    ),
    (
        "atletico-go",
        "Atlético Goianiense",
        &["atletico go", "atletico goianiense"],
    ),
    (
        "athletico-pr",
        "Athletico Paranaense",
        &[
            "athletico pr",
            "atletico pr",
            "athletico paranaense",
            "atletico paranaense",
            "clube athletico paranaense",
        ],
    ),
    (
        "america-mg",
        "América Mineiro",
        &["america mg", "america mineiro"],
    ),
    (
        "america-rn",
        "América de Natal",
        &["america rn", "america fc natal", "america natal", "america de natal"],
    ),
    (
        "bahia",
        "Bahia",
        &["bahia", "bahia ba", "ec bahia", "esporte clube bahia"],
    ),
    (
        "fortaleza",
        "Fortaleza",
        &["fortaleza", "fortaleza ce", "fortaleza fc", "fortaleza ec"],
    ),
    (
        "bragantino",
        "Red Bull Bragantino",
        &["bragantino", "bragantino sp", "red bull bragantino", "red bull bragantino sp"],
    ),
    ("bragantino-pa", "Bragantino-PA", &["bragantino pa"]),
    (
        "santa-cruz",
        "Santa Cruz",
        &["santa cruz", "santa cruz pe", "santa cruz fc"],
    ),
    (
        "sport-recife",
        "Sport Recife",
        &["sport", "sport pe", "sport recife", "sport club do recife"],
    ),
    (
        "vasco",
        "Vasco da Gama",
        &["vasco", "vasco rj", "vasco da gama", "vasco da gama rj"],
    ),
    (
        "juventude",
        "Juventude",
        &["juventude", "juventude rs", "ec juventude"],
    ),
    ("botafogo-sp", "Botafogo-SP", &["botafogo sp"]),
    ("botafogo-pb", "Botafogo-PB", &["botafogo pb"]),
];

struct Registry {
    /// variant lookup-key -> canonical key
    aliases: HashMap<&'static str, &'static str>,
    /// canonical key -> display name
    displays: HashMap<&'static str, &'static str>,
}

fn registry() -> &'static Registry {
    static REGISTRY: OnceLock<Registry> = OnceLock::new();
    REGISTRY.get_or_init(|| {
        let mut aliases = HashMap::new();
        let mut displays = HashMap::new();
        for (canon, display, variants) in CLUBS {
            displays.insert(*canon, *display);
            for v in *variants {
                aliases.insert(*v, *canon);
            }
        }
        Registry { aliases, displays }
    })
}

/// Fold common Portuguese/Latin accented characters down to ASCII.
pub fn fold_accents(s: &str) -> String {
    s.chars()
        .map(|c| match c {
            'á' | 'à' | 'â' | 'ã' | 'ä' | 'Á' | 'À' | 'Â' | 'Ã' | 'Ä' => 'a',
            'é' | 'è' | 'ê' | 'ë' | 'É' | 'È' | 'Ê' | 'Ë' => 'e',
            'í' | 'ì' | 'î' | 'ï' | 'Í' | 'Ì' | 'Î' | 'Ï' => 'i',
            'ó' | 'ò' | 'ô' | 'õ' | 'ö' | 'Ó' | 'Ò' | 'Ô' | 'Õ' | 'Ö' => 'o',
            'ú' | 'ù' | 'û' | 'ü' | 'Ú' | 'Ù' | 'Û' | 'Ü' => 'u',
            'ç' | 'Ç' => 'c',
            'ñ' | 'Ñ' => 'n',
            other => other,
        })
        .collect()
}

fn strip_parentheticals(s: &str) -> String {
    let mut out = String::new();
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

fn collapse_ws(s: &str) -> String {
    s.split_whitespace().collect::<Vec<_>>().join(" ")
}

/// Normalized form used for registry lookup: accent-folded, lower-cased, with
/// parentheticals removed and `-`/`/`/`.` turned into spaces. The trailing
/// state suffix is *kept* so distinct same-named clubs stay distinct.
pub fn lookup_key(raw: &str) -> String {
    let folded = fold_accents(raw).to_lowercase();
    let no_paren = strip_parentheticals(&folded);
    let spaced: String = no_paren
        .chars()
        .map(|c| if matches!(c, '-' | '/' | '.' | ',') { ' ' } else { c })
        .collect();
    collapse_ws(&spaced)
}

/// Drop a single trailing state/country code token from a lookup key.
fn fallback_key(lookup: &str) -> String {
    let mut tokens: Vec<&str> = lookup.split_whitespace().collect();
    if tokens.len() > 1 {
        if let Some(last) = tokens.last() {
            if SUFFIX_CODES.contains(last) {
                tokens.pop();
            }
        }
    }
    tokens.join(" ")
}

/// Human-readable club name: parentheticals and a trailing state suffix
/// removed, accents and capitalization preserved.
pub fn clean_name(raw: &str) -> String {
    let no_paren = strip_parentheticals(raw);
    let collapsed = collapse_ws(&no_paren);
    // Strip a trailing "-XX" / " - XX" / " XX" state-or-country code.
    let lower_fold = fold_accents(&collapsed).to_lowercase();
    let tokens: Vec<&str> = collapsed.split_whitespace().collect();
    let fold_tokens: Vec<&str> = lower_fold.split_whitespace().collect();
    if tokens.len() > 1 {
        if let Some(last) = fold_tokens.last() {
            let last = last.trim_end_matches('-');
            if SUFFIX_CODES.contains(&last) {
                return tokens[..tokens.len() - 1]
                    .join(" ")
                    .trim_end_matches(|c| c == '-' || c == ' ')
                    .to_string();
            }
        }
    }
    collapsed
}

/// Resolve a raw club name to its `(canonical_key, display_name)`.
pub fn resolve(raw: &str) -> (String, String) {
    let lk = lookup_key(raw);
    if lk.is_empty() {
        return (String::new(), raw.trim().to_string());
    }
    let reg = registry();
    if let Some(&canon) = reg.aliases.get(lk.as_str()) {
        let display = reg.displays.get(canon).copied().unwrap_or(canon);
        return (canon.to_string(), display.to_string());
    }
    (fallback_key(&lk), clean_name(raw))
}

/// Canonical match key for a raw club name.
pub fn team_key(raw: &str) -> String {
    resolve(raw).0
}

/// True when a stored club key plausibly refers to the same club as a free
/// text `query`. Matching uses both the query's resolved canonical key and its
/// suffix-stripped fallback key, with symmetric-substring tolerance so partial
/// names ("Atletico") still match.
pub fn key_matches(team_key: &str, query: &str) -> bool {
    if team_key.is_empty() {
        return false;
    }
    let qk = resolve(query).0;
    let q_fallback = fallback_key(&lookup_key(query));
    for candidate in [qk.as_str(), q_fallback.as_str()] {
        if candidate.is_empty() {
            continue;
        }
        if team_key == candidate
            || team_key.contains(candidate)
            || candidate.contains(team_key)
        {
            return true;
        }
    }
    false
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn registry_unifies_long_and_short_names() {
        // Atlético Mineiro: short+state, no-accent and long forms all agree.
        assert_eq!(team_key("Atlético-MG"), "atletico-mg");
        assert_eq!(team_key("Atletico-MG"), "atletico-mg");
        assert_eq!(team_key("Atletico Mineiro"), "atletico-mg");
    }

    #[test]
    fn registry_keeps_distinct_clubs_apart() {
        // The three "Atléticos" must not collapse together.
        assert_ne!(team_key("Atlético-MG"), team_key("Atlético-GO"));
        assert_ne!(team_key("Atlético-MG"), team_key("Athletico-PR"));
        assert_ne!(team_key("América-MG"), team_key("América-RN"));
    }

    #[test]
    fn fallback_unifies_simple_suffix_variants() {
        assert_eq!(team_key("Flamengo"), team_key("Flamengo-RJ"));
        assert_eq!(team_key("Sao Paulo"), team_key("São Paulo"));
        assert_eq!(team_key("Palmeiras-SP"), "palmeiras");
    }

    #[test]
    fn long_name_aliases_resolve() {
        assert_eq!(team_key("Vasco da Gama"), team_key("Vasco"));
        assert_eq!(team_key("EC Bahia"), team_key("Bahia"));
        assert_eq!(team_key("Sport Recife"), team_key("Sport"));
        assert_eq!(team_key("Red Bull Bragantino"), team_key("Bragantino"));
    }

    #[test]
    fn key_matching_tolerates_partial_queries() {
        assert!(key_matches("flamengo", "Flamengo"));
        assert!(key_matches("flamengo", "Flamengo-RJ"));
        assert!(key_matches("atletico-mg", "Atletico Mineiro"));
        assert!(!key_matches("flamengo", "Fluminense"));
    }
}
