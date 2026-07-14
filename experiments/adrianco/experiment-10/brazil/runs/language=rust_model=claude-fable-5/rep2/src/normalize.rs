// ============================================================================
// CONTEXT: Brazilian Soccer MCP Server - normalization layer
//
// Purpose:  The six source CSVs spell the same club many different ways:
//             "Palmeiras-SP", "Palmeiras", "Sociedade Esportiva Palmeiras - SP"
//             "Atlético-MG", "Atletico Mineiro", "Atlético Mineiro"
//             "América - MG", "America MG", "América FC (Minas Gerais)"
//           This module folds every variant onto one canonical key so that
//           cross-dataset joins, deduplication and statistics group rows for
//           the same club together.
//
// Approach: lowercase -> strip accents -> drop parentheticals -> tokenize on
//           '-' and whitespace -> peel a trailing Brazilian UF / country code
//           into a separate "state" -> apply an explicit alias table -> for
//           ambiguous bases (Atlético, América, Botafogo...) re-attach the
//           state so distinct clubs never merge.
//
// Also here: date parsing (ISO, "DD/MM/YYYY", with/without time) and
//           competition-name normalization.
// ============================================================================

/// Brazilian state (UF) codes that appear as team-name suffixes.
const UF_CODES: &[&str] = &[
    "ac", "al", "am", "ap", "ba", "ce", "df", "es", "go", "ma", "mg", "ms",
    "mt", "pa", "pb", "pe", "pi", "pr", "rj", "rn", "ro", "rr", "rs", "sc",
    "se", "sp", "to",
];

/// Country codes used as suffixes in the Libertadores dataset.
const COUNTRY_CODES: &[&str] = &[
    "arg", "bol", "chi", "col", "ecu", "equ", "mex", "par", "per", "uru", "ven",
];

/// Club bases where the state suffix distinguishes different clubs.
const AMBIGUOUS_BASES: &[&str] =
    &["atletico", "athletico", "america", "botafogo", "boavista", "bragantino"];

/// Remove accents/diacritics common in Brazilian Portuguese.
pub fn deaccent(s: &str) -> String {
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
            _ => c,
        })
        .collect()
}

fn strip_parentheticals(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    let mut depth = 0usize;
    for c in s.chars() {
        match c {
            '(' => depth += 1,
            ')' => depth = depth.saturating_sub(1),
            _ if depth == 0 => out.push(c),
            _ => {}
        }
    }
    out
}

/// Exact alias table applied after tokenization. Maps a (base, state) pair
/// onto the canonical (base, state). Empty state string means "none".
fn alias(base: &str, state: Option<&str>) -> (String, Option<String>) {
    let st = state.map(|s| s.to_string());
    match base {
        "vasco da gama" => ("vasco".into(), st),
        "red bull bragantino" | "rb bragantino" => ("bragantino".into(), Some("sp".into())),
        "sport club corinthians paulista" => ("corinthians".into(), st),
        "sport club do recife" | "sport recife" => ("sport".into(), Some("pe".into())),
        "sociedade esportiva palmeiras" => ("palmeiras".into(), st),
        "sao paulo fc" | "sao paulo futebol clube" => ("sao paulo".into(), st),
        "clube de regatas do flamengo" => ("flamengo".into(), st),
        "fluminense football club" => ("fluminense".into(), st),
        "atletico mineiro" => ("atletico".into(), Some("mg".into())),
        "atletico goianiense" => ("atletico".into(), Some("go".into())),
        "athletico paranaense" | "atletico paranaense" | "athletico" | "athletico club paranaense" => {
            ("athletico".into(), Some("pr".into()))
        }
        "america mineiro" | "america fc" => ("america".into(), Some("mg".into())),
        "america fc natal" | "america de natal" => ("america".into(), Some("rn".into())),
        "ceara sporting club" => ("ceara".into(), st),
        "gremio fbpa" | "gremio foot ball porto alegrense" => ("gremio".into(), st),
        "esporte clube bahia" | "ec bahia" => ("bahia".into(), st),
        "ec juventude" => ("juventude".into(), st),
        "fortaleza fc" | "fortaleza ec" => ("fortaleza".into(), st),
        "santa cruz fc" => ("santa cruz".into(), st),
        "esporte clube vitoria" => ("vitoria".into(), Some("ba".into())),
        "associacao chapecoense de futebol" => ("chapecoense".into(), st),
        _ => (base.to_string(), st),
    }
}

/// Produce the canonical key for a team name from any dataset or user query.
pub fn canonical_team(raw: &str) -> String {
    let s = deaccent(&strip_parentheticals(raw)).to_lowercase();
    let mut tokens: Vec<String> = s
        .split(|c: char| c == '-' || c == '–' || c.is_whitespace() || c == '/')
        .filter(|t| !t.is_empty())
        .map(|t| t.trim_matches(|c: char| !c.is_alphanumeric()).to_string())
        .filter(|t| !t.is_empty())
        .collect();

    let mut state: Option<String> = None;
    if tokens.len() > 1 {
        let last = tokens.last().unwrap().as_str();
        if UF_CODES.contains(&last) || COUNTRY_CODES.contains(&last) {
            state = Some(tokens.pop().unwrap());
        }
    }
    let base = tokens.join(" ");
    let (mut base, mut state) = alias(&base, state.as_deref());

    // "Atlético-PR" (older spelling) is today's Athletico Paranaense.
    if base == "atletico" && state.as_deref() == Some("pr") {
        base = "athletico".into();
    }
    if base == "athletico" && state.is_none() {
        state = Some("pr".into());
    }
    // Bare "Botafogo" in national/continental data is Botafogo-RJ, and bare
    // "Bragantino" is the Série A club from Bragança Paulista.
    if base == "botafogo" && state.is_none() {
        state = Some("rj".into());
    }
    if base == "bragantino" && state.is_none() {
        state = Some("sp".into());
    }
    if AMBIGUOUS_BASES.contains(&base.as_str()) {
        if let Some(st) = &state {
            return format!("{} {}", base, st);
        }
    }
    base
}

