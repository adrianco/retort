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
    let state = words
        .last()
        .copied()
        .filter(|word| words.len() > 1 && STATES.contains(word));
    let with_state = words.join(" ");
    if state.is_some() {
        words.pop();
    }
    let simple = words.join(" ");

    // A state suffix is normally dataset decoration, but it is part of the
    // identity for ambiguous club names. Resolve those before applying the
    // general suffix-removal rule.
    match with_state.as_str() {
        "atletico mg" => return "atletico mineiro".into(),
        "atletico pr" | "athletico pr" => return "athletico paranaense".into(),
        "atletico go" => return "atletico goianiense".into(),
        "america mg" => return "america mineiro".into(),
        "botafogo rj" => return "botafogo".into(),
        _ => {}
    }
    if matches!(simple.as_str(), "america" | "botafogo" | "nacional") {
        if let Some(state) = state {
            return format!("{simple} {state}");
        }
    }

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
            "atletico mineiro",
        ),
        (
            &[
                "clube atletico paranaense",
                "atletico paranaense",
                "athletico paranaense",
            ][..],
            "athletico paranaense",
        ),
        (&["atletico goianiense"][..], "atletico goianiense"),
        (&["america mineiro"][..], "america mineiro"),
        (&["esporte clube bahia", "ec bahia"][..], "bahia"),
        (
            &["fortaleza esporte clube", "fortaleza fc"][..],
            "fortaleza",
        ),
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
    team_key(candidate) == team_key(query)
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
    fn preserves_distinct_clubs_while_joining_real_aliases() {
        assert_eq!(team_key("Atletico-MG"), team_key("Atlético Mineiro"));
        assert_eq!(team_key("Atletico-PR"), team_key("Athletico Paranaense"));
        assert_ne!(team_key("Atletico-MG"), team_key("Atletico-PR"));
        assert_ne!(team_key("América-MG"), team_key("América-RN"));
        assert_ne!(team_key("Botafogo-RJ"), team_key("Botafogo-PB"));
        assert_eq!(team_key("EC Bahia"), team_key("Bahia-BA"));
        assert_eq!(team_key("Fortaleza FC"), team_key("Fortaleza-CE"));
    }

    #[test]
    fn accepts_all_documented_date_formats() {
        for date in ["2023-09-24", "2012-05-19 18:30:00", "29/03/2003"] {
            assert!(parse_date(date).is_some(), "failed to parse {date}");
        }
    }
}
