//! Query engine.
//!
//! Pure functions over a [`Database`] implementing the five capability groups
//! from the specification: match queries, team queries, player queries,
//! competition standings and aggregate statistics. Team names are matched via
//! [`normalize::normalize_key`] so any naming convention in the data or the
//! user's question resolves to the same club.

use crate::data::Database;
use crate::models::{Competition, Match, Outcome, Player};
use crate::normalize;
use serde::Serialize;
use std::collections::HashMap;

/// Criteria for [`find_matches`]. All set fields must hold (logical AND).
#[derive(Debug, Default, Clone)]
pub struct MatchFilter {
    /// Primary team (matches home or away unless restricted).
    pub team: Option<String>,
    /// Restrict to matches against this opponent.
    pub opponent: Option<String>,
    pub home_only: bool,
    pub away_only: bool,
    pub competition: Option<Competition>,
    pub season: Option<i32>,
    /// Inclusive ISO `YYYY-MM-DD` lower bound.
    pub date_from: Option<String>,
    /// Inclusive ISO `YYYY-MM-DD` upper bound.
    pub date_to: Option<String>,
    pub limit: Option<usize>,
}

/// Return matches satisfying `filter`, most recent first.
pub fn find_matches(db: &Database, filter: &MatchFilter) -> Vec<Match> {
    let team_key = filter.team.as_deref().map(normalize::normalize_key);
    let opp_key = filter.opponent.as_deref().map(normalize::normalize_key);

    let mut out: Vec<Match> = db
        .matches
        .iter()
        .filter(|m| {
            if let Some(ref tk) = team_key {
                let ok = if filter.home_only {
                    &m.home_key() == tk
                } else if filter.away_only {
                    &m.away_key() == tk
                } else {
                    m.involves(tk)
                };
                if !ok {
                    return false;
                }
            }
            if let Some(ref ok) = opp_key {
                if !m.involves(ok) {
                    return false;
                }
                // When both team and opponent are set they must be distinct sides.
                if let Some(ref tk) = team_key {
                    let other = if &m.home_key() == tk {
                        m.away_key()
                    } else {
                        m.home_key()
                    };
                    if &other != ok {
                        return false;
                    }
                }
            }
            if let Some(ref c) = filter.competition {
                if &m.competition != c {
                    return false;
                }
            }
            if let Some(s) = filter.season {
                if m.season != s {
                    return false;
                }
            }
            if let Some(ref from) = filter.date_from {
                match &m.date {
                    Some(d) if d >= from => {}
                    _ => return false,
                }
            }
            if let Some(ref to) = filter.date_to {
                match &m.date {
                    Some(d) if d <= to => {}
                    _ => return false,
                }
            }
            true
        })
        .cloned()
        .collect();

    // Most recent first; matches without a date sort last.
    out.sort_by(|a, b| b.date.cmp(&a.date));
    if let Some(limit) = filter.limit {
        out.truncate(limit);
    }
    out
}

/// Head-to-head summary between two teams.
#[derive(Debug, Serialize, PartialEq)]
pub struct HeadToHead {
    pub team_a: String,
    pub team_b: String,
    pub team_a_wins: u32,
    pub team_b_wins: u32,
    pub draws: u32,
    pub total: u32,
    pub team_a_goals: u32,
    pub team_b_goals: u32,
}

