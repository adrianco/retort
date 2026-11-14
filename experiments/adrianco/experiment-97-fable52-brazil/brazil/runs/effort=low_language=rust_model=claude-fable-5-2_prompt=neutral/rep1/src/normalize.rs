//! Normalisation of team names, free text and dates across the datasets.

const STATES: &[&str] = &[
    "ac", "al", "am", "ap", "ba", "ce", "df", "es", "go", "ma", "mg", "ms", "mt", "pa", "pb",
    "pe", "pi", "pr", "rj", "rn", "ro", "rr", "rs", "sc", "se", "sp", "to",
];
const COUNTRIES: &[&str] = &[
    "equ", "par", "uru", "arg", "chi", "col", "bol", "per", "ven", "mex",
];
/// Club names shared by different clubs in different states, with the state of the
/// best-known club (which gets the bare key). Other states are kept in the key
/// ("santos" is Santos-SP, "santos-ap" is the Amapá club). An empty default means
/// no club owns the bare name.
const AMBIGUOUS: &[(&str, &str)] = &[
    ("atletico", ""),
    ("america", ""),
    ("nacional", ""),
    ("rio branco", ""),
    ("comercial", ""),
    ("sao raimundo", ""),
    ("botafogo", "rj"),
    ("flamengo", "rj"),
    ("santos", "sp"),
    ("guarani", "sp"),
    ("bragantino", "sp"),
    ("juventude", "rs"),
    ("internacional", "rs"),
    ("ypiranga", "rs"),
    ("santa cruz", "pe"),
    ("nautico", "pe"),
    ("vitoria", "ba"),
    ("operario", "pr"),
];

/// Lowercase and strip Portuguese/Spanish diacritics.
pub fn fold(s: &str) -> String {
    s.chars()
        .flat_map(|c| c.to_lowercase())
        .map(|c| match c {
            'á' | 'à' | 'â' | 'ã' | 'ä' => 'a',
            'é' | 'è' | 'ê' | 'ë' => 'e',
            'í' | 'ì' | 'î' | 'ï' => 'i',
            'ó' | 'ò' | 'ô' | 'õ' | 'ö' => 'o',
            'ú' | 'ù' | 'û' | 'ü' => 'u',
            'ç' => 'c',
            'ñ' => 'n',
            c => c,
        })
        .collect::<String>()
        .split_whitespace()
        .collect::<Vec<_>>()
        .join(" ")
}

fn strip_parens(s: &str) -> String {
    let mut out = String::new();
    let mut depth = 0;
    for c in s.chars() {
        match c {
            '(' => depth += 1,
            ')' => depth = (depth as i32 - 1).max(0) as usize,
            c if depth == 0 => out.push(c),
            _ => {}
        }
    }
    out.split_whitespace().collect::<Vec<_>>().join(" ")
}

/// Split "Palmeiras-SP" / "América - MG" / "Tupi MG" into (name, Some(state)).
/// Parenthesised remarks and country suffixes ("Barcelona-EQU") are removed.
pub fn split_state(name: &str) -> (String, Option<String>) {
    let s = strip_parens(name);
    let s = s.trim().trim_end_matches(['-', ' ']).to_string();
    let chars: Vec<char> = s.chars().collect();
    let n = chars.len();
    let tail = |k: usize| -> String { chars[n - k..].iter().collect::<String>().to_lowercase() };
    let head = |k: usize| -> String {
        chars[..n - k]
            .iter()
            .collect::<String>()
            .trim_end_matches([' ', '-'])
            .to_string()
    };
    if n > 3 && (chars[n - 3] == '-' || chars[n - 3] == ' ') && STATES.contains(&tail(2).as_str())
    {
        let base = head(3);
        if !base.is_empty() {
            return (base, Some(tail(2)));
        }
    }
    if n > 4 && chars[n - 4] == '-' && COUNTRIES.contains(&tail(3).as_str()) {
        return (head(4), None);
    }
    (s, None)
}

/// Canonical key for a team name. `state_hint` is used when the dataset carries
/// the state in a separate column.
pub fn team_key(name: &str, state_hint: Option<&str>) -> String {
    let (base, st) = split_state(name);
    let mut st = st.or_else(|| {
        state_hint
            .map(|s| s.trim().to_lowercase())
            .filter(|s| STATES.contains(&s.as_str()))
    });
    let mut base = fold(&base).replace('.', "");
    let alias: Option<(&str, Option<&str>)> = match base.as_str() {
        "athletico paranaense" | "atletico paranaense" | "athletico" | "club athletico paranaense" => {
            Some(("atletico", Some("pr")))
        }
        "atletico mineiro" | "clube atletico mineiro" => Some(("atletico", Some("mg"))),
        "atletico goianiense" => Some(("atletico", Some("go"))),
        "america mineiro" | "america fc" => Some(("america", Some("mg"))),
        "vasco da gama" | "cr vasco da gama" => Some(("vasco", None)),
        "sport recife" | "sport club do recife" => Some(("sport", None)),
        "sport club corinthians paulista" => Some(("corinthians", None)),
        "clube de regatas do flamengo" => Some(("flamengo", None)),
        "sociedade esportiva palmeiras" => Some(("palmeiras", None)),
        "sport club internacional" => Some(("internacional", None)),
        "gremio foot-ball porto alegrense" => Some(("gremio", None)),
        "ceara sporting club" => Some(("ceara", None)),
        "nautico capibaribe" => Some(("nautico", None)),
        "portuguesa desportos" => Some(("portuguesa", None)),
        "red bull bragantino" | "rb bragantino" => Some(("bragantino", None)),
        "clube do remo" => Some(("remo", None)),
        _ => None,
    };
    if let Some((b, s)) = alias {
        base = b.to_string();
        if s.is_some() {
            st = s.map(String::from);
        }
    } else {
        base = base.replace(" sport club", "");
        let toks: Vec<&str> = base.split(' ').collect();
        let kept: Vec<&str> = toks
            .iter()
            .copied()
            .filter(|t| !matches!(*t, "fc" | "ec" | "sc" | "futebol" | "clube" | "club" | "esporte"))
            .collect();
        if !kept.is_empty() {
            base = kept.join(" ");
        }
    }
    match (AMBIGUOUS.iter().find(|(b, _)| *b == base), st) {
        (Some((_, default)), Some(s)) if s != *default => format!("{base}-{s}"),
        _ => base,
    }
}

