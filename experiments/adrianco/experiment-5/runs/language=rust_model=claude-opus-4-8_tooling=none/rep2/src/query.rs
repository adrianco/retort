//! ============================================================================
//! Context
//! ----------------------------------------------------------------------------
//! Module:   query
//! Purpose:  The analytical core of the server. Pure functions over a loaded
//!           `Database` that implement the five capability areas from the spec:
//!           match queries, team queries, player queries, competition queries
//!           (standings) and statistical analysis.
//!
//! These functions return plain data structures; turning them into
//! user-facing text is the job of `format`. Keeping query and formatting
//! separate makes the engine straightforward to unit/BDD test.
//! ============================================================================

use std::collections::HashMap;

use crate::data::Database;
use crate::models::{Match, Outcome, Player};
use crate::normalize::{
    competition_matches, fold_accents, normalize_team, team_matches, Date,
};

/// Which side of a fixture to count.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum Venue {
    Home,
    Away,
    #[default]
    Any,
}

impl Venue {
    pub fn parse(s: &str) -> Venue {
        match s.trim().to_lowercase().as_str() {
            "home" => Venue::Home,
            "away" => Venue::Away,
            _ => Venue::Any,
        }
    }
}

/// Filters for [`search_matches`]. All fields are optional ("None" = no filter).
#[derive(Debug, Default, Clone)]
pub struct MatchFilter {
    pub team: Option<String>,
    pub opponent: Option<String>,
    pub competition: Option<String>,
    pub season: Option<i32>,
    pub venue: Venue,
    pub date_from: Option<Date>,
    pub date_to: Option<Date>,
    /// Include rows from the overlapping "extended" BR-Football dataset. Off by
    /// default to avoid showing each fixture multiple times.
    pub include_extended: bool,
}

/// Find matches by any combination of criteria, newest first.
pub fn search_matches<'a>(db: &'a Database, f: &MatchFilter) -> Vec<&'a Match> {
    let team_norm = f.team.as_deref().map(normalize_team);
    let opp_norm = f.opponent.as_deref().map(normalize_team);

    let mut out: Vec<&Match> = db
        .matches
        .iter()
        .filter(|m| {
            // Extended (BR-Football) rows are opt-in.
            if m.is_extended() && !f.include_extended {
                return false;
            }
            // Competition
            if let Some(c) = &f.competition {
                if !competition_matches(c, &m.competition) {
                    return false;
                }
            }
            // Season
            if let Some(s) = f.season {
                if m.season != Some(s) {
                    return false;
                }
            }
            // Date range
            if let Some(from) = f.date_from {
                match m.date {
                    Some(d) if d >= from => {}
                    _ => return false,
                }
            }
            if let Some(to) = f.date_to {
                match m.date {
                    Some(d) if d <= to => {}
                    _ => return false,
                }
            }
            // Team + venue
            if let Some(t) = &team_norm {
                let on_home = team_matches(t, &m.home_team_norm);
                let on_away = team_matches(t, &m.away_team_norm);
                let venue_ok = match f.venue {
                    Venue::Home => on_home,
                    Venue::Away => on_away,
                    Venue::Any => on_home || on_away,
                };
                if !venue_ok {
                    return false;
                }
            }
            // Opponent (must be present on the side the team is not, or either)
            if let Some(o) = &opp_norm {
                let opp_present =
                    team_matches(o, &m.home_team_norm) || team_matches(o, &m.away_team_norm);
                if !opp_present {
                    return false;
                }
                // When both team and opponent are given, ensure they are on
                // opposite sides of the same fixture.
                if let Some(t) = &team_norm {
                    let valid = (team_matches(t, &m.home_team_norm)
                        && team_matches(o, &m.away_team_norm))
                        || (team_matches(t, &m.away_team_norm)
                            && team_matches(o, &m.home_team_norm));
                    if !valid {
                        return false;
                    }
                }
            }
            true
        })
        .collect();

    // Newest first; matches without a date sort last.
    out.sort_by_key(|m| std::cmp::Reverse(m.date));
    out
}

