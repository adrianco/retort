use chrono::{Datelike, NaiveDate, NaiveDateTime};

const STATE_CODES: &[&str] = &[
    "ac", "al", "ap", "am", "ba", "ce", "df", "es", "go", "ma", "mt", "ms", "mg", "pa", "pb", "pr",
    "pe", "pi", "rj", "rn", "rs", "ro", "rr", "sc", "sp", "se", "to",
];

pub fn normalize_text(value: &str) -> String {
    fold_accents(value)
        .to_lowercase()
        .chars()
        .map(|c| if c.is_ascii_alphanumeric() { c } else { ' ' })
        .collect::<String>()
        .split_whitespace()
        .collect::<Vec<_>>()
        .join(" ")
}

pub fn team_key(value: &str) -> String {
    let mut raw = fold_accents(value).to_lowercase();
    raw = raw.trim().to_owned();
    let mut suffix = None;

    for state in STATE_CODES {
        for separator in [" - ", "-", "/"] {
            let suffix_text = format!("{separator}{state}");
            if raw.ends_with(&suffix_text) {
                raw.truncate(raw.len() - suffix_text.len());
                raw = raw.trim().to_owned();
                suffix = Some((*state).to_owned());
                break;
            }
        }
    }

    let normalized = normalize_text(&raw);
    let mut words: Vec<&str> = normalized.split_whitespace().collect();
    while matches!(
        words.last().copied(),
        Some("fc" | "futebol" | "football" | "clube" | "club")
    ) {
        words.pop();
    }
    let key = words.join(" ");
    let canonical = match key.as_str() {
        "sport club corinthians paulista" | "corinthians paulista" => "corinthians".into(),
        "sociedade esportiva palmeiras" => "palmeiras".into(),
        "clube de regatas do flamengo" => "flamengo".into(),
        "sao paulo futebol" => "sao paulo".into(),
        "santos futebol" => "santos".into(),
        "fluminense football" => "fluminense".into(),
        "gremio foot ball porto alegrense" | "gremio fbpa" => "gremio".into(),
        "vasco da gama" | "club de regatas vasco da gama" => "vasco".into(),
        "atletico paranaense" => "athletico pr".into(),
        "athletico paranaense" => "athletico pr".into(),
        other => other.to_owned(),
    };
    if canonical == "atletico" && suffix.as_deref() == Some("pr") {
        "athletico pr".into()
    } else if matches!(canonical.as_str(), "atletico" | "america" | "nacional") {
        suffix
            .map(|s| format!("{canonical} {s}"))
            .unwrap_or(canonical)
    } else {
        canonical
    }
}

fn fold_accents(value: &str) -> String {
    value
        .chars()
        .map(|c| match c {
            'á' | 'à' | 'â' | 'ã' | 'ä' | 'Á' | 'À' | 'Â' | 'Ã' | 'Ä' => 'a',
            'é' | 'è' | 'ê' | 'ë' | 'É' | 'È' | 'Ê' | 'Ë' => 'e',
            'í' | 'ì' | 'î' | 'ï' | 'Í' | 'Ì' | 'Î' | 'Ï' => 'i',
            'ó' | 'ò' | 'ô' | 'õ' | 'ö' | 'Ó' | 'Ò' | 'Ô' | 'Õ' | 'Ö' => 'o',
            'ú' | 'ù' | 'û' | 'ü' | 'Ú' | 'Ù' | 'Û' | 'Ü' => 'u',
            'ç' | 'Ç' => 'c',
            'ñ' | 'Ñ' => 'n',
            other => other,
        })
        .collect()
}

pub fn competition_key(value: &str) -> String {
    let key = normalize_text(value);
    if key.contains("libertadores") {
        "libertadores".into()
    } else if key.contains("copa do brasil") || key.contains("brazilian cup") {
        "copa do brasil".into()
    } else if key.contains("brasile")
        || key.contains("serie a")
        || key.contains("campeonato brasileiro")
    {
        "brasileirao".into()
    } else {
        key
    }
}

pub fn parse_date(value: &str) -> Option<NaiveDate> {
    let value = value.trim().trim_matches('"');
    for format in ["%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"] {
        if let Ok(date) = NaiveDate::parse_from_str(value, format) {
            return Some(date);
        }
    }
    for format in ["%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S"] {
        if let Ok(date_time) = NaiveDateTime::parse_from_str(value, format) {
            return Some(date_time.date());
        }
    }
    None
}

pub fn season_from_date(date: NaiveDate) -> u16 {
    date.year() as u16
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn normalizes_accents_suffixes_and_aliases() {
        assert_eq!(team_key("São Paulo FC"), "sao paulo");
        assert_eq!(team_key("Flamengo-RJ"), "flamengo");
        assert_eq!(team_key("América - MG"), "america mg");
        assert_ne!(team_key("Atlético-MG"), team_key("Atlético-GO"));
        assert_eq!(team_key("Atlético-PR"), team_key("Athletico Paranaense"));
        assert_eq!(team_key("Vasco da Gama"), team_key("Vasco"));
        assert_eq!(team_key("Sport Club Corinthians Paulista"), "corinthians");
        assert_eq!(team_key("Nacional (URU)"), "nacional uru");
    }

    #[test]
    fn parses_supported_dates() {
        assert_eq!(parse_date("29/03/2003").unwrap().to_string(), "2003-03-29");
        assert_eq!(
            parse_date("2012-05-19 18:30:00").unwrap().to_string(),
            "2012-05-19"
        );
    }
}
