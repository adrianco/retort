//! Team-name and text normalization.
//!
//! The six datasets spell the same club many different ways:
//! `"Palmeiras-SP"`, `"Palmeiras"`, `"São Paulo"`, `"Sao Paulo"`,
//! `"Atlético - MG"`, `"Atletico Mineiro"`, `"C. R. B. - AL"` ...
//! This module folds every variant to a stable canonical key so that
//! matches and queries line up across files.

/// Brazilian state abbreviations that may appear as a team-name suffix.
const STATES: &[&str] = &[
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB",
    "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
];

/// Country codes used by the Libertadores file, e.g. `"Barcelona-EQU"`.
const COUNTRIES: &[&str] = &[
    "ARG", "BOL", "CHI", "COL", "ECU", "EQU", "MEX", "PAR", "PER", "URU", "VEN", "BRA",
];

/// Base names that are shared by several different clubs; for these the
/// state/country suffix is kept inside the canonical key.
const AMBIGUOUS_BASES: &[&str] = &[
    "atletico",
    "athletico",
    "america",
    "botafogo",
    "bragantino",
    "boavista",
    "nacional",
    "barcelona",
    "guarani",
    "santa cruz",
    "vitoria",
    "independiente",
    "internacional",
    "nautico",
];

/// Fold Latin accented characters to plain ASCII (ã -> a, ç -> c, ...).
pub fn fold_accents(s: &str) -> String {
    s.chars()
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

/// Lower-case, accent-fold and whitespace-collapse arbitrary text.
/// Used for case/accent-insensitive substring matching (players, clubs).
pub fn fold_text(s: &str) -> String {
    let folded = fold_accents(s).to_lowercase();
    folded.split_whitespace().collect::<Vec<_>>().join(" ")
}

/// A canonical team identity.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TeamName {
    /// Stable key used for joins and comparisons, e.g. `"palmeiras"`,
    /// `"atletico-mg"`.
    pub key: String,
    /// Human-readable display name, e.g. `"Palmeiras"`, `"Atlético-MG"`.
    pub display: String,
}

/// Split a trailing region (state or country) suffix off a raw team name.
/// Handles `"Palmeiras-SP"`, `"América - MG"`, `"America MG"`,
/// `"Barcelona-EQU"` and `"Guaraní (PAR)"`.
fn split_region(raw: &str) -> (String, Option<String>) {
    let mut name = raw.trim().to_string();
    let mut region: Option<String> = None;

    // Parenthetical: "(PAR)" country, "(Minas Gerais)" state, or noise
    // like "(antigo Esporte Clube Barreira)" which is simply dropped.
    if let (Some(open), Some(close)) = (name.find('('), name.rfind(')')) {
        if open < close {
            let inner = name[open + 1..close].trim().to_string();
            let mut rest = String::new();
            rest.push_str(&name[..open]);
            rest.push_str(&name[close + 1..]);
            name = rest.trim().to_string();
            let inner_up = fold_accents(&inner).to_uppercase();
            let inner_folded = fold_text(&inner);
            if COUNTRIES.contains(&inner_up.as_str()) || STATES.contains(&inner_up.as_str()) {
                region = Some(inner_up);
            } else if inner_folded == "minas gerais" {
                region = Some("MG".into());
            }
        }
    }

    // Trailing "-XX" / " - XX" suffix.
    if region.is_none() {
        if let Some(pos) = name.rfind('-') {
            let suffix = name[pos + 1..].trim();
            let suffix_up = fold_accents(suffix).to_uppercase();
            if STATES.contains(&suffix_up.as_str()) || COUNTRIES.contains(&suffix_up.as_str()) {
                region = Some(suffix_up);
                name = name[..pos].trim().trim_end_matches('-').trim().to_string();
            }
        }
    }

    // Trailing bare state token, e.g. "America MG" (only when the name has
    // more than one token, so "ABC" stays intact).
    if region.is_none() {
        let tokens: Vec<&str> = name.split_whitespace().collect();
        if tokens.len() >= 2 {
            let last = fold_accents(tokens[tokens.len() - 1]).to_uppercase();
            let is_all_upper = tokens[tokens.len() - 1]
                .chars()
                .all(|c| c.is_ascii_uppercase());
            if is_all_upper && (STATES.contains(&last.as_str()) || COUNTRIES.contains(&last.as_str()))
            {
                region = Some(last);
                name = tokens[..tokens.len() - 1].join(" ");
            }
        }
    }

    (name, region)
}