/// Compute the all-competitions head-to-head record between two teams.
pub fn head_to_head(db: &Database, team_a: &str, team_b: &str) -> HeadToHead {
    let ka = normalize::normalize_key(team_a);
    let kb = normalize::normalize_key(team_b);
    let mut h = HeadToHead {
        team_a: display_for(db, &ka).unwrap_or_else(|| team_a.to_string()),
        team_b: display_for(db, &kb).unwrap_or_else(|| team_b.to_string()),
        team_a_wins: 0,
        team_b_wins: 0,
        draws: 0,
        total: 0,
        team_a_goals: 0,
        team_b_goals: 0,
    };
    for m in &db.matches {
        let (hk, ak) = (m.home_key(), m.away_key());
        let involves_pair = (hk == ka && ak == kb) || (hk == kb && ak == ka);
        if !involves_pair {
            continue;
        }
        h.total += 1;
        let (a_goals, b_goals) = if hk == ka {
            (m.home_goal, m.away_goal)
        } else {
            (m.away_goal, m.home_goal)
        };
        h.team_a_goals += a_goals;
        h.team_b_goals += b_goals;
        match a_goals.cmp(&b_goals) {
            std::cmp::Ordering::Greater => h.team_a_wins += 1,
            std::cmp::Ordering::Less => h.team_b_wins += 1,
            std::cmp::Ordering::Equal => h.draws += 1,
        }
    }
    h
}

/// A team's win/draw/loss and goal record over a set of matches.
#[derive(Debug, Serialize, PartialEq, Clone)]
pub struct TeamRecord {
    pub team: String,
    pub matches: u32,
    pub wins: u32,
    pub draws: u32,
    pub losses: u32,
    pub goals_for: u32,
    pub goals_against: u32,
    pub win_rate: f64,
}

impl TeamRecord {
    fn new(team: String) -> Self {
        TeamRecord {
            team,
            matches: 0,
            wins: 0,
            draws: 0,
            losses: 0,
            goals_for: 0,
            goals_against: 0,
            win_rate: 0.0,
        }
    }

    fn add(&mut self, gf: u32, ga: u32) {
        self.matches += 1;
        self.goals_for += gf;
        self.goals_against += ga;
        match gf.cmp(&ga) {
            std::cmp::Ordering::Greater => self.wins += 1,
            std::cmp::Ordering::Less => self.losses += 1,
            std::cmp::Ordering::Equal => self.draws += 1,
        }
    }

    fn finalize(&mut self) {
        self.win_rate = if self.matches == 0 {
            0.0
        } else {
            self.wins as f64 / self.matches as f64
        };
    }
}

/// Compute a single team's record, honoring the team/competition/season and
/// home/away restrictions on `filter`.
pub fn team_record(db: &Database, filter: &MatchFilter) -> TeamRecord {
    let key = filter
        .team
        .as_deref()
        .map(normalize::normalize_key)
        .unwrap_or_default();
    let display = display_for(db, &key).unwrap_or_else(|| filter.team.clone().unwrap_or_default());
    let mut rec = TeamRecord::new(display);
    for m in find_matches(db, filter) {
        if m.home_key() == key {
            rec.add(m.home_goal, m.away_goal);
        } else {
            rec.add(m.away_goal, m.home_goal);
        }
    }
    rec.finalize();
    rec
}

/// A row in a calculated league table.
#[derive(Debug, Serialize, PartialEq, Clone)]
pub struct StandingRow {
    pub rank: usize,
    pub team: String,
    pub played: u32,
    pub wins: u32,
    pub draws: u32,
    pub losses: u32,
    pub goals_for: u32,
    pub goals_against: u32,
    pub goal_difference: i32,
    pub points: u32,
}

/// Calculate the final league table for a competition season (3pts win, 1 draw),
/// ordered by points, then goal difference, then goals scored, then name.
pub fn standings(db: &Database, competition: &Competition, season: i32) -> Vec<StandingRow> {
    let mut table: HashMap<String, StandingRow> = HashMap::new();
    for m in &db.matches {
        if &m.competition != competition || m.season != season {
            continue;
        }
        for (team, gf, ga) in [
            (&m.home_team, m.home_goal, m.away_goal),
            (&m.away_team, m.away_goal, m.home_goal),
        ] {
            let key = normalize::normalize_key(team);
            let row = table.entry(key).or_insert_with(|| StandingRow {
                rank: 0,
                team: team.clone(),
                played: 0,
                wins: 0,
                draws: 0,
                losses: 0,
                goals_for: 0,
                goals_against: 0,
                goal_difference: 0,
                points: 0,
            });
            row.played += 1;
            row.goals_for += gf;
            row.goals_against += ga;
            match gf.cmp(&ga) {
                std::cmp::Ordering::Greater => {
                    row.wins += 1;
                    row.points += 3;
                }
                std::cmp::Ordering::Equal => {
                    row.draws += 1;
                    row.points += 1;
                }
                std::cmp::Ordering::Less => row.losses += 1,
            }
        }
    }
    let mut rows: Vec<StandingRow> = table.into_values().collect();
    for r in &mut rows {
        r.goal_difference = r.goals_for as i32 - r.goals_against as i32;
    }
    rows.sort_by(|a, b| {
        b.points
            .cmp(&a.points)
            .then(b.goal_difference.cmp(&a.goal_difference))
            .then(b.goals_for.cmp(&a.goals_for))
            .then(a.team.cmp(&b.team))
    });
    for (i, r) in rows.iter_mut().enumerate() {
        r.rank = i + 1;
    }
    rows
}

