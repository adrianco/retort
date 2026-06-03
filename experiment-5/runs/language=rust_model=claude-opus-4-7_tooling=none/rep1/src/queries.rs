use std::collections::HashMap;

use chrono::NaiveDate;

use crate::data::{Competition, Match, MatchResult, Player};
use crate::normalize::{normalize_team, team_matches, text_contains};
use crate::store::Store;

#[derive(Debug, Clone, Default)]
pub struct MatchFilter<'a> {
    pub team: Option<&'a str>,
    pub opponent: Option<&'a str>,
    pub competition: Option<Competition>,
    pub season: Option<i32>,
    pub from: Option<NaiveDate>,
    pub to: Option<NaiveDate>,
    pub home_only: bool,
    pub away_only: bool,
}

pub fn search_matches<'a>(store: &'a Store, filter: &MatchFilter<'_>) -> Vec<&'a Match> {
    let team_q = filter.team.map(normalize_team);
    let opp_q = filter.opponent.map(normalize_team);

    store
        .matches
        .iter()
        .filter(|m| {
            if let Some(c) = filter.competition {
                if m.competition != c {
                    return false;
                }
            }
            if let Some(s) = filter.season {
                if m.season != Some(s) {
                    return false;
                }
            }
            if let Some(from) = filter.from {
                if let Some(d) = m.date {
                    if d < from {
                        return false;
                    }
                } else {
                    return false;
                }
            }
            if let Some(to) = filter.to {
                if let Some(d) = m.date {
                    if d > to {
                        return false;
                    }
                } else {
                    return false;
                }
            }
            match (&team_q, &opp_q) {
                (Some(t), Some(o)) => {
                    let t_home = m.home_team_norm.contains(t);
                    let t_away = m.away_team_norm.contains(t);
                    let o_home = m.home_team_norm.contains(o);
                    let o_away = m.away_team_norm.contains(o);
                    if filter.home_only {
                        return t_home && o_away;
                    }
                    if filter.away_only {
                        return t_away && o_home;
                    }
                    (t_home && o_away) || (t_away && o_home)
                }
                (Some(t), None) => {
                    let t_home = m.home_team_norm.contains(t);
                    let t_away = m.away_team_norm.contains(t);
                    if filter.home_only {
                        t_home
                    } else if filter.away_only {
                        t_away
                    } else {
                        t_home || t_away
                    }
                }
                (None, Some(o)) => m.home_team_norm.contains(o) || m.away_team_norm.contains(o),
                (None, None) => true,
            }
        })
        .collect()
}

#[derive(Debug, Default, Clone)]
pub struct TeamStats {
    pub played: u32,
    pub wins: u32,
    pub draws: u32,
    pub losses: u32,
    pub goals_for: i32,
    pub goals_against: i32,
}

impl TeamStats {
    pub fn points(&self) -> i32 {
        (self.wins as i32) * 3 + self.draws as i32
    }

    pub fn goal_diff(&self) -> i32 {
        self.goals_for - self.goals_against
    }

    pub fn win_rate(&self) -> f64 {
        if self.played == 0 {
            0.0
        } else {
            self.wins as f64 / self.played as f64
        }
    }

    pub fn record(&mut self, scored: i32, conceded: i32) {
        self.played += 1;
        self.goals_for += scored;
        self.goals_against += conceded;
        if scored > conceded {
            self.wins += 1;
        } else if scored < conceded {
            self.losses += 1;
        } else {
            self.draws += 1;
        }
    }
}

pub fn team_stats(store: &Store, team: &str, filter: &MatchFilter<'_>) -> TeamStats {
    let team_norm = normalize_team(team);
    if team_norm.is_empty() {
        return TeamStats::default();
    }
    let mut stats = TeamStats::default();
    for m in &store.matches {
        if let Some(c) = filter.competition {
            if m.competition != c {
                continue;
            }
        }
        if let Some(s) = filter.season {
            if m.season != Some(s) {
                continue;
            }
        }
        let home_is_team = m.home_team_norm.contains(&team_norm);
        let away_is_team = m.away_team_norm.contains(&team_norm);
        if !home_is_team && !away_is_team {
            continue;
        }
        if filter.home_only && !home_is_team {
            continue;
        }
        if filter.away_only && !away_is_team {
            continue;
        }
        if home_is_team {
            stats.record(m.home_goal, m.away_goal);
        } else {
            stats.record(m.away_goal, m.home_goal);
        }
    }
    stats
}

