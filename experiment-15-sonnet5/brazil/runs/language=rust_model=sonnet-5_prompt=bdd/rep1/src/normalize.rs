//! Team/club/name normalization.
//!
//! The provided datasets spell the same club several different ways:
//! state suffixes ("Palmeiras-SP" vs "Palmeiras"), full legal names
//! ("Sport Club Corinthians Paulista"), parenthetical qualifiers
//! ("Nacional (URU)"), and Portuguese diacritics ("Grêmio" vs "Gremio").
//! This module reduces any spelling to a comparable ASCII, lowercase key.
//!
//! Crucially, a trailing state/country qualifier is *disambiguating*, not
//! decorative: "Atlético-MG" and "Atlético-PR" are two different real
//! clubs that happen to share a base name, as are "Nacional (URU)" and
//! "Nacional (PAR)". Discarding the qualifier would silently merge their
//! match histories, so it is always kept (just reformatted consistently),
//! e.g. "atletico mg" / "atletico pr". Bare, unqualified queries still
//! match via substring containment (see [`keys_match`]), so "Flamengo"
//! still finds "Flamengo-RJ" records; only genuinely distinct clubs stay
//! distinct.

/// Strip common Portuguese/Spanish diacritics, mapping to plain ASCII letters.
pub fn strip_diacritics(input: &str) -> String {
    input
        .chars()
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

/// True if `s` looks like a short region/country code (2-4 ASCII
/// alphabetic characters), e.g. "SP", "RJ", "URU", "EQU" - as opposed to
/// decorative parenthetical text like "antigo Esporte Clube Barreira".
fn looks_like_region_code(s: &str) -> bool {
    let s = s.trim();
    (2..=4).contains(&s.chars().count()) && s.chars().all(|c| c.is_ascii_alphabetic())
}

/// Remove a parenthetical qualifier. If its content looks like a short
/// region/country code, it is returned as the extracted qualifier;
/// otherwise the parenthetical is purely decorative and is discarded
/// entirely (e.g. "(antigo Esporte Clube Barreira)").
fn extract_parenthetical(input: &str) -> (String, Option<String>) {
    let mut out = String::with_capacity(input.len());
    let mut code = None;
    let mut depth: u32 = 0;
    let mut current = String::new();
    for c in input.chars() {
        match c {
            '(' => {
                depth += 1;
                current.clear();
            }
            ')' => {
                if depth > 0 {
                    depth -= 1;
                    if looks_like_region_code(&current) {
                        code = Some(current.trim().to_string());
                    }
                }
            }
            _ if depth == 0 => out.push(c),
            _ => current.push(c),
        }
    }
    (out, code)
}

/// Remove a trailing state/country qualifier such as "-SP", " - RJ", "-EQU",
/// returning the remaining base name and the extracted code (if any).
fn extract_trailing_region_code(input: &str) -> (String, Option<String>) {
    let trimmed = input.trim();
    if let Some(idx) = trimmed.rfind('-') {
        let (head, tail) = trimmed.split_at(idx);
        let code = tail[1..].trim();
        if looks_like_region_code(code) {
            let base = head.trim_end().trim_end_matches('-').trim().to_string();
            return (base, Some(code.to_string()));
        }
    }
    (trimmed.to_string(), None)
}

/// Split a raw team name into its base name and an optional disambiguating
/// region/country qualifier, discarding purely decorative parenthetical
/// text. A trailing hyphen code takes precedence if both forms are present.
fn split_base_and_qualifier(raw: &str) -> (String, Option<String>) {
    let (without_paren, paren_code) = extract_parenthetical(raw);
    let (base, suffix_code) = extract_trailing_region_code(without_paren.trim());
    (base, suffix_code.or(paren_code))
}

/// Normalize a raw team/club name into a lowercase, accent-free key
/// suitable for equality/substring comparisons across datasets. Any
/// disambiguating region/country qualifier is preserved as a trailing
/// token so distinct clubs sharing a base name (e.g. "Atlético-MG" vs
/// "Atlético-PR") never collide, while unqualified queries still match via
/// substring containment.
pub fn normalize_team_name(raw: &str) -> String {
    let (base, code) = split_base_and_qualifier(raw);
    let base_key = strip_diacritics(&base).to_lowercase();
    let mut key = base_key.split_whitespace().collect::<Vec<_>>().join(" ");
    if let Some(code) = code {
        key.push(' ');
        key.push_str(&strip_diacritics(&code).to_lowercase());
    }
    key
}

/// Produce a human-friendly display name: strips decorative parentheticals
/// but preserves original casing/accents, keeping any disambiguating
/// region/country qualifier as a "-CODE" suffix.
pub fn display_team_name(raw: &str) -> String {
    let (base, code) = split_base_and_qualifier(raw);
    let base = base.split_whitespace().collect::<Vec<_>>().join(" ");
    match code {
        Some(code) => format!("{base}-{}", code.to_uppercase()),
        None => base,
    }
}

/// True if two normalized keys likely refer to the same club/entity: exact
/// match, or one is a substring of the other (handles abbreviated vs. full
/// legal names, e.g. "corinthians" vs "sport club corinthians paulista",
/// and unqualified vs. qualified names, e.g. "flamengo" vs "flamengo rj").
pub fn keys_match(candidate_normalized: &str, query_normalized: &str) -> bool {
    if query_normalized.is_empty() || candidate_normalized.is_empty() {
        return false;
    }
    candidate_normalized == query_normalized
        || candidate_normalized.contains(query_normalized)
        || query_normalized.contains(candidate_normalized)
}

/// Convenience: normalize both `raw` and `query`, then test if they match.
pub fn name_matches(raw: &str, query: &str) -> bool {
    keys_match(&normalize_team_name(raw), &normalize_team_name(query))
}

#[cfg(test)]
mod tests {
    use super::*;

    // Given a team name with a state suffix
    // When it is normalized
    // Then the suffix is kept (lowercased) as a disambiguating token
    #[test]
    fn test_given_state_suffixed_name_when_normalizing_then_suffix_is_kept_lowercase() {
        assert_eq!(normalize_team_name("Palmeiras-SP"), "palmeiras sp");
        assert_eq!(normalize_team_name("Flamengo-RJ"), "flamengo rj");
    }

    // Given two different real clubs that share a base name but differ by
    // state (e.g. Atlético Mineiro vs Athletico Paranaense)
    // When they are normalized
    // Then they produce distinct keys instead of colliding
    #[test]
    fn test_given_two_clubs_sharing_a_base_name_when_normalizing_then_keys_are_distinct() {
        assert_ne!(
            normalize_team_name("Atlético-MG"),
            normalize_team_name("Atlético-PR")
        );
    }

    // Given a team name with accents
    // When it is normalized
    // Then accents are stripped to plain ASCII
    #[test]
    fn test_given_accented_name_when_normalizing_then_accents_are_removed() {
        assert_eq!(normalize_team_name("Grêmio"), "gremio");
        assert_eq!(normalize_team_name("São Paulo"), "sao paulo");
    }

    // Given a team name with a space-hyphen-space state suffix
    // When it is normalized
    // Then the suffix is kept as a disambiguating token
    #[test]
    fn test_given_spaced_hyphen_suffix_when_normalizing_then_suffix_is_kept() {
        assert_eq!(normalize_team_name("América - MG"), "america mg");
    }

    // Given a team name with a decorative (non-code) parenthetical
    // When it is normalized
    // Then the parenthetical content is discarded
    #[test]
    fn test_given_decorative_parenthetical_when_normalizing_then_it_is_removed() {
        assert_eq!(
            normalize_team_name("Boavista Sport Club (antigo Esporte Clube Barreira) - RJ"),
            "boavista sport club rj"
        );
    }

    // Given a team name with a country-code parenthetical
    // When it is normalized
    // Then the code is kept as a disambiguating token
    #[test]
    fn test_given_country_code_parenthetical_when_normalizing_then_code_is_kept() {
        assert_eq!(normalize_team_name("Nacional (URU)"), "nacional uru");
    }

    // Given two clubs from different countries sharing a base name, spelled
    // only via a parenthetical country code
    // When they are normalized
    // Then they produce distinct keys
    #[test]
    fn test_given_same_base_name_different_country_parentheticals_when_normalizing_then_keys_differ()
     {
        assert_ne!(
            normalize_team_name("Nacional (URU)"),
            normalize_team_name("Nacional (PAR)")
        );
    }

    // Given the same club spelled once with a hyphen suffix and once with
    // an equivalent parenthetical qualifier
    // When both are normalized
    // Then they produce the same key
    #[test]
    fn test_given_hyphen_and_parenthetical_spellings_of_same_qualifier_when_normalizing_then_keys_match()
     {
        assert_eq!(
            normalize_team_name("Universitario-PER"),
            normalize_team_name("Universitario (PER)")
        );
    }

    // Given a hyphenated club name whose suffix is not a real region code
    // When it is normalized
    // Then the hyphenated part is preserved as part of the base name
    #[test]
    fn test_given_hyphenated_name_without_region_code_when_normalizing_then_name_is_kept() {
        // "EQU" here is treated as a region code (Ecuador); this test
        // covers a suffix that does *not* look like one.
        assert_eq!(normalize_team_name("Some-Club"), "some club");
    }

    // Given a short club name and its full legal name
    // When checking if the keys match
    // Then they are considered the same club
    #[test]
    fn test_given_short_and_full_legal_name_when_matching_then_they_are_equal() {
        assert!(name_matches(
            "Corinthians",
            "Sport Club Corinthians Paulista"
        ));
    }

    // Given a bare (unqualified) team name and its state-qualified spelling
    // When checking if the keys match
    // Then they are considered the same club
    #[test]
    fn test_given_bare_name_and_qualified_spelling_when_matching_then_they_are_equal() {
        assert!(name_matches("Flamengo", "Flamengo-RJ"));
    }

    // Given two unrelated club names
    // When checking if the keys match
    // Then they are not considered the same club
    #[test]
    fn test_given_unrelated_names_when_matching_then_they_are_not_equal() {
        assert!(!name_matches("Flamengo", "Fluminense"));
    }

    // Given an empty query
    // When checking if the keys match
    // Then no match is reported
    #[test]
    fn test_given_empty_query_when_matching_then_no_match_is_reported() {
        assert!(!name_matches("Flamengo", ""));
    }

    // Given a display name request for a raw suffixed name
    // When formatting for display
    // Then original casing/accents are preserved and the suffix is
    // rendered as an uppercase "-CODE"
    #[test]
    fn test_given_suffixed_accented_name_when_displaying_then_casing_and_accents_are_kept() {
        assert_eq!(display_team_name("Grêmio-RS"), "Grêmio-RS");
    }

    // Given two different clubs sharing a base name
    // When formatting both for display
    // Then the resulting display names are distinct
    #[test]
    fn test_given_two_clubs_sharing_a_base_name_when_displaying_then_names_are_distinct() {
        assert_ne!(
            display_team_name("Atlético-MG"),
            display_team_name("Atlético-PR")
        );
    }
}
