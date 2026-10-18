//! Query layer: match filtering, aggregation, standings and player search.
//!
//! Every function here is pure over a [`Dataset`], so the MCP layer and the
//! tests share one implementation.

use std::collections::HashMap;

use crate::data::{Competition, Dataset, Match, Player};
use crate::normalize::{fold, team_key};

/// Optional criteria for selecting matches. `None` fields are not filtered.
#[derive(Debug, Default, Clone)]
pub struct MatchFilter {
    /// Matches where this team played (home or away).
    pub team: Option<String>,
    /// Combined with `team`: only matches between the two teams.
    pub opponent: Option<String>,
    pub competition: Option<Competition>,
    pub season: Option<i32>,
    /// ISO dates, inclusive.
    pub date_from: Option<String>,
    pub date_to: Option<String>,
}

/// Matches satisfying `filter`, most recent first.
pub fn find_matches<'a>(ds: &'a Dataset, filter: &MatchFilter) -> Vec<&'a Match> {
    let team = filter.team.as_deref().map(team_key);
    let opponent = filter.opponent.as_deref().map(team_key);
    let mut matches: Vec<&Match> = ds
        .matches
        .iter()
        .filter(|m| filter.competition.is_none_or(|c| m.competition == c))
        .filter(|m| filter.season.is_none_or(|s| m.season == s))
        .filter(|m| filter.date_from.as_deref().is_none_or(|from| m.date.as_str() >= from))
        .filter(|m| filter.date_to.as_deref().is_none_or(|to| m.date.as_str() <= to))
        .filter(|m| match (&team, &opponent) {
            (None, None) => true,
            (Some(t), None) => m.involves(t),
            (None, Some(o)) => m.involves(o),
            (Some(t), Some(o)) => {
                (m.home.key == *t && m.away.key == *o) || (m.home.key == *o && m.away.key == *t)
            }
        })
        .collect();
    matches.sort_by(|a, b| b.date.cmp(&a.date));
    matches
}

impl Match {
    /// True when the team with this key played in the match.
    pub fn involves(&self, key: &str) -> bool {
        self.home.key == key || self.away.key == key
    }

    /// Goals scored and conceded from the perspective of the team with `key`.
    fn goals_from_view(&self, key: &str) -> Option<(u32, u32, bool)> {
        if self.home.key == key {
            Some((self.home_goals, self.away_goals, true))
        } else if self.away.key == key {
            Some((self.away_goals, self.home_goals, false))
        } else {
            None
        }
    }
}

/// Wins, draws, losses and goals for one slice of matches.
#[derive(Debug, Default, Clone, PartialEq, Eq)]
pub struct Record {
    pub played: u32,
    pub wins: u32,
    pub draws: u32,
    pub losses: u32,
    pub goals_for: u32,
    pub goals_against: u32,
}

impl Record {
    fn add(&mut self, goals_for: u32, goals_against: u32) {
        self.played += 1;
        self.goals_for += goals_for;
        self.goals_against += goals_against;
        match goals_for.cmp(&goals_against) {
            std::cmp::Ordering::Greater => self.wins += 1,
            std::cmp::Ordering::Equal => self.draws += 1,
            std::cmp::Ordering::Less => self.losses += 1,
        }
    }

    pub fn points(&self) -> u32 {
        self.wins * 3 + self.draws
    }

    /// Wins divided by matches played; `0.0` when no matches.
    pub fn win_rate(&self) -> f64 {
        if self.played == 0 { 0.0 } else { f64::from(self.wins) / f64::from(self.played) }
    }
}

/// A team's record overall and split by venue.
#[derive(Debug, Default, Clone, PartialEq, Eq)]
pub struct TeamStats {
    pub overall: Record,
    pub home: Record,
    pub away: Record,
}

/// Aggregates a team's results for the given competition and season.
pub fn team_stats(ds: &Dataset, team: &str, competition: Option<Competition>, season: Option<i32>) -> TeamStats {
    let key = team_key(team);
    let filter = MatchFilter { team: Some(team.to_string()), competition, season, ..Default::default() };
    let mut stats = TeamStats::default();
    for m in find_matches(ds, &filter) {
        if let Some((gf, ga, at_home)) = m.goals_from_view(&key) {
            stats.overall.add(gf, ga);
            if at_home {
                stats.home.add(gf, ga);
            } else {
                stats.away.add(gf, ga);
            }
        }
    }
    stats
}

/// Results between two teams, from the first team's point of view.
#[derive(Debug, Default, Clone, PartialEq, Eq)]
pub struct HeadToHead {
    pub first_wins: u32,
    pub draws: u32,
    pub second_wins: u32,
    pub first_goals: u32,
    pub second_goals: u32,
    /// Most recent first.
    pub matches: Vec<Match>,
}

/// Compares two teams across every match in the dataset (or one competition).
pub fn head_to_head(ds: &Dataset, first: &str, second: &str, competition: Option<Competition>) -> HeadToHead {
    let first_key = team_key(first);
    let filter = MatchFilter {
        team: Some(first.to_string()),
        opponent: Some(second.to_string()),
        competition,
        ..Default::default()
    };
    let mut h2h = HeadToHead::default();
    for m in find_matches(ds, &filter) {
        let (gf, ga, _) = m.goals_from_view(&first_key).expect("filter guarantees first team played");
        h2h.matches.push(m.clone());
        h2h.first_goals += gf;
        h2h.second_goals += ga;
        match gf.cmp(&ga) {
            std::cmp::Ordering::Greater => h2h.first_wins += 1,
            std::cmp::Ordering::Equal => h2h.draws += 1,
            std::cmp::Ordering::Less => h2h.second_wins += 1,
        }
    }
    h2h
}

