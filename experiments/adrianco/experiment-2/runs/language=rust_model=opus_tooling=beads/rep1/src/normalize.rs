// Team name normalization. Many datasets use different conventions
// (e.g. "Palmeiras-SP", "Palmeiras", "SE Palmeiras"). We strip state
// suffixes, diacritics, punctuation, and lowercase to get a stable key.

pub fn normalize_team(name: &str) -> String {
    let mut s = name.trim().to_string();
    // strip trailing " - UF" or "-UF" (2-letter state) possibly with extra text
    // First remove parenthesized suffixes like "(URU)"
    if let Some(idx) = s.find('(') {
        s.truncate(idx);
        s = s.trim().to_string();
    }
    // Strip trailing state suffix patterns: " - XX", "-XX"
    s = strip_state_suffix(&s);
    // Strip common long-form prefixes
    let lower = s.to_lowercase();
    let prefixes = [
        "sport club ", "sociedade esportiva ", "clube de regatas ",
        "clube de regatas do ", "esporte clube ", "associação atlética ",
        "associacao atletica ", "clube atlético ", "clube atletico ",
        "fortaleza esporte clube", "cruzeiro esporte clube",
    ];
    for p in prefixes {
        if lower.starts_with(p) {
            s = s[p.len()..].to_string();
            break;
        }
    }
    // Remove diacritics
    let s = remove_diacritics(&s);
    // lowercase, collapse whitespace, remove punctuation
    let mut out = String::new();
    let mut last_space = false;
    for c in s.chars() {
        if c.is_alphanumeric() {
            for lc in c.to_lowercase() { out.push(lc); }
            last_space = false;
        } else if c.is_whitespace() {
            if !last_space && !out.is_empty() {
                out.push(' ');
                last_space = true;
            }
        }
        // drop other punctuation
    }
    let out = out.trim().to_string();
    // Canonical aliases
    canonical(&out)
}

fn strip_state_suffix(s: &str) -> String {
    let s = s.trim();
    // " - SP" or " -SP"
    if let Some(idx) = s.rfind(" - ") {
        let tail = &s[idx + 3..];
        if tail.len() == 2 && tail.chars().all(|c| c.is_ascii_alphabetic()) {
            return s[..idx].to_string();
        }
    }
    if let Some(idx) = s.rfind('-') {
        let tail = &s[idx + 1..];
        if tail.len() == 2 && tail.chars().all(|c| c.is_ascii_alphabetic()) {
            return s[..idx].to_string();
        }
        // 3-letter country code: EQU, URU, ARG, etc.
        if tail.len() == 3 && tail.chars().all(|c| c.is_ascii_alphabetic()) {
            return s[..idx].to_string();
        }
    }
    s.to_string()
}

fn remove_diacritics(s: &str) -> String {
    s.chars()
        .map(|c| match c {
            'á' | 'à' | 'â' | 'ã' | 'ä' => 'a',
            'Á' | 'À' | 'Â' | 'Ã' | 'Ä' => 'A',
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

fn canonical(s: &str) -> String {
    // map common variations to a canonical key
    match s {
        "sao paulo" | "sao paulo fc" | "sao paulo futebol clube" => "sao paulo".into(),
        "athletico pr" | "athletico paranaense" | "atletico pr" | "atletico paranaense" => "athletico paranaense".into(),
        "atletico mg" | "atletico mineiro" | "clube atletico mineiro" => "atletico mineiro".into(),
        "atletico go" | "atletico goianiense" => "atletico goianiense".into(),
        "gremio" | "gremio football porto alegrense" => "gremio".into(),
        "flamengo" | "cr flamengo" => "flamengo".into(),
        "corinthians" | "sc corinthians paulista" => "corinthians".into(),
        "palmeiras" | "se palmeiras" => "palmeiras".into(),
        "santos" | "santos fc" => "santos".into(),
        "fluminense" | "fluminense fc" => "fluminense".into(),
        "vasco" | "vasco da gama" | "cr vasco da gama" => "vasco da gama".into(),
        "botafogo" | "botafogo rj" | "botafogo fr" => "botafogo".into(),
        "internacional" | "sc internacional" => "internacional".into(),
        "bahia" | "ec bahia" => "bahia".into(),
        other => other.to_string(),
    }
}

pub fn display_team(name: &str) -> String {
    // Strip trailing state suffix for display
    let s = name.trim();
    let s = if let Some(idx) = s.rfind('-') {
        let tail = &s[idx + 1..];
        if tail.len() == 2 && tail.chars().all(|c| c.is_ascii_alphabetic()) {
            s[..idx].trim().to_string()
        } else {
            s.to_string()
        }
    } else {
        s.to_string()
    };
    s
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn normalizes_state_suffix() {
        assert_eq!(normalize_team("Palmeiras-SP"), normalize_team("Palmeiras"));
        assert_eq!(normalize_team("Flamengo-RJ"), normalize_team("Flamengo"));
    }

    #[test]
    fn normalizes_diacritics() {
        assert_eq!(normalize_team("São Paulo"), normalize_team("Sao Paulo"));
        assert_eq!(normalize_team("Grêmio"), normalize_team("Gremio"));
    }

    #[test]
    fn normalizes_country_code() {
        let n = normalize_team("Nacional (URU)");
        assert_eq!(n, "nacional");
    }

    #[test]
    fn canonical_aliases() {
        assert_eq!(normalize_team("Vasco"), normalize_team("Vasco da Gama"));
    }
}
