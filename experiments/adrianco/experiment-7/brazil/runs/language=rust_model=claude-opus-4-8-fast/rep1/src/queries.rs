// =============================================================================
// Context: Brazilian Soccer MCP Server
// File:    src/queries.rs
// Purpose: The analytical core. Pure functions over a loaded `Database` that
//          implement every capability the specification requires:
//            - match search (by team, opponent, competition, season, dates)
//            - team statistics (W/D/L, goals for/against, win rate, by venue)
//            - head-to-head records between two clubs
//            - player search (name / nationality / club / position / rating)
//            - league standings computed from match results
//            - aggregate competition statistics (avg goals, home-win rate,
//              biggest victories)
//
//          Nothing here performs I/O; the MCP tool layer adapts these results
//          into protocol responses, which keeps the logic unit-testable.
// =============================================================================

use serde::Serialize;

use crate::model::{Match, MatchOutcome, Player};
use crate::normalize::{loose_contains, normalize_key, team_matches};
use crate::data::Database;

/// Criteria for [`Database::search_matches`].
#[derive(Debug, Default, Clone)]
pub struct MatchQuery {
    pub team: Option<String>,
    pub opponent: Option<String>,
    pub competition: Option<String>,
    pub season: Option<i32>,
    pub date_from: Option<String>,
    pub date_to: Option<String>,
    pub limit: Option<usize>,
}

/// Aggregated win/draw/loss record.
#[derive(Debug, Default, Clone, Serialize)]
pub struct Record {
    pub matches: u32,
    pub wins: u32,
    pub draws: u32,
    pub losses: u32,
    pub goals_for: i32,
    pub goals_against: i32,
}

impl Record {
    fn add(&mut self, outcome: MatchOutcome, gf: i32, ga: i32) {
        self.matches += 1;
        self.goals_for += gf;
        self.goals_against += ga;
        match outcome {
            MatchOutcome::Win => self.wins += 1,
            MatchOutcome::Draw => self.draws += 1,
            MatchOutcome::Loss => self.losses += 1,
        }
    }

    pub fn points(&self) -> u32 {
        self.wins * 3 + self.draws
    }

    pub fn goal_difference(&self) -> i32 {
        self.goals_for - self.goals_against
    }

    pub fn win_rate(&self) -> f64 {
        if self.matches == 0 {
            0.0
        } else {
            self.wins as f64 / self.matches as f64 * 100.0
        }
    }
}

/// A row in a league standings table.
#[derive(Debug, Clone, Serialize)]
pub struct StandingRow {
    pub position: usize,
    pub team: String,
    pub points: u32,
    pub record: Record,
    pub goal_difference: i32,
}

/// Head-to-head summary between two clubs.
#[derive(Debug, Clone, Serialize)]
pub struct HeadToHead {
    pub team1: String,
    pub team2: String,
    pub team1_wins: u32,
    pub team2_wins: u32,
    pub draws: u32,
    pub total_matches: u32,
    pub team1_goals: i32,
    pub team2_goals: i32,
}

/// Aggregate statistics for a competition (optionally a single season).
#[derive(Debug, Clone, Serialize)]
pub struct CompetitionStats {
    pub competition: Option<String>,
    pub season: Option<i32>,
    pub matches: u32,
    pub total_goals: i32,
    pub avg_goals_per_match: f64,
    pub home_wins: u32,
    pub away_wins: u32,
    pub draws: u32,
    pub home_win_rate: f64,
}

/// Resolve a free-text competition name to one of the canonical labels used
/// internally. Defaults to Série A, which is what "Brasileirão" usually means.
pub fn resolve_competition(input: &str) -> String {
    let low = crate::normalize::strip_accents(input);
    if low.contains("libertadores") {
        "Copa Libertadores".to_string()
    } else if low.contains("copa do brasil") || low.contains("cup") {
        "Copa do Brasil".to_string()
    } else if low.contains("serie c") {
        "Brasileirão Série C".to_string()
    } else if low.contains("serie b") {
        "Brasileirão Série B".to_string()
    } else {
        "Brasileirão Série A".to_string()
    }
}

fn match_in_range(m: &Match, from: &Option<String>, to: &Option<String>) -> bool {
    // ISO dates compare lexicographically. Matches without a date are only
    // excluded when an explicit range is requested.
    match (&m.date, from, to) {
        (_, None, None) => true,
        (Some(d), Some(f), Some(t)) => d.as_str() >= f.as_str() && d.as_str() <= t.as_str(),
        (Some(d), Some(f), None) => d.as_str() >= f.as_str(),
        (Some(d), None, Some(t)) => d.as_str() <= t.as_str(),
        (None, _, _) => false,
    }
}

