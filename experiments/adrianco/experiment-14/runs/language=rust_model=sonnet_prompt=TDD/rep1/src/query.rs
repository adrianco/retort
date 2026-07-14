use std::collections::HashMap;

use crate::models::{Competition, Match, Player, TeamStats, normalize_team_name};

pub struct MatchFilter<'a> {
    pub team: Option<&'a str>,
    pub home_team: Option<&'a str>,
    pub away_team: Option<&'a str>,
    pub season: Option<u32>,
    pub competition: Option<Competition>,
    pub date_from: Option<&'a str>,
    pub date_to: Option<&'a str>,
}

impl<'a> Default for MatchFilter<'a> {
    fn default() -> Self {
        MatchFilter {
            team: None,
            home_team: None,
            away_team: None,
            season: None,
            competition: None,
            date_from: None,
            date_to: None,
        }
    }
}

pub fn search_matches<'a>(matches: &'a [Match], filter: &MatchFilter) -> Vec<&'a Match> {
    matches
        .iter()
        .filter(|m| {
            if let Some(team) = filter.team {
                if !m.involves_team(team) {
                    return false;
                }
            }
            if let Some(home) = filter.home_team {
                let norm_home = normalize_team_name(home);
                if !normalize_team_name(&m.home_team).contains(&norm_home) {
                    return false;
                }
            }
            if let Some(away) = filter.away_team {
                let norm_away = normalize_team_name(away);
                if !normalize_team_name(&m.away_team).contains(&norm_away) {
                    return false;
                }
            }
            if let Some(season) = filter.season {
                if m.season != season {
                    return false;
                }
            }
            if let Some(ref comp) = filter.competition {
                if &m.competition != comp {
                    return false;
                }
            }
            if let Some(from) = filter.date_from {
                if m.datetime.as_str() < from {
                    return false;
                }
            }
            if let Some(to) = filter.date_to {
                if m.datetime.as_str() > to {
                    return false;
                }
            }
            true
        })
        .collect()
}

pub fn head_to_head<'a>(matches: &'a [Match], team_a: &str, team_b: &str) -> Vec<&'a Match> {
    let norm_a = normalize_team_name(team_a);
    let norm_b = normalize_team_name(team_b);
    matches
        .iter()
        .filter(|m| {
            let nh = normalize_team_name(&m.home_team);
            let na = normalize_team_name(&m.away_team);
            (nh.contains(&norm_a) && na.contains(&norm_b))
                || (nh.contains(&norm_b) && na.contains(&norm_a))
        })
        .collect()
}

pub fn team_stats(matches: &[Match], team: &str) -> TeamStats {
    let norm = normalize_team_name(team);
    let mut stats = TeamStats {
        team: team.to_string(),
        ..Default::default()
    };

    for m in matches {
        let nh = normalize_team_name(&m.home_team);
        let na = normalize_team_name(&m.away_team);
        let is_home = nh.contains(&norm);
        let is_away = na.contains(&norm);

        if !is_home && !is_away {
            continue;
        }

        stats.matches += 1;
        if is_home {
            stats.goals_for += m.home_goal;
            stats.goals_against += m.away_goal;
            if m.home_goal > m.away_goal {
                stats.wins += 1;
            } else if m.home_goal == m.away_goal {
                stats.draws += 1;
            } else {
                stats.losses += 1;
            }
        } else {
            stats.goals_for += m.away_goal;
            stats.goals_against += m.home_goal;
            if m.away_goal > m.home_goal {
                stats.wins += 1;
            } else if m.away_goal == m.home_goal {
                stats.draws += 1;
            } else {
                stats.losses += 1;
            }
        }
    }

    stats
}

