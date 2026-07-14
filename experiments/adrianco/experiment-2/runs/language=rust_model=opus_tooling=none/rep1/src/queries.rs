use crate::data::{normalize_team, Competition, Dataset, Match, Player};
use serde::Serialize;
use std::collections::HashMap;

#[derive(Debug, Default, Clone, Serialize)]
pub struct TeamStats {
    pub team: String,
    pub matches: u32,
    pub wins: u32,
    pub draws: u32,
    pub losses: u32,
    pub goals_for: u32,
    pub goals_against: u32,
    pub points: u32,
}

#[derive(Debug, Default, Clone, Serialize)]
pub struct HeadToHead {
    pub team_a: String,
    pub team_b: String,
    pub total: u32,
    pub a_wins: u32,
    pub b_wins: u32,
    pub draws: u32,
    pub matches: Vec<Match>,
}

pub struct Query<'a> {
    ds: &'a Dataset,
}

impl<'a> Query<'a> {
    pub fn new(ds: &'a Dataset) -> Self {
        Self { ds }
    }

    pub fn matches_between(&self, team_a: &str, team_b: &str) -> Vec<&Match> {
        let a = normalize_team(team_a);
        let b = normalize_team(team_b);
        self.ds
            .matches
            .iter()
            .filter(|m| {
                (m.home_team_norm == a && m.away_team_norm == b)
                    || (m.home_team_norm == b && m.away_team_norm == a)
            })
            .collect()
    }

    pub fn matches_for_team(&self, team: &str) -> Vec<&Match> {
        let n = normalize_team(team);
        self.ds
            .matches
            .iter()
            .filter(|m| m.home_team_norm == n || m.away_team_norm == n)
            .collect()
    }

    pub fn matches_by_competition_season(
        &self,
        comp: Competition,
        season: i32,
    ) -> Vec<&Match> {
        self.ds
            .matches
            .iter()
            .filter(|m| m.competition == comp && m.season == season)
            .collect()
    }

    pub fn team_stats(&self, team: &str, season: Option<i32>, home_only: bool, away_only: bool) -> TeamStats {
        let n = normalize_team(team);
        let mut s = TeamStats {
            team: team.to_string(),
            ..Default::default()
        };
        for m in &self.ds.matches {
            if let Some(y) = season {
                if m.season != y {
                    continue;
                }
            }
            let is_home = m.home_team_norm == n;
            let is_away = m.away_team_norm == n;
            if !is_home && !is_away {
                continue;
            }
            if home_only && !is_home {
                continue;
            }
            if away_only && !is_away {
                continue;
            }
            s.matches += 1;
            let (gf, ga) = if is_home {
                (m.home_goal, m.away_goal)
            } else {
                (m.away_goal, m.home_goal)
            };
            s.goals_for += gf.max(0) as u32;
            s.goals_against += ga.max(0) as u32;
            if gf > ga {
                s.wins += 1;
                s.points += 3;
            } else if gf == ga {
                s.draws += 1;
                s.points += 1;
            } else {
                s.losses += 1;
            }
        }
        s
    }

    pub fn head_to_head(&self, team_a: &str, team_b: &str) -> HeadToHead {
        let a = normalize_team(team_a);
        let b = normalize_team(team_b);
        let mut h = HeadToHead {
            team_a: team_a.to_string(),
            team_b: team_b.to_string(),
            ..Default::default()
        };
        for m in &self.ds.matches {
            let a_home = m.home_team_norm == a && m.away_team_norm == b;
            let b_home = m.home_team_norm == b && m.away_team_norm == a;
            if !a_home && !b_home {
                continue;
            }
            h.total += 1;
            h.matches.push(m.clone());
            let (gf_a, gf_b) = if a_home {
                (m.home_goal, m.away_goal)
            } else {
                (m.away_goal, m.home_goal)
            };
            if gf_a > gf_b {
                h.a_wins += 1;
            } else if gf_b > gf_a {
                h.b_wins += 1;
            } else {
                h.draws += 1;
            }
        }
        h
    }

