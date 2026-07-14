//! Team-name normalization for cross-dataset matching.
//!
//! The bundled CSVs spell the same team many ways: "Palmeiras-SP",
//! "Palmeiras", "SE Palmeiras", "São Paulo" / "Sao Paulo".  Queries need to
//! match these against each other and against user input that may also be
//! casually spelled.  We strip diacritics, drop the state suffix, lowercase,
//! and collapse whitespace — the result is suitable as a key for grouping
//! matches across files and for substring matching against user input.

/// Split a team name into (body, state-code).  Returns `("", body)` if no
/// recognised state suffix is present.
fn split_state_suffix(s: &str) -> (String, Option<String>) {
    let trimmed = s.trim();
    let sep = trimmed
        .char_indices()
        .rev()
        .find(|(_, c)| *c == '-' || c.is_whitespace())
        .map(|(i, _)| i);
    let Some(idx) = sep else {
        return (trimmed.to_string(), None);
    };
    let tail = trimmed[idx + 1..]
        .trim()
        .trim_matches(|c: char| !c.is_alphanumeric());
    if tail.len() == 2 && is_brazilian_state(tail) {
        (
            trimmed[..idx].trim_end().to_string(),
            Some(tail.to_ascii_lowercase()),
        )
    } else {
        (trimmed.to_string(), None)
    }
}

fn is_brazilian_state(s: &str) -> bool {
    matches!(
        s.to_ascii_uppercase().as_str(),
        "AC" | "AL" | "AP" | "AM" | "BA" | "CE" | "DF" | "ES" | "GO" | "MA" | "MT"
            | "MS" | "MG" | "PA" | "PB" | "PR" | "PE" | "PI" | "RJ" | "RN" | "RS"
            | "RO" | "RR" | "SC" | "SP" | "SE" | "TO"
    )
}

/// Strip common Brazilian club-type tokens ("FC", "EC", "SC", "AC", "AA",
/// "Esporte Clube", "Futebol Clube", "Sport Club", "Clube de Regatas")
/// from the start or end of a normalized name.
fn strip_club_type(name: &str) -> String {
    let lower = name.trim();
    // Multi-word descriptors are removed first.
    let multi = [
        "futebol clube",
        "esporte clube",
        "sport club",
        "clube de regatas",
        "associacao atletica",
        "associacao desportiva",
        "esporte clube de",
    ];
    let mut s = lower.to_string();
    for m in multi {
        if s.starts_with(m) {
            s = s[m.len()..].trim_start().to_string();
        }
        if s.ends_with(m) {
            s = s[..s.len() - m.len()].trim_end().to_string();
        }
    }
    // Single-token descriptors.
    let single = ["fc", "ec", "sc", "ac", "aa", "ad", "cr", "ca", "se"];
    let mut tokens: Vec<&str> = s.split_whitespace().collect();
    while let Some(first) = tokens.first() {
        if single.contains(first) {
            tokens.remove(0);
        } else {
            break;
        }
    }
    while let Some(last) = tokens.last() {
        if single.contains(last) {
            tokens.pop();
        } else {
            break;
        }
    }
    tokens.join(" ")
}

/// A small alias table for Brazilian clubs whose common long-form name
/// doesn't reduce to the short form via simple suffix stripping.
fn apply_alias(name: &str) -> String {
    match name {
        "atletico mineiro" | "clube atletico mineiro" => "atletico mg".to_string(),
        "atletico paranaense" | "athletico paranaense" => "atletico pr".to_string(),
        "athletico" => "atletico pr".to_string(),
        "atletico goianiense" => "atletico go".to_string(),
        "vasco da gama" => "vasco".to_string(),
        "bragantino" | "red bull bragantino" => "bragantino".to_string(),
        "botafogo de futebol e regatas" => "botafogo".to_string(),
        "csa" => "csa".to_string(),
        _ => name.to_string(),
    }
}

/// Map Latin characters with diacritics to their ASCII counterparts.
fn fold_diacritic(c: char) -> char {
    match c {
        'á' | 'à' | 'â' | 'ã' | 'ä' | 'å' | 'ª' => 'a',
        'Á' | 'À' | 'Â' | 'Ã' | 'Ä' | 'Å' => 'a',
        'é' | 'è' | 'ê' | 'ë' => 'e',
        'É' | 'È' | 'Ê' | 'Ë' => 'e',
        'í' | 'ì' | 'î' | 'ï' => 'i',
        'Í' | 'Ì' | 'Î' | 'Ï' => 'i',
        'ó' | 'ò' | 'ô' | 'õ' | 'ö' | 'º' => 'o',
        'Ó' | 'Ò' | 'Ô' | 'Õ' | 'Ö' => 'o',
        'ú' | 'ù' | 'û' | 'ü' => 'u',
        'Ú' | 'Ù' | 'Û' | 'Ü' => 'u',
        'ç' | 'Ç' => 'c',
        'ñ' | 'Ñ' => 'n',
        _ => c.to_ascii_lowercase(),
    }
}

