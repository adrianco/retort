use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum Competition {
    Brasileirao,
    CopaDoBrasil,
    Libertadores,
    Extended,
    Historical,
}

impl Competition {
    pub fn display_name(&self) -> &str {
        match self {
            Competition::Brasileirao => "Brasileirão Serie A",
            Competition::CopaDoBrasil => "Copa do Brasil",
            Competition::Libertadores => "Copa Libertadores",
            Competition::Extended => "BR Football (Extended)",
            Competition::Historical => "Brasileirão (Historical)",
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Match {
    pub competition: Competition,
    pub datetime: String,
    pub home_team: String,
    pub away_team: String,
    pub home_goal: u32,
    pub away_goal: u32,
    pub season: u32,
    pub round: Option<String>,
    pub stage: Option<String>,
    pub arena: Option<String>,
}

impl Match {
    pub fn result_str(&self) -> String {
        format!("{} {}-{} {}", self.home_team, self.home_goal, self.away_goal, self.away_team)
    }

    pub fn winner(&self) -> Option<&str> {
        if self.home_goal > self.away_goal {
            Some(&self.home_team)
        } else if self.away_goal > self.home_goal {
            Some(&self.away_team)
        } else {
            None
        }
    }

    pub fn involves_team(&self, team: &str) -> bool {
        let norm = normalize_team_name(team);
        normalize_team_name(&self.home_team).contains(&norm)
            || normalize_team_name(&self.away_team).contains(&norm)
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Player {
    pub id: u64,
    pub name: String,
    pub age: u32,
    pub nationality: String,
    pub overall: u32,
    pub potential: u32,
    pub club: String,
    pub position: String,
    pub jersey_number: Option<u32>,
    pub height: String,
    pub weight: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct TeamStats {
    pub team: String,
    pub matches: u32,
    pub wins: u32,
    pub draws: u32,
    pub losses: u32,
    pub goals_for: u32,
    pub goals_against: u32,
}

impl TeamStats {
    pub fn points(&self) -> u32 {
        self.wins * 3 + self.draws
    }

    pub fn goal_difference(&self) -> i32 {
        self.goals_for as i32 - self.goals_against as i32
    }

    pub fn win_rate(&self) -> f64 {
        if self.matches == 0 {
            0.0
        } else {
            self.wins as f64 / self.matches as f64 * 100.0
        }
    }
}

/// Normalize a team name by removing state suffixes and lowercasing.
pub fn normalize_team_name(name: &str) -> String {
    // Remove state suffixes like "-SP", "-RJ", " - RJ", " (RJ)", etc.
    let name = name.trim();

    // Remove " - STATE" patterns (with spaces around dash)
    let name = if let Some(pos) = name.rfind(" - ") {
        let suffix = &name[pos + 3..];
        // Check if the suffix is a 2-char state code or similar
        if suffix.len() <= 5 && suffix.chars().all(|c| c.is_uppercase() || c.is_whitespace()) {
            &name[..pos]
        } else {
            name
        }
    } else {
        name
    };

    // Remove "-STATE" patterns (dash directly attached)
    let normalized = if let Some(dash_pos) = name.rfind('-') {
        let suffix = &name[dash_pos + 1..];
        if suffix.len() == 2 && suffix.chars().all(|c| c.is_uppercase()) {
            name[..dash_pos].trim().to_lowercase()
        } else {
            name.to_lowercase()
        }
    } else {
        name.to_lowercase()
    };

    normalized
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn normalize_removes_state_suffix_dash() {
        assert_eq!(normalize_team_name("Palmeiras-SP"), "palmeiras");
        assert_eq!(normalize_team_name("Flamengo-RJ"), "flamengo");
        assert_eq!(normalize_team_name("Corinthians-SP"), "corinthians");
    }

    #[test]
    fn normalize_removes_state_suffix_space_dash() {
        assert_eq!(normalize_team_name("América - MG"), "américa");
        assert_eq!(normalize_team_name("Vasco - RJ"), "vasco");
    }

    #[test]
    fn normalize_no_suffix_unchanged() {
        assert_eq!(normalize_team_name("Flamengo"), "flamengo");
        assert_eq!(normalize_team_name("Palmeiras"), "palmeiras");
    }

    #[test]
    fn normalize_lowercases() {
        assert_eq!(normalize_team_name("SANTOS"), "santos");
    }

    #[test]
    fn normalize_trims_whitespace() {
        assert_eq!(normalize_team_name("  Flamengo  "), "flamengo");
    }

    #[test]
    fn match_result_str() {
        let m = Match {
            competition: Competition::Brasileirao,
            datetime: "2023-09-03".to_string(),
            home_team: "Flamengo".to_string(),
            away_team: "Fluminense".to_string(),
            home_goal: 2,
            away_goal: 1,
            season: 2023,
            round: Some("22".to_string()),
            stage: None,
            arena: None,
        };
        assert_eq!(m.result_str(), "Flamengo 2-1 Fluminense");
    }

    #[test]
    fn match_winner_home() {
        let m = Match {
            competition: Competition::Brasileirao,
            datetime: "2023-09-03".to_string(),
            home_team: "Flamengo".to_string(),
            away_team: "Fluminense".to_string(),
            home_goal: 2,
            away_goal: 1,
            season: 2023,
            round: None,
            stage: None,
            arena: None,
        };
        assert_eq!(m.winner(), Some("Flamengo"));
    }

    #[test]
    fn match_winner_away() {
        let m = Match {
            competition: Competition::Brasileirao,
            datetime: "2023-09-03".to_string(),
            home_team: "Flamengo".to_string(),
            away_team: "Fluminense".to_string(),
            home_goal: 0,
            away_goal: 2,
            season: 2023,
            round: None,
            stage: None,
            arena: None,
        };
        assert_eq!(m.winner(), Some("Fluminense"));
    }

    #[test]
    fn match_winner_draw() {
        let m = Match {
            competition: Competition::Brasileirao,
            datetime: "2023-09-03".to_string(),
            home_team: "Flamengo".to_string(),
            away_team: "Fluminense".to_string(),
            home_goal: 1,
            away_goal: 1,
            season: 2023,
            round: None,
            stage: None,
            arena: None,
        };
        assert_eq!(m.winner(), None);
    }

    #[test]
    fn match_involves_team_with_suffix() {
        let m = Match {
            competition: Competition::Brasileirao,
            datetime: "2023-09-03".to_string(),
            home_team: "Palmeiras-SP".to_string(),
            away_team: "Flamengo-RJ".to_string(),
            home_goal: 1,
            away_goal: 0,
            season: 2023,
            round: None,
            stage: None,
            arena: None,
        };
        assert!(m.involves_team("Palmeiras"));
        assert!(m.involves_team("Flamengo"));
        assert!(!m.involves_team("Santos"));
    }

    #[test]
    fn team_stats_points() {
        let stats = TeamStats {
            team: "Flamengo".to_string(),
            matches: 10,
            wins: 6,
            draws: 2,
            losses: 2,
            goals_for: 20,
            goals_against: 10,
        };
        assert_eq!(stats.points(), 20);
    }

    #[test]
    fn team_stats_goal_difference() {
        let stats = TeamStats {
            team: "Flamengo".to_string(),
            matches: 10,
            wins: 6,
            draws: 2,
            losses: 2,
            goals_for: 20,
            goals_against: 10,
        };
        assert_eq!(stats.goal_difference(), 10);
    }

    #[test]
    fn team_stats_win_rate() {
        let stats = TeamStats {
            team: "Flamengo".to_string(),
            matches: 4,
            wins: 3,
            draws: 0,
            losses: 1,
            goals_for: 8,
            goals_against: 3,
        };
        assert!((stats.win_rate() - 75.0).abs() < 0.001);
    }

    #[test]
    fn team_stats_win_rate_zero_matches() {
        let stats = TeamStats::default();
        assert_eq!(stats.win_rate(), 0.0);
    }
}
