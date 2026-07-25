//! Name normalization for Brazilian club names and free-text queries.
//!
//! The six source datasets spell the same club in many ways:
//!
//! | source                        | example spellings                                    |
//! |-------------------------------|------------------------------------------------------|
//! | `Brasileirao_Matches.csv`     | `Palmeiras-SP`, `Atletico-PR`, `Vasco da Gama-RJ`     |
//! | `novo_campeonato_brasileiro`  | `São Paulo`, `Grêmio`, `Athletico-PR`, `Avaí`         |
//! | `BR-Football-Dataset.csv`     | `Sao Paulo`, `EC Bahia`, `Vasco Da Gama RJ`           |
//! | `Brazilian_Cup_Matches.csv`   | `América - MG`, `A.b.c. - RN`, `Boavista Sport Club…` |
//! | `Libertadores_Matches.csv`    | `Nacional (URU)`, `Nacional-URU`, `Athletico`         |
//! | `fifa_data.csv` (Club column) | `Atlético Mineiro`, `América FC (Minas Gerais)`       |
//!
//! [`normalize_team`] folds all of those onto a single [`TeamKey`] made of a
//! base name plus an optional state (UF) or country code, so matches and
//! players from different files land on the same knowledge-graph node.

use std::collections::HashMap;

/// Brazilian state (Unidade Federativa) abbreviations.
pub const STATES: [&str; 27] = [
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR",
    "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
];

/// Country codes used by the Libertadores dataset for non-Brazilian clubs.
pub const COUNTRIES: [&str; 13] = [
    "URU", "PAR", "ARG", "CHI", "COL", "PER", "BOL", "VEN", "MEX", "EQU", "ECU", "BRA", "USA",
];

/// Tokens that carry no identity ("Esporte Clube Bahia" == "Bahia").
const FILLER: &[&str] = &[
    "clube",
    "club",
    "futebol",
    "football",
    "esporte",
    "esportivo",
    "esportiva",
    "associacao",
    "atletica",
    "de",
    "do",
    "da",
    "dos",
    "das",
    "e",
    "fc",
    "ec",
    "sc",
    "ac",
    "cr",
    "sd",
    "ae",
    "se",
    // Club-type prefixes used by the smaller sides: Clube Atlético, Clube
    // Sportivo, Clube Esportivo, Grêmio Esportivo, Esporte Futebol.
    "ca",
    "cs",
    "ce",
    "ge",
    "ef",
];

/// Full state names as they appear inside parentheses in the FIFA club column.
const STATE_NAMES: [(&str, &str); 27] = [
    ("acre", "AC"),
    ("alagoas", "AL"),
    ("amapa", "AP"),
    ("amazonas", "AM"),
    ("bahia", "BA"),
    ("ceara", "CE"),
    ("distrito federal", "DF"),
    ("espirito santo", "ES"),
    ("goias", "GO"),
    ("maranhao", "MA"),
    ("mato grosso", "MT"),
    ("mato grosso do sul", "MS"),
    ("minas gerais", "MG"),
    ("para", "PA"),
    ("paraiba", "PB"),
    ("parana", "PR"),
    ("pernambuco", "PE"),
    ("piaui", "PI"),
    ("rio de janeiro", "RJ"),
    ("rio grande do norte", "RN"),
    ("rio grande do sul", "RS"),
    ("rondonia", "RO"),
    ("roraima", "RR"),
    ("santa catarina", "SC"),
    ("sao paulo", "SP"),
    ("sergipe", "SE"),
    ("tocantins", "TO"),
];