/// Apply club-specific aliases. Returns `(base, region_override)`.
fn apply_aliases(base: &str, region: Option<&str>) -> (String, Option<String>) {
    let r = region.map(|s| s.to_string());
    match base {
        "athletico paranaense" | "atletico paranaense" | "athletico" | "atletico pr" => {
            ("athletico".into(), Some("PR".into()))
        }
        "atletico mineiro" => ("atletico".into(), Some("MG".into())),
        "atletico goianiense" => ("atletico".into(), Some("GO".into())),
        "america fc natal" | "america rn" => ("america".into(), Some("RN".into())),
        "america fc" | "america mineiro" => ("america".into(), Some("MG".into())),
        "ceara sporting club" | "ceara sc" => ("ceara".into(), r),
        "nautico capibaribe" | "clube nautico capibaribe" => ("nautico".into(), Some("PE".into())),
        "sport club do recife" | "sport recife" | "sport club recife" => ("sport".into(), r),
        "vasco da gama" | "cr vasco da gama" => ("vasco".into(), r),
        "sao paulo fc" | "sao paulo futebol clube" => ("sao paulo".into(), r),
        "red bull bragantino" | "rb bragantino" => ("bragantino".into(), Some("SP".into())),
        "cr flamengo" | "clube de regatas do flamengo" => ("flamengo".into(), r),
        "se palmeiras" | "sociedade esportiva palmeiras" => ("palmeiras".into(), r),
        "sport club corinthians paulista" | "corinthians paulista" => ("corinthians".into(), r),
        "gremio fbpa" | "gremio foot ball porto alegrense" => ("gremio".into(), r),
        "ec bahia" | "esporte clube bahia" => ("bahia".into(), r),
        "santos fc" => ("santos".into(), r),
        "cruzeiro ec" | "cruzeiro esporte clube" => ("cruzeiro".into(), r),
        "botafogo fr" | "botafogo de futebol e regatas" => ("botafogo".into(), Some("RJ".into())),
        "ec vitoria" | "esporte clube vitoria" => ("vitoria".into(), Some("BA".into())),
        "fortaleza ec" | "fortaleza esporte clube" => ("fortaleza".into(), r),
        "csa al" => ("csa".into(), Some("AL".into())),
        other => (other.to_string(), r),
    }
}

/// Default regions for ambiguous bases when the dataset omits the suffix
/// (e.g. the Libertadores file lists Botafogo de Futebol e Regatas simply
/// as "Botafogo").
fn default_region(base: &str) -> Option<&'static str> {
    match base {
        "botafogo" => Some("RJ"),
        "guarani" => Some("SP"),
        "bragantino" => Some("SP"),
        "vitoria" => Some("BA"),
        "internacional" => Some("RS"),
        "nautico" => Some("PE"),
        "america" => None,
        _ => None,
    }
}

/// Club-type abbreviations ("Esporte Clube", "Futebol Clube", ...) that some
/// files prepend or append to a club's short name: `"EC Bahia"`,
/// `"Fortaleza EC"`, `"Fortaleza FC"` all mean the bare club name.
const CLUB_TYPE_TOKENS: &[&str] = &["ec", "fc", "sc", "ac", "ad", "aa", "se", "cr", "ca"];

fn strip_club_type_tokens(base: &str) -> String {
    let mut tokens: Vec<&str> = base.split_whitespace().collect();
    if tokens.len() >= 2 && CLUB_TYPE_TOKENS.contains(&tokens[0]) {
        tokens.remove(0);
    }
    if tokens.len() >= 2 && CLUB_TYPE_TOKENS.contains(tokens.last().unwrap()) {
        tokens.pop();
    }
    tokens.join(" ")
}