pub fn standings(matches: &[Match]) -> Vec<TeamStats> {
    let mut map: HashMap<String, TeamStats> = HashMap::new();

    for m in matches {
        let home = &m.home_team;
        let away = &m.away_team;

        let home_entry = map.entry(home.clone()).or_insert_with(|| TeamStats {
            team: home.clone(),
            ..Default::default()
        });
        home_entry.matches += 1;
        home_entry.goals_for += m.home_goal;
        home_entry.goals_against += m.away_goal;
        if m.home_goal > m.away_goal {
            home_entry.wins += 1;
        } else if m.home_goal == m.away_goal {
            home_entry.draws += 1;
        } else {
            home_entry.losses += 1;
        }

        let away_entry = map.entry(away.clone()).or_insert_with(|| TeamStats {
            team: away.clone(),
            ..Default::default()
        });
        away_entry.matches += 1;
        away_entry.goals_for += m.away_goal;
        away_entry.goals_against += m.home_goal;
        if m.away_goal > m.home_goal {
            away_entry.wins += 1;
        } else if m.away_goal == m.home_goal {
            away_entry.draws += 1;
        } else {
            away_entry.losses += 1;
        }
    }

    let mut result: Vec<TeamStats> = map.into_values().collect();
    result.sort_by(|a, b| {
        b.points()
            .cmp(&a.points())
            .then(b.goal_difference().cmp(&a.goal_difference()))
            .then(b.goals_for.cmp(&a.goals_for))
    });
    result
}

pub fn search_players<'a>(
    players: &'a [Player],
    name_query: Option<&str>,
    nationality: Option<&str>,
    club_query: Option<&str>,
    min_overall: Option<u32>,
) -> Vec<&'a Player> {
    players
        .iter()
        .filter(|p| {
            if let Some(name) = name_query {
                if !p.name.to_lowercase().contains(&name.to_lowercase()) {
                    return false;
                }
            }
            if let Some(nat) = nationality {
                if !p.nationality.to_lowercase().contains(&nat.to_lowercase()) {
                    return false;
                }
            }
            if let Some(club) = club_query {
                if !p.club.to_lowercase().contains(&club.to_lowercase()) {
                    return false;
                }
            }
            if let Some(min) = min_overall {
                if p.overall < min {
                    return false;
                }
            }
            true
        })
        .collect()
}

pub fn goals_per_match(matches: &[Match]) -> f64 {
    if matches.is_empty() {
        return 0.0;
    }
    let total: u32 = matches.iter().map(|m| m.home_goal + m.away_goal).sum();
    total as f64 / matches.len() as f64
}

pub fn home_win_rate(matches: &[Match]) -> f64 {
    if matches.is_empty() {
        return 0.0;
    }
    let home_wins = matches.iter().filter(|m| m.home_goal > m.away_goal).count();
    home_wins as f64 / matches.len() as f64 * 100.0
}