/// One row of a league table.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StandingRow {
    pub team: String,
    pub record: Record,
}

impl StandingRow {
    pub fn goal_difference(&self) -> i64 {
        i64::from(self.record.goals_for) - i64::from(self.record.goals_against)
    }
}

/// League table for one competition and season, sorted by points, then
/// wins, goal difference, goals scored and name.
pub fn standings(ds: &Dataset, competition: Competition, season: i32) -> Vec<StandingRow> {
    let filter = MatchFilter { competition: Some(competition), season: Some(season), ..Default::default() };
    let mut table: HashMap<String, StandingRow> = HashMap::new();
    for m in find_matches(ds, &filter) {
        for (side, goals_for, goals_against) in [
            (&m.home, m.home_goals, m.away_goals),
            (&m.away, m.away_goals, m.home_goals),
        ] {
            let row = table
                .entry(side.key.clone())
                .or_insert_with(|| StandingRow { team: side.name.clone(), record: Record::default() });
            row.record.add(goals_for, goals_against);
        }
    }
    let mut rows: Vec<StandingRow> = table.into_values().collect();
    rows.sort_by(|a, b| {
        b.record
            .points()
            .cmp(&a.record.points())
            .then(b.record.wins.cmp(&a.record.wins))
            .then(b.goal_difference().cmp(&a.goal_difference()))
            .then(b.record.goals_for.cmp(&a.record.goals_for))
            .then(a.team.cmp(&b.team))
    });
    rows
}

/// Aggregate statistics for a set of matches.
#[derive(Debug, Clone, PartialEq)]
pub struct LeagueStats {
    pub matches: usize,
    pub total_goals: u32,
    pub avg_goals_per_match: f64,
    pub home_wins: usize,
    pub draws: usize,
    pub away_wins: usize,
    /// Largest margins of victory, biggest first.
    pub biggest_wins: Vec<Match>,
}

impl LeagueStats {
    pub fn home_win_rate(&self) -> f64 {
        ratio(self.home_wins, self.matches)
    }

    pub fn draw_rate(&self) -> f64 {
        ratio(self.draws, self.matches)
    }

    pub fn away_win_rate(&self) -> f64 {
        ratio(self.away_wins, self.matches)
    }
}

fn ratio(part: usize, whole: usize) -> f64 {
    if whole == 0 { 0.0 } else { part as f64 / whole as f64 }
}

/// Goal, home/draw/away and biggest-win statistics for the matching games.
pub fn league_stats(ds: &Dataset, competition: Option<Competition>, season: Option<i32>) -> LeagueStats {
    let filter = MatchFilter { competition, season, ..Default::default() };
    let matches = find_matches(ds, &filter);
    let total_goals: u32 = matches.iter().map(|m| m.home_goals + m.away_goals).sum();
    let (mut home_wins, mut draws, mut away_wins) = (0, 0, 0);
    for m in &matches {
        match m.home_goals.cmp(&m.away_goals) {
            std::cmp::Ordering::Greater => home_wins += 1,
            std::cmp::Ordering::Equal => draws += 1,
            std::cmp::Ordering::Less => away_wins += 1,
        }
    }
    let mut decisive: Vec<&Match> = matches.iter().copied().filter(|m| m.home_goals != m.away_goals).collect();
    decisive.sort_by(|a, b| {
        margin(b).cmp(&margin(a)).then(b.date.cmp(&a.date))
    });
    LeagueStats {
        matches: matches.len(),
        total_goals,
        avg_goals_per_match: ratio(total_goals as usize, matches.len()),
        home_wins,
        draws,
        away_wins,
        biggest_wins: decisive.into_iter().take(5).cloned().collect(),
    }
}

fn margin(m: &Match) -> u32 {
    m.home_goals.abs_diff(m.away_goals)
}

/// Criteria for player search. Text fields are case- and accent-insensitive.
#[derive(Debug, Default, Clone)]
pub struct PlayerFilter {
    /// Substring of the player's name.
    pub name: Option<String>,
    /// Exact nationality, e.g. `Brazil`.
    pub nationality: Option<String>,
    /// Substring of the club name, e.g. `Flamengo`.
    pub club: Option<String>,
    /// Exact position code, e.g. `ST`, `GK`.
    pub position: Option<String>,
    pub min_overall: Option<u32>,
}

/// Players matching `filter`, highest overall rating first.
pub fn search_players<'a>(ds: &'a Dataset, filter: &PlayerFilter, limit: usize) -> Vec<&'a Player> {
    let name = filter.name.as_deref().map(fold);
    let nationality = filter.nationality.as_deref().map(fold);
    let club = filter.club.as_deref().map(fold);
    let position = filter.position.as_deref().map(fold);
    let mut players: Vec<&Player> = ds
        .players
        .iter()
        .filter(|p| name.as_deref().is_none_or(|n| fold(&p.name).contains(n)))
        .filter(|p| nationality.as_deref().is_none_or(|n| fold(&p.nationality) == n))
        .filter(|p| club.as_deref().is_none_or(|c| fold(&p.club).contains(c)))
        .filter(|p| position.as_deref().is_none_or(|pos| fold(&p.position) == pos))
        .filter(|p| filter.min_overall.is_none_or(|min| p.overall >= min))
        .collect();
    players.sort_by(|a, b| b.overall.cmp(&a.overall).then(a.name.cmp(&b.name)));
    players.truncate(limit);
    players
}
