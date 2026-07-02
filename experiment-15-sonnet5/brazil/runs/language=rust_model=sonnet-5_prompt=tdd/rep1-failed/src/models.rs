use chrono::NaiveDate;

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub enum Competition {
    BrasileiraoSerieA,
    BrasileiraoSerieB,
    BrasileiraoSerieC,
    CopaDoBrasil,
    Libertadores,
    Other(String),
}

impl std::fmt::Display for Competition {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        let s = match self {
            Competition::BrasileiraoSerieA => "Brasileirao Serie A",
            Competition::BrasileiraoSerieB => "Brasileirao Serie B",
            Competition::BrasileiraoSerieC => "Brasileirao Serie C",
            Competition::CopaDoBrasil => "Copa do Brasil",
            Competition::Libertadores => "Copa Libertadores",
            Competition::Other(name) => name,
        };
        write!(f, "{s}")
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct Match {
    pub date: Option<NaiveDate>,
    pub competition: Competition,
    pub season: i32,
    pub round: Option<String>,
    pub stage: Option<String>,
    pub home_team: String,
    pub away_team: String,
    pub home_goal: u32,
    pub away_goal: u32,
    pub venue: Option<String>,
    pub source: &'static str,
}

#[derive(Debug, Clone, PartialEq)]
pub struct Player {
    pub id: i64,
    pub name: String,
    pub age: Option<u32>,
    pub nationality: String,
    pub overall: Option<u32>,
    pub potential: Option<u32>,
    pub club: Option<String>,
    pub position: Option<String>,
    pub jersey_number: Option<u32>,
    pub height: Option<String>,
    pub weight: Option<String>,
}

/// Parses a human-friendly competition name (as an LLM caller might type it) into a
/// `Competition`. Case-insensitive; returns `None` for anything unrecognized.
pub fn parse_competition(name: &str) -> Option<Competition> {
    match name.trim().to_lowercase().as_str() {
        "brasileirao" | "brasileirão" | "serie a" | "série a" | "brasileirao serie a" => {
            Some(Competition::BrasileiraoSerieA)
        }
        "serie b" | "série b" => Some(Competition::BrasileiraoSerieB),
        "serie c" | "série c" => Some(Competition::BrasileiraoSerieC),
        "copa do brasil" | "copa" => Some(Competition::CopaDoBrasil),
        "libertadores" | "copa libertadores" => Some(Competition::Libertadores),
        _ => None,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_known_competition_names_case_insensitively() {
        assert_eq!(
            parse_competition("Brasileirao"),
            Some(Competition::BrasileiraoSerieA)
        );
        assert_eq!(
            parse_competition("copa do brasil"),
            Some(Competition::CopaDoBrasil)
        );
        assert_eq!(
            parse_competition("LIBERTADORES"),
            Some(Competition::Libertadores)
        );
    }

    #[test]
    fn returns_none_for_unrecognized_competition_names() {
        assert_eq!(parse_competition("premier league"), None);
    }
}