pub fn biggest_wins(matches: &[Match], n: usize) -> Vec<&Match> {
    let mut with_margin: Vec<(&Match, i32)> = matches
        .iter()
        .map(|m| (m, (m.home_goal as i32 - m.away_goal as i32).abs()))
        .collect();
    with_margin.sort_by(|a, b| b.1.cmp(&a.1));
    with_margin.into_iter().take(n).map(|(m, _)| m).collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::models::Competition;

    fn sample_match(
        home: &str,
        away: &str,
        home_goal: u32,
        away_goal: u32,
        season: u32,
        comp: Competition,
    ) -> Match {
        Match {
            competition: comp,
            datetime: format!("{}-01-01", season),
            home_team: home.to_string(),
            away_team: away.to_string(),
            home_goal,
            away_goal,
            season,
            round: None,
            stage: None,
            arena: None,
        }
    }

    fn sample_player(name: &str, nationality: &str, club: &str, overall: u32) -> Player {
        Player {
            id: 1,
            name: name.to_string(),
            age: 25,
            nationality: nationality.to_string(),
            overall,
            potential: overall,
            club: club.to_string(),
            position: "CF".to_string(),
            jersey_number: Some(10),
            height: "5'11".to_string(),
            weight: "170lbs".to_string(),
        }
    }

    #[test]
    fn search_matches_by_team() {
        let matches = vec![
            sample_match("Flamengo", "Santos", 2, 1, 2022, Competition::Brasileirao),
            sample_match("Palmeiras", "Flamengo", 0, 0, 2022, Competition::Brasileirao),
            sample_match("Santos", "Corinthians", 1, 0, 2022, Competition::Brasileirao),
        ];
        let filter = MatchFilter {
            team: Some("Flamengo"),
            ..Default::default()
        };
        let result = search_matches(&matches, &filter);
        assert_eq!(result.len(), 2);
    }

    #[test]
    fn search_matches_by_team_with_suffix() {
        let matches = vec![
            sample_match("Palmeiras-SP", "Santos-SP", 1, 0, 2022, Competition::Brasileirao),
            sample_match("Flamengo-RJ", "Palmeiras-SP", 1, 1, 2022, Competition::Brasileirao),
            sample_match("Santos-SP", "Corinthians-SP", 2, 0, 2022, Competition::Brasileirao),
        ];
        let filter = MatchFilter {
            team: Some("Palmeiras"),
            ..Default::default()
        };
        let result = search_matches(&matches, &filter);
        assert_eq!(result.len(), 2);
    }

    #[test]
    fn search_matches_by_season() {
        let matches = vec![
            sample_match("Flamengo", "Santos", 2, 1, 2022, Competition::Brasileirao),
            sample_match("Flamengo", "Santos", 1, 0, 2023, Competition::Brasileirao),
        ];
        let filter = MatchFilter {
            season: Some(2023),
            ..Default::default()
        };
        let result = search_matches(&matches, &filter);
        assert_eq!(result.len(), 1);
        assert_eq!(result[0].season, 2023);
    }

    #[test]
    fn search_matches_by_competition() {
        let matches = vec![
            sample_match("Flamengo", "Santos", 2, 1, 2022, Competition::Brasileirao),
            sample_match("Flamengo", "Santos", 1, 0, 2022, Competition::CopaDoBrasil),
        ];
        let filter = MatchFilter {
            competition: Some(Competition::CopaDoBrasil),
            ..Default::default()
        };
        let result = search_matches(&matches, &filter);
        assert_eq!(result.len(), 1);
        assert_eq!(result[0].competition, Competition::CopaDoBrasil);
    }

    #[test]
    fn head_to_head_finds_both_directions() {
        let matches = vec![
            sample_match("Flamengo", "Fluminense", 2, 1, 2023, Competition::Brasileirao),
            sample_match("Fluminense", "Flamengo", 0, 1, 2023, Competition::Brasileirao),
            sample_match("Santos", "Corinthians", 1, 0, 2023, Competition::Brasileirao),
        ];
        let result = head_to_head(&matches, "Flamengo", "Fluminense");
        assert_eq!(result.len(), 2);
    }

    #[test]
    fn head_to_head_with_suffix() {
        let matches = vec![
            sample_match("Flamengo-RJ", "Fluminense-RJ", 2, 1, 2023, Competition::Brasileirao),
            sample_match("Palmeiras-SP", "Santos-SP", 1, 0, 2023, Competition::Brasileirao),
        ];
        let result = head_to_head(&matches, "Flamengo", "Fluminense");
        assert_eq!(result.len(), 1);
    }

    #[test]
    fn team_stats_calculates_correctly() {
        let matches = vec![
            sample_match("Flamengo", "Santos", 3, 1, 2022, Competition::Brasileirao), // home win
            sample_match("Santos", "Flamengo", 1, 1, 2022, Competition::Brasileirao), // away draw
            sample_match("Flamengo", "Palmeiras", 0, 2, 2022, Competition::Brasileirao), // home loss
        ];
        let stats = team_stats(&matches, "Flamengo");
        assert_eq!(stats.matches, 3);
        assert_eq!(stats.wins, 1);
        assert_eq!(stats.draws, 1);
        assert_eq!(stats.losses, 1);
        assert_eq!(stats.goals_for, 4); // 3 + 1
        assert_eq!(stats.goals_against, 4); // 1 + 1 + 2
    }

    #[test]
    fn team_stats_with_suffix() {
        let matches = vec![
            sample_match("Palmeiras-SP", "Santos-SP", 2, 0, 2022, Competition::Brasileirao),
        ];
        let stats = team_stats(&matches, "Palmeiras");
        assert_eq!(stats.matches, 1);
        assert_eq!(stats.wins, 1);
    }

    #[test]
    fn standings_sorted_by_points() {
        let matches = vec![
            sample_match("Flamengo", "Santos", 3, 0, 2022, Competition::Brasileirao),
            sample_match("Santos", "Palmeiras", 0, 2, 2022, Competition::Brasileirao),
            sample_match("Flamengo", "Palmeiras", 1, 1, 2022, Competition::Brasileirao),
        ];
        let table = standings(&matches);
        // Flamengo: 1W 1D 0L = 4 pts
        // Palmeiras: 1W 1D 0L = 4 pts
        // Santos: 0W 0D 2L = 0 pts
        assert_eq!(table.last().unwrap().team, "Santos");
        assert_eq!(table.last().unwrap().points(), 0);
        let fla = table.iter().find(|t| t.team == "Flamengo").unwrap();
        assert_eq!(fla.wins, 1);
        assert_eq!(fla.draws, 1);
    }

    #[test]
    fn search_players_by_name() {
        let players = vec![
            sample_player("Neymar Jr", "Brazil", "PSG", 92),
            sample_player("Cristiano Ronaldo", "Portugal", "Juventus", 94),
        ];
        let result = search_players(&players, Some("neymar"), None, None, None);
        assert_eq!(result.len(), 1);
        assert_eq!(result[0].name, "Neymar Jr");
    }

    #[test]
    fn search_players_by_nationality() {
        let players = vec![
            sample_player("Neymar Jr", "Brazil", "PSG", 92),
            sample_player("Cristiano Ronaldo", "Portugal", "Juventus", 94),
            sample_player("Casemiro", "Brazil", "Real Madrid", 89),
        ];
        let result = search_players(&players, None, Some("Brazil"), None, None);
        assert_eq!(result.len(), 2);
    }

    #[test]
    fn search_players_by_club() {
        let players = vec![
            sample_player("Player A", "Brazil", "Flamengo", 75),
            sample_player("Player B", "Brazil", "Palmeiras", 72),
            sample_player("Player C", "Argentina", "Flamengo", 78),
        ];
        let result = search_players(&players, None, None, Some("Flamengo"), None);
        assert_eq!(result.len(), 2);
    }

    #[test]
    fn search_players_by_min_overall() {
        let players = vec![
            sample_player("High", "Brazil", "PSG", 90),
            sample_player("Low", "Brazil", "Club", 70),
        ];
        let result = search_players(&players, None, None, None, Some(85));
        assert_eq!(result.len(), 1);
        assert_eq!(result[0].name, "High");
    }

    #[test]
    fn goals_per_match_calculates_average() {
        let matches = vec![
            sample_match("A", "B", 2, 1, 2022, Competition::Brasileirao),
            sample_match("C", "D", 0, 0, 2022, Competition::Brasileirao),
            sample_match("E", "F", 3, 2, 2022, Competition::Brasileirao),
        ];
        let avg = goals_per_match(&matches);
        // (3 + 0 + 5) / 3 = 2.666...
        assert!((avg - 8.0 / 3.0).abs() < 0.001);
    }

    #[test]
    fn goals_per_match_empty() {
        assert_eq!(goals_per_match(&[]), 0.0);
    }

    #[test]
    fn home_win_rate_calculates() {
        let matches = vec![
            sample_match("A", "B", 2, 0, 2022, Competition::Brasileirao), // home win
            sample_match("C", "D", 0, 1, 2022, Competition::Brasileirao), // away win
            sample_match("E", "F", 1, 1, 2022, Competition::Brasileirao), // draw
            sample_match("G", "H", 3, 1, 2022, Competition::Brasileirao), // home win
        ];
        let rate = home_win_rate(&matches);
        assert!((rate - 50.0).abs() < 0.001);
    }

    #[test]
    fn biggest_wins_returns_correct_order() {
        let matches = vec![
            sample_match("A", "B", 1, 0, 2022, Competition::Brasileirao), // margin 1
            sample_match("C", "D", 5, 0, 2022, Competition::Brasileirao), // margin 5
            sample_match("E", "F", 3, 1, 2022, Competition::Brasileirao), // margin 2
        ];
        let big = biggest_wins(&matches, 2);
        assert_eq!(big.len(), 2);
        assert_eq!(big[0].home_team, "C");
        assert_eq!(big[1].home_team, "E");
    }
}
