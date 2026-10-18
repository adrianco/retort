//! Context: normalisation helpers shared by every dataset loader and query.
//!
//! The source CSVs disagree about team names ("Palmeiras-SP", "Palmeiras",
//! "Sport Club Corinthians Paulista", "Nacional (URU)", "Vasco Da Gama RJ"),
//! dates ("2012-05-19 18:30:00", "29/03/2003") and competitions. This module
//! reduces all of those to one canonical form so that matching is consistent.

/// A team reduced to a canonical key plus an optional state (UF) code.
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct Team {
    /// Accent-free, lower-case canonical name, e.g. `"sao paulo"`.
    pub key: String,
    /// Two- or three-letter state/country code when the source provides one.
    pub state: Option<String>,
    /// Human-readable name used in responses, e.g. `"Sao Paulo"`.
    pub name: String,
}

impl Team {
    /// Parses any raw team name from the datasets or from a user query.
    pub fn parse(raw: &str) -> Team {
        let without_parens = strip_parentheticals(raw);
        let (base, state) = split_state_suffix(&without_parens);
        let display = base.trim().to_string();
        let mut key = fold(&display);
        let mut state = state;

        if let Some((alias_key, alias_state)) = team_alias(&key) {
            key = alias_key.to_string();
            if state.is_none() {
                state = alias_state.map(str::to_string);
            }
        }
        key = strip_affixes(&key);

        Team {
            key,
            state,
            name: display,
        }
    }

    /// Stable identifier for grouping (standings etc.): key plus state if known.
    pub fn identity(&self) -> String {
        match &self.state {
            Some(s) => format!("{}-{}", self.key, s.to_lowercase()),
            None => self.key.clone(),
        }
    }

    /// Whether this (dataset) team satisfies a (query) team reference.
    /// A missing state on either side matches anything.
    pub fn matches(&self, query: &Team) -> bool {
        self.key == query.key
            && match (&self.state, &query.state) {
                (Some(a), Some(b)) => a.eq_ignore_ascii_case(b),
                _ => true,
            }
    }
}

/// Maps arbitrary competition text to the canonical competition name.
/// Returns `None` when the text does not name a known competition.
pub fn canonical_competition(raw: &str) -> Option<&'static str> {
    let f = fold(raw);
    if f.contains("liberta") {
        Some("Copa Libertadores")
    } else if f.contains("copa do brasil") || f.contains("cup") {
        Some("Copa do Brasil")
    } else if f.contains("serie b") {
        Some("Brasileirão Série B")
    } else if f.contains("serie c") {
        Some("Brasileirão Série C")
    } else if f.contains("serie a") || f.contains("brasileir") {
        Some("Brasileirão Série A")
    } else {
        None
    }
}

/// Parses `YYYY-MM-DD[ HH:MM:SS]` or `DD/MM/YYYY` into `YYYY-MM-DD`.
pub fn parse_date(raw: &str) -> Option<String> {
    let token = raw.split_whitespace().next()?;
    if token.contains('/') {
        let parts: Vec<&str> = token.split('/').collect();
        if parts.len() != 3 {
            return None;
        }
        let (d, m, y) = (parts[0], parts[1], parts[2]);
        return valid_ymd(y, m, d);
    }
    let parts: Vec<&str> = token.split('-').collect();
    if parts.len() != 3 {
        return None;
    }
    valid_ymd(parts[0], parts[1], parts[2])
}

fn valid_ymd(y: &str, m: &str, d: &str) -> Option<String> {
    let year: u32 = y.parse().ok()?;
    let month: u32 = m.parse().ok()?;
    let day: u32 = d.parse().ok()?;
    if !(1000..=9999).contains(&year) || !(1..=12).contains(&month) || !(1..=31).contains(&day) {
        return None;
    }
    Some(format!("{year:04}-{month:02}-{day:02}"))
}