/// Head-to-head record between two teams.
#[derive(Debug, Clone)]
pub struct HeadToHead<'a> {
    pub team_a: String,
    pub team_b: String,
    pub matches: Vec<&'a Match>,
    pub a_wins: u32,
    pub b_wins: u32,
    pub draws: u32,
}

pub fn head_to_head<'a>(db: &'a Database, team_a: &str, team_b: &str) -> HeadToHead<'a> {
    let a = normalize_team(team_a);
    let b = normalize_team(team_b);
    let matches = search_matches(
        db,
        &MatchFilter {
            team: Some(team_a.to_string()),
            opponent: Some(team_b.to_string()),
            ..Default::default()
        },
    );

    let (mut a_wins, mut b_wins, mut draws) = (0, 0, 0);
    for m in &matches {
        match m.outcome_for(&a) {
            Some(Outcome::Win) => a_wins += 1,
            Some(Outcome::Loss) => b_wins += 1,
            Some(Outcome::Draw) => draws += 1,
            None => {}
        }
    }
    let _ = b; // b is implied by opponent filter; kept for clarity.
    HeadToHead {
        team_a: team_a.to_string(),
        team_b: team_b.to_string(),
        matches,
        a_wins,
        b_wins,
        draws,
    }
}

/// Aggregate win/loss/draw and goal record for a team.
#[derive(Debug, Clone, Default)]
pub struct TeamRecord {
    pub team: String,
    pub matches: u32,
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
    pub fn win_rate(&self) -> f64 {
        if self.matches == 0 {
            0.0
        } else {
            100.0 * self.wins as f64 / self.matches as f64
        }
    }
    pub fn goal_difference(&self) -> i64 {
        self.goals_for as i64 - self.goals_against as i64
    }
}

/// Compute a team's record, optionally scoped by season/competition/venue.
pub fn team_record(
    db: &Database,
    team: &str,
    season: Option<i32>,
    competition: Option<&str>,
    venue: Venue,
) -> TeamRecord {
    let team_norm = normalize_team(team);
    let mut rec = TeamRecord {
        team: team.to_string(),
        ..Default::default()
    };

    for m in &db.matches {
        if m.is_extended() || !m.has_score() {
            continue;
        }
        if let Some(s) = season {
            if m.season != Some(s) {
                continue;
            }
        }
        if let Some(c) = competition {
            if !competition_matches(c, &m.competition) {
                continue;
            }
        }
        let is_home = team_matches(&team_norm, &m.home_team_norm);
        let is_away = team_matches(&team_norm, &m.away_team_norm);
        let counts = match venue {
            Venue::Home => is_home,
            Venue::Away => is_away,
            Venue::Any => is_home || is_away,
        };
        if !counts {
            continue;
        }
        // Guard against a team listed on both sides (shouldn't happen).
        let (gf, ga) = if is_home {
            (m.home_goal.unwrap(), m.away_goal.unwrap())
        } else {
            (m.away_goal.unwrap(), m.home_goal.unwrap())
        };
        rec.matches += 1;
        rec.goals_for += gf;
        rec.goals_against += ga;
        match gf.cmp(&ga) {
            std::cmp::Ordering::Greater => rec.wins += 1,
            std::cmp::Ordering::Equal => rec.draws += 1,
            std::cmp::Ordering::Less => rec.losses += 1,
        }
    }
    rec
}

/// One row of a calculated league table.
#[derive(Debug, Clone, Default)]
pub struct Standing {
    pub team: String,
    pub played: u32,
    pub wins: u32,
    pub draws: u32,
    pub losses: u32,
    pub goals_for: u32,
    pub goals_against: u32,
}

impl Standing {
    pub fn points(&self) -> u32 {
        self.wins * 3 + self.draws
    }
    pub fn goal_difference(&self) -> i64 {
        self.goals_for as i64 - self.goals_against as i64
    }
}