impl Database {
    /// Find matches satisfying every supplied criterion. Results are sorted by
    /// date descending (undated last) and truncated to `limit`.
    pub fn search_matches(&self, q: &MatchQuery) -> Vec<&Match> {
        let mut out: Vec<&Match> = self
            .matches
            .iter()
            .filter(|m| {
                if let Some(season) = q.season {
                    if m.season != season {
                        return false;
                    }
                }
                if let Some(comp) = &q.competition {
                    if !loose_contains(&m.competition, comp) {
                        return false;
                    }
                }
                if let Some(team) = &q.team {
                    if !(team_matches(team, &m.home_team) || team_matches(team, &m.away_team)) {
                        return false;
                    }
                }
                if let Some(opp) = &q.opponent {
                    if !(team_matches(opp, &m.home_team) || team_matches(opp, &m.away_team)) {
                        return false;
                    }
                }
                match_in_range(m, &q.date_from, &q.date_to)
            })
            .collect();

        out.sort_by(|a, b| b.date.cmp(&a.date));
        if let Some(limit) = q.limit {
            out.truncate(limit);
        }
        out
    }

    /// All matches involving `team`, optionally constrained by season / venue
    /// / competition, collapsed into a single [`Record`].
    pub fn team_record(
        &self,
        team: &str,
        season: Option<i32>,
        competition: Option<&str>,
        venue: Venue,
    ) -> Record {
        let mut rec = Record::default();
        for m in &self.matches {
            if let Some(s) = season {
                if m.season != s {
                    continue;
                }
            }
            if let Some(c) = competition {
                if !loose_contains(&m.competition, c) {
                    continue;
                }
            }
            let is_home = team_matches(team, &m.home_team);
            let is_away = team_matches(team, &m.away_team);
            let counts = match venue {
                Venue::Home => is_home,
                Venue::Away => is_away,
                Venue::All => is_home || is_away,
            };
            if !counts {
                continue;
            }
            // Guard against a team somehow matching both sides.
            let treat_home = is_home && (venue != Venue::Away);
            let (gf, ga) = if treat_home {
                (m.home_goal, m.away_goal)
            } else {
                (m.away_goal, m.home_goal)
            };
            rec.add(m.outcome_for(treat_home), gf, ga);
        }
        rec
    }

    /// Head-to-head record between two clubs across all competitions.
    pub fn head_to_head(&self, team1: &str, team2: &str) -> (HeadToHead, Vec<&Match>) {
        let mut h2h = HeadToHead {
            team1: team1.to_string(),
            team2: team2.to_string(),
            team1_wins: 0,
            team2_wins: 0,
            draws: 0,
            total_matches: 0,
            team1_goals: 0,
            team2_goals: 0,
        };
        let mut matches: Vec<&Match> = Vec::new();
        for m in &self.matches {
            let t1_home = team_matches(team1, &m.home_team);
            let t1_away = team_matches(team1, &m.away_team);
            let t2_home = team_matches(team2, &m.home_team);
            let t2_away = team_matches(team2, &m.away_team);
            let is_h2h = (t1_home && t2_away) || (t1_away && t2_home);
            if !is_h2h {
                continue;
            }
            matches.push(m);
            h2h.total_matches += 1;
            let (t1_goals, t2_goals) = if t1_home {
                (m.home_goal, m.away_goal)
            } else {
                (m.away_goal, m.home_goal)
            };
            h2h.team1_goals += t1_goals;
            h2h.team2_goals += t2_goals;
            match t1_goals.cmp(&t2_goals) {
                std::cmp::Ordering::Greater => h2h.team1_wins += 1,
                std::cmp::Ordering::Less => h2h.team2_wins += 1,
                std::cmp::Ordering::Equal => h2h.draws += 1,
            }
        }
        matches.sort_by(|a, b| b.date.cmp(&a.date));
        (h2h, matches)
    }

    /// Compute a standings table for a competition + season from match results.
    ///
    /// Operates on the canonical match set (one authoritative source per
    /// competition+season, selected at load time), so counts are correct and
    /// club names are internally consistent. The competition is resolved to an
    /// exact canonical label to avoid mixing Séries A/B/C.
    pub fn standings(&self, competition: &str, season: i32) -> Vec<StandingRow> {
        use std::collections::HashMap;
        let competition = resolve_competition(competition);
        // Aggregate per normalized team key, but keep a display name.
        let mut table: HashMap<String, (String, Record)> = HashMap::new();
        for m in self.matches.iter().filter(|m| m.season == season && m.competition == competition) {
            let home_key = normalize_key(&m.home_team);
            let away_key = normalize_key(&m.away_team);
            {
                let entry = table
                    .entry(home_key)
                    .or_insert_with(|| (m.home_team.clone(), Record::default()));
                entry.1.add(m.home_outcome(), m.home_goal, m.away_goal);
            }
            {
                let outcome = match m.home_outcome() {
                    MatchOutcome::Win => MatchOutcome::Loss,
                    MatchOutcome::Loss => MatchOutcome::Win,
                    MatchOutcome::Draw => MatchOutcome::Draw,
                };
                let entry = table
                    .entry(away_key)
                    .or_insert_with(|| (m.away_team.clone(), Record::default()));
                entry.1.add(outcome, m.away_goal, m.home_goal);
            }
        }
        let mut rows: Vec<StandingRow> = table
            .into_values()
            .map(|(team, record)| StandingRow {
                position: 0,
                goal_difference: record.goal_difference(),
                points: record.points(),
                team,
                record,
            })
            .collect();
        rows.sort_by(|a, b| {
            b.points
                .cmp(&a.points)
                .then(b.record.wins.cmp(&a.record.wins))
                .then(b.goal_difference.cmp(&a.goal_difference))
                .then(b.record.goals_for.cmp(&a.record.goals_for))
                .then(a.team.cmp(&b.team))
        });
        for (i, row) in rows.iter_mut().enumerate() {
            row.position = i + 1;
        }
        rows
    }

