//! Context: team-name and date normalization shared by every dataset loader.
//!
//! The source files disagree on team naming ("Palmeiras-SP", "Palmeiras",
//! "Sport Club Corinthians Paulista", "Nacional (URU)") and on date formats.
//! Everything is reduced to a lowercase, accent-free key for matching, plus a
//! human-friendly display name taken from the first spelling seen.

/// Long-form or variant names that should map onto a shorter canonical key.
const ALIASES: &[(&str, &str)] = &[
    ("sport club corinthians paulista", "corinthians"),
    ("sao paulo fc", "sao paulo"),
    ("atletico", "atletico mg"),
    ("atletico mineiro", "atletico mg"),
    ("clube atletico mineiro", "atletico mg"),
    ("athletico", "athletico pr"),
    ("athletico paranaense", "athletico pr"),
    ("atletico pr", "athletico pr"),
    ("atletico paranaense", "athletico pr"),
    ("vasco da gama", "vasco"),
    ("ec bahia", "bahia"),
    ("esporte clube bahia", "bahia"),
    ("fluminense fc", "fluminense"),
    ("gremio foot ball porto alegrense", "gremio"),
];

/// Base names shared by several clubs that differ only by state code (Atlético-MG,
/// Atlético-GO, Atlético-PR). A state code on these is kept as part of the key.
const AMBIGUOUS_BASES: &[&str] = &["atletico"];

/// Lowercase and strip the diacritics that appear in the Portuguese team names.
pub fn fold_accents(input: &str) -> String {
    input
        .chars()
        .flat_map(|c| c.to_lowercase())
        .map(|c| match c {
            'á' | 'à' | 'â' | 'ã' | 'ä' => 'a',
            'é' | 'è' | 'ê' | 'ë' => 'e',
            'í' | 'ì' | 'î' | 'ï' => 'i',
            'ó' | 'ò' | 'ô' | 'õ' | 'ö' => 'o',
            'ú' | 'ù' | 'û' | 'ü' => 'u',
            'ç' => 'c',
            'ñ' => 'n',
            other => other,
        })
        .collect()
}

/// Remove a trailing state or country code: `-SP`, ` - RJ`, `-EQU`, or a
/// space-separated two-letter state such as `Vasco Da Gama RJ`.
fn strip_suffix_code(s: &str) -> &str {
    let trimmed = s.trim_end();
    let Some(idx) = trimmed.rfind(['-', ' ']) else {
        return s;
    };
    let suffix = &trimmed[idx + 1..];
    let code_len_ok = if trimmed.as_bytes()[idx] == b'-' {
        (2..=3).contains(&suffix.len())
    } else {
        suffix.len() == 2
    };
    if !code_len_ok || !suffix.chars().all(|c| c.is_ascii_uppercase()) {
        return s;
    }
    let base = trimmed[..idx].trim_end().trim_end_matches('-').trim_end();
    if base.is_empty() {
        s
    } else {
        base
    }
}

/// Remove every `(...)` section.
fn remove_parentheticals(raw: &str) -> String {
    let mut out = String::with_capacity(raw.len());
    let mut depth = 0usize;
    for c in raw.chars() {
        match c {
            '(' => depth += 1,
            ')' if depth > 0 => depth -= 1,
            _ if depth == 0 => out.push(c),
            _ => {}
        }
    }
    out.trim().to_string()
}

/// Remove a `(...)` section and any trailing state/country code.
fn clean_raw(raw: &str) -> String {
    strip_suffix_code(&remove_parentheticals(raw))
        .trim()
        .to_string()
}

/// Canonical matching key for a team name, e.g. "Palmeiras-SP" -> "palmeiras".
///
/// The full name (including any state code) is tried against the aliases first,
/// so "Atlético-PR" can map to Athletico Paranaense while plain "Atlético" (with no
/// code) maps to Atlético-MG.
pub fn team_key(raw: &str) -> String {
    let full = words(raw);
    if let Some(to) = alias_for(&full) {
        return to.to_string();
    }
    let key = words(&clean_raw(raw));
    if full != key && AMBIGUOUS_BASES.contains(&key.as_str()) {
        // Several clubs share this base name and differ only by state, so keep the code.
        return full;
    }
    alias_for(&key).map(str::to_string).unwrap_or(key)
}

/// Lowercase, accent-free words separated by single spaces, without a trailing " fc".
fn words(s: &str) -> String {
    let spaced: String = fold_accents(s)
        .chars()
        .map(|c| if c.is_alphanumeric() { c } else { ' ' })
        .collect();
    let joined = spaced.split_whitespace().collect::<Vec<_>>().join(" ");
    match joined.strip_suffix(" fc") {
        Some(stripped) => stripped.to_string(),
        None => joined,
    }
}

fn alias_for(key: &str) -> Option<&'static str> {
    ALIASES
        .iter()
        .find(|(from, _)| *from == key)
        .map(|(_, to)| *to)
}

