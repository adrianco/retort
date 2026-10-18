//! Context: match, team and competition queries over a [`Dataset`].
//!
//! Each function returns plain data; formatting for the LLM lives in `mcp.rs`.
//! Team arguments are raw user text (e.g. "Palmeiras-SP") and are normalised
//! with [`Team::parse`] before comparison.

use std::collections::HashMap;

use crate::data::{Dataset, Match, Player};
use crate::normalize::{Team, canonical_competition};

/// Filters for [`search_matches`]. All fields are optional and ANDed together.
#[derive(Debug, Default, Clone)]
pub struct MatchFilter {
    /// Team on either side.
    pub team: Option<String>,
    /// Second team; when set together with `team`, only fixtures between them.
    pub opponent: Option<String>,
    pub competition: Option<String>,
    pub season: Option<i32>,
    /// Inclusive ISO dates `YYYY-MM-DD`.
    pub date_from: Option<String>,
    pub date_to: Option<String>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Venue {
    Any,
    Home,
    Away,
}

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
    pub fn win_rate(&self) -> f64 {
        if self.played == 0 {
            0.0
        } else {
            f64::from(self.wins) / f64::from(self.played) * 100.0
        }
    }

    fn add(&mut self, result: char, scored: u32, conceded: u32) {
        self.played += 1;
        self.goals_for += scored;
        self.goals_against += conceded;
        match result {
            'W' => self.wins += 1,
            'D' => self.draws += 1,
            _ => self.losses += 1,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StandingRow {
    pub team: String,
    pub points: u32,
    pub record: Record,
}

impl StandingRow {
    pub fn goal_difference(&self) -> i64 {
        i64::from(self.record.goals_for) - i64::from(self.record.goals_against)
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct LeagueStats {
    pub matches: usize,
    pub avg_goals: f64,
    pub home_win_pct: f64,
    pub draw_pct: f64,
    pub away_win_pct: f64,
    pub biggest_wins: Vec<Match>,
}

/// Parses a raw team argument, returning `None` for empty input.
fn team_arg(raw: &Option<String>) -> Option<Team> {
    raw.as_deref()
        .map(str::trim)
        .filter(|s| !s.is_empty())
        .map(Team::parse)
}

/// Canonicalises a competition argument; unknown names are an error.
pub fn competition_arg(raw: &Option<String>) -> Result<Option<&'static str>, String> {
    match raw.as_deref().map(str::trim).filter(|s| !s.is_empty()) {
        None => Ok(None),
        Some(text) => canonical_competition(text)
            .map(Some)
            .ok_or_else(|| format!("unknown competition `{text}`")),
    }
}

fn involves(m: &Match, team: &Team) -> bool {
    m.home.matches(team) || m.away.matches(team)
}

fn is_between(m: &Match, a: &Team, b: &Team) -> bool {
    (m.home.matches(a) && m.away.matches(b)) || (m.home.matches(b) && m.away.matches(a))
}

/// Matches satisfying `filter`, most recent first.
pub fn search_matches<'a>(ds: &'a Dataset, filter: &MatchFilter) -> Result<Vec<&'a Match>, String> {
    let team = team_arg(&filter.team);
    let opponent = team_arg(&filter.opponent);
    let competition = competition_arg(&filter.competition)?;
    let mut out: Vec<&Match> = ds
        .matches
        .iter()
        .filter(|m| match (&team, &opponent) {
            (Some(a), Some(b)) => is_between(m, a, b),
            (Some(a), None) => involves(m, a),
            (None, Some(b)) => involves(m, b),
            (None, None) => true,
        })
        .filter(|m| competition.is_none_or(|c| m.competition == c))
        .filter(|m| filter.season.is_none_or(|s| m.season == s))
        .filter(|m| {
            filter
                .date_from
                .as_ref()
                .is_none_or(|d| m.date.as_str() >= d.as_str())
        })
        .filter(|m| {
            filter
                .date_to
                .as_ref()
                .is_none_or(|d| m.date.as_str() <= d.as_str())
        })
        .collect();
    out.sort_by(|a, b| b.date.cmp(&a.date));
    Ok(out)
}

/// Win/draw/loss and goals for `team`, optionally restricted by season,
/// competition and venue.
pub fn team_record(
    ds: &Dataset,
    team: &str,
    season: Option<i32>,
    competition: Option<&str>,
    venue: Venue,
) -> Result<(Team, Record), String> {
    let team = Team::parse(team);
    let competition = competition_arg(&competition.map(str::to_string))?;
    let mut rec = Record::default();
    for m in &ds.matches {
        if season.is_some_and(|s| m.season != s) || competition.is_some_and(|c| m.competition != c)
        {
            continue;
        }
        let at_home = m.home.matches(&team);
        let at_away = m.away.matches(&team);
        let venue_ok = match venue {
            Venue::Any => at_home || at_away,
            Venue::Home => at_home,
            Venue::Away => at_away,
        };
        if !venue_ok {
            continue;
        }
        if let (Some(result), Some((scored, conceded))) = (m.result_for(&team), m.goals_for(&team))
        {
            rec.add(result, scored, conceded);
        }
    }
    Ok((team, rec))
}

/// All meetings between two teams, most recent first, plus the head-to-head
/// tally from `a`'s perspective.
pub fn head_to_head(
    ds: &Dataset,
    a: &str,
    b: &str,
    competition: Option<&str>,
) -> Result<(Team, Team, Vec<Match>, Record), String> {
    let (ta, tb) = (Team::parse(a), Team::parse(b));
    let competition = competition_arg(&competition.map(str::to_string))?;
    let mut meetings: Vec<Match> = ds
        .matches
        .iter()
        .filter(|m| is_between(m, &ta, &tb))
        .filter(|m| competition.is_none_or(|c| m.competition == c))
        .cloned()
        .collect();
    meetings.sort_by(|x, y| y.date.cmp(&x.date));
    let mut rec = Record::default();
    for m in &meetings {
        if let (Some(result), Some((scored, conceded))) = (m.result_for(&ta), m.goals_for(&ta)) {
            rec.add(result, scored, conceded);
        }
    }
    Ok((ta, tb, meetings, rec))
}

/// League table for one competition and season, using 3/1/0 points.
/// Sorted by points, then goal difference, then goals scored.
pub fn standings(ds: &Dataset, competition: &str, season: i32) -> Result<Vec<StandingRow>, String> {
    let competition = competition_arg(&Some(competition.to_string()))?
        .ok_or_else(|| "competition is required".to_string())?;
    let mut table: HashMap<String, StandingRow> = HashMap::new();
    for m in ds
        .matches
        .iter()
        .filter(|m| m.competition == competition && m.season == season)
    {
        for team in [&m.home, &m.away] {
            let (scored, conceded) = m.goals_for(team).unwrap_or((0, 0));
            let result = m.result_for(team).unwrap_or('D');
            let row = table.entry(team.identity()).or_insert_with(|| StandingRow {
                team: display_name(team),
                points: 0,
                record: Record::default(),
            });
            row.record.add(result, scored, conceded);
            row.points += match result {
                'W' => 3,
                'D' => 1,
                _ => 0,
            };
        }
    }
    let mut rows: Vec<StandingRow> = table.into_values().collect();
    rows.sort_by(|a, b| {
        b.points
            .cmp(&a.points)
            .then(b.goal_difference().cmp(&a.goal_difference()))
            .then(b.record.goals_for.cmp(&a.record.goals_for))
            .then(a.team.cmp(&b.team))
    });
    Ok(rows)
}

/// Team label for standings: name, plus state when the team is ambiguous.
fn display_name(team: &Team) -> String {
    match &team.state {
        Some(s) => format!("{} ({})", team.name, s),
        None => team.name.clone(),
    }
}

/// Aggregate statistics for the matches of a competition (optionally one season).
pub fn league_stats(
    ds: &Dataset,
    competition: Option<&str>,
    season: Option<i32>,
) -> Result<LeagueStats, String> {
    let competition = competition_arg(&competition.map(str::to_string))?;
    let games: Vec<&Match> = ds
        .matches
        .iter()
        .filter(|m| competition.is_none_or(|c| m.competition == c))
        .filter(|m| season.is_none_or(|s| m.season == s))
        .collect();
    let n = games.len();
    let pct = |count: usize| {
        if n == 0 {
            0.0
        } else {
            count as f64 / n as f64 * 100.0
        }
    };
    let total_goals: u64 = games
        .iter()
        .map(|m| u64::from(m.home_goals + m.away_goals))
        .sum();
    let home_wins = games.iter().filter(|m| m.home_goals > m.away_goals).count();
    let draws = games
        .iter()
        .filter(|m| m.home_goals == m.away_goals)
        .count();
    let away_wins = games.iter().filter(|m| m.home_goals < m.away_goals).count();
    let mut biggest_wins: Vec<Match> = games.iter().map(|m| (*m).clone()).collect();
    biggest_wins.sort_by_key(|m| std::cmp::Reverse(m.home_goals.abs_diff(m.away_goals)));
    biggest_wins.truncate(5);
    Ok(LeagueStats {
        matches: n,
        avg_goals: if n == 0 {
            0.0
        } else {
            total_goals as f64 / n as f64
        },
        home_win_pct: pct(home_wins),
        draw_pct: pct(draws),
        away_win_pct: pct(away_wins),
        biggest_wins,
    })
}

/// Filters for [`search_players`]. Text filters are case- and accent-insensitive.
#[derive(Debug, Default, Clone)]
pub struct PlayerFilter {
    /// Substring of the player's name (FIFA abbreviates, e.g. "L. Messi").
    pub name: Option<String>,
    pub nationality: Option<String>,
    /// Substring of the club name.
    pub club: Option<String>,
    /// Exact position code, e.g. "ST", "GK".
    pub position: Option<String>,
    pub min_overall: Option<u32>,
}

/// Players matching `filter`, highest overall rating first.
pub fn search_players<'a>(ds: &'a Dataset, filter: &PlayerFilter) -> Vec<&'a Player> {
    let contains = |hay: &str, needle: &Option<String>| {
        needle
            .as_ref()
            .is_none_or(|n| crate::normalize::fold(hay).contains(&crate::normalize::fold(n)))
    };
    let mut out: Vec<&Player> =
        ds.players
            .iter()
            .filter(|p| contains(&p.name, &filter.name))
            .filter(|p| {
                filter.nationality.as_ref().is_none_or(|n| {
                    crate::normalize::fold(&p.nationality) == crate::normalize::fold(n)
                })
            })
            .filter(|p| {
                p.club
                    .as_deref()
                    .map_or(filter.club.is_none(), |c| contains(c, &filter.club))
            })
            .filter(|p| {
                filter.position.as_ref().is_none_or(|pos| {
                    p.position
                        .as_deref()
                        .is_some_and(|x| x.eq_ignore_ascii_case(pos.trim()))
                })
            })
            .filter(|p| filter.min_overall.is_none_or(|min| p.overall >= min))
            .collect();
    out.sort_by(|a, b| b.overall.cmp(&a.overall).then(a.name.cmp(&b.name)));
    out
}