/// Parses a goal count. Sources store integers as `"2"`, floats as `"1.0"`,
/// and unplayed fixtures as `"NA"` (which yields `None`).
pub fn parse_goals(raw: &str) -> Option<u32> {
    let v: f64 = raw.trim().parse().ok()?;
    if v.is_finite() && v >= 0.0 {
        Some(v.round() as u32)
    } else {
        None
    }
}

/// Lower-cases, strips Portuguese accents and collapses punctuation to spaces.
pub fn fold(raw: &str) -> String {
    let mut out = String::with_capacity(raw.len());
    for c in raw.chars() {
        let mapped = match c {
            'á' | 'à' | 'â' | 'ã' | 'ä' | 'Á' | 'À' | 'Â' | 'Ã' | 'Ä' => 'a',
            'é' | 'è' | 'ê' | 'ë' | 'É' | 'È' | 'Ê' | 'Ë' => 'e',
            'í' | 'ì' | 'î' | 'ï' | 'Í' | 'Ì' | 'Î' | 'Ï' => 'i',
            'ó' | 'ò' | 'ô' | 'õ' | 'ö' | 'Ó' | 'Ò' | 'Ô' | 'Õ' | 'Ö' => 'o',
            'ú' | 'ù' | 'û' | 'ü' | 'Ú' | 'Ù' | 'Û' | 'Ü' => 'u',
            'ç' | 'Ç' => 'c',
            'ñ' | 'Ñ' => 'n',
            c if c.is_alphanumeric() => c.to_ascii_lowercase(),
            _ => ' ',
        };
        out.push(mapped);
    }
    out.split_whitespace().collect::<Vec<_>>().join(" ")
}

/// Removes `( ... )` segments, e.g. `"Nacional (URU)"` -> `"Nacional"`.
fn strip_parentheticals(raw: &str) -> String {
    let mut out = String::new();
    let mut depth = 0;
    for c in raw.chars() {
        match c {
            '(' => depth += 1,
            ')' if depth > 0 => depth -= 1,
            _ if depth == 0 => out.push(c),
            _ => {}
        }
    }
    out.split_whitespace().collect::<Vec<_>>().join(" ")
}

/// Splits a trailing state code: `"Palmeiras-SP"`, `"Vasco Da Gama RJ"`,
/// `"Boavista Sport Club - RJ"`. Only upper-case 2–3 letter codes are taken.
fn split_state_suffix(raw: &str) -> (String, Option<String>) {
    let trimmed = raw.trim();
    let is_code = |s: &str| {
        let s = s.trim();
        (2..=3).contains(&s.len()) && s.chars().all(|c| c.is_ascii_uppercase())
    };
    if let Some(idx) = trimmed.rfind('-') {
        let code = &trimmed[idx + 1..];
        if is_code(code) {
            return (
                trimmed[..idx].trim().to_string(),
                Some(code.trim().to_string()),
            );
        }
    }
    if let Some(idx) = trimmed.rfind(' ') {
        let code = &trimmed[idx + 1..];
        if is_code(code) && idx > 0 {
            return (trimmed[..idx].trim().to_string(), Some(code.to_string()));
        }
    }
    (trimmed.to_string(), None)
}

/// Known naming differences that must resolve to one team.
/// Input is the folded name; output is `(canonical key, state)`.
fn team_alias(folded: &str) -> Option<(&'static str, Option<&'static str>)> {
    Some(match folded {
        "athletico" | "athletico paranaense" | "atletico paranaense" => ("atletico", Some("PR")),
        "atletico mineiro" | "atletico mg" => ("atletico", Some("MG")),
        "corinthians paulista" | "sport club corinthians paulista" => ("corinthians", Some("SP")),
        "sociedade esportiva palmeiras" => ("palmeiras", Some("SP")),
        "clube de regatas do flamengo" => ("flamengo", Some("RJ")),
        "sao paulo futebol clube" => ("sao paulo", Some("SP")),
        "gremio foot ball porto alegrense" => ("gremio", Some("RS")),
        _ => return None,
    })
}