/// Readable team name with state/country decorations removed. Ambiguous base names
/// keep their state code so "Atlético-MG" and "Atlético-GO" stay distinguishable.
pub fn display_name(raw: &str) -> String {
    let cleaned = clean_raw(raw);
    let ambiguous = AMBIGUOUS_BASES.contains(&words(&cleaned).as_str());
    if ambiguous && words(raw) != words(&cleaned) {
        return remove_parentheticals(raw);
    }
    cleaned
}

/// Normalize the date formats found in the datasets to ISO `YYYY-MM-DD`.
///
/// Accepts `2023-09-24`, `2012-05-19 18:30:00`, `29/03/2003` and `2003.01.0001`-style
/// year prefixes are not dates and return `None`.
pub fn iso_date(raw: &str) -> Option<String> {
    let trimmed = raw.trim();
    let date_part = trimmed.split_whitespace().next()?;
    if let Some((d, rest)) = date_part.split_once('/') {
        let (m, y) = rest.split_once('/')?;
        return build_iso(y, m, d);
    }
    let mut parts = date_part.split('-');
    let (y, m, d) = (parts.next()?, parts.next()?, parts.next()?);
    if parts.next().is_some() {
        return None;
    }
    build_iso(y, m, d)
}

fn build_iso(y: &str, m: &str, d: &str) -> Option<String> {
    let year: u32 = y.trim().parse().ok()?;
    let month: u32 = m.trim().parse().ok()?;
    let day: u32 = d.trim().parse().ok()?;
    if !(1..=12).contains(&month) || !(1..=31).contains(&day) || year < 1800 {
        return None;
    }
    Some(format!("{year:04}-{month:02}-{day:02}"))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn given_state_suffix_when_keyed_then_suffix_is_dropped() {
        assert_eq!(team_key("Palmeiras-SP"), "palmeiras");
        assert_eq!(team_key("Palmeiras"), "palmeiras");
        assert_eq!(team_key("Flamengo - RJ"), "flamengo");
        assert_eq!(team_key("Atlético-MG"), "atletico mg");
    }

    #[test]
    fn given_space_separated_state_when_keyed_then_it_is_dropped() {
        assert_eq!(team_key("Vasco Da Gama RJ"), "vasco");
        assert_eq!(team_key("Botafogo RJ"), "botafogo");
        assert_eq!(team_key("Botafogo - RJ"), "botafogo");
        assert_eq!(team_key("Sao Paulo FC"), "sao paulo");
    }

    #[test]
    fn given_country_code_when_keyed_then_parenthetical_and_code_are_dropped() {
        assert_eq!(team_key("Nacional (URU)"), "nacional");
        assert_eq!(team_key("Barcelona-EQU"), "barcelona");
    }

    #[test]
    fn given_accents_when_keyed_then_they_fold_to_ascii() {
        assert_eq!(team_key("São Paulo"), "sao paulo");
        assert_eq!(team_key("Grêmio"), "gremio");
        assert_eq!(team_key("Avaí"), "avai");
        assert_eq!(
            team_key("Fortaleza Esporte Clube"),
            "fortaleza esporte clube"
        );
    }

    #[test]
    fn given_long_form_names_when_keyed_then_aliases_apply() {
        assert_eq!(team_key("Sport Club Corinthians Paulista"), "corinthians");
        assert_eq!(team_key("Sao Paulo FC"), "sao paulo");
        assert_eq!(team_key("Atlético Mineiro"), "atletico mg");
    }

    #[test]
    fn given_state_code_when_keyed_then_aliases_see_it_before_it_is_dropped() {
        assert_eq!(team_key("Atlético-PR"), "athletico pr");
        assert_eq!(team_key("Athletico-PR"), "athletico pr");
        assert_eq!(team_key("Atletico"), "atletico mg");
        assert_eq!(team_key("Atlético-GO"), "atletico go");
        assert_eq!(team_key("Atlético-MG"), "atletico mg");
    }

    #[test]
    fn given_decorated_name_when_displayed_then_decorations_removed() {
        assert_eq!(display_name("Palmeiras-SP"), "Palmeiras");
        assert_eq!(display_name("Nacional (URU)"), "Nacional");
        assert_eq!(display_name("Atlético-MG"), "Atlético-MG");
        assert_eq!(display_name("Atlético-PR"), "Atlético-PR");
    }

    #[test]
    fn given_each_dataset_date_format_when_parsed_then_iso_is_returned() {
        assert_eq!(iso_date("2023-09-24").as_deref(), Some("2023-09-24"));
        assert_eq!(
            iso_date("2012-05-19 18:30:00").as_deref(),
            Some("2012-05-19")
        );
        assert_eq!(iso_date("29/03/2003").as_deref(), Some("2003-03-29"));
        assert_eq!(iso_date("2003.01.0001"), None);
        assert_eq!(iso_date("not a date"), None);
        assert_eq!(iso_date("2023-13-01"), None);
    }
}