/// True when a stored canonical team key satisfies a canonical query key.
/// Equality first, then word-boundary-ish containment so that the query
/// "flamengo" matches "clube de regatas do flamengo".
pub fn team_matches(canonical: &str, query_canonical: &str) -> bool {
    if query_canonical.is_empty() {
        return false;
    }
    if canonical == query_canonical {
        return true;
    }
    contains_words(canonical, query_canonical) || contains_words(query_canonical, canonical)
}

fn contains_words(haystack: &str, needle: &str) -> bool {
    if let Some(pos) = haystack.find(needle) {
        let before_ok = pos == 0 || haystack.as_bytes()[pos - 1] == b' ';
        let end = pos + needle.len();
        let after_ok = end == haystack.len() || haystack.as_bytes()[end] == b' ';
        before_ok && after_ok
    } else {
        false
    }
}

/// Canonical competition labels used across the knowledge base.
pub const SERIE_A: &str = "Brasileirão Série A";
pub const SERIE_B: &str = "Brasileirão Série B";
pub const SERIE_C: &str = "Brasileirão Série C";
pub const COPA_DO_BRASIL: &str = "Copa do Brasil";
pub const LIBERTADORES: &str = "Copa Libertadores";

/// Map a free-form competition string onto a canonical label.
pub fn normalize_competition(q: &str) -> Option<&'static str> {
    let s = deaccent(q).to_lowercase();
    if s.contains("libertadores") {
        Some(LIBERTADORES)
    } else if s.contains("copa do brasil") || s.contains("brazilian cup") || s.contains("cup") {
        Some(COPA_DO_BRASIL)
    } else if s.contains("serie b") || s.contains("série b") {
        Some(SERIE_B)
    } else if s.contains("serie c") {
        Some(SERIE_C)
    } else if s.contains("brasileir") || s.contains("serie a") || s.contains("campeonato brasileiro") {
        Some(SERIE_A)
    } else {
        None
    }
}

/// Parse the date formats found in the datasets into ISO "YYYY-MM-DD":
///   "2012-05-19 18:30:00", "2023-09-24", "29/03/2003", "9/3/2003"
pub fn parse_date(s: &str) -> Option<String> {
    let d = s.trim().split_whitespace().next()?;
    if d.len() == 10 && d.as_bytes().get(4) == Some(&b'-') {
        return Some(d.to_string());
    }
    let parts: Vec<&str> = d.split('/').collect();
    if parts.len() == 3 && parts[2].len() == 4 {
        let day: u32 = parts[0].parse().ok()?;
        let month: u32 = parts[1].parse().ok()?;
        let year: i32 = parts[2].parse().ok()?;
        if (1..=31).contains(&day) && (1..=12).contains(&month) {
            return Some(format!("{:04}-{:02}-{:02}", year, month, day));
        }
    }
    None
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn canonical_folds_state_suffixes_and_accents() {
        assert_eq!(canonical_team("Palmeiras-SP"), "palmeiras");
        assert_eq!(canonical_team("São Paulo"), "sao paulo");
        assert_eq!(canonical_team("Sao Paulo-SP"), "sao paulo");
        assert_eq!(canonical_team("Grêmio"), "gremio");
    }

    #[test]
    fn ambiguous_clubs_keep_their_state() {
        assert_eq!(canonical_team("Atlético-MG"), "atletico mg");
        assert_eq!(canonical_team("Atletico Mineiro"), "atletico mg");
        assert_eq!(canonical_team("Atlético-GO"), "atletico go");
        assert_eq!(canonical_team("Atlético-PR"), "athletico pr");
        assert_eq!(canonical_team("Athletico Paranaense"), "athletico pr");
        assert_eq!(canonical_team("América - MG"), "america mg");
        assert_eq!(canonical_team("América FC (Minas Gerais)"), "america mg");
        assert_eq!(canonical_team("Botafogo-RJ"), "botafogo rj");
        assert_eq!(canonical_team("Botafogo"), "botafogo rj");
        assert_eq!(canonical_team("Botafogo PB"), "botafogo pb");
    }

    #[test]
    fn aliases_fold_full_names() {
        assert_eq!(canonical_team("Vasco da Gama-RJ"), "vasco");
        assert_eq!(canonical_team("Sport Club do Recife"), "sport");
        assert_eq!(canonical_team("Red Bull Bragantino-SP"), "bragantino sp");
    }

    #[test]
    fn query_matching_supports_partial_names() {
        assert!(team_matches("clube de regatas do flamengo", "flamengo"));
        assert!(team_matches("flamengo", "flamengo"));
        assert!(!team_matches("atletico mg", "atletico go"));
    }

    #[test]
    fn date_formats_are_normalized() {
        assert_eq!(parse_date("2012-05-19 18:30:00").unwrap(), "2012-05-19");
        assert_eq!(parse_date("2023-09-24").unwrap(), "2023-09-24");
        assert_eq!(parse_date("29/03/2003").unwrap(), "2003-03-29");
    }
}