#[derive(Debug, Clone, Default)]
pub struct HeadToHead {
    pub team1_wins: u32,
    pub team2_wins: u32,
    pub draws: u32,
    pub team1_goals: i32,
    pub team2_goals: i32,
}

pub fn head_to_head(store: &Store, team1: &str, team2: &str) -> HeadToHead {
    let mut h = HeadToHead::default();
    let t1 = normalize_team(team1);
    let t2 = normalize_team(team2);
    for m in &store.matches {
        let t1_home = m.home_team_norm.contains(&t1);
        let t1_away = m.away_team_norm.contains(&t1);
        let t2_home = m.home_team_norm.contains(&t2);
        let t2_away = m.away_team_norm.contains(&t2);
        let (t1_scored, t2_scored) = if t1_home && t2_away {
            (m.home_goal, m.away_goal)
        } else if t2_home && t1_away {
            (m.away_goal, m.home_goal)
        } else {
            continue;
        };
        h.team1_goals += t1_scored;
        h.team2_goals += t2_scored;
        match t1_scored.cmp(&t2_scored) {
            std::cmp::Ordering::Greater => h.team1_wins += 1,
            std::cmp::Ordering::Less => h.team2_wins += 1,
            std::cmp::Ordering::Equal => h.draws += 1,
        }
    }
    h
}

#[derive(Debug, Clone)]
pub struct StandingsRow {
    pub team: String,
    pub stats: TeamStats,
}

pub fn season_standings(
    store: &Store,
    season: i32,
    competition: Competition,
) -> Vec<StandingsRow> {
    let mut by_team: HashMap<String, (String, TeamStats)> = HashMap::new();
    for m in &store.matches {
        if m.competition != competition {
            continue;
        }
        if m.season != Some(season) {
            continue;
        }
        let entry_home = by_team
            .entry(m.home_team_norm.clone())
            .or_insert_with(|| (m.home_team.clone(), TeamStats::default()));
        entry_home.1.record(m.home_goal, m.away_goal);
        let entry_away = by_team
            .entry(m.away_team_norm.clone())
            .or_insert_with(|| (m.away_team.clone(), TeamStats::default()));
        entry_away.1.record(m.away_goal, m.home_goal);
    }
    let mut rows: Vec<StandingsRow> = by_team
        .into_iter()
        .map(|(_norm, (team, stats))| StandingsRow { team, stats })
        .collect();
    rows.sort_by(|a, b| {
        b.stats
            .points()
            .cmp(&a.stats.points())
            .then(b.stats.wins.cmp(&a.stats.wins))
            .then(b.stats.goal_diff().cmp(&a.stats.goal_diff()))
            .then(b.stats.goals_for.cmp(&a.stats.goals_for))
            .then_with(|| a.team.to_lowercase().cmp(&b.team.to_lowercase()))
    });
    rows
}

pub fn biggest_wins<'a>(
    store: &'a Store,
    competition: Option<Competition>,
    limit: usize,
) -> Vec<&'a Match> {
    let mut filtered: Vec<&Match> = store
        .matches
        .iter()
        .filter(|m| match competition {
            Some(c) => m.competition == c,
            None => true,
        })
        .collect();
    filtered.sort_by(|a, b| {
        let da = (a.home_goal - a.away_goal).abs();
        let db = (b.home_goal - b.away_goal).abs();
        db.cmp(&da)
            .then((b.home_goal + b.away_goal).cmp(&(a.home_goal + a.away_goal)))
    });
    filtered.truncate(limit);
    filtered
}

