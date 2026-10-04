//! Team-name and date normalisation shared by every dataset.
//!
//! The datasets spell the same club in many ways ("Palmeiras-SP",
//! "Palmeiras - SP", "Palmeiras", "Sport Club do Recife", "EC Bahia"...).
//! `canonical` maps each spelling to a stable key used for matching.

const UFS: &[&str] = &[
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB",
    "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
];

/// (display name, home state, aliases in folded form).
const CLUBS: &[(&str, &str, &[&str])] = &[
    ("Flamengo", "RJ", &["flamengo", "cr flamengo", "clube de regatas do flamengo"]),
    ("Fluminense", "RJ", &["fluminense"]),
    ("Vasco", "RJ", &["vasco", "vasco da gama"]),
    ("Botafogo", "RJ", &["botafogo"]),
    ("Palmeiras", "SP", &["palmeiras", "se palmeiras"]),
    ("Corinthians", "SP", &["corinthians", "sport club corinthians paulista"]),
    ("São Paulo", "SP", &["sao paulo"]),
    ("Santos", "SP", &["santos"]),
    ("Grêmio", "RS", &["gremio"]),
    ("Internacional", "RS", &["internacional"]),
    ("Cruzeiro", "MG", &["cruzeiro"]),
    ("Atlético-MG", "MG", &["atletico mg", "atletico mineiro"]),
    ("Athletico-PR", "PR", &["atletico pr", "athletico pr", "athletico", "athletico paranaense", "atletico paranaense"]),
    ("Atlético-GO", "GO", &["atletico go", "atletico goianiense"]),
    ("América-MG", "MG", &["america mg", "america mineiro", "america minas gerais"]),
    ("América-RN", "RN", &["america rn", "america natal", "america de natal"]),
    ("Bahia", "BA", &["bahia"]),
    ("Vitória", "BA", &["vitoria"]),
    ("Sport", "PE", &["sport", "sport recife", "sport club do recife"]),
    ("Náutico", "PE", &["nautico", "nautico capibaribe"]),
    ("Santa Cruz", "PE", &["santa cruz"]),
    ("Fortaleza", "CE", &["fortaleza", "fortaleza esporte clube"]),
    ("Ceará", "CE", &["ceara", "ceara sporting club"]),
    ("Goiás", "GO", &["goias"]),
    ("Coritiba", "PR", &["coritiba"]),
    ("Paraná", "PR", &["parana", "ca parana", "parana clube"]),
    ("Chapecoense", "SC", &["chapecoense"]),
    ("Avaí", "SC", &["avai"]),
    ("Figueirense", "SC", &["figueirense"]),
    ("Criciúma", "SC", &["criciuma"]),
    ("Joinville", "SC", &["joinville"]),
    ("Juventude", "RS", &["juventude"]),
    ("Bragantino", "SP", &["bragantino", "red bull bragantino"]),
    ("Ponte Preta", "SP", &["ponte preta"]),
    ("Portuguesa", "SP", &["portuguesa", "portuguesa desportos"]),
    ("Guarani", "SP", &["guarani"]),
    ("CSA", "AL", &["csa", "cs alagoano"]),
    ("CRB", "AL", &["crb"]),
    ("Cuiabá", "MT", &["cuiaba"]),
    ("Paysandu", "PA", &["paysandu"]),
    ("Remo", "PA", &["remo", "clube do remo"]),
    ("ABC", "RN", &["abc"]),
    ("ASA", "AL", &["asa"]),
    ("Santo André", "SP", &["santo andre"]),
    ("São Caetano", "SP", &["sao caetano"]),
];