/// `(spelling, canonical base, state)` for clubs whose variants cannot be
/// derived mechanically. Keys are already folded/filler-stripped base names.
const ALIASES: &[(&str, &str, &str)] = &[
    // Rio de Janeiro
    ("flamengo", "flamengo", "RJ"),
    ("regatas flamengo", "flamengo", "RJ"),
    ("fluminense", "fluminense", "RJ"),
    ("botafogo", "botafogo", "RJ"),
    ("vasco", "vasco", "RJ"),
    ("vasco gama", "vasco", "RJ"),
    ("regatas vasco gama", "vasco", "RJ"),
    ("boavista sport", "boavista", "RJ"),
    ("boavista saquarema", "boavista", "RJ"),
    // São Paulo
    ("palmeiras", "palmeiras", "SP"),
    ("sao paulo", "sao paulo", "SP"),
    ("corinthians", "corinthians", "SP"),
    ("corinthians paulista", "corinthians", "SP"),
    ("sport corinthians paulista", "corinthians", "SP"),
    ("santos", "santos", "SP"),
    ("portuguesa", "portuguesa", "SP"),
    ("portuguesa desportos", "portuguesa", "SP"),
    ("ponte preta", "ponte preta", "SP"),
    ("guarani", "guarani", "SP"),
    ("sao caetano", "sao caetano", "SP"),
    ("santo andre", "santo andre", "SP"),
    ("bragantino", "bragantino", "SP"),
    ("red bull bragantino", "bragantino", "SP"),
    ("rb bragantino", "bragantino", "SP"),
    ("ituano", "ituano", "SP"),
    ("mirassol", "mirassol", "SP"),
    // Minas Gerais
    ("cruzeiro", "cruzeiro", "MG"),
    ("atletico mineiro", "atletico", "MG"),
    ("america mineiro", "america", "MG"),
    ("america minas gerais", "america", "MG"),
    ("america natal", "america", "RN"),
    ("ipatinga", "ipatinga", "MG"),
    ("tombense", "tombense", "MG"),
    // Paraná
    ("athletico", "athletico", "PR"),
    ("athletico paranaense", "athletico", "PR"),
    ("atletico paranaense", "athletico", "PR"),
    ("coritiba", "coritiba", "PR"),
    ("parana", "parana", "PR"),
    ("londrina", "londrina", "PR"),
    // Rio Grande do Sul
    ("gremio", "gremio", "RS"),
    ("internacional", "internacional", "RS"),
    ("juventude", "juventude", "RS"),
    // Santa Catarina
    ("chapecoense", "chapecoense", "SC"),
    ("avai", "avai", "SC"),
    ("figueirense", "figueirense", "SC"),
    ("criciuma", "criciuma", "SC"),
    ("joinville", "joinville", "SC"),
    // Nordeste
    ("bahia", "bahia", "BA"),
    ("vitoria", "vitoria", "BA"),
    ("sport", "sport", "PE"),
    ("sport recife", "sport", "PE"),
    ("recife", "sport", "PE"),
    ("nautico", "nautico", "PE"),
    ("nautico capibaribe", "nautico", "PE"),
    ("santa cruz", "santa cruz", "PE"),
    ("afogados ingazeira", "afogados", "PE"),
    ("fortaleza", "fortaleza", "CE"),
    ("ceara", "ceara", "CE"),
    ("ceara sporting", "ceara", "CE"),
    ("csa", "csa", "AL"),
    ("crb", "crb", "AL"),
    ("confianca", "confianca", "SE"),
    ("abc", "abc", "RN"),
    ("sampaio correa", "sampaio correa", "MA"),
    // Centro-Oeste / Norte
    ("goias", "goias", "GO"),
    ("atletico goianiense", "atletico", "GO"),
    ("atletico acreano", "atletico", "AC"),
    ("atletico cearense", "atletico", "CE"),
    ("atletico alagoinhas", "atletico", "BA"),
    ("moto sao luis", "moto", "MA"),
    ("real noroeste capixaba", "real noroeste", "ES"),
    ("vila nova", "vila nova", "GO"),
    ("cuiaba", "cuiaba", "MT"),
    ("brasilia", "brasilia", "DF"),
];

/// State-qualified aliases: `(base, state) -> canonical base`.
/// e.g. `Atlético-PR` (base `atletico`, state `PR`) is the same club as
/// `Athletico Paranaense` (base `athletico`, state `PR`).
const STATE_ALIASES: &[(&str, &str, &str)] = &[
    ("atletico", "PR", "athletico"),
    ("atletico paranaense", "PR", "athletico"),
    ("vasco gama", "RJ", "vasco"),
    ("america mineiro", "MG", "america"),
];

/// A normalized club identity.
#[derive(Debug, Clone, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct TeamKey {
    /// Accent-folded, filler-stripped base name, e.g. `"sao paulo"`.
    pub base: String,
    /// Brazilian state abbreviation when known, e.g. `Some("SP")`.
    pub state: Option<String>,
    /// Country code for non-Brazilian clubs, e.g. `Some("URU")`.
    pub country: Option<String>,
}

impl TeamKey {
    /// Stable identifier used as the knowledge-graph node key.
    pub fn id(&self) -> String {
        match (&self.state, &self.country) {
            (Some(s), _) => format!("{}-{}", self.base.replace(' ', "_"), s),
            (None, Some(c)) => format!("{}-{}", self.base.replace(' ', "_"), c),
            (None, None) => self.base.replace(' ', "_"),
        }
    }