/// Human-readable name candidate for a raw team name with the given key.
pub fn display_candidate(name: &str, key: &str) -> String {
    let (base, st) = split_state(name);
    match st {
        Some(s) if key.ends_with(&format!("-{s}")) => format!("{}-{}", base, s.to_uppercase()),
        _ => base,
    }
}

/// Parse "2023-09-24", "2012-05-19 18:30:00" or "29/03/2003" into ISO "YYYY-MM-DD".
pub fn parse_date(s: &str) -> Option<String> {
    let s = s.trim().split([' ', 'T']).next()?;
    let (y, m, d) = if s.contains('/') {
        let p: Vec<&str> = s.split('/').collect();
        if p.len() != 3 {
            return None;
        }
        (p[2].parse::<i32>().ok()?, p[1].parse::<u32>().ok()?, p[0].parse::<u32>().ok()?)
    } else {
        let p: Vec<&str> = s.split('-').collect();
        if p.len() != 3 {
            return None;
        }
        (p[0].parse::<i32>().ok()?, p[1].parse::<u32>().ok()?, p[2].parse::<u32>().ok()?)
    };
    if !(1800..=2200).contains(&y) || !(1..=12).contains(&m) || !(1..=31).contains(&d) {
        return None;
    }
    Some(format!("{y:04}-{m:02}-{d:02}"))
}

/// Days since 1970-01-01 for an ISO date.
pub fn day_number(iso: &str) -> i64 {
    let p: Vec<i64> = iso.split('-').filter_map(|x| x.parse().ok()).collect();
    if p.len() != 3 {
        return 0;
    }
    let (y, m, d) = (if p[1] <= 2 { p[0] - 1 } else { p[0] }, p[1], p[2]);
    let era = y.div_euclid(400);
    let yoe = y.rem_euclid(400);
    let doy = (153 * (if m > 2 { m - 3 } else { m + 9 }) + 2) / 5 + d - 1;
    era * 146097 + yoe * 365 + yoe / 4 - yoe / 100 + doy - 719468
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn team_name_variations_share_a_key() {
        for n in ["Palmeiras-SP", "Palmeiras", "Palmeiras - SP", "palmeiras", "Sociedade Esportiva Palmeiras"] {
            assert_eq!(team_key(n, None), "palmeiras", "{n}");
        }
        for n in ["São Paulo", "Sao Paulo-SP", "São Paulo - SP", "São Paulo FC"] {
            assert_eq!(team_key(n, None), "sao paulo", "{n}");
        }
        for n in ["Grêmio", "Gremio-RS", "Grêmio - RS"] {
            assert_eq!(team_key(n, None), "gremio");
        }
        assert_eq!(team_key("Sport Club Corinthians Paulista", None), "corinthians");
        assert_eq!(team_key("Vasco da Gama - RJ", None), "vasco");
        assert_eq!(team_key("Vasco Da Gama RJ", None), "vasco");
    }

    #[test]
    fn ambiguous_clubs_keep_their_state() {
        assert_eq!(team_key("Atlético-MG", None), "atletico-mg");
        assert_eq!(team_key("Atletico Mineiro", None), "atletico-mg");
        assert_eq!(team_key("Atlético - PR", None), "atletico-pr");
        assert_eq!(team_key("Athletico Paranaense", None), "atletico-pr");
        assert_eq!(team_key("Athletico-PR", None), "atletico-pr");
        assert_eq!(team_key("America", Some("MG")), "america-mg");
        assert_eq!(team_key("América - RN", None), "america-rn");
        assert_eq!(team_key("Botafogo RJ", None), "botafogo");
        assert_eq!(team_key("Botafogo SP", None), "botafogo-sp");
        assert_eq!(team_key("Santos - SP", None), "santos");
        assert_eq!(team_key("Santos - AP", None), "santos-ap");
        assert_eq!(team_key("Flamengo - PI", None), "flamengo-pi");
    }

    #[test]
    fn foreign_and_annotated_names() {
        assert_eq!(team_key("Barcelona-EQU", None), "barcelona");
        assert_eq!(team_key("Colo-Colo", None), "colo-colo");
        assert_eq!(
            team_key("Boavista Sport Club (antigo Esporte Clube Barreira) - RJ", None),
            "boavista"
        );
    }

    #[test]
    fn dates_in_all_formats() {
        assert_eq!(parse_date("2023-09-24").as_deref(), Some("2023-09-24"));
        assert_eq!(parse_date("29/03/2003").as_deref(), Some("2003-03-29"));
        assert_eq!(parse_date("2012-05-19 18:30:00").as_deref(), Some("2012-05-19"));
        assert_eq!(parse_date("garbage"), None);
        assert_eq!(day_number("1970-01-01"), 0);
        assert_eq!(day_number("2020-03-01") - day_number("2020-02-28"), 2);
    }

    #[test]
    fn folding_handles_utf8() {
        assert_eq!(fold("São Paulo"), "sao paulo");
        assert_eq!(fold("Avaí  Grêmio Ceará"), "avai gremio ceara");
    }
}