/// Calculate the final league table for a competition + season from results.
/// Sorted by points, then goal difference, then goals scored. Overlapping
/// sources are already resolved at load time (see `Database::resolve_overlaps`)
/// so a simple pass over the matching matches yields one row per club.
pub fn standings(db: &Database, competition: &str, season: i32) -> Vec<Standing> {
    let mut table: HashMap<String, Standing> = HashMap::new();

    for m in &db.matches {
        if m.is_extended() {
            continue;
        }
        if m.season != Some(season) || !competition_matches(competition, &m.competition) {
            continue;
        }
        if !m.has_score() {
            continue;
        }
        let (hg, ag) = (m.home_goal.unwrap(), m.away_goal.unwrap());

        let home = table.entry(m.home_team_norm.clone()).or_insert_with(|| Standing {
            team: m.home_team.clone(),
            ..Default::default()
        });
        home.played += 1;
        home.goals_for += hg;
        home.goals_against += ag;
        match hg.cmp(&ag) {
            std::cmp::Ordering::Greater => home.wins += 1,
            std::cmp::Ordering::Equal => home.draws += 1,
            std::cmp::Ordering::Less => home.losses += 1,
        }

        let away = table.entry(m.away_team_norm.clone()).or_insert_with(|| Standing {
            team: m.away_team.clone(),
            ..Default::default()
        });
        away.played += 1;
        away.goals_for += ag;
        away.goals_against += hg;
        match ag.cmp(&hg) {
            std::cmp::Ordering::Greater => away.wins += 1,
            std::cmp::Ordering::Equal => away.draws += 1,
            std::cmp::Ordering::Less => away.losses += 1,
        }
    }

    let mut rows: Vec<Standing> = table.into_values().collect();
    rows.sort_by(|a, b| {
        b.points()
            .cmp(&a.points())
            .then(b.goal_difference().cmp(&a.goal_difference()))
            .then(b.goals_for.cmp(&a.goals_for))
            .then(a.team.cmp(&b.team))
    });
    rows
}

/// Filters for [`search_players`].
#[derive(Debug, Default, Clone)]
pub struct PlayerFilter {
    pub name: Option<String>,
    pub nationality: Option<String>,
    pub club: Option<String>,
    pub position: Option<String>,
    pub min_overall: Option<u32>,
    pub limit: Option<usize>,
}

/// Search players, sorted by Overall rating (descending). Honors `limit`.
pub fn search_players<'a>(db: &'a Database, f: &PlayerFilter) -> Vec<&'a Player> {
    let name = f.name.as_deref().map(|s| fold_accents(s).to_lowercase());
    let nat = f.nationality.as_deref().map(|s| fold_accents(s).to_lowercase());
    let club = f.club.as_deref().map(normalize_team);
    let pos = f.position.as_deref().map(|s| s.trim().to_lowercase());

    let mut out: Vec<&Player> = db
        .players
        .iter()
        .filter(|p| {
            if let Some(n) = &name {
                if !fold_accents(&p.name).to_lowercase().contains(n.as_str()) {
                    return false;
                }
            }
            if let Some(n) = &nat {
                if fold_accents(&p.nationality).to_lowercase() != *n {
                    return false;
                }
            }
            if let Some(c) = &club {
                if !team_matches(c, &normalize_team(&p.club)) {
                    return false;
                }
            }
            if let Some(po) = &pos {
                if p.position.to_lowercase() != *po {
                    return false;
                }
            }
            if let Some(min) = f.min_overall {
                if p.overall.unwrap_or(0) < min {
                    return false;
                }
            }
            true
        })
        .collect();

    out.sort_by(|a, b| b.overall.cmp(&a.overall).then(a.name.cmp(&b.name)));
    if let Some(limit) = f.limit {
        out.truncate(limit);
    }
    out
}

/// Aggregate statistics over a (possibly filtered) set of matches.
#[derive(Debug, Clone, Default)]
pub struct CompetitionStats {
    pub total_matches: u32,
    pub matches_with_score: u32,
    pub total_goals: u32,
    pub home_wins: u32,
    pub away_wins: u32,
    pub draws: u32,
}