/// Traditional rivalries: (team a, team b, derby name). Names are CLUBS display names.
pub const DERBIES: &[(&str, &str, &str)] = &[
    ("Flamengo", "Fluminense", "Fla-Flu"),
    ("Flamengo", "Vasco", "Clássico dos Milhões"),
    ("Flamengo", "Botafogo", "Clássico da Rivalidade"),
    ("Fluminense", "Vasco", "Clássico dos Gigantes"),
    ("Fluminense", "Botafogo", "Clássico Vovô"),
    ("Botafogo", "Vasco", "Clássico da Amizade"),
    ("Corinthians", "Palmeiras", "Derby Paulista"),
    ("Corinthians", "São Paulo", "Majestoso"),
    ("Palmeiras", "São Paulo", "Choque-Rei"),
    ("Santos", "Corinthians", "Clássico Alvinegro"),
    ("Santos", "Palmeiras", "Clássico da Saudade"),
    ("Santos", "São Paulo", "San-São"),
    ("Grêmio", "Internacional", "Gre-Nal"),
    ("Atlético-MG", "Cruzeiro", "Clássico Mineiro"),
    ("Bahia", "Vitória", "Ba-Vi"),
    ("Athletico-PR", "Coritiba", "Atletiba"),
    ("Sport", "Náutico", "Clássico dos Clássicos"),
    ("Sport", "Santa Cruz", "Clássico das Multidões"),
    ("Náutico", "Santa Cruz", "Clássico das Emoções"),
    ("Ceará", "Fortaleza", "Clássico-Rei"),
    ("Avaí", "Figueirense", "Clássico de Florianópolis"),
    ("Remo", "Paysandu", "Re-Pa"),
    ("CRB", "CSA", "Clássico das Multidões (AL)"),
];

fn deaccent(c: char) -> char {
    match c {
        'á' | 'à' | 'â' | 'ã' | 'ä' => 'a',
        'é' | 'è' | 'ê' | 'ë' => 'e',
        'í' | 'ì' | 'î' | 'ï' => 'i',
        'ó' | 'ò' | 'ô' | 'õ' | 'ö' => 'o',
        'ú' | 'ù' | 'û' | 'ü' => 'u',
        'ç' => 'c',
        'ñ' => 'n',
        _ => c,
    }
}

/// Lowercase, strip accents and punctuation, collapse whitespace.
pub fn fold(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    for c in s.chars().flat_map(|c| c.to_lowercase()) {
        let c = deaccent(c);
        if c.is_alphanumeric() {
            out.push(c);
        } else if c != '.' && c != '\'' && !out.ends_with(' ') {
            out.push(' ');
        }
    }
    out.trim().to_string()
}

fn is_uf(s: &str) -> bool {
    UFS.iter().any(|u| u.eq_ignore_ascii_case(s))
}

fn is_code(s: &str) -> bool {
    (2..=3).contains(&s.len()) && s.chars().all(|c| c.is_ascii_uppercase())
}

/// Split a trailing state/country marker off a raw team name:
/// "Palmeiras-SP", "América - MG", "Nacional (URU)", "Botafogo RJ".
pub fn split_suffix(raw: &str) -> (String, Option<String>) {
    let raw = raw.trim();
    if let (Some(open), true) = (raw.rfind('('), raw.ends_with(')')) {
        let code = &raw[open + 1..raw.len() - 1];
        if is_code(code) && open > 0 {
            return (raw[..open].trim().to_string(), Some(code.to_string()));
        }
    }
    if let Some(pos) = raw.rfind('-') {
        let (base, code) = (raw[..pos].trim(), raw[pos + 1..].trim());
        if !base.is_empty() && (is_code(code) || is_uf(code)) {
            return (base.to_string(), Some(code.to_uppercase()));
        }
    }
    if let Some(pos) = raw.rfind(' ') {
        let (base, code) = (raw[..pos].trim(), &raw[pos + 1..]);
        if !base.is_empty() && is_code(code) && is_uf(code) {
            return (base.to_string(), Some(code.to_string()));
        }
    }
    (raw.to_string(), None)
}

#[derive(Debug, Clone, PartialEq)]
pub struct TeamId {
    /// Stable matching key (folded).
    pub key: String,
    /// Human readable name.
    pub display: String,
    /// True when the name had no state marker and is not a well-known club, so
    /// it may be the same team as a "<key> <uf>" spelling elsewhere.
    pub stateless: bool,
}

fn find_club(alias: &str) -> Option<&'static (&'static str, &'static str, &'static [&'static str])> {
    CLUBS.iter().find(|c| c.2.contains(&alias))
}

/// Whether `key` is one of the well-known Brazilian clubs.
pub fn is_known_club(key: &str) -> bool {
    CLUBS.iter().any(|c| fold(c.0) == key)
}

