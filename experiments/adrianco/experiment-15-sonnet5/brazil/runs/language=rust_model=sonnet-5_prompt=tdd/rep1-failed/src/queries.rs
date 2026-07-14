use chrono::NaiveDate;

use crate::models::{Competition, Match};
use crate::normalize::team_comparison_key;

/// Matches where `team` played either at home or away, in chronological order.
pub fn matches_by_team<'a>(matches: &'a [Match], team: &str) -> Vec<&'a Match> {
    let key = team_comparison_key(team);
    let mut results: Vec<&Match> = matches
        .iter()
        .filter(|m| team_comparison_key(&m.home_team) == key || team_comparison_key(&m.away_team) == key)
        .collect();
    results.sort_by_key(|m| m.date);
    results
}

/// Matches with a known date within `[start, end]` inclusive.
pub fn matches_by_date_range(matches: &[Match], start: NaiveDate, end: NaiveDate) -> Vec<&Match> {
    matches
        .iter()
        .filter(|m| matches!(m.date, Some(d) if d >= start && d <= end))
        .collect()
}

pub fn matches_by_competition<'a>(
    matches: &'a [Match],
    competition: &Competition,
) -> Vec<&'a Match> {
    matches.iter().filter(|m| &m.competition == competition).collect()
}

pub fn matches_by_season(matches: &[Match], season: i32) -> Vec<&Match> {
    matches.iter().filter(|m| m.season == season).collect()
}

#[derive(Debug, Clone, PartialEq)]
pub struct HeadToHead<'a> {
    pub wins_a: u32,
    pub wins_b: u32,
    pub draws: u32,
    pub matches: Vec<&'a Match>,
}

/// Head-to-head record between `team_a` and `team_b` across all matches, regardless
/// of which side was home or away in a given fixture.
pub fn head_to_head<'a>(matches: &'a [Match], team_a: &str, team_b: &str) -> HeadToHead<'a> {
    let key_a = team_comparison_key(team_a);
    let key_b = team_comparison_key(team_b);
    let mut relevant: Vec<&Match> = matches
        .iter()
        .filter(|m| {
            let home = team_comparison_key(&m.home_team);
            let away = team_comparison_key(&m.away_team);
            (home == key_a && away == key_b) || (home == key_b && away == key_a)
        })
        .collect();
    relevant.sort_by_key(|m| m.date);

    let mut wins_a = 0;
    let mut wins_b = 0;
    let mut draws = 0;
    for game in &relevant {
        let home_is_a = team_comparison_key(&game.home_team) == key_a;
        if game.home_goal == game.away_goal {
            draws += 1;
        } else if (game.home_goal > game.away_goal) == home_is_a {
            wins_a += 1;
        } else {
            wins_b += 1;
        }
    }

    HeadToHead {
        wins_a,
        wins_b,
        draws,
        matches: relevant,
    }
}

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct TeamRecord {
    pub played: u32,
    pub wins: u32,
    pub draws: u32,
    pub losses: u32,
    pub goals_for: u32,
    pub goals_against: u32,
}

impl TeamRecord {
    pub fn points(&self) -> u32 {
        self.wins * 3 + self.draws
    }

    pub fn goal_difference(&self) -> i64 {
        self.goals_for as i64 - self.goals_against as i64
    }

    pub fn win_rate(&self) -> f64 {
        if self.played == 0 {
            0.0
        } else {
            self.wins as f64 / self.played as f64
        }
    }
}

/// Aggregate record for `team`, optionally restricted to a single `season`, a single
/// `competition`, and/or to only home matches (`Some(true)`) or only away matches
/// (`Some(false)`).
pub fn team_record(
    matches: &[Match],
    team: &str,
    season: Option<i32>,
    competition: Option<&Competition>,
    home_only: Option<bool>,
) -> TeamRecord {
    let key = team_comparison_key(team);
    let mut record = TeamRecord::default();
    for game in matches {
        if let Some(s) = season {
            if game.season != s {
                continue;
            }
        }
        if let Some(c) = competition {
            if &game.competition != c {
                continue;
            }
        }
        let is_home = team_comparison_key(&game.home_team) == key;
        let is_away = team_comparison_key(&game.away_team) == key;
        if !is_home && !is_away {
            continue;
        }
        match home_only {
            Some(true) if !is_home => continue,
            Some(false) if !is_away => continue,
            _ => {}
        }

        let (goals_for, goals_against) = if is_home {
            (game.home_goal, game.away_goal)
        } else {
            (game.away_goal, game.home_goal)
        };
        record.played += 1;
        record.goals_for += goals_for;
        record.goals_against += goals_against;
        match goals_for.cmp(&goals_against) {
            std::cmp::Ordering::Greater => record.wins += 1,
            std::cmp::Ordering::Equal => record.draws += 1,
            std::cmp::Ordering::Less => record.losses += 1,
        }
    }
    record
}