/// Criteria for [`find_players`].
#[derive(Debug, Default, Clone)]
pub struct PlayerFilter {
    /// Case-insensitive substring on the player's name.
    pub name: Option<String>,
    pub nationality: Option<String>,
    /// Case-insensitive substring on club name.
    pub club: Option<String>,
    /// Case-insensitive substring on position (e.g. "ST", "LW").
    pub position: Option<String>,
    pub min_overall: Option<u32>,
    pub limit: Option<usize>,
}

/// Find players matching `filter`, sorted by overall rating descending.
pub fn find_players(db: &Database, filter: &PlayerFilter) -> Vec<Player> {
    let name = filter.name.as_deref().map(normalize::normalize_key);
    let nat = filter.nationality.as_deref().map(normalize::normalize_key);
    let club = filter.club.as_deref().map(normalize::normalize_key);
    let pos = filter.position.as_deref().map(|s| s.to_ascii_lowercase());

    let mut out: Vec<Player> = db
        .players
        .iter()
        .filter(|p| {
            if let Some(ref n) = name {
                if !normalize::normalize_key(&p.name).contains(n.as_str()) {
                    return false;
                }
            }
            if let Some(ref n) = nat {
                if normalize::normalize_key(&p.nationality) != *n {
                    return false;
                }
            }
            if let Some(ref c) = club {
                if !normalize::normalize_key(&p.club).contains(c.as_str()) {
                    return false;
                }
            }
            if let Some(ref pp) = pos {
                if p.position.to_ascii_lowercase() != *pp {
                    return false;
                }
            }
            if let Some(min) = filter.min_overall {
                if p.overall.unwrap_or(0) < min {
                    return false;
                }
            }
            true
        })
        .cloned()
        .collect();

    out.sort_by(|a, b| {
        b.overall
            .unwrap_or(0)
            .cmp(&a.overall.unwrap_or(0))
            .then(a.name.cmp(&b.name))
    });
    if let Some(limit) = filter.limit {
        out.truncate(limit);
    }
    out
}

/// Aggregate goal statistics over a filtered set of matches.
#[derive(Debug, Serialize, PartialEq)]
pub struct GoalStats {
    pub matches: u32,
    pub total_goals: u32,
    pub average_goals_per_match: f64,
    pub home_wins: u32,
    pub away_wins: u32,
    pub draws: u32,
    pub home_win_rate: f64,
}

/// Compute aggregate goal/result statistics for the matches passing `filter`.
pub fn goal_stats(db: &Database, filter: &MatchFilter) -> GoalStats {
    let matches = find_matches(db, filter);
    let mut stats = GoalStats {
        matches: 0,
        total_goals: 0,
        average_goals_per_match: 0.0,
        home_wins: 0,
        away_wins: 0,
        draws: 0,
        home_win_rate: 0.0,
    };
    for m in &matches {
        stats.matches += 1;
        stats.total_goals += m.total_goals();
        match m.outcome() {
            Outcome::HomeWin => stats.home_wins += 1,
            Outcome::AwayWin => stats.away_wins += 1,
            Outcome::Draw => stats.draws += 1,
        }
    }
    if stats.matches > 0 {
        stats.average_goals_per_match = stats.total_goals as f64 / stats.matches as f64;
        stats.home_win_rate = stats.home_wins as f64 / stats.matches as f64;
    }
    stats
}