impl CompetitionStats {
    pub fn avg_goals_per_match(&self) -> f64 {
        if self.matches_with_score == 0 {
            0.0
        } else {
            self.total_goals as f64 / self.matches_with_score as f64
        }
    }
    pub fn home_win_rate(&self) -> f64 {
        if self.matches_with_score == 0 {
            0.0
        } else {
            100.0 * self.home_wins as f64 / self.matches_with_score as f64
        }
    }
    pub fn away_win_rate(&self) -> f64 {
        if self.matches_with_score == 0 {
            0.0
        } else {
            100.0 * self.away_wins as f64 / self.matches_with_score as f64
        }
    }
    pub fn draw_rate(&self) -> f64 {
        if self.matches_with_score == 0 {
            0.0
        } else {
            100.0 * self.draws as f64 / self.matches_with_score as f64
        }
    }
}

/// Compute aggregate statistics, optionally scoped by competition + season.
pub fn competition_stats(
    db: &Database,
    competition: Option<&str>,
    season: Option<i32>,
) -> CompetitionStats {
    let mut s = CompetitionStats::default();
    for m in &db.matches {
        if m.is_extended() {
            continue;
        }
        if let Some(c) = competition {
            if !competition_matches(c, &m.competition) {
                continue;
            }
        }
        if let Some(yr) = season {
            if m.season != Some(yr) {
                continue;
            }
        }
        s.total_matches += 1;
        if let (Some(h), Some(a)) = (m.home_goal, m.away_goal) {
            s.matches_with_score += 1;
            s.total_goals += h + a;
            match h.cmp(&a) {
                std::cmp::Ordering::Greater => s.home_wins += 1,
                std::cmp::Ordering::Equal => s.draws += 1,
                std::cmp::Ordering::Less => s.away_wins += 1,
            }
        }
    }
    s
}

/// The biggest victories (by goal margin) within an optional filter.
pub fn biggest_wins<'a>(
    db: &'a Database,
    competition: Option<&str>,
    season: Option<i32>,
    limit: usize,
) -> Vec<&'a Match> {
    let mut scored: Vec<&Match> = db
        .matches
        .iter()
        .filter(|m| {
            if m.is_extended() {
                return false;
            }
            if let Some(c) = competition {
                if !competition_matches(c, &m.competition) {
                    return false;
                }
            }
            if let Some(yr) = season {
                if m.season != Some(yr) {
                    return false;
                }
            }
            m.has_score()
        })
        .collect();

    scored.sort_by(|a, b| {
        let ma = (a.home_goal.unwrap() as i64 - a.away_goal.unwrap() as i64).abs();
        let mb = (b.home_goal.unwrap() as i64 - b.away_goal.unwrap() as i64).abs();
        mb.cmp(&ma)
            .then(b.total_goals().cmp(&a.total_goals()))
            .then(b.date.cmp(&a.date))
    });
    scored.truncate(limit);
    scored
}

/// Aggregate how many Brazilian-club players sit at each club, with average
/// overall rating — supports the "Brazilian players at Brazilian clubs" view.
#[derive(Debug, Clone)]
pub struct ClubAggregate {
    pub club: String,
    pub count: usize,
    pub avg_overall: f64,
}

/// Group players (already filtered however the caller likes) by club.
pub fn group_by_club(players: &[&Player]) -> Vec<ClubAggregate> {
    let mut map: HashMap<String, (usize, u32)> = HashMap::new();
    for p in players {
        if p.club.trim().is_empty() {
            continue;
        }
        let e = map.entry(p.club.clone()).or_insert((0, 0));
        e.0 += 1;
        e.1 += p.overall.unwrap_or(0);
    }
    let mut out: Vec<ClubAggregate> = map
        .into_iter()
        .map(|(club, (count, sum))| ClubAggregate {
            club,
            count,
            avg_overall: if count == 0 {
                0.0
            } else {
                sum as f64 / count as f64
            },
        })
        .collect();
    out.sort_by(|a, b| b.count.cmp(&a.count).then(a.club.cmp(&b.club)));
    out
}
