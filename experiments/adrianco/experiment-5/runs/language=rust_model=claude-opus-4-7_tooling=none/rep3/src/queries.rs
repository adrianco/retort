//! Query layer.
//!
//! Pure functions over `Dataset` that the MCP tool handlers call.  Each
//! returns plain Rust types; the MCP layer serializes them.

use std::collections::HashMap;

use serde::Serialize;

use crate::data::{Competition, Dataset, Match, Player};
use crate::normalize::{matches_team, normalize_team};

// ---------------------------------------------------------------------------
// Filters
// ---------------------------------------------------------------------------

#[derive(Debug, Default, Clone)]
pub struct MatchFilter<'a> {
    pub team: Option<&'a str>,
    pub opponent: Option<&'a str>,
    pub season: Option<i32>,
    pub competition: Option<Competition>,
    pub home_only: bool,
    pub away_only: bool,
    pub limit: Option<usize>,
}

#[derive(Debug, Serialize)]
pub struct MatchSummary {
    pub date: String,
    pub competition: &'static str,
    pub season: i32,
    pub round: Option<String>,
    pub stage: Option<String>,
    pub home_team: String,
    pub away_team: String,
    pub home_goal: i32,
    pub away_goal: i32,
    pub arena: Option<String>,
}

impl From<&Match> for MatchSummary {
    fn from(m: &Match) -> Self {
        MatchSummary {
            date: m.date.clone(),
            competition: m.competition.label(),
            season: m.season,
            round: m.round.clone(),
            stage: m.stage.clone(),
            home_team: m.home_team.clone(),
            away_team: m.away_team.clone(),
            home_goal: m.home_goal,
            away_goal: m.away_goal,
            arena: m.arena.clone(),
        }
    }
}

/// Apply a filter and return matches sorted by date (most recent first).
pub fn find_matches<'a>(ds: &'a Dataset, f: &MatchFilter<'a>) -> Vec<&'a Match> {
    let team_norm = f.team.map(normalize_team);
    let opp_norm = f.opponent.map(normalize_team);

    let mut out: Vec<&Match> = ds
        .matches
        .iter()
        .filter(|m| {
            if let Some(season) = f.season {
                if m.season != season {
                    return false;
                }
            }
            if let Some(comp) = f.competition {
                if m.competition != comp {
                    return false;
                }
            }
            if let Some(tn) = team_norm.as_deref() {
                if f.home_only {
                    if m.home_team_norm != tn {
                        return false;
                    }
                } else if f.away_only {
                    if m.away_team_norm != tn {
                        return false;
                    }
                } else if !m.involves(tn) {
                    return false;
                }
            }
            if let Some(on) = opp_norm.as_deref() {
                if !m.involves(on) {
                    return false;
                }
                if let Some(tn) = team_norm.as_deref() {
                    // Both teams must appear, and they must be different.
                    if tn == on || !(m.involves(tn) && m.involves(on)) {
                        return false;
                    }
                }
            }
            true
        })
        .collect();
    out.sort_by(|a, b| b.date.cmp(&a.date));
    if let Some(n) = f.limit {
        out.truncate(n);
    }
    out
}

// ---------------------------------------------------------------------------
// Team statistics
// ---------------------------------------------------------------------------

#[derive(Debug, Serialize, Default, Clone)]
pub struct TeamRecord {
    pub team: String,
    pub matches: u32,
    pub wins: u32,
    pub draws: u32,
    pub losses: u32,
    pub goals_for: i32,
    pub goals_against: i32,
}

impl TeamRecord {
    pub fn points(&self) -> i32 {
        (self.wins * 3 + self.draws) as i32
    }

    pub fn win_rate(&self) -> f64 {
        if self.matches == 0 {
            0.0
        } else {
            self.wins as f64 / self.matches as f64
        }
    }

    pub fn goal_difference(&self) -> i32 {
        self.goals_for - self.goals_against
    }