/// Preferred display spelling (with accents) for well-known clubs whose
/// names appear unaccented in some files.
fn display_override(key: &str) -> Option<&'static str> {
    Some(match key {
        "gremio" => "Grêmio",
        "sao paulo" => "São Paulo",
        "goias" => "Goiás",
        "ceara" => "Ceará",
        "avai" => "Avaí",
        "nautico" => "Náutico",
        "criciuma" => "Criciúma",
        "cuiaba" => "Cuiabá",
        "parana" => "Paraná",
        "sao caetano" => "São Caetano",
        "santo andre" => "Santo André",
        "vasco" => "Vasco da Gama",
        "atletico-mg" => "Atlético-MG",
        "atletico-go" => "Atlético-GO",
        "athletico-pr" => "Athletico-PR",
        "america-mg" => "América-MG",
        "america-rn" => "América-RN",
        "vitoria-ba" => "Vitória",
        "internacional-rs" => "Internacional",
        "nautico-pe" => "Náutico",
        "bragantino-sp" => "Red Bull Bragantino",
        _ => return None,
    })
}

/// Compute the canonical identity for a raw team name as it appears in any
/// of the CSV files (or in a user query).
pub fn canonical_team(raw: &str) -> TeamName {
    let raw = raw.trim().trim_matches('"').trim();
    let (name, region) = split_region(raw);

    // Normalized base: accent-folded, lower-case, dots/apostrophes removed.
    let mut base = fold_accents(&name)
        .to_lowercase()
        .replace(['.', '\''], " ");
    base = base.split_whitespace().collect::<Vec<_>>().join(" ");

    // "c r b" -> "crb": join runs of single-letter tokens.
    let tokens: Vec<&str> = base.split_whitespace().collect();
    if tokens.len() >= 2 && tokens.iter().all(|t| t.chars().count() == 1) {
        base = tokens.concat();
    }

    base = strip_club_type_tokens(&base);

    let (mut base, region) = apply_aliases(&base, region.as_deref());
    let region = region.or_else(|| default_region(&base).map(|s| s.to_string()));

    // The club renamed itself from Atlético-PR to Athletico-PR in 2019;
    // both spellings appear across the datasets and must share a key.
    if base == "atletico" && region.as_deref() == Some("PR") {
        base = "athletico".to_string();
    }

    let ambiguous = AMBIGUOUS_BASES.contains(&base.as_str());
    let key = match (&region, ambiguous) {
        (Some(r), true) => format!("{}-{}", base, r.to_lowercase()),
        _ => base.clone(),
    };

    // Display: title-case the folded base, re-attaching the suffix only for
    // ambiguous names ("Atlético-MG") so users can tell the clubs apart.
    let display = match display_override(&key) {
        Some(d) => d.to_string(),
        None => {
            let display_base = title_case_team(&name, &base);
            match (&region, ambiguous) {
                (Some(r), true) => format!("{}-{}", display_base, r),
                _ => display_base,
            }
        }
    };

    TeamName { key, display }
}

/// Keep the original (accented) spelling when it still matches the base,
/// otherwise title-case the normalized base.
fn title_case_team(original: &str, base: &str) -> String {
    let orig_folded = fold_text(original).replace(['.', '\''], "");
    let orig_folded = orig_folded.split_whitespace().collect::<Vec<_>>().join(" ");
    if orig_folded == *base || fold_text(original) == *base {
        return original.trim().to_string();
    }
    base.split_whitespace()
        .map(|w| {
            let mut chars = w.chars();
            match chars.next() {
                Some(first) => first.to_uppercase().collect::<String>() + chars.as_str(),
                None => String::new(),
            }
        })
        .collect::<Vec<_>>()
        .join(" ")
}