/// Return the biggest-margin victories among matches passing `filter`.
pub fn biggest_wins(db: &Database, filter: &MatchFilter, limit: usize) -> Vec<Match> {
    let mut matches = find_matches(db, filter);
    matches.retain(|m| m.margin() > 0);
    matches.sort_by(|a, b| {
        b.margin()
            .cmp(&a.margin())
            .then(b.total_goals().cmp(&a.total_goals()))
            .then(b.date.cmp(&a.date))
    });
    matches.truncate(limit);
    matches
}

/// Rank teams by win rate over the matches passing `filter` (home/away aware).
/// `min_matches` filters out tiny samples. Returns records sorted best-first.
pub fn team_rankings(db: &Database, filter: &MatchFilter, min_matches: u32) -> Vec<TeamRecord> {
    let mut by_team: HashMap<String, TeamRecord> = HashMap::new();
    for m in find_matches(db, filter) {
        // home_only / away_only restrict which side of each match is counted.
        let entries = if filter.home_only {
            vec![(&m.home_team, m.home_goal, m.away_goal)]
        } else if filter.away_only {
            vec![(&m.away_team, m.away_goal, m.home_goal)]
        } else {
            vec![
                (&m.home_team, m.home_goal, m.away_goal),
                (&m.away_team, m.away_goal, m.home_goal),
            ]
        };
        for (team, gf, ga) in entries {
            let key = normalize::normalize_key(team);
            by_team
                .entry(key)
                .or_insert_with(|| TeamRecord::new(team.clone()))
                .add(gf, ga);
        }
    }
    let mut records: Vec<TeamRecord> = by_team
        .into_values()
        .filter(|r| r.matches >= min_matches)
        .map(|mut r| {
            r.finalize();
            r
        })
        .collect();
    records.sort_by(|a, b| {
        b.win_rate
            .partial_cmp(&a.win_rate)
            .unwrap_or(std::cmp::Ordering::Equal)
            .then(b.wins.cmp(&a.wins))
            .then(a.team.cmp(&b.team))
    });
    records
}

/// Find the display name actually used in the data for a normalized key.
fn display_for(db: &Database, key: &str) -> Option<String> {
    db.matches.iter().find_map(|m| {
        if m.home_key() == key {
            Some(m.home_team.clone())
        } else if m.away_key() == key {
            Some(m.away_team.clone())
        } else {
            None
        }
    })
}

/// All distinct competitions a team has appeared in.
pub fn competitions_for_team(db: &Database, team: &str) -> Vec<String> {
    let key = normalize::normalize_key(team);
    let mut comps: Vec<String> = Vec::new();
    for m in &db.matches {
        if m.involves(&key) {
            let name = m.competition.display_name();
            if !comps.contains(&name) {
                comps.push(name);
            }
        }
    }
    comps.sort();
    comps
}

#[cfg(test)]
mod tests {
    use super::*;

    fn m(comp: Competition, h: &str, a: &str, hg: u32, ag: u32, season: i32, date: &str) -> Match {
        Match {
            competition: comp,
            home_team: h.into(),
            away_team: a.into(),
            home_goal: hg,
            away_goal: ag,
            season,
            date: Some(date.into()),
            round: None,
            stage: None,
        }
    }

    fn sample_db() -> Database {
        let mut db = Database::new();
        db.matches = vec![
            m(Competition::Brasileirao, "Flamengo", "Santos", 3, 1, 2019, "2019-05-01"),
            m(Competition::Brasileirao, "Santos", "Flamengo", 0, 2, 2019, "2019-09-01"),
            m(Competition::Brasileirao, "Flamengo", "Palmeiras", 1, 1, 2019, "2019-06-01"),
            m(Competition::Brasileirao, "Palmeiras", "Santos", 2, 0, 2019, "2019-07-01"),
            m(Competition::CopaDoBrasil, "Flamengo", "Santos", 0, 0, 2019, "2019-08-01"),
            m(Competition::Brasileirao, "Santos", "Palmeiras", 4, 0, 2018, "2018-05-01"),
        ];
        db
    }

