//! Name normalization shared by the loaders and the query layer.
//!
//! The source files spell the same club several ways: `Palmeiras-SP`,
//! `Palmeiras - SP`, `Sociedade Esportiva Palmeiras`, `Sao Paulo`, `São Paulo`.
//! Every spelling is reduced to a stable lowercase key, so matching is a plain
//! equality check on keys.

/// Full-name spellings that map onto a canonical key.
const ALIASES: &[(&str, &str)] = &[
    ("sociedade esportiva palmeiras", "palmeiras"),
    ("sport club corinthians paulista", "corinthians"),
    ("clube de regatas do flamengo", "flamengo"),
    ("sao paulo futebol clube", "sao paulo"),
    ("gremio foot-ball porto alegrense", "gremio"),
    ("fluminense football club", "fluminense"),
    ("santos futebol clube", "santos"),
    ("club de regatas vasco da gama", "vasco"),
    ("vasco da gama", "vasco"),
    ("clube atletico mineiro", "atletico-mg"),
    ("atletico mineiro", "atletico-mg"),
    ("atletico paranaense", "athletico-pr"),
    ("athletico paranaense", "athletico-pr"),
    ("atletico-pr", "athletico-pr"),
    ("america mineiro", "america-mg"),
    ("ec bahia", "bahia"),
    ("esporte clube bahia", "bahia"),
    ("sport club do recife", "sport"),
    ("ceara sporting club", "ceara"),
    ("ceara sc", "ceara"),
    ("goias esporte clube", "goias"),
];

/// Club names shared by several state teams. For these the state code is part
/// of the key (`atletico-mg` is not `atletico-pr`); everywhere else it is dropped.
const AMBIGUOUS_BASES: &[&str] = &["atletico", "athletico", "america", "guarani", "sao jose"];

/// Lowercases, folds Latin accents and collapses whitespace.
pub fn fold(text: &str) -> String {
    let folded: String = text
        .chars()
        .flat_map(|c| c.to_lowercase())
        .map(|c| match c {
            'à'..='å' => 'a',
            'è'..='ë' => 'e',
            'ì'..='ï' => 'i',
            'ò'..='ö' => 'o',
            'ù'..='ü' => 'u',
            'ç' => 'c',
            'ñ' => 'n',
            other => other,
        })
        .collect();
    folded.split_whitespace().collect::<Vec<_>>().join(" ")
}

/// Removes parenthesised segments, e.g. `Nacional (URU)` -> `Nacional`.
fn strip_parens(text: &str) -> String {
    let mut out = String::with_capacity(text.len());
    let mut depth = 0usize;
    for c in text.chars() {
        match c {
            '(' => depth += 1,
            ')' => depth = depth.saturating_sub(1),
            _ if depth == 0 => out.push(c),
            _ => {}
        }
    }
    out.split_whitespace().collect::<Vec<_>>().join(" ")
}

/// Splits a trailing two-letter state code. Accepts a hyphen (`Palmeiras - SP`,
/// `Palmeiras-SP`) or a space before upper-case letters (`Botafogo RJ`).
fn split_state(text: &str) -> (&str, Option<&str>) {
    let text = text.trim();
    if let Some(idx) = text.rfind('-') {
        let head = text[..idx].trim_end();
        let tail = text[idx + 1..].trim();
        if !head.is_empty() && tail.len() == 2 && tail.chars().all(|c| c.is_ascii_alphabetic()) {
            return (head, Some(tail));
        }
    }
    if let Some((head, tail)) = text.rsplit_once(' ') {
        if !head.is_empty() && tail.len() == 2 && tail.chars().all(|c| c.is_ascii_uppercase()) {
            return (head.trim_end(), Some(tail));
        }
    }
    (text, None)
}

/// Human-readable team name with parenthetical notes removed. The state is
/// dropped except for ambiguous clubs, where it tells the teams apart.
pub fn display_name(raw: &str) -> String {
    let cleaned = strip_parens(raw);
    match split_state(&cleaned) {
        (base, Some(state)) if AMBIGUOUS_BASES.contains(&fold(base).as_str()) => {
            format!("{base}-{}", state.to_uppercase())
        }
        (base, _) => base.to_string(),
    }
}

/// Stable matching key for a team name as written in any data source or query.
pub fn team_key(raw: &str) -> String {
    let cleaned = strip_parens(raw);
    let (base, state) = split_state(&cleaned);
    let base = fold(base);
    let base = base.strip_suffix(" fc").unwrap_or(&base).to_string();
    let full = match state {
        Some(state) if AMBIGUOUS_BASES.contains(&base.as_str()) => {
            format!("{base}-{}", state.to_lowercase())
        }
        _ => base,
    };
    ALIASES
        .iter()
        .find(|(alias, _)| *alias == full)
        .map(|(_, canonical)| canonical.to_string())
        .unwrap_or(full)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn state_suffixes_are_dropped_for_plain_clubs() {
        assert_eq!(team_key("Palmeiras-SP"), "palmeiras");
        assert_eq!(team_key("Palmeiras - SP"), "palmeiras");
        assert_eq!(team_key("Palmeiras"), "palmeiras");
        assert_eq!(team_key("Botafogo RJ"), "botafogo");
        assert_eq!(team_key("Fortaleza FC"), team_key("Fortaleza"));
        assert_eq!(team_key("EC Bahia"), team_key("Bahia"));
    }

    #[test]
    fn accents_and_case_are_folded() {
        assert_eq!(team_key("Grêmio"), "gremio");
        assert_eq!(team_key("AVAÍ"), "avai");
        assert_eq!(team_key("São Paulo"), team_key("Sao Paulo"));
    }

    #[test]
    fn long_names_resolve_to_canonical_keys() {
        assert_eq!(team_key("Sport Club Corinthians Paulista"), "corinthians");
        assert_eq!(team_key("Sociedade Esportiva Palmeiras"), "palmeiras");
        assert_eq!(team_key("Clube de Regatas do Flamengo - RJ"), "flamengo");
    }

    #[test]
    fn parenthetical_notes_are_ignored() {
        assert_eq!(team_key("Nacional (URU)"), "nacional");
        assert_eq!(
            display_name("Boavista Sport Club (antigo Esporte Clube Barreira) - RJ"),
            "Boavista Sport Club"
        );
        assert_eq!(display_name("Atlético-MG"), "Atlético-MG");
        assert_eq!(display_name("Palmeiras-SP"), "Palmeiras");
    }

    #[test]
    fn ambiguous_clubs_keep_their_state() {
        assert_eq!(team_key("Atlético-MG"), "atletico-mg");
        assert_eq!(team_key("Atlético-PR"), "athletico-pr");
        assert_eq!(team_key("Athletico-PR"), "athletico-pr");
        assert_eq!(team_key("Atlético Mineiro"), "atletico-mg");
        assert_eq!(team_key("Athletico PR"), "athletico-pr");
        assert_ne!(team_key("America-MG"), team_key("America-RN"));
    }
}