/// Drops club-type boilerplate so "Sport Club Internacional" and
/// "Internacional" share one key.
fn strip_affixes(key: &str) -> String {
    const PREFIXES: [&str; 4] = [
        "sociedade esportiva ",
        "clube de regatas ",
        "sport club ",
        "esporte clube ",
    ];
    const SUFFIXES: [&str; 3] = [" futebol clube", " esporte clube", " football club"];
    let mut k = key.to_string();
    for p in PREFIXES {
        if let Some(rest) = k.strip_prefix(p) {
            k = rest.to_string();
            break;
        }
    }
    for s in SUFFIXES {
        if let Some(rest) = k.strip_suffix(s) {
            k = rest.to_string();
            break;
        }
    }
    k
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn strips_state_suffix_with_hyphen() {
        let t = Team::parse("Palmeiras-SP");
        assert_eq!(t.key, "palmeiras");
        assert_eq!(t.state.as_deref(), Some("SP"));
        assert_eq!(t.name, "Palmeiras");
    }

    #[test]
    fn strips_trailing_state_code_with_space() {
        let t = Team::parse("Vasco Da Gama RJ");
        assert_eq!(t.key, "vasco da gama");
        assert_eq!(t.state.as_deref(), Some("RJ"));
    }

    #[test]
    fn accents_and_plain_names_match() {
        assert_eq!(Team::parse("São Paulo").key, Team::parse("Sao Paulo").key);
        assert_eq!(Team::parse("Grêmio-RS").key, "gremio");
    }

    #[test]
    fn long_names_resolve_to_short_form() {
        let t = Team::parse("Sport Club Corinthians Paulista");
        assert_eq!(t.key, "corinthians");
        assert_eq!(t.state.as_deref(), Some("SP"));
        assert_eq!(Team::parse("Athletico-PR").key, "atletico");
        assert_eq!(Team::parse("Atletico Mineiro").identity(), "atletico-mg");
    }

    #[test]
    fn parentheticals_are_removed() {
        let t = Team::parse("Nacional (URU)");
        assert_eq!(t.key, "nacional");
        assert_eq!(Team::parse("Barcelona-EQU").state.as_deref(), Some("EQU"));
    }

    #[test]
    fn state_mismatch_does_not_match_but_missing_state_does() {
        let pr = Team::parse("Atletico-PR");
        let mg = Team::parse("Atletico-MG");
        let plain = Team::parse("Atletico");
        assert!(!pr.matches(&mg));
        assert!(pr.matches(&plain));
        assert!(plain.matches(&pr));
    }

    #[test]
    fn parses_multiple_date_formats() {
        assert_eq!(
            parse_date("2012-05-19 18:30:00").as_deref(),
            Some("2012-05-19")
        );
        assert_eq!(parse_date("29/03/2003").as_deref(), Some("2003-03-29"));
        assert_eq!(parse_date("2023-09-24").as_deref(), Some("2023-09-24"));
        assert_eq!(parse_date("not a date"), None);
        assert_eq!(parse_date("31/02/2003x"), None);
    }

    #[test]
    fn parses_goals_including_floats_and_na() {
        assert_eq!(parse_goals("2"), Some(2));
        assert_eq!(parse_goals("1.0"), Some(1));
        assert_eq!(parse_goals("NA"), None);
        assert_eq!(parse_goals("-1"), None);
    }

    #[test]
    fn maps_competitions() {
        assert_eq!(
            canonical_competition("Serie A"),
            Some("Brasileirão Série A")
        );
        assert_eq!(
            canonical_competition("Brasileirão Série B"),
            Some("Brasileirão Série B")
        );
        assert_eq!(
            canonical_competition("Copa do Brasil"),
            Some("Copa do Brasil")
        );
        assert_eq!(
            canonical_competition("Copa Libertadores"),
            Some("Copa Libertadores")
        );
        assert_eq!(canonical_competition("Premier League"), None);
    }
}
