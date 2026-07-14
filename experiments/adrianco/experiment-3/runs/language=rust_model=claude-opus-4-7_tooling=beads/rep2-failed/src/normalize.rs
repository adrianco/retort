//! Text normalization and team-identity resolution.
//!
//! The Kaggle datasets name teams inconsistently: state suffixes
//! ("Palmeiras-SP"), country codes ("Barcelona-EQU"), parenthetical notes
//! ("Nacional (URU)") and accent variation ("São Paulo" vs "Sao Paulo").
//!
//! The hard case is that a state suffix is sometimes the *only* thing
//! distinguishing two genuinely different clubs — "Atletico-MG" (Mineiro),
//! "Atletico-PR" (Paranaense) and "Atletico-GO" (Goianiense) share the base
//! name "Atletico". So suffixes cannot simply be discarded.
//!
//! The resolution is two-phase: scan every team name to learn which base
//! names are *ambiguous* (appear with two or more distinct state codes), then
//! build a `team_id` that keeps the state code only for those ambiguous bases.
//! "Flamengo-RJ" and "Flamengo" collapse to one id; the three Atléticos stay
//! separate. `team_id`/`team_display` are computed once at load time.

use std::collections::HashMap;

/// Replace Latin accented characters with their ASCII base form.
pub fn strip_accents(s: &str) -> String {
    s.chars()
        .map(|c| match c {
            'á' | 'à' | 'â' | 'ã' | 'ä' | 'å' => 'a',
            'é' | 'è' | 'ê' | 'ë' => 'e',
            'í' | 'ì' | 'î' | 'ï' => 'i',
            'ó' | 'ò' | 'ô' | 'õ' | 'ö' => 'o',
            'ú' | 'ù' | 'û' | 'ü' => 'u',
            'ç' => 'c',
            'ñ' => 'n',
            'ý' | 'ÿ' => 'y',
            'Á' | 'À' | 'Â' | 'Ã' | 'Ä' | 'Å' => 'A',
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

/// Lower-case and accent-fold a string (the generic "matching fold").
pub fn fold(s: &str) -> String {
    strip_accents(s).to_lowercase()
}

/// Collapse runs of whitespace to single spaces and trim the ends.
pub fn collapse_ws(s: &str) -> String {
    s.split_whitespace().collect::<Vec<_>>().join(" ")
}

/// Is `s` a 2-3 letter all-uppercase code (a Brazilian state or country code)?
fn is_region_code(s: &str) -> bool {
    let len = s.chars().count();
    (2..=3).contains(&len) && s.chars().all(|c| c.is_ascii_uppercase())
}

/// Split a team name into its `(display_base, region_code)`.
///
/// `display_base` keeps original casing and accents with the trailing
/// state/country code removed; `region_code` is the lower-cased code, or an
/// empty string when the name carried none. Non-code parentheticals such as
/// "(antigo ...)" are dropped without producing a code.
pub fn split_suffix(name: &str) -> (String, String) {
    let mut s = name.trim().to_string();
    let mut code = String::new();
    loop {
        let before = s.clone();

        // Trailing parenthetical group, e.g. "(URU)" or "(antigo ...)".
        if s.ends_with(')') {
            if let Some(idx) = s.rfind('(') {
                let inner = s[idx + 1..s.len() - 1].trim().to_string();
                let head = s[..idx].trim().to_string();
                if !head.is_empty() {
                    if code.is_empty() && is_region_code(&inner) {
                        code = inner.to_lowercase();
                    }
                    s = head;
                }
            }
        }

        // Trailing "-XX" / " - XX" state or country code.
        if let Some(idx) = s.rfind('-') {
            let tail = s[idx + 1..].trim().to_string();
            let head = s[..idx].trim().to_string();
            if !head.is_empty() && is_region_code(&tail) {
                if code.is_empty() {
                    code = tail.to_lowercase();
                }
                s = head;
            }
        }

        if s == before {
            break;
        }
    }
    (collapse_ws(&s), code)
}

/// The clean display name of a team with any region suffix removed.
pub fn strip_team_suffix(name: &str) -> String {
    split_suffix(name).0
}

/// The folded base key of a team name (region code excluded).
#[cfg(test)]
fn base_key(name: &str) -> String {
    collapse_ws(&fold(&split_suffix(name).0))
}

/// A registry of which base team names are *ambiguous* — i.e. shared by clubs
/// from two or more states — built from one full scan of every team name.
///
/// For each ambiguous base it also records the *dominant* (most frequent)
/// region code. A name that uses an ambiguous base but carries no code (as in
/// the extended-stats file, which writes a bare "Santos") is resolved to that
/// dominant code, so it merges with the suffixed spelling in the other files.
pub struct TeamRegistry {
    /// Ambiguous base key -> dominant region code.
    dominant: HashMap<String, String>,
}

impl TeamRegistry {
    /// Build the registry from every team name in the data.
    pub fn build<'a>(names: impl Iterator<Item = &'a str>) -> TeamRegistry {
        // base -> region code -> occurrence count
        let mut counts: HashMap<String, HashMap<String, usize>> = HashMap::new();
        for name in names {
            let (display, code) = split_suffix(name);
            let base = collapse_ws(&fold(&display));
            let entry = counts.entry(base).or_default();
            if !code.is_empty() {
                *entry.entry(code).or_default() += 1;
            }
        }

        let mut dominant = HashMap::new();
        for (base, code_counts) in counts {
            if code_counts.len() >= 2 {
                let dom = code_counts
                    .iter()
                    .max_by_key(|(code, n)| (**n, (*code).clone()))
                    .map(|(code, _)| code.clone())
                    .unwrap();
                dominant.insert(base, dom);
            }
        }
        TeamRegistry { dominant }
    }

    /// Resolve the code to use for a `(base, code)` pair: the explicit code if
    /// present, otherwise the dominant code for an ambiguous base.
    fn resolved_code<'r>(&'r self, base: &str, code: &'r str) -> Option<&'r str> {
        match self.dominant.get(base) {
            Some(dom) if code.is_empty() => Some(dom),
            Some(_) => Some(code),
            None => None,
        }
    }

    /// The canonical identity key for a team name. For ambiguous bases this is
    /// `"base|code"`; otherwise just `"base"`.
    pub fn id(&self, name: &str) -> String {
        let (display, code) = split_suffix(name);
        let base = collapse_ws(&fold(&display));
        match self.resolved_code(&base, &code) {
            Some(c) => format!("{base}|{c}"),
            None => base,
        }
    }

    /// The canonical display name — keeps a state suffix only when it is
    /// needed to disambiguate (e.g. "Atletico-MG").
    pub fn display(&self, name: &str) -> String {
        let (display, code) = split_suffix(name);
        let base = collapse_ws(&fold(&display));
        match self.resolved_code(&base, &code) {
            Some(c) => format!("{}-{}", display, c.to_uppercase()),
            None => display,
        }
    }
}

/// Decide whether a user-supplied team query refers to the team whose
/// canonical identity key is `team_id`.
///
/// The query is split the same way as stored names. The base must match
/// exactly or as a (>=3 char) substring; if the query carries a region code it
/// must equal the stored team's code, but a query with no code matches every
/// region (so "Atletico" finds all three Atléticos).
pub fn team_matches(query: &str, team_id: &str) -> bool {
    let (q_display, q_code) = split_suffix(query);
    let q_base = collapse_ws(&fold(&q_display));
    if q_base.is_empty() {
        return false;
    }
    let (t_base, t_code) = match team_id.split_once('|') {
        Some((b, c)) => (b, c),
        None => (team_id, ""),
    };
    let base_ok = q_base == t_base
        || (q_base.len() >= 3 && (t_base.contains(&q_base) || q_base.contains(t_base)));
    if !base_ok {
        return false;
    }
    q_code.is_empty() || q_code == t_code
}

/// Decide whether a competition query refers to the canonical competition
/// name `competition`. Folded substring match in either direction so that
/// "libertadores", "Copa Libertadores", "serie a" and "brasileirão" all work.
pub fn competition_matches(query: &str, competition: &str) -> bool {
    let q = fold(query.trim());
    let c = fold(competition);
    if q.is_empty() {
        return false;
    }
    c.contains(&q) || q.contains(&c)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn registry(names: &[&str]) -> TeamRegistry {
        TeamRegistry::build(names.iter().copied())
    }

    #[test]
    fn suffix_splitting() {
        assert_eq!(split_suffix("Palmeiras-SP"), ("Palmeiras".into(), "sp".into()));
        assert_eq!(split_suffix("América - MG"), ("América".into(), "mg".into()));
        assert_eq!(split_suffix("Barcelona-EQU"), ("Barcelona".into(), "equ".into()));
        assert_eq!(split_suffix("Nacional (URU)"), ("Nacional".into(), "uru".into()));
        assert_eq!(split_suffix("São Paulo"), ("São Paulo".into(), String::new()));
    }

    #[test]
    fn unambiguous_club_merges_across_suffix() {
        // Flamengo only ever appears with the RJ code -> not ambiguous.
        let r = registry(&["Flamengo-RJ", "Flamengo", "Santos-SP"]);
        assert_eq!(r.id("Flamengo-RJ"), r.id("Flamengo"));
        assert_eq!(r.id("Flamengo"), "flamengo");
    }

    #[test]
    fn ambiguous_clubs_stay_distinct() {
        // Three different Atléticos share a base; the code must be kept.
        let r = registry(&["Atletico-MG", "Atletico-PR", "Atletico-GO"]);
        assert_ne!(r.id("Atletico-MG"), r.id("Atletico-PR"));
        assert_eq!(r.id("Atletico-MG"), "atletico|mg");
        assert_eq!(r.display("Atletico-MG"), "Atletico-MG");
    }

    #[test]
    fn bare_ambiguous_name_resolves_to_dominant_code() {
        // "Santos-SP" dominates -> a bare "Santos" merges into it.
        let r = registry(&[
            "Santos-SP", "Santos-SP", "Santos-SP", "Santos-AP", "Atletico-MG", "Atletico-PR",
        ]);
        assert_eq!(r.id("Santos"), "santos|sp");
        assert_eq!(r.id("Santos"), r.id("Santos-SP"));
        assert_eq!(r.display("Santos"), "Santos-SP");
    }

    #[test]
    fn team_matching() {
        let r = registry(&["Atletico-MG", "Atletico-PR", "Flamengo-RJ"]);
        assert!(team_matches("Flamengo", &r.id("Flamengo-RJ")));
        assert!(team_matches("Atletico-MG", &r.id("Atletico-MG")));
        // A bare "Atletico" query matches every Atlético.
        assert!(team_matches("Atletico", &r.id("Atletico-PR")));
        // ...but a coded query does not cross states.
        assert!(!team_matches("Atletico-MG", &r.id("Atletico-PR")));
        assert!(!team_matches("Santos", &r.id("Flamengo-RJ")));
    }

    #[test]
    fn accents_fold() {
        assert_eq!(fold("Grêmio"), "gremio");
        assert_eq!(base_key("São Paulo-SP"), base_key("Sao Paulo"));
    }
}