/// Bases that are ambiguous without a state qualifier: "atletico" alone
/// could be MG, PR or GO; "america" could be MG, RJ or RN.  For these, the
/// state code (or its equivalent from the long form) is retained.
const AMBIGUOUS_BASES: &[&str] = &["atletico", "america"];

/// Lowercase, fold accents, collapse whitespace and punctuation.  Doesn't
/// touch state suffixes or aliases — those are handled by `normalize_team`.
fn ascii_collapse(s: &str) -> String {
    let folded: String = s.chars().map(fold_diacritic).collect();
    let mut out = String::with_capacity(folded.len());
    let mut prev_space = true;
    for c in folded.chars() {
        if c.is_alphanumeric() {
            out.push(c);
            prev_space = false;
        } else if c.is_whitespace() || c == '-' || c == '.' || c == ',' || c == '/' {
            if !prev_space {
                out.push(' ');
                prev_space = true;
            }
        }
    }
    out.trim().to_string()
}

/// Normalize a free-form team name to a canonical key suitable for cross-CSV
/// matching: lowercase, ASCII-folded, with state suffix and club-type
/// descriptors removed.  For ambiguous bases (e.g. "Atletico") the state code
/// is preserved.
pub fn normalize_team(name: &str) -> String {
    let (body, state) = split_state_suffix(name.trim());
    let body = ascii_collapse(&body);
    let body = strip_club_type(&body);
    let (body, _) = split_state_suffix(&body); // catches "Botafogo FC RJ"
    let body = strip_club_type(&body);
    let aliased = apply_alias(&body);
    if aliased != body {
        return aliased;
    }
    // For ambiguous bases keep the state code so e.g. atletico-mg ≠ atletico-pr.
    if let Some(st) = state {
        let first = body.split_whitespace().next().unwrap_or("");
        if AMBIGUOUS_BASES.contains(&first) {
            return format!("{body} {st}");
        }
    }
    body
}

/// Does `haystack` (already a normalized key, or raw name) contain the
/// normalized form of `needle`?  Used for "fuzzy" team lookup from user input.
pub fn matches_team(haystack: &str, needle: &str) -> bool {
    let h = normalize_team(haystack);
    let n = normalize_team(needle);
    if n.is_empty() {
        return false;
    }
    h == n || h.split_whitespace().any(|tok| tok == n) || h.contains(&n)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn strips_unambiguous_state_suffix() {
        assert_eq!(normalize_team("Palmeiras-SP"), "palmeiras");
        assert_eq!(normalize_team("Flamengo-RJ"), "flamengo");
        assert_eq!(normalize_team("Botafogo RJ"), "botafogo");
        assert_eq!(normalize_team("Sao Paulo-SP"), "sao paulo");
    }

    #[test]
    fn keeps_state_for_ambiguous_bases() {
        // Multiple clubs share these prefixes — the state code disambiguates.
        assert_eq!(normalize_team("Atletico-MG"), "atletico mg");
        assert_eq!(normalize_team("Atletico-PR"), "atletico pr");
        assert_eq!(normalize_team("America-MG"), "america mg");
    }

    #[test]
    fn folds_accents() {
        assert_eq!(normalize_team("São Paulo"), "sao paulo");
        assert_eq!(normalize_team("Grêmio"), "gremio");
        assert_eq!(normalize_team("Avaí"), "avai");
    }

    #[test]
    fn long_form_aliases_match_short_form() {
        assert_eq!(normalize_team("Atletico Mineiro"), "atletico mg");
        assert_eq!(normalize_team("Atletico Mineiro"), normalize_team("Atletico-MG"));
        assert_eq!(normalize_team("Athletico Paranaense"), normalize_team("Atletico-PR"));
        assert_eq!(normalize_team("Vasco Da Gama RJ"), normalize_team("Vasco da Gama-RJ"));
        assert_eq!(normalize_team("EC Bahia"), normalize_team("Bahia-BA"));
        assert_eq!(normalize_team("Fortaleza FC"), normalize_team("Fortaleza-CE"));
    }

    #[test]
    fn matches_team_substring() {
        assert!(matches_team("Palmeiras-SP", "palmeiras"));
        assert!(matches_team("São Paulo", "sao paulo"));
        assert!(matches_team("FC Barcelona", "barcelona"));
        assert!(!matches_team("Palmeiras", "santos"));
    }

    #[test]
    fn empty_needle_does_not_match() {
        assert!(!matches_team("Palmeiras", ""));
    }
}