    /// True when this key carries no state/country qualifier.
    pub fn is_bare(&self) -> bool {
        self.state.is_none() && self.country.is_none()
    }
}

/// Replaces accented Latin characters with their ASCII counterparts.
pub fn fold_accents(input: &str) -> String {
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
            'ý' | 'ÿ' => 'y',
            other => other,
        })
        .collect()
}

/// Lowercases, folds accents and reduces punctuation to single spaces.
pub fn simplify(input: &str) -> String {
    let folded = fold_accents(input).to_lowercase();
    let mut out = String::with_capacity(folded.len());
    for c in folded.chars() {
        if c.is_alphanumeric() {
            out.push(c);
        } else {
            out.push(' ');
        }
    }
    out.split_whitespace().collect::<Vec<_>>().join(" ")
}

fn strip_parenthetical(raw: &str) -> (String, Option<String>) {
    match (raw.find('('), raw.rfind(')')) {
        (Some(open), Some(close)) if close > open => {
            let inner = raw[open + 1..close].trim().to_string();
            let mut outer = String::new();
            outer.push_str(&raw[..open]);
            outer.push(' ');
            outer.push_str(&raw[close + 1..]);
            (outer, Some(inner))
        }
        _ => (raw.to_string(), None),
    }
}

fn lookup_state_name(inner: &str) -> Option<String> {
    let simple = simplify(inner);
    STATE_NAMES
        .iter()
        .find(|(name, _)| *name == simple)
        .map(|(_, uf)| uf.to_string())
}

fn is_state(token: &str) -> bool {
    token.len() == 2 && STATES.iter().any(|s| s.eq_ignore_ascii_case(token))
}

fn is_country(token: &str) -> bool {
    token.len() == 3 && COUNTRIES.iter().any(|c| c.eq_ignore_ascii_case(token))
}

/// Normalizes a raw club spelling into a [`TeamKey`].
///
/// `hint_state` supplies a state from a sibling column (the historical
/// Brasileirão file keeps `Mandante_UF` separate from the club name).
pub fn normalize_team(raw: &str, hint_state: Option<&str>) -> TeamKey {
    let (outer, inner) = strip_parenthetical(raw);
    let mut state = hint_state
        .map(|s| s.trim().to_uppercase())
        .filter(|s| is_state(s));
    let mut country = None;

    if state.is_none() {
        if let Some(paren) = inner.as_deref() {
            if let Some(uf) = lookup_state_name(paren) {
                state = Some(uf);
            } else {
                let simple = simplify(paren).to_uppercase();
                if is_state(&simple) {
                    state = Some(simple);
                } else if is_country(&simple) {
                    country = Some(simple);
                }
            }
        }
    }

    let mut tokens: Vec<String> = simplify(&outer)
        .split_whitespace()
        .map(|t| t.to_string())
        .collect();

    // A trailing UF/country token qualifies the club ("Avai-SC", "Nacional URU").
    while tokens.len() > 1 {
        let last = tokens.last().unwrap().to_uppercase();
        if is_state(&last) {
            if state.is_none() {
                state = Some(last);
            }
            tokens.pop();
        } else if is_country(&last) {
            if country.is_none() {
                country = Some(last);
            }
            tokens.pop();
        } else {
            break;
        }
    }

    // "A.b.c." -> ["a","b","c"] -> "abc"
    if tokens.len() > 1 && tokens.iter().all(|t| t.chars().count() == 1) {
        tokens = vec![tokens.concat()];
    }

    let mut kept: Vec<String> = tokens
        .iter()
        .filter(|t| !FILLER.contains(&t.as_str()))
        .cloned()
        .collect();
    // Stray initials from abbreviations such as "Serra F.C." or
    // "Parnahyba S.C."; digits are kept because "4 de Julho" is a real club.
    if kept.len() > 1 {
        let trimmed: Vec<String> = kept
            .iter()
            .filter(|t| t.chars().count() > 1 || t.chars().all(|c| c.is_numeric()))
            .cloned()
            .collect();
        if !trimmed.is_empty() {
            kept = trimmed;
        }
    }
    let mut base = if kept.is_empty() {
        tokens.join(" ")
    } else {
        kept.join(" ")
    };

    if base.is_empty() {
        base = simplify(raw);
    }

    // Alias resolution: state-qualified first, then bare spelling.
    if let Some(uf) = state.clone() {
        if let Some((_, _, canonical)) = STATE_ALIASES
            .iter()
            .find(|(b, s, _)| *b == base && *s == uf.as_str())
        {
            base = canonical.to_string();
        }
    }
    if let Some((_, canonical_base, canonical_state)) = ALIASES.iter().find(|(v, _, _)| *v == base)
    {
        base = canonical_base.to_string();
        if state.is_none() && country.is_none() {
            state = Some(canonical_state.to_string());
        }
    }

    if state.is_some() {
        country = None;
    }

    TeamKey {
        base,
        state,
        country,
    }
}