    #[test]
    fn find_matches_by_team_sorted_recent_first() {
        let db = sample_db();
        let f = MatchFilter {
            team: Some("flamengo".into()),
            ..Default::default()
        };
        let res = find_matches(&db, &f);
        assert_eq!(res.len(), 4);
        // Most recent first.
        assert_eq!(res[0].date.as_deref(), Some("2019-09-01"));
    }

    #[test]
    fn find_matches_team_vs_opponent_and_competition() {
        let db = sample_db();
        let f = MatchFilter {
            team: Some("Flamengo".into()),
            opponent: Some("Santos".into()),
            competition: Some(Competition::Brasileirao),
            ..Default::default()
        };
        let res = find_matches(&db, &f);
        assert_eq!(res.len(), 2);
        assert!(res.iter().all(|m| m.competition == Competition::Brasileirao));
    }

    #[test]
    fn find_matches_home_only_and_season_and_daterange() {
        let db = sample_db();
        let f = MatchFilter {
            team: Some("Flamengo".into()),
            home_only: true,
            season: Some(2019),
            date_from: Some("2019-01-01".into()),
            date_to: Some("2019-12-31".into()),
            ..Default::default()
        };
        let res = find_matches(&db, &f);
        // Flamengo home Brasileirao+cup in 2019: vs Santos (May), vs Palmeiras (Jun), cup vs Santos (Aug)
        assert_eq!(res.len(), 3);
        assert!(res.iter().all(|m| m.home_key() == "flamengo"));
    }

    #[test]
    fn head_to_head_counts_both_directions() {
        let db = sample_db();
        let h = head_to_head(&db, "Flamengo", "Santos");
        // 3 meetings: Fla 3-1 (W), Fla won away 2-0 (W), cup 0-0 (D)
        assert_eq!(h.total, 3);
        assert_eq!(h.team_a_wins, 2);
        assert_eq!(h.team_b_wins, 0);
        assert_eq!(h.draws, 1);
        assert_eq!(h.team_a_goals, 5);
        assert_eq!(h.team_b_goals, 1);
    }

    #[test]
    fn team_record_home_in_competition() {
        let db = sample_db();
        let f = MatchFilter {
            team: Some("Flamengo".into()),
            competition: Some(Competition::Brasileirao),
            season: Some(2019),
            ..Default::default()
        };
        let r = team_record(&db, &f);
        // Brasileirao 2019: home 3-1 W vs Santos, away 0-2 W vs Santos, home 1-1 D vs Palmeiras
        assert_eq!(r.matches, 3);
        assert_eq!(r.wins, 2);
        assert_eq!(r.draws, 1);
        assert_eq!(r.losses, 0);
        assert_eq!(r.goals_for, 6);
        assert_eq!(r.goals_against, 2);
        assert!((r.win_rate - 2.0 / 3.0).abs() < 1e-9);
    }

    #[test]
    fn standings_calculated_and_ranked() {
        let db = sample_db();
        let table = standings(&db, &Competition::Brasileirao, 2019);
        // Flamengo: W,W,D => 7 pts; Palmeiras: D vs Fla, W vs Santos => 4; Santos: L,L,L => 0
        assert_eq!(table[0].team, "Flamengo");
        assert_eq!(table[0].points, 7);
        assert_eq!(table[0].rank, 1);
        assert_eq!(table[1].team, "Palmeiras");
        assert_eq!(table[1].points, 4);
        assert_eq!(table[2].team, "Santos");
        assert_eq!(table[2].points, 0);
        assert_eq!(table[2].goal_difference, -6); // scored 1, conceded 7
    }