#[derive(Debug, Clone, PartialEq)]
pub struct StandingRow {
    pub team: String,
    pub played: u32,
    pub wins: u32,
    pub draws: u32,
    pub losses: u32,
    pub goals_for: u32,
    pub goals_against: u32,
    pub goal_difference: i64,
    pub points: u32,
}

/// League table for `competition`/`season`, computed from match results and sorted
/// by points, then goal difference, then goals for (descending).
pub fn standings(matches: &[Match], competition: &Competition, season: i32) -> Vec<StandingRow> {
    let relevant: Vec<&Match> = matches
        .iter()
        .filter(|m| &m.competition == competition && m.season == season)
        .collect();

    let mut teams: Vec<String> = Vec::new();
    for game in &relevant {
        if !teams.iter().any(|t| team_comparison_key(t) == team_comparison_key(&game.home_team)) {
            teams.push(game.home_team.clone());
        }
        if !teams.iter().any(|t| team_comparison_key(t) == team_comparison_key(&game.away_team)) {
            teams.push(game.away_team.clone());
        }
    }

    let mut table: Vec<StandingRow> = teams
        .into_iter()
        .map(|team| {
            let record = team_record(matches, &team, Some(season), Some(competition), None);
            StandingRow {
                team,
                played: record.played,
                wins: record.wins,
                draws: record.draws,
                losses: record.losses,
                goals_for: record.goals_for,
                goals_against: record.goals_against,
                goal_difference: record.goal_difference(),
                points: record.points(),
            }
        })
        .filter(|row| row.played > 0)
        .collect();

    table.sort_by(|a, b| {
        b.points
            .cmp(&a.points)
            .then(b.goal_difference.cmp(&a.goal_difference))
            .then(b.goals_for.cmp(&a.goals_for))
            .then(a.team.cmp(&b.team))
    });
    table
}

/// The `limit` matches with the largest goal difference, largest first.
pub fn biggest_wins(matches: &[Match], limit: usize) -> Vec<&Match> {
    let mut ranked: Vec<&Match> = matches.iter().collect();
    ranked.sort_by_key(|m| {
        std::cmp::Reverse((m.home_goal as i64 - m.away_goal as i64).abs())
    });
    ranked.truncate(limit);
    ranked
}

pub fn average_goals_per_match(matches: &[Match]) -> f64 {
    if matches.is_empty() {
        return 0.0;
    }
    let total: u64 = matches.iter().map(|m| (m.home_goal + m.away_goal) as u64).sum();
    total as f64 / matches.len() as f64
}

/// Fraction of matches won by the home side (draws and away wins are not counted).
pub fn home_win_rate(matches: &[Match]) -> f64 {
    if matches.is_empty() {
        return 0.0;
    }
    let home_wins = matches.iter().filter(|m| m.home_goal > m.away_goal).count();
    home_wins as f64 / matches.len() as f64
}

use crate::models::Player;

pub fn players_by_name<'a>(players: &'a [Player], query: &str) -> Vec<&'a Player> {
    let query = query.to_lowercase();
    players
        .iter()
        .filter(|p| p.name.to_lowercase().contains(&query))
        .collect()
}

pub fn players_by_nationality<'a>(players: &'a [Player], nationality: &str) -> Vec<&'a Player> {
    let nationality = nationality.to_lowercase();
    players
        .iter()
        .filter(|p| p.nationality.to_lowercase() == nationality)
        .collect()
}

pub fn players_by_club<'a>(players: &'a [Player], club: &str) -> Vec<&'a Player> {
    let club = club.to_lowercase();
    players
        .iter()
        .filter(|p| p.club.as_deref().is_some_and(|c| c.to_lowercase().contains(&club)))
        .collect()
}