/// Does a record's canonical key satisfy a user-supplied team query key?
///
/// `"botafogo"` matches `"botafogo-rj"` and `"botafogo-pb"`; the exact key
/// always matches itself; a fully-qualified query (`"atletico-mg"`) also
/// matches an unqualified record (`"atletico"`).
pub fn team_key_matches(query_key: &str, record_key: &str) -> bool {
    if query_key == record_key {
        return true;
    }
    if record_key.starts_with(query_key) && record_key[query_key.len()..].starts_with('-') {
        return true;
    }
    if query_key.starts_with(record_key) && query_key[record_key.len()..].starts_with('-') {
        return true;
    }
    false
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn strips_state_suffix() {
        assert_eq!(canonical_team("Palmeiras-SP").key, "palmeiras");
        assert_eq!(canonical_team("Flamengo-RJ").key, "flamengo");
        assert_eq!(canonical_team("São Paulo").key, "sao paulo");
        assert_eq!(canonical_team("Sao Paulo-SP").key, "sao paulo");
    }

    #[test]
    fn keeps_suffix_for_ambiguous_clubs() {
        assert_eq!(canonical_team("Atlético-MG").key, "atletico-mg");
        assert_eq!(canonical_team("Atletico Mineiro").key, "atletico-mg");
        assert_eq!(canonical_team("Atlético - MG").key, "atletico-mg");
        assert_eq!(canonical_team("Athletico-PR").key, "athletico-pr");
        assert_eq!(canonical_team("Atletico Paranaense").key, "athletico-pr");
        assert_eq!(canonical_team("Athletico Paranaense - PR").key, "athletico-pr");
        assert_eq!(canonical_team("Atletico-PR").key, "athletico-pr");
        assert_eq!(canonical_team("Atlético - PR").key, "athletico-pr");
        assert_eq!(canonical_team("América - MG").key, "america-mg");
        assert_eq!(canonical_team("America MG").key, "america-mg");
        assert_eq!(canonical_team("América FC (Minas Gerais)").key, "america-mg");
    }

    #[test]
    fn handles_country_codes_and_parentheses() {
        assert_eq!(canonical_team("Barcelona-EQU").key, "barcelona-equ");
        assert_eq!(canonical_team("Guaraní (PAR)").key, "guarani-par");
        assert_eq!(canonical_team("Guaraní-PAR").key, "guarani-par");
        assert_eq!(canonical_team("Guarani").key, "guarani-sp");
    }

    #[test]
    fn handles_full_official_names() {
        assert_eq!(
            canonical_team("Sport Club Corinthians Paulista").key,
            "corinthians"
        );
        assert_eq!(canonical_team("Vasco da Gama-RJ").key, "vasco");
        assert_eq!(canonical_team("Vasco").key, "vasco");
        assert_eq!(canonical_team("Sport Club do Recife").key, "sport");
        assert_eq!(canonical_team("Sport-PE").key, "sport");
    }

    #[test]
    fn joins_initialisms() {
        assert_eq!(canonical_team("C. R. B. - AL").key, "crb");
        assert_eq!(canonical_team("A.s.a. - AL").key, "asa");
        assert_eq!(canonical_team("ABC - RN").key, "abc");
        assert_eq!(canonical_team("Csa-AL").key, "csa");
    }

    #[test]
    fn botafogo_defaults_to_rio() {
        assert_eq!(canonical_team("Botafogo").key, "botafogo-rj");
        assert_eq!(canonical_team("Botafogo-RJ").key, "botafogo-rj");
        assert_eq!(canonical_team("Botafogo - PB").key, "botafogo-pb");
    }

    #[test]
    fn query_matching() {
        assert!(team_key_matches("botafogo", "botafogo-rj"));
        assert!(team_key_matches("atletico-mg", "atletico-mg"));
        assert!(team_key_matches("atletico-mg", "atletico"));
        assert!(!team_key_matches("atletico-mg", "atletico-go"));
        assert!(!team_key_matches("flamengo", "fluminense"));
    }

    #[test]
    fn fold_text_handles_utf8() {
        assert_eq!(fold_text("São Paulo"), "sao paulo");
        assert_eq!(fold_text("Grêmio"), "gremio");
        assert_eq!(fold_text("Avaí"), "avai");
    }
}