    #[test]
    fn goal_stats_aggregate() {
        let db = sample_db();
        let f = MatchFilter {
            competition: Some(Competition::Brasileirao),
            season: Some(2019),
            ..Default::default()
        };
        let s = goal_stats(&db, &f);
        assert_eq!(s.matches, 4);
        assert_eq!(s.total_goals, 3 + 1 + 2 + 2 + 1 + 1); // 10
        assert!((s.average_goals_per_match - 2.5).abs() < 1e-9);
        assert_eq!(s.home_wins, 2); // Fla 3-1, Palmeiras 2-0
        assert_eq!(s.away_wins, 1); // Fla 2-0 at Santos
        assert_eq!(s.draws, 1);
    }

    #[test]
    fn biggest_wins_sorted_by_margin() {
        let db = sample_db();
        let f = MatchFilter::default();
        let res = biggest_wins(&db, &f, 2);
        assert_eq!(res.len(), 2);
        assert_eq!(res[0].margin(), 4); // Santos 4-0 Palmeiras (2018)
        assert!(res[1].margin() <= res[0].margin());
    }

    #[test]
    fn team_rankings_best_win_rate() {
        let db = sample_db();
        let f = MatchFilter {
            competition: Some(Competition::Brasileirao),
            season: Some(2019),
            ..Default::default()
        };
        let ranks = team_rankings(&db, &f, 1);
        assert_eq!(ranks[0].team, "Flamengo");
        assert!(ranks[0].win_rate >= ranks[1].win_rate);
    }

    #[test]
    fn competitions_for_team_lists_distinct() {
        let db = sample_db();
        let comps = competitions_for_team(&db, "Flamengo");
        assert!(comps.contains(&"Brasileirão".to_string()));
        assert!(comps.contains(&"Copa do Brasil".to_string()));
        assert_eq!(comps.len(), 2);
    }

    fn player(id: u64, name: &str, nat: &str, club: &str, pos: &str, ovr: u32) -> Player {
        Player {
            id,
            name: name.into(),
            age: Some(27),
            nationality: nat.into(),
            overall: Some(ovr),
            potential: Some(ovr),
            club: club.into(),
            position: pos.into(),
        }
    }

    fn player_db() -> Database {
        let mut db = Database::new();
        db.players = vec![
            player(1, "Neymar Jr", "Brazil", "Paris Saint-Germain", "LW", 92),
            player(2, "Gabriel Barbosa", "Brazil", "Flamengo", "ST", 80),
            player(3, "L. Messi", "Argentina", "FC Barcelona", "RW", 94),
            player(4, "Bruno Henrique", "Brazil", "Flamengo", "LW", 78),
        ];
        db
    }

    #[test]
    fn find_players_by_name_substring() {
        let db = player_db();
        let res = find_players(&db, &PlayerFilter {
            name: Some("gabriel".into()),
            ..Default::default()
        });
        assert_eq!(res.len(), 1);
        assert_eq!(res[0].name, "Gabriel Barbosa");
    }

    #[test]
    fn find_players_by_nationality_sorted_by_overall() {
        let db = player_db();
        let res = find_players(&db, &PlayerFilter {
            nationality: Some("Brazil".into()),
            ..Default::default()
        });
        assert_eq!(res.len(), 3);
        assert_eq!(res[0].name, "Neymar Jr"); // highest overall first
        assert!(res[0].overall >= res[1].overall);
    }

    #[test]
    fn find_players_by_club_and_min_overall() {
        let db = player_db();
        let res = find_players(&db, &PlayerFilter {
            club: Some("Flamengo".into()),
            min_overall: Some(79),
            ..Default::default()
        });
        assert_eq!(res.len(), 1);
        assert_eq!(res[0].name, "Gabriel Barbosa");
    }

    #[test]
    fn find_players_by_position_and_limit() {
        let db = player_db();
        let res = find_players(&db, &PlayerFilter {
            position: Some("LW".into()),
            limit: Some(1),
            ..Default::default()
        });
        assert_eq!(res.len(), 1);
        assert_eq!(res[0].name, "Neymar Jr");
    }
}