/// Normalise any spelling of a team name.
pub fn canonical(raw: &str) -> TeamId {
    let (base, state) = split_suffix(raw);
    let folded = fold(&base);
    let tokens: Vec<&str> = folded.split(' ').collect();
    let stripped: Vec<&str> = tokens.iter().copied().filter(|t| *t != "fc" && *t != "ec").collect();
    let base_key = if stripped.is_empty() { folded.clone() } else { stripped.join(" ") };

    // "Atlético" and "América" only identify a club together with the state.
    if let Some(st) = &state {
        if let Some(c) = find_club(&format!("{} {}", base_key, st.to_lowercase())) {
            return TeamId { key: fold(c.0), display: c.0.to_string(), stateless: false };
        }
    }
    if let Some(c) = find_club(&base_key) {
        if state.as_deref().map_or(true, |s| s == c.1) {
            return TeamId { key: fold(c.0), display: c.0.to_string(), stateless: false };
        }
    }
    match state {
        Some(st) => TeamId {
            key: format!("{} {}", base_key, st.to_lowercase()),
            display: format!("{}-{}", base, st),
            stateless: false,
        },
        None => TeamId { key: base_key, display: base, stateless: true },
    }
}

/// Parse "2023-09-24", "2012-05-19 18:30:00" or "29/03/2003" into ISO `YYYY-MM-DD`.
pub fn parse_date(s: &str) -> Option<String> {
    let s = s.trim();
    let digits = |p: &str, n: usize| p.len() == n && p.chars().all(|c| c.is_ascii_digit());
    let head = s.split(|c| c == ' ' || c == 'T').next()?;
    let (y, m, d) = if head.contains('/') {
        let p: Vec<&str> = head.split('/').collect();
        if p.len() != 3 { return None; }
        (p[2], p[1], p[0])
    } else {
        let p: Vec<&str> = head.split('-').collect();
        if p.len() != 3 { return None; }
        (p[0], p[1], p[2])
    };
    if !digits(y, 4) || m.is_empty() || d.is_empty() || m.len() > 2 || d.len() > 2 {
        return None;
    }
    let (mi, di): (u32, u32) = (m.parse().ok()?, d.parse().ok()?);
    if !(1..=12).contains(&mi) || !(1..=31).contains(&di) {
        return None;
    }
    Some(format!("{}-{:02}-{:02}", y, mi, di))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn folds_accents_and_case() {
        assert_eq!(fold("São Paulo"), "sao paulo");
        assert_eq!(fold("Grêmio"), "gremio");
        assert_eq!(fold("A.s.a."), "asa");
    }

    #[test]
    fn team_name_variations_share_a_key() {
        for n in ["Palmeiras-SP", "Palmeiras - SP", "Palmeiras", "palmeiras"] {
            assert_eq!(canonical(n).key, "palmeiras", "{n}");
        }
        for n in ["Atlético-MG", "Atletico-MG", "Atlético - MG", "Atletico Mineiro", "atletico mg"] {
            assert_eq!(canonical(n).display, "Atlético-MG", "{n}");
        }
        for n in ["Athletico-PR", "Atletico-PR", "Atlético Paranaense - PR", "Athletico", "Athletico Paranaense"] {
            assert_eq!(canonical(n).display, "Athletico-PR", "{n}");
        }
        for n in ["Vasco da Gama-RJ", "Vasco", "Vasco Da Gama RJ"] {
            assert_eq!(canonical(n).display, "Vasco", "{n}");
        }
        assert_eq!(canonical("Sport Club do Recife").display, "Sport");
        assert_eq!(canonical("EC Bahia").display, "Bahia");
        assert_eq!(canonical("América FC (Minas Gerais)").display, "América-MG");
    }

    #[test]
    fn homonyms_in_other_states_stay_distinct() {
        assert_ne!(canonical("Botafogo - PB").key, canonical("Botafogo-RJ").key);
        assert_ne!(canonical("Guaraní (PAR)").key, canonical("Guarani-SP").key);
        assert_ne!(canonical("América - RN").key, canonical("América - MG").key);
        assert_eq!(canonical("Nacional (URU)").key, canonical("Nacional-URU").key);
        assert_eq!(canonical("Colo-Colo").display, "Colo-Colo");
    }

    #[test]
    fn parses_all_date_formats() {
        assert_eq!(parse_date("2023-09-24").as_deref(), Some("2023-09-24"));
        assert_eq!(parse_date("29/03/2003").as_deref(), Some("2003-03-29"));
        assert_eq!(parse_date("2012-05-19 18:30:00").as_deref(), Some("2012-05-19"));
        assert_eq!(parse_date("NA"), None);
    }
}