/// Normalizes a user-supplied team name for lookup (no state hint available).
pub fn normalize_query(raw: &str) -> TeamKey {
    normalize_team(raw, None)
}

/// Case/accent-insensitive comparison key for player names, clubs, positions.
pub fn text_key(raw: &str) -> String {
    simplify(raw)
}

/// Levenshtein distance, used for "did you mean" suggestions.
pub fn edit_distance(a: &str, b: &str) -> usize {
    let a: Vec<char> = a.chars().collect();
    let b: Vec<char> = b.chars().collect();
    if a.is_empty() {
        return b.len();
    }
    if b.is_empty() {
        return a.len();
    }
    let mut prev: Vec<usize> = (0..=b.len()).collect();
    let mut cur = vec![0usize; b.len() + 1];
    for i in 1..=a.len() {
        cur[0] = i;
        for j in 1..=b.len() {
            let cost = usize::from(a[i - 1] != b[j - 1]);
            cur[j] = (prev[j] + 1).min(cur[j - 1] + 1).min(prev[j - 1] + cost);
        }
        std::mem::swap(&mut prev, &mut cur);
    }
    prev[b.len()]
}

/// Club-type abbreviations that add nothing to a display name.
const ABBREVIATIONS: &[&str] = &[
    "EC", "FC", "SC", "AC", "CR", "SE", "AD", "AE", "SD", "CD", "AA", "EF",
];

/// Trims a raw spelling down to a readable club name: `Atlético-MG` ->
/// `Atlético`, `EC Bahia` -> `Bahia`, `Boavista Sport Club (antigo …) - RJ` ->
/// `Boavista Sport Club`.
pub fn clean_display(raw: &str) -> String {
    let without_parens = match (raw.find('('), raw.rfind(')')) {
        (Some(open), Some(close)) if close > open => {
            format!("{} {}", &raw[..open], &raw[close + 1..])
        }
        _ => raw.to_string(),
    };
    let mut tokens: Vec<&str> = without_parens
        .split(|c: char| c.is_whitespace() || c == '-')
        .map(str::trim)
        .filter(|token| !token.is_empty())
        .collect();

    while tokens.len() > 1 {
        let last = tokens.last().unwrap().to_uppercase();
        if is_state(&last) || is_country(&last) || ABBREVIATIONS.contains(&last.as_str()) {
            tokens.pop();
        } else {
            break;
        }
    }
    while tokens.len() > 1 {
        let first = tokens[0].to_uppercase();
        if ABBREVIATIONS.contains(&first.as_str()) {
            tokens.remove(0);
        } else {
            break;
        }
    }
    tokens.join(" ")
}