    pub fn standings(&self, comp: Competition, season: i32) -> Vec<TeamStats> {
        let mut by_team: HashMap<String, TeamStats> = HashMap::new();
        for m in &self.ds.matches {
            if m.competition != comp || m.season != season {
                continue;
            }
            for (team, team_norm, gf, ga) in [
                (&m.home_team, &m.home_team_norm, m.home_goal, m.away_goal),
                (&m.away_team, &m.away_team_norm, m.away_goal, m.home_goal),
            ] {
                let entry = by_team.entry(team_norm.clone()).or_insert_with(|| TeamStats {
                    team: team.clone(),
                    ..Default::default()
                });
                entry.matches += 1;
                entry.goals_for += gf.max(0) as u32;
                entry.goals_against += ga.max(0) as u32;
                if gf > ga {
                    entry.wins += 1;
                    entry.points += 3;
                } else if gf == ga {
                    entry.draws += 1;
                    entry.points += 1;
                } else {
                    entry.losses += 1;
                }
            }
        }
        let mut v: Vec<TeamStats> = by_team.into_values().collect();
        v.sort_by(|a, b| {
            b.points
                .cmp(&a.points)
                .then((b.goals_for as i32 - b.goals_against as i32).cmp(&(a.goals_for as i32 - a.goals_against as i32)))
                .then(b.goals_for.cmp(&a.goals_for))
        });
        v
    }

    pub fn search_players(&self, name: &str) -> Vec<&Player> {
        let q = name.to_lowercase();
        self.ds
            .players
            .iter()
            .filter(|p| p.name.to_lowercase().contains(&q))
            .collect()
    }

    pub fn players_by_nationality(&self, nat: &str, limit: usize) -> Vec<&Player> {
        let q = nat.to_lowercase();
        let mut v: Vec<&Player> = self
            .ds
            .players
            .iter()
            .filter(|p| p.nationality.to_lowercase() == q)
            .collect();
        v.sort_by(|a, b| b.overall.cmp(&a.overall));
        v.truncate(limit);
        v
    }

    pub fn players_by_club(&self, club: &str) -> Vec<&Player> {
        let q = club.to_lowercase();
        let mut v: Vec<&Player> = self
            .ds
            .players
            .iter()
            .filter(|p| p.club.to_lowercase().contains(&q))
            .collect();
        v.sort_by(|a, b| b.overall.cmp(&a.overall));
        v
    }

    pub fn biggest_wins(&self, limit: usize) -> Vec<&Match> {
        let mut v: Vec<&Match> = self.ds.matches.iter().collect();
        v.sort_by(|a, b| {
            let da = (a.home_goal - a.away_goal).abs();
            let db = (b.home_goal - b.away_goal).abs();
            db.cmp(&da).then((b.home_goal + b.away_goal).cmp(&(a.home_goal + a.away_goal)))
        });
        v.truncate(limit);
        v
    }

    pub fn average_goals_per_match(&self, comp: Option<Competition>) -> f64 {
        let it = self.ds.matches.iter().filter(|m| match comp {
            Some(c) => m.competition == c,
            None => true,
        });
        let (mut total, mut count) = (0i64, 0i64);
        for m in it {
            total += (m.home_goal + m.away_goal) as i64;
            count += 1;
        }
        if count == 0 {
            0.0
        } else {
            total as f64 / count as f64
        }
    }

    pub fn home_win_rate(&self, comp: Option<Competition>) -> f64 {
        let mut wins = 0u32;
        let mut total = 0u32;
        for m in self.ds.matches.iter().filter(|m| match comp {
            Some(c) => m.competition == c,
            None => true,
        }) {
            total += 1;
            if m.home_goal > m.away_goal {
                wins += 1;
            }
        }
        if total == 0 {
            0.0
        } else {
            wins as f64 / total as f64
        }
    }
}