/// Top `limit` players by FIFA overall rating (highest first), optionally filtered by
/// nationality and/or a substring match on club.
pub fn top_rated_players<'a>(
    players: &'a [Player],
    nationality: Option<&str>,
    club: Option<&str>,
    limit: usize,
) -> Vec<&'a Player> {
    let mut filtered: Vec<&Player> = players
        .iter()
        .filter(|p| {
            nationality.is_none_or(|n| p.nationality.eq_ignore_ascii_case(n))
                && club.is_none_or(|c| {
                    p.club
                        .as_deref()
                        .is_some_and(|pc| pc.to_lowercase().contains(&c.to_lowercase()))
                })
        })
        .collect();
    filtered.sort_by_key(|p| std::cmp::Reverse(p.overall.unwrap_or(0)));
    filtered.truncate(limit);
    filtered
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::models::{Competition, Match, Player};
    use chrono::NaiveDate;

    fn m(
        date: (i32, u32, u32),
        competition: Competition,
        season: i32,
        home_team: &str,
        away_team: &str,
        home_goal: u32,
        away_goal: u32,
    ) -> Match {
        Match {
            date: NaiveDate::from_ymd_opt(date.0, date.1, date.2),
            competition,
            season,
            round: None,
            stage: None,
            home_team: home_team.to_string(),
            away_team: away_team.to_string(),
            home_goal,
            away_goal,
            venue: None,
            source: "test",
        }
    }

    fn sample_matches() -> Vec<Match> {
        vec![
            m(
                (2023, 5, 28),
                Competition::BrasileiraoSerieA,
                2023,
                "Fluminense",
                "Flamengo",
                1,
                0,
            ),
            m(
                (2023, 9, 3),
                Competition::BrasileiraoSerieA,
                2023,
                "Flamengo",
                "Fluminense",
                2,
                1,
            ),
            m(
                (2023, 4, 1),
                Competition::BrasileiraoSerieA,
                2023,
                "Palmeiras",
                "Santos",
                3,
                0,
            ),
            m(
                (2022, 4, 1),
                Competition::CopaDoBrasil,
                2022,
                "Palmeiras",
                "Santos",
                1,
                1,
            ),
        ]
    }

    #[test]
    fn finds_matches_by_team_on_either_side() {
        let matches = sample_matches();
        let results = matches_by_team(&matches, "Flamengo");
        assert_eq!(results.len(), 2);
    }

    #[test]
    fn filters_matches_by_date_range() {
        let matches = sample_matches();
        let start = NaiveDate::from_ymd_opt(2023, 1, 1).unwrap();
        let end = NaiveDate::from_ymd_opt(2023, 12, 31).unwrap();
        let results = matches_by_date_range(&matches, start, end);
        assert_eq!(results.len(), 3);
    }

    #[test]
    fn filters_matches_by_competition() {
        let matches = sample_matches();
        let results = matches_by_competition(&matches, &Competition::CopaDoBrasil);
        assert_eq!(results.len(), 1);
    }

    #[test]
    fn filters_matches_by_season() {
        let matches = sample_matches();
        let results = matches_by_season(&matches, 2023);
        assert_eq!(results.len(), 3);
    }

    #[test]
    fn computes_head_to_head_record() {
        let matches = sample_matches();
        let h2h = head_to_head(&matches, "Flamengo", "Fluminense");
        assert_eq!(h2h.matches.len(), 2);
        assert_eq!(h2h.wins_a, 1);
        assert_eq!(h2h.wins_b, 1);
        assert_eq!(h2h.draws, 0);
    }

    #[test]
    fn computes_team_record_across_home_and_away() {
        let matches = sample_matches();
        // Flamengo: away loss 0-1 vs Fluminense, home win 2-1 vs Fluminense.
        let record = team_record(&matches, "Flamengo", None, None, None);
        assert_eq!(record.played, 2);
        assert_eq!(record.wins, 1);
        assert_eq!(record.draws, 0);
        assert_eq!(record.losses, 1);
        assert_eq!(record.goals_for, 2);
        assert_eq!(record.goals_against, 2);
    }

    #[test]
    fn team_record_can_filter_to_home_matches_only() {
        let matches = sample_matches();
        let record = team_record(&matches, "Flamengo", None, None, Some(true));
        assert_eq!(record.played, 1);
        assert_eq!(record.wins, 1);
    }

    #[test]
    fn team_record_can_filter_by_season_and_competition() {
        let matches = sample_matches();
        let record = team_record(&matches, "Palmeiras", Some(2022), None, None);
        assert_eq!(record.played, 1);
        assert_eq!(record.draws, 1);
    }

    #[test]
    fn computes_standings_sorted_by_points_then_goal_difference() {
        let matches = sample_matches();
        let table = standings(&matches, &Competition::BrasileiraoSerieA, 2023);
        assert_eq!(table.len(), 4);
        // Palmeiras: 1W (3 pts), goal difference +3 - tops the table despite one match played.
        assert_eq!(table[0].team, "Palmeiras");
        assert_eq!(table[0].points, 3);
        assert_eq!(table[0].goal_difference, 3);
        // Santos: 1L (0 pts), goal difference -3 - bottom of the table.
        assert_eq!(table[3].team, "Santos");
        assert_eq!(table[3].points, 0);
        // Flamengo and Fluminense are tied on points (3) and goal difference (0).
        let middle: std::collections::HashSet<&str> =
            table[1..3].iter().map(|s| s.team.as_str()).collect();
        assert_eq!(
            middle,
            std::collections::HashSet::from(["Flamengo", "Fluminense"])
        );
    }

    #[test]
    fn ranks_biggest_wins_by_goal_difference_descending() {
        let matches = sample_matches();
        let biggest = biggest_wins(&matches, 2);
        assert_eq!(biggest.len(), 2);
        // Palmeiras 3-0 Santos (GD 3) is the biggest margin in the sample data.
        assert_eq!(biggest[0].home_team, "Palmeiras");
    }

    #[test]
    fn computes_average_goals_per_match() {
        let matches = sample_matches();
        // Goals per match: 1, 3, 3, 2 -> average 2.25
        let avg = average_goals_per_match(&matches);
        assert!((avg - 2.25).abs() < 1e-9);
    }

    #[test]
    fn computes_home_win_rate() {
        let matches = sample_matches();
        // Home wins: Fluminense 1-0, Flamengo 2-1, Palmeiras 3-0 = 3 of 4 matches.
        let rate = home_win_rate(&matches);
        assert!((rate - 0.75).abs() < 1e-9);
    }

    fn p(name: &str, nationality: &str, club: Option<&str>, overall: Option<u32>) -> Player {
        Player {
            id: 1,
            name: name.to_string(),
            age: Some(25),
            nationality: nationality.to_string(),
            overall,
            potential: None,
            club: club.map(|c| c.to_string()),
            position: None,
            jersey_number: None,
            height: None,
            weight: None,
        }
    }

    fn sample_players() -> Vec<Player> {
        vec![
            p("Gabriel Barbosa", "Brazil", Some("Flamengo"), Some(79)),
            p("Neymar Jr", "Brazil", Some("Paris Saint-Germain"), Some(92)),
            p("L. Messi", "Argentina", Some("FC Barcelona"), Some(94)),
            p("Everton Ribeiro", "Brazil", Some("Flamengo"), Some(76)),
        ]
    }

    #[test]
    fn finds_players_by_case_insensitive_partial_name() {
        let players = sample_players();
        let results = players_by_name(&players, "neymar");
        assert_eq!(results.len(), 1);
        assert_eq!(results[0].name, "Neymar Jr");
    }

    #[test]
    fn finds_players_by_nationality() {
        let players = sample_players();
        let results = players_by_nationality(&players, "Brazil");
        assert_eq!(results.len(), 3);
    }

    #[test]
    fn finds_players_by_club_substring() {
        let players = sample_players();
        let results = players_by_club(&players, "Flamengo");
        assert_eq!(results.len(), 2);
    }

    #[test]
    fn ranks_top_rated_players_by_overall_descending() {
        let players = sample_players();
        let top = top_rated_players(&players, Some("Brazil"), None, 2);
        assert_eq!(top.len(), 2);
        assert_eq!(top[0].name, "Neymar Jr");
        assert_eq!(top[1].name, "Gabriel Barbosa");
    }
}