    fn record(&mut self, scored: i32, conceded: i32) {
        self.matches += 1;
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

/// Team record under a filter. `venue` selects home/away/all.
#[derive(Debug, Clone, Copy)]
pub enum Venue {
    Home,
    Away,
    All,
}

pub fn team_record(
    ds: &Dataset,
    team: &str,
    season: Option<i32>,
    competition: Option<Competition>,
    venue: Venue,
) -> TeamRecord {
    let tn = normalize_team(team);
    let mut rec = TeamRecord {
        team: team.to_string(),
        ..Default::default()
    };
    for m in &ds.matches {
        if let Some(s) = season {
            if m.season != s {
                continue;
            }
        }
        if let Some(c) = competition {
            if m.competition != c {
                continue;
            }
        }
        let is_home = m.home_team_norm == tn;
        let is_away = m.away_team_norm == tn;
        if !(is_home || is_away) {
            continue;
        }
        match venue {
            Venue::Home if !is_home => continue,
            Venue::Away if !is_away => continue,
            _ => {}
        }
        if is_home {
            rec.record(m.home_goal, m.away_goal);
        } else {
            rec.record(m.away_goal, m.home_goal);
        }
    }
    rec
}

// ---------------------------------------------------------------------------
// Head-to-head
// ---------------------------------------------------------------------------

#[derive(Debug, Serialize)]
pub struct HeadToHead {
    pub team_a: String,
    pub team_b: String,
    pub matches: u32,
    pub team_a_wins: u32,
    pub team_b_wins: u32,
    pub draws: u32,
    pub team_a_goals: i32,
    pub team_b_goals: i32,
}

pub fn head_to_head(ds: &Dataset, a: &str, b: &str) -> HeadToHead {
    let an = normalize_team(a);
    let bn = normalize_team(b);
    let mut h = HeadToHead {
        team_a: a.to_string(),
        team_b: b.to_string(),
        matches: 0,
        team_a_wins: 0,
        team_b_wins: 0,
        draws: 0,
        team_a_goals: 0,
        team_b_goals: 0,
    };
    if an == bn {
        return h;
    }
    for m in &ds.matches {
        let home_a = m.home_team_norm == an && m.away_team_norm == bn;
        let home_b = m.home_team_norm == bn && m.away_team_norm == an;
        if !(home_a || home_b) {
            continue;
        }
        h.matches += 1;
        let (a_scored, b_scored) = if home_a {
            (m.home_goal, m.away_goal)
        } else {
            (m.away_goal, m.home_goal)
        };
        h.team_a_goals += a_scored;
        h.team_b_goals += b_scored;
        if a_scored > b_scored {
            h.team_a_wins += 1;
        } else if b_scored > a_scored {
            h.team_b_wins += 1;
        } else {
            h.draws += 1;
        }
    }
    h
}

// ---------------------------------------------------------------------------
// Standings
// ---------------------------------------------------------------------------

#[derive(Debug, Serialize)]
pub struct StandingsRow {
    pub rank: usize,
    pub team: String,
    pub matches: u32,
    pub wins: u32,
    pub draws: u32,
    pub losses: u32,
    pub goals_for: i32,
    pub goals_against: i32,
    pub goal_difference: i32,
    pub points: i32,
}

/// Compute a season's standings from match results.
pub fn standings(
    ds: &Dataset,
    season: i32,
    competition: Competition,
) -> Vec<StandingsRow> {
    let mut by_team: HashMap<String, TeamRecord> = HashMap::new();
    for m in &ds.matches {
        if m.season != season || m.competition != competition {
            continue;
        }
        by_team
            .entry(m.home_team_norm.clone())
            .or_insert_with(|| TeamRecord {
                team: m.home_team.clone(),
                ..Default::default()
            })
            .record(m.home_goal, m.away_goal);
        by_team
            .entry(m.away_team_norm.clone())
            .or_insert_with(|| TeamRecord {
                team: m.away_team.clone(),
                ..Default::default()
            })
            .record(m.away_goal, m.home_goal);
    }

    let mut rows: Vec<TeamRecord> = by_team.into_values().collect();
    rows.sort_by(|a, b| {
        b.points()
            .cmp(&a.points())
            .then_with(|| b.wins.cmp(&a.wins))
            .then_with(|| b.goal_difference().cmp(&a.goal_difference()))
            .then_with(|| b.goals_for.cmp(&a.goals_for))
            .then_with(|| a.team.cmp(&b.team))
    });
    rows.into_iter()
        .enumerate()
        .map(|(i, r)| {
            let points = r.points();
            let gd = r.goal_difference();
            StandingsRow {
                rank: i + 1,
                team: r.team,
                matches: r.matches,
                wins: r.wins,
                draws: r.draws,
                losses: r.losses,
                goals_for: r.goals_for,
                goals_against: r.goals_against,
                goal_difference: gd,
                points,
            }
        })
        .collect()
}

// ---------------------------------------------------------------------------
// Player queries
// ---------------------------------------------------------------------------

#[derive(Debug, Default, Clone)]
pub struct PlayerFilter<'a> {
    pub name: Option<&'a str>,
    pub nationality: Option<&'a str>,
    pub club: Option<&'a str>,
    pub position: Option<&'a str>,
    pub min_overall: Option<i32>,
    pub limit: Option<usize>,
    /// Sort by overall rating descending if true (default: name asc).
    pub sort_by_overall: bool,
}

pub fn find_players<'a>(ds: &'a Dataset, f: &PlayerFilter<'a>) -> Vec<&'a Player> {
    let name_q = f.name.map(|s| s.to_lowercase());
    let nat_q = f.nationality.map(|s| s.to_lowercase());
    let pos_q = f.position.map(|s| s.to_uppercase());

    let mut out: Vec<&Player> = ds
        .players
        .iter()
        .filter(|p| {
            if let Some(n) = &name_q {
                if !p.name.to_lowercase().contains(n) {
                    return false;
                }
            }
            if let Some(nat) = &nat_q {
                if !p.nationality.to_lowercase().contains(nat) {
                    return false;
                }
            }
            if let Some(club) = f.club {
                if !matches_team(&p.club, club) {
                    return false;
                }
            }
            if let Some(pos) = &pos_q {
                if !p.position.to_uppercase().contains(pos) {
                    return false;
                }
            }
            if let Some(min) = f.min_overall {
                if p.overall < min {
                    return false;
                }
            }
            true
        })
        .collect();

    if f.sort_by_overall {
        out.sort_by(|a, b| b.overall.cmp(&a.overall).then_with(|| a.name.cmp(&b.name)));
    } else {
        out.sort_by(|a, b| a.name.cmp(&b.name));
    }
    if let Some(n) = f.limit {
        out.truncate(n);
    }
    out
}

// ---------------------------------------------------------------------------
// Aggregate stats
// ---------------------------------------------------------------------------

#[derive(Debug, Serialize)]
pub struct CompetitionStats {
    pub competition: &'static str,
    pub season: Option<i32>,
    pub matches: usize,
    pub total_goals: i32,
    pub avg_goals_per_match: f64,
    pub home_wins: u32,
    pub away_wins: u32,
    pub draws: u32,
    pub home_win_rate: f64,
    pub away_win_rate: f64,
    pub draw_rate: f64,
}

pub fn competition_stats(
    ds: &Dataset,
    competition: Option<Competition>,
    season: Option<i32>,
) -> CompetitionStats {
    let mut total = 0i32;
    let mut count = 0usize;
    let mut hw = 0u32;
    let mut aw = 0u32;
    let mut dr = 0u32;
    let label = competition.map(|c| c.label()).unwrap_or("All competitions");
    for m in &ds.matches {
        if let Some(c) = competition {
            if m.competition != c {
                continue;
            }
        }
        if let Some(s) = season {
            if m.season != s {
                continue;
            }
        }
        count += 1;
        total += m.home_goal + m.away_goal;
        if m.home_goal > m.away_goal {
            hw += 1;
        } else if m.away_goal > m.home_goal {
            aw += 1;
        } else {
            dr += 1;
        }
    }
    let denom = count.max(1) as f64;
    CompetitionStats {
        competition: label,
        season,
        matches: count,
        total_goals: total,
        avg_goals_per_match: total as f64 / denom,
        home_wins: hw,
        away_wins: aw,
        draws: dr,
        home_win_rate: hw as f64 / denom,
        away_win_rate: aw as f64 / denom,
        draw_rate: dr as f64 / denom,
    }
}

pub fn biggest_wins<'a>(
    ds: &'a Dataset,
    competition: Option<Competition>,
    season: Option<i32>,
    limit: usize,
) -> Vec<&'a Match> {
    let mut v: Vec<&Match> = ds
        .matches
        .iter()
        .filter(|m| competition.map_or(true, |c| m.competition == c))
        .filter(|m| season.map_or(true, |s| m.season == s))
        .collect();
    v.sort_by(|a, b| {
        let da = (a.home_goal - a.away_goal).abs();
        let db = (b.home_goal - b.away_goal).abs();
        db.cmp(&da)
            .then_with(|| (b.home_goal + b.away_goal).cmp(&(a.home_goal + a.away_goal)))
            .then_with(|| b.date.cmp(&a.date))
    });
    v.truncate(limit);
    v
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::data::Dataset;
    use std::path::PathBuf;

    fn data_dir() -> PathBuf {
        PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("data/kaggle")
    }

    #[test]
    fn dataset_loads_expected_counts() {
        let ds = Dataset::load_from_dir(data_dir()).expect("load");
        // Loose lower bounds — exact counts are checked by integration tests.
        assert!(ds.matches.len() > 20_000, "got {}", ds.matches.len());
        assert!(ds.players.len() > 18_000, "got {}", ds.players.len());
    }

    #[test]
    fn h2h_returns_symmetric_results_for_known_clubs() {
        let ds = Dataset::load_from_dir(data_dir()).expect("load");
        let h = head_to_head(&ds, "Flamengo", "Fluminense");
        assert!(h.matches > 0);
        assert_eq!(
            h.matches,
            h.team_a_wins + h.team_b_wins + h.draws,
            "wins+draws must equal total"
        );
    }
}