/// Picks the "nicest" display spelling among the variants seen for a club.
///
/// Prefers accented spellings ("Grêmio" over "Gremio"), spellings that agree
/// with the canonical base ("Athletico-PR" over "Atlético - PR" when the club
/// resolves to `athletico`), short forms over long ones, and frequent
/// spellings over rare ones.
pub fn best_display_name(variants: &HashMap<String, usize>, base: &str) -> String {
    let base_tokens = base.split_whitespace().count();
    let mut best: Option<(String, i64)> = None;
    for (raw, count) in variants {
        let cleaned = clean_display(raw);
        if cleaned.is_empty() {
            continue;
        }
        let simple = simplify(&cleaned);
        let mut score = (*count as i64).min(500);
        if !cleaned.is_ascii() {
            score += 1_000;
        }
        if simple.contains(base) {
            score += 800;
        }
        if raw.contains('(') {
            score -= 2_000;
        }
        let extra_tokens = simple.split_whitespace().count() as i64 - base_tokens as i64;
        score -= extra_tokens.max(0) * 300;
        match &best {
            Some((_, best_score)) if *best_score >= score => {}
            _ => best = Some((cleaned, score)),
        }
    }
    best.map(|(name, _)| name).unwrap_or_default()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn key(raw: &str) -> String {
        normalize_team(raw, None).id()
    }

    #[test]
    fn state_suffixes_are_folded() {
        assert_eq!(key("Palmeiras-SP"), "palmeiras-SP");
        assert_eq!(key("Palmeiras"), "palmeiras-SP");
        assert_eq!(key("SE Palmeiras"), "palmeiras-SP");
    }

    #[test]
    fn accents_and_case_are_folded() {
        assert_eq!(key("São Paulo"), key("Sao Paulo"));
        assert_eq!(key("Grêmio"), key("Gremio"));
        assert_eq!(key("Avaí"), key("Avai-SC"));
        assert_eq!(key("Vitória"), key("Vitoria-BA"));
    }

    #[test]
    fn athletico_spellings_converge() {
        assert_eq!(key("Athletico-PR"), key("Atletico-PR"));
        assert_eq!(key("Athletico"), key("Athletico Paranaense"));
        assert_eq!(key("Atlético Paranaense"), key("Athletico-PR"));
        assert_ne!(key("Atlético-MG"), key("Athletico-PR"));
        assert_ne!(key("Atletico-GO"), key("Atlético-MG"));
    }

    #[test]
    fn full_club_names_are_folded() {
        assert_eq!(key("Sport Club Corinthians Paulista"), "corinthians-SP");
        assert_eq!(key("EC Bahia"), "bahia-BA");
        assert_eq!(key("Ceará Sporting Club"), "ceara-CE");
        assert_eq!(key("Sport Club do Recife"), "sport-PE");
        assert_eq!(key("Vasco Da Gama RJ"), "vasco-RJ");
    }

    #[test]
    fn initialisms_are_joined() {
        assert_eq!(key("A.b.c. - RN"), "abc-RN");
        assert_eq!(key("ABC - RN"), "abc-RN");
    }

    #[test]
    fn fifa_parenthetical_state_is_used() {
        assert_eq!(key("América FC (Minas Gerais)"), "america-MG");
        assert_ne!(key("América FC (Minas Gerais)"), key("América-RN"));
    }

    #[test]
    fn country_codes_are_folded() {
        assert_eq!(key("Nacional (URU)"), "nacional-URU");
        assert_eq!(key("Nacional-URU"), "nacional-URU");
        assert_eq!(key("Guaraní (PAR)"), key("Guaraní-PAR"));
        assert_eq!(
            key("Independiente Del Valle"),
            key("Independiente del Valle")
        );
    }

    #[test]
    fn hint_state_column_is_honoured() {
        assert_eq!(normalize_team("América", Some("RN")).id(), "america-RN");
        assert_eq!(normalize_team("América", Some("MG")).id(), "america-MG");
    }

    #[test]
    fn trailing_initials_are_dropped() {
        assert_eq!(key("Serra F.C."), key("Serra"));
        assert_eq!(key("Parnahyba S.C. - PI"), key("Parnahyba - PI"));
        // Digits are part of the name, not an abbreviation.
        assert_eq!(key("4 de Julho - PI"), "4_julho-PI");
    }

    #[test]
    fn long_form_club_names_fold_onto_the_short_form() {
        assert_eq!(key("Nautico Capibaribe"), key("Náutico - PE"));
        assert_eq!(key("Portuguesa Desportos"), key("Portuguesa-SP"));
        assert_eq!(key("Atletico Acreano"), key("Atlético - AC"));
    }

    #[test]
    fn display_names_are_trimmed() {
        assert_eq!(clean_display("Atlético-MG"), "Atlético");
        assert_eq!(clean_display("EC Bahia"), "Bahia");
        assert_eq!(clean_display("Fortaleza FC"), "Fortaleza");
        assert_eq!(clean_display("Vasco da Gama-RJ"), "Vasco da Gama");
        assert_eq!(clean_display("Nacional (URU)"), "Nacional");
    }

    #[test]
    fn distinct_clubs_stay_distinct() {
        assert_ne!(key("Santos"), key("Santos Laguna"));
        assert_ne!(key("Sport-PE"), key("Sport Boys"));
        assert_ne!(key("Grêmio"), key("Grêmio Prudente"));
        assert_ne!(key("Atlético Nacional"), key("Nacional (URU)"));
    }
}