    /// Select the matches an analytical query should operate over. When a
    /// specific competition *and* season are given we match the resolved
    /// competition exactly (clean, single-source counts); otherwise we loosely
    /// filter the canonical pool so partial inputs still return something.
    fn select_matches(&self, competition: Option<&str>, season: Option<i32>) -> Vec<&Match> {
        match (competition, season) {
            (Some(c), Some(s)) => {
                let comp = resolve_competition(c);
                self.matches
                    .iter()
                    .filter(|m| m.season == s && m.competition == comp)
                    .collect()
            }
            _ => self
                .matches
                .iter()
                .filter(|m| {
                    competition.is_none_or(|c| loose_contains(&m.competition, c))
                        && season.is_none_or(|s| m.season == s)
                })
                .collect(),
        }
    }

    /// Aggregate statistics over a slice of the match data.
    pub fn competition_stats(
        &self,
        competition: Option<&str>,
        season: Option<i32>,
    ) -> CompetitionStats {
        let mut stats = CompetitionStats {
            competition: competition.map(|s| s.to_string()),
            season,
            matches: 0,
            total_goals: 0,
            avg_goals_per_match: 0.0,
            home_wins: 0,
            away_wins: 0,
            draws: 0,
            home_win_rate: 0.0,
        };
        for m in self.select_matches(competition, season) {
            stats.matches += 1;
            stats.total_goals += m.home_goal + m.away_goal;
            match m.home_outcome() {
                MatchOutcome::Win => stats.home_wins += 1,
                MatchOutcome::Loss => stats.away_wins += 1,
                MatchOutcome::Draw => stats.draws += 1,
            }
        }
        if stats.matches > 0 {
            stats.avg_goals_per_match = stats.total_goals as f64 / stats.matches as f64;
            stats.home_win_rate = stats.home_wins as f64 / stats.matches as f64 * 100.0;
        }
        stats
    }

    /// The biggest victories (by goal margin) matching the given filters.
    pub fn biggest_wins(
        &self,
        competition: Option<&str>,
        season: Option<i32>,
        limit: usize,
    ) -> Vec<&Match> {
        let mut out: Vec<&Match> = self.select_matches(competition, season);
        out.sort_by(|a, b| {
            let ma = (a.home_goal - a.away_goal).abs();
            let mb = (b.home_goal - b.away_goal).abs();
            mb.cmp(&ma)
                .then((b.home_goal + b.away_goal).cmp(&(a.home_goal + a.away_goal)))
                .then(b.date.cmp(&a.date))
        });
        out.truncate(limit);
        out
    }

    /// Search players by any combination of name / nationality / club /
    /// position / minimum rating. Sorted by overall rating descending.
    pub fn search_players(&self, q: &PlayerQuery) -> Vec<&Player> {
        let mut out: Vec<&Player> = self
            .players
            .iter()
            .filter(|p| {
                if let Some(name) = &q.name {
                    if !loose_contains(&p.name, name) {
                        return false;
                    }
                }
                if let Some(nat) = &q.nationality {
                    if !loose_contains(&p.nationality, nat) {
                        return false;
                    }
                }
                if let Some(club) = &q.club {
                    if !loose_contains(&p.club, club) {
                        return false;
                    }
                }
                if let Some(pos) = &q.position {
                    if !p.position.eq_ignore_ascii_case(pos) {
                        return false;
                    }
                }
                if let Some(min) = q.min_overall {
                    if p.overall < min {
                        return false;
                    }
                }
                true
            })
            .collect();
        out.sort_by(|a, b| b.overall.cmp(&a.overall).then(a.name.cmp(&b.name)));
        if let Some(limit) = q.limit {
            out.truncate(limit);
        }
        out
    }
}

/// Venue filter for [`Database::team_record`].
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Venue {
    Home,
    Away,
    All,
}

/// Criteria for [`Database::search_players`].
#[derive(Debug, Default, Clone)]
pub struct PlayerQuery {
    pub name: Option<String>,
    pub nationality: Option<String>,
    pub club: Option<String>,
    pub position: Option<String>,
    pub min_overall: Option<i32>,
    pub limit: Option<usize>,
}
