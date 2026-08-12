use chrono::NaiveDate;

const STATES: &[&str] = &[
    "ac", "al", "ap", "am", "ba", "ce", "df", "es", "go", "ma", "mt", "ms", "mg", "pa", "pb", "pr",
    "pe", "pi", "rj", "rn", "rs", "ro", "rr", "sc", "sp", "se", "to",
];

pub fn fold(value: &str) -> String {
    let mut result = String::with_capacity(value.len());
    let mut space = true;
    for original in value.chars() {
        let ch = match original {
            'á' | 'à' | 'â' | 'ã' | 'ä' | 'Á' | 'À' | 'Â' | 'Ã' | 'Ä' => 'a',
            'é' | 'è' | 'ê' | 'ë' | 'É' | 'È' | 'Ê' | 'Ë' => 'e',
            'í' | 'ì' | 'î' | 'ï' | 'Í' | 'Ì' | 'Î' | 'Ï' => 'i',
            'ó' | 'ò' | 'ô' | 'õ' | 'ö' | 'Ó' | 'Ò' | 'Ô' | 'Õ' | 'Ö' => 'o',
            'ú' | 'ù' | 'û' | 'ü' | 'Ú' | 'Ù' | 'Û' | 'Ü' => 'u',
            'ç' | 'Ç' => 'c',
            other => other.to_ascii_lowercase(),
        };
        if ch.is_ascii_alphanumeric() {
            result.push(ch);
            space = false;
        } else if !space {
            result.push(' ');
            space = true;
        }
    }
    result.trim().to_string()
}

pub fn team_key(value: &str) -> String {
    let folded = fold(value);
    let mut words: Vec<&str> = folded.split_whitespace().collect();
    if words.len() > 1 && STATES.contains(words.last().unwrap()) {
        words.pop();
    }
    let simple = words.join(" ");
    let aliases = [
        (&["sport club corinthians paulista"][..], "corinthians"),
        (&["corinthians paulista"][..], "corinthians"),
        (&["clube de regatas do flamengo"][..], "flamengo"),
        (&["fluminense football club"][..], "fluminense"),
        (&["sociedade esportiva palmeiras"][..], "palmeiras"),
        (&["santos futebol clube", "santos fc"][..], "santos"),
        (
            &["sao paulo futebol clube", "sao paulo fc"][..],
            "sao paulo",
        ),
        (
            &["club de regatas vasco da gama", "vasco da gama"][..],
            "vasco",
        ),
        (
            &["clube atletico mineiro", "atletico mineiro"][..],
            "atletico mg",
        ),
        (
            &["clube atletico paranaense", "atletico paranaense"][..],
            "athletico pr",
        ),
        (&["athletico paranaense"][..], "athletico pr"),
        (&["gremio foot ball porto alegrense"][..], "gremio"),
        (&["sport club internacional"][..], "internacional"),
    ];
    for (variants, canonical) in aliases {
        if variants.contains(&simple.as_str()) {
            return canonical.to_string();
        }
    }
    simple
}

pub fn team_matches(candidate: &str, query: &str) -> bool {
    let candidate = team_key(candidate);
    let query = team_key(query);
    candidate == query
        || (query.len() >= 4 && candidate.split_whitespace().any(|word| word == query))
        || (candidate.len() >= 4 && query.split_whitespace().any(|word| word == candidate))
}

pub fn competition_key(value: &str) -> String {
    let folded = fold(value);
    if folded.contains("libertadores") {
        "libertadores".into()
    } else if folded.contains("copa do brasil") || folded.contains("brazilian cup") {
        "copa do brasil".into()
    } else if folded.contains("brasileirao")
        || folded.contains("brasileiro")
        || folded.contains("serie a")
    {
        "brasileirao".into()
    } else {
        folded
    }
}

pub fn display_competition(value: &str) -> String {
    match competition_key(value).as_str() {
        "brasileirao" => "Brasileirão".into(),
        "copa do brasil" => "Copa do Brasil".into(),
        "libertadores" => "Copa Libertadores".into(),
        _ => value.trim().to_string(),
    }
}

pub fn parse_date(value: &str) -> Option<NaiveDate> {
    let value = value.trim().trim_matches('"');
    ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y"]
        .iter()
        .find_map(|format| NaiveDate::parse_from_str(value, format).ok())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn normalizes_accents_suffixes_and_aliases() {
        assert_eq!(team_key("São Paulo-SP"), "sao paulo");
        assert_eq!(team_key("São Paulo FC"), "sao paulo");
        assert_eq!(team_key("Sport Club Corinthians Paulista"), "corinthians");
        assert!(team_matches("Flamengo-RJ", "flamengo"));
        assert_eq!(
            competition_key("Campeonato Brasileiro Série A"),
            "brasileirao"
        );
    }

    #[test]
    fn accepts_all_documented_date_formats() {
        for date in ["2023-09-24", "2012-05-19 18:30:00", "29/03/2003"] {
            assert!(parse_date(date).is_some(), "failed to parse {date}");
        }
    }
}
