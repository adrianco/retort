//! Team / club name normalization.
//!
//! The datasets name the same club many ways:
//!   - state suffix:    "Palmeiras-SP", "América - MG", "Barcelona-EQU"
//!   - country code:    "Nacional (URU)"
//!   - accented/plain:  "São Paulo" vs "Sao Paulo"
//!   - English variant: "Vasco Da Gama RJ", "Atletico Mineiro", "Sao Paulo"
//!
//! Naively dropping the state suffix is wrong: "Atlético-MG" (Mineiro) and
//! "Athletico-PR" (Paranaense) are *different* clubs. So we resolve each name
//! through a curated alias table to a single canonical club, falling back to a
//! cleaned, suffix-preserving key for clubs not in the table.

/// Replace accented Latin characters with their ASCII counterpart.
pub fn strip_accents(input: &str) -> String {
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

fn collapse_whitespace(s: &str) -> String {
    s.split_whitespace().collect::<Vec<_>>().join(" ")
}

/// Remove any "(...)" qualifier such as country codes "(URU)".
fn strip_parens(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    let mut depth = 0i32;
    for c in s.chars() {
        match c {
            '(' => depth += 1,
            ')' => depth = (depth - 1).max(0),
            _ if depth == 0 => out.push(c),
            _ => {}
        }
    }
    out
}

/// Drop a trailing 2-4 letter state/country code after the final hyphen.
fn strip_state_suffix(s: &str) -> String {
    if let Some(idx) = s.rfind('-') {
        let (head, tail) = s.split_at(idx);
        let tail = tail[1..].trim();
        let head_trimmed = head.trim();
        let is_code = (2..=4).contains(&tail.chars().count())
            && tail.chars().all(|c| c.is_ascii_alphabetic());
        if is_code && !head_trimmed.is_empty() {
            return head_trimmed.to_string();
        }
    }
    s.to_string()
}

/// Lower-case, accent-free, parenthesis-free form with whitespace collapsed.
fn clean(name: &str) -> String {
    let s = strip_accents(name).to_lowercase();
    let s = strip_parens(&s);
    let s = s.replace(" - ", "-");
    collapse_whitespace(&s)
}

/// A resolved canonical name: a lookup `key` (accent-free, lower-case) and a
/// human-friendly `display` form.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Canon {
    pub key: String,
    pub display: String,
}

/// Resolve a cleaned, space-separated name to a canonical club display name.
/// Ordered most-specific first so e.g. "atletico mg" never matches the bare
/// "atletico" rule. Returns `None` for clubs outside the curated set.
fn alias(spaced: &str) -> Option<&'static str> {
    let has = |needle: &str| spaced.split_whitespace().any(|w| w == needle);
    let contains = |needle: &str| spaced.contains(needle);

    // Clubs that are only distinguishable by their state suffix.
    if contains("athletico") || (contains("atletico") && (has("pr") || contains("paranaense"))) {
        return Some("Athletico Paranaense");
    }
    if contains("atletico") && (has("mg") || contains("mineiro")) {
        return Some("Atlético Mineiro");
    }
    if contains("atletico") && (has("go") || contains("goianiense")) {
        return Some("Atlético Goianiense");
    }
    if contains("atletico") && (has("ac") || contains("acreano")) {
        return Some("Atlético Acreano");
    }
    if contains("america") && (has("mg") || contains("mineiro")) {
        return Some("América-MG");
    }
    if contains("america") && (has("rn") || contains("natal")) {
        return Some("América-RN");
    }
    if contains("botafogo") && has("sp") {
        return Some("Botafogo-SP");
    }
    if contains("botafogo") && has("pb") {
        return Some("Botafogo-PB");
    }
    if contains("botafogo") {
        return Some("Botafogo");
    }

    // Unambiguous single-identifier clubs.
    let rules: &[(&str, &str)] = &[
        ("sao paulo", "São Paulo"),
        ("flamengo", "Flamengo"),
        ("fluminense", "Fluminense"),
        ("vasco", "Vasco da Gama"),
        ("corinthians", "Corinthians"),
        ("palmeiras", "Palmeiras"),
        ("santos", "Santos"),
        ("gremio", "Grêmio"),
        ("internacional", "Internacional"),
        ("cruzeiro", "Cruzeiro"),
        ("bahia", "Bahia"),
        ("fortaleza", "Fortaleza"),
        ("ceara", "Ceará"),
        ("goias", "Goiás"),
        ("chapecoense", "Chapecoense"),
        ("avai", "Avaí"),
        ("csa", "CSA"),
        ("coritiba", "Coritiba"),
        ("bragantino", "Red Bull Bragantino"),
        ("red bull", "Red Bull Bragantino"),
        ("cuiaba", "Cuiabá"),
        ("vitoria", "Vitória"),
        ("parana", "Paraná"),
        ("nautico", "Náutico"),
        ("ponte preta", "Ponte Preta"),
        ("juventude", "Juventude"),
        ("figueirense", "Figueirense"),
        ("criciuma", "Criciúma"),
        ("portuguesa", "Portuguesa"),
        ("guarani", "Guarani"),
        ("sport", "Sport Recife"),
        ("nautico", "Náutico"),
    ];
    for (needle, canonical) in rules {
        if contains(needle) {
            return Some(canonical);
        }
    }
    None
}