#[derive(Debug, Clone, Default)]
pub struct CompetitionStats {
    pub matches: u32,
    pub total_goals: i32,
    pub home_wins: u32,
    pub away_wins: u32,
    pub draws: u32,
}

impl CompetitionStats {
    pub fn average_goals(&self) -> f64 {
        if self.matches == 0 {
            0.0
        } else {
            self.total_goals as f64 / self.matches as f64
        }
    }
    pub fn home_win_rate(&self) -> f64 {
        if self.matches == 0 {
            0.0
        } else {
            self.home_wins as f64 / self.matches as f64
        }
    }
}

pub fn competition_stats(
    store: &Store,
    competition: Option<Competition>,
    season: Option<i32>,
) -> CompetitionStats {
    let mut s = CompetitionStats::default();
    for m in &store.matches {
        if let Some(c) = competition {
            if m.competition != c {
                continue;
            }
        }
        if let Some(y) = season {
            if m.season != Some(y) {
                continue;
            }
        }
        s.matches += 1;
        s.total_goals += m.home_goal + m.away_goal;
        match m.winner() {
            MatchResult::HomeWin => s.home_wins += 1,
            MatchResult::AwayWin => s.away_wins += 1,
            MatchResult::Draw => s.draws += 1,
        }
    }
    s
}

#[derive(Debug, Clone, Default)]
pub struct PlayerFilter<'a> {
    pub name: Option<&'a str>,
    pub nationality: Option<&'a str>,
    pub club: Option<&'a str>,
    pub position: Option<&'a str>,
    pub min_overall: Option<i32>,
}

pub fn search_players<'a>(store: &'a Store, f: &PlayerFilter<'_>) -> Vec<&'a Player> {
    store
        .players
        .iter()
        .filter(|p| {
            if let Some(n) = f.name {
                if !text_contains(n, &p.name) {
                    return false;
                }
            }
            if let Some(nat) = f.nationality {
                if !text_contains(nat, &p.nationality) {
                    return false;
                }
            }
            if let Some(club) = f.club {
                if !team_matches(club, &p.club_norm) {
                    return false;
                }
            }
            if let Some(pos) = f.position {
                let want = pos.to_uppercase();
                match &p.position {
                    Some(player_pos) => {
                        if !player_pos.to_uppercase().contains(&want) {
                            return false;
                        }
                    }
                    None => return false,
                }
            }
            if let Some(m) = f.min_overall {
                if p.overall.unwrap_or(0) < m {
                    return false;
                }
            }
            true
        })
        .collect()
}

pub fn top_players<'a>(
    store: &'a Store,
    nationality: Option<&str>,
    club: Option<&str>,
    limit: usize,
) -> Vec<&'a Player> {
    let f = PlayerFilter {
        nationality,
        club,
        ..Default::default()
    };
    let mut v = search_players(store, &f);
    v.sort_by(|a, b| b.overall.unwrap_or(0).cmp(&a.overall.unwrap_or(0)));
    v.truncate(limit);
    v
}

/// Average rating per club, restricted to players of a given nationality.
pub fn club_averages_by_nationality<'a>(
    store: &'a Store,
    nationality: &str,
) -> Vec<(String, usize, f64)> {
    let mut by_club: HashMap<String, (String, Vec<i32>)> = HashMap::new();
    for p in &store.players {
        if !text_contains(nationality, &p.nationality) {
            continue;
        }
        if p.club.is_empty() {
            continue;
        }
        let entry = by_club
            .entry(p.club_norm.clone())
            .or_insert_with(|| (p.club.clone(), Vec::new()));
        entry.1.push(p.overall.unwrap_or(0));
    }
    let mut out: Vec<(String, usize, f64)> = by_club
        .into_iter()
        .map(|(_norm, (club, ratings))| {
            let n = ratings.len();
            let avg = if n == 0 {
                0.0
            } else {
                ratings.iter().sum::<i32>() as f64 / n as f64
            };
            (club, n, avg)
        })
        .collect();
    out.sort_by(|a, b| b.1.cmp(&a.1).then(b.2.partial_cmp(&a.2).unwrap()));
    out
}