/// Resolve any team name to a canonical [`Canon`].
pub fn canon(name: &str) -> Canon {
    let cleaned = clean(name);
    let spaced = collapse_whitespace(&cleaned.replace('-', " "));
    if let Some(display) = alias(&spaced) {
        return Canon {
            key: strip_accents(display).to_lowercase(),
            display: display.to_string(),
        };
    }
    // Fallback: keep the suffix in the key (avoids collisions) but present a
    // tidy, suffix-free display name.
    Canon {
        key: spaced,
        display: pretty_team(name),
    }
}

/// A human-friendly team name (drop country parentheticals and a trailing
/// state code) preserving accents and casing. Used as the display fallback.
pub fn pretty_team(name: &str) -> String {
    let s = strip_parens(name);
    let s = s.replace(" - ", "-");
    let s = collapse_whitespace(&s);
    collapse_whitespace(&strip_state_suffix(&s))
}

/// Does a user query refer to the same club as a stored canonical key?
pub fn key_matches(query_key: &str, stored_key: &str) -> bool {
    if query_key.is_empty() || stored_key.is_empty() {
        return false;
    }
    query_key == stored_key
        || (query_key.len() >= 3 && stored_key.contains(query_key))
        || (stored_key.len() >= 3 && query_key.contains(stored_key))
}

/// Normalize a FIFA club name (no state suffixes there): fold accents/case/ws.
pub fn normalize_club(name: &str) -> String {
    collapse_whitespace(&strip_accents(name).to_lowercase())
}

/// Loose substring match for FIFA club names.
pub fn club_matches(query: &str, candidate: &str) -> bool {
    let q = normalize_club(query);
    let c = normalize_club(candidate);
    if q.is_empty() || c.is_empty() {
        return false;
    }
    q == c || (q.len() >= 3 && c.contains(&q)) || (c.len() >= 3 && q.contains(&c))
}

/// Resolve a competition query to a canonical competition name. `None` means
/// "no precise match" — callers may fall back to a loose substring test.
pub fn resolve_competition(query: &str) -> Option<&'static str> {
    let q = strip_accents(query).to_lowercase();
    if q.contains("serie b") {
        Some("Brasileirão Série B")
    } else if q.contains("serie c") {
        Some("Brasileirão Série C")
    } else if q.contains("copa do brasil") || q.contains("cup") {
        Some("Copa do Brasil")
    } else if q.contains("libertadores") {
        Some("Copa Libertadores")
    } else if q.contains("brasileir") || q.contains("serie a") || q.contains("campeonato brasileiro")
    {
        Some("Brasileirão Série A")
    } else {
        None
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn distinguishes_atleticos() {
        assert_eq!(canon("Atletico-MG").display, "Atlético Mineiro");
        assert_eq!(canon("Atletico Mineiro").display, "Atlético Mineiro");
        assert_eq!(canon("Athletico-PR").display, "Athletico Paranaense");
        assert_eq!(canon("Atletico Paranaense").display, "Athletico Paranaense");
        assert_ne!(canon("Atletico-MG").key, canon("Athletico-PR").key);
    }

    #[test]
    fn unifies_cross_dataset_variants() {
        assert_eq!(canon("São Paulo-SP").key, canon("Sao Paulo").key);
        assert_eq!(canon("Vasco da Gama-RJ").key, canon("Vasco Da Gama RJ").key);
        assert_eq!(canon("Flamengo-RJ").key, canon("Flamengo").key);
        assert_eq!(canon("Grêmio").key, canon("Gremio-RS").key);
    }

    #[test]
    fn strips_country_parens() {
        assert_eq!(canon("Nacional (URU)").display, "Nacional");
    }

    #[test]
    fn query_matching() {
        assert!(key_matches(&canon("Flamengo").key, &canon("Flamengo-RJ").key));
        assert!(key_matches(&canon("Sao Paulo").key, &canon("São Paulo-SP").key));
        assert!(!key_matches(&canon("Atletico-MG").key, &canon("Athletico-PR").key));
    }

    #[test]
    fn competition_resolution() {
        assert_eq!(resolve_competition("Brasileirão"), Some("Brasileirão Série A"));
        assert_eq!(resolve_competition("Libertadores"), Some("Copa Libertadores"));
        assert_eq!(resolve_competition("Copa do Brasil"), Some("Copa do Brasil"));
        assert_eq!(resolve_competition("Serie B"), Some("Brasileirão Série B"));
    }
}
