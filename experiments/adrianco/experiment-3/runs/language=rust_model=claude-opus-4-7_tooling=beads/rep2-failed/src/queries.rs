//! Query layer: match, team, player, competition and statistics queries.
//!
//! Every function here works against a loaded `Database`. Match-centric
//! queries operate on `Database::canonical_matches` so that overlapping
//! datasets do not double-count results. Functions return plain data
//! structures; presentation (text formatting for MCP responses) lives in
//! `mcp.rs`, keeping query logic independently testable.

use std::collections::{BTreeSet, HashMap};

use crate::data::Database;
use crate::models::{Date, Match, Outcome, Player};
use crate::normalize::{competition_matches, fold, team_matches};

// ---------------------------------------------------------------------------
// Match queries
// ---------------------------------------------------------------------------

/// Which side of a fixture a single-team query should consider.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Venue {
    Home,
    Away,
    Either,
}

impl Venue {
    /// Parse a venue from a tool argument; unknown / empty values mean `Either`.
    pub fn parse(s: Option<&str>) -> Venue {
        match s.map(|v| v.trim().to_lowercase()).as_deref() {
            Some("home") => Venue::Home,
            Some("away") => Venue::Away,
            _ => Venue::Either,
        }
    }
}

/// Criteria for `find_matches`.
#[derive(Debug, Default, Clone)]
pub struct MatchFilter {
    pub team: Option<String>,
    pub team2: Option<String>,
    pub competition: Option<String>,
    pub season: Option<i32>,
    pub date_from: Option<Date>,
    pub date_to: Option<Date>,
    pub venue: Option<Venue>,
}

/// Find matches satisfying every supplied criterion, most recent first.
///
/// When both `team` and `team2` are set, the fixture must be between those two
/// clubs (in either home/away orientation). With only `team` set, `venue`
/// restricts to home/away/either games for that club.
pub fn find_matches<'a>(db: &'a Database, f: &MatchFilter) -> Vec<&'a Match> {
    let venue = f.venue.unwrap_or(Venue::Either);
    let mut result: Vec<&Match> = db
        .canonical_matches()
        .into_iter()
        .filter(|m| {
            if let Some(s) = f.season {
                if m.season != s {
                    return false;
                }
            }
            if let Some(c) = &f.competition {
                if !competition_matches(c, &m.competition) {
                    return false;
                }
            }
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
            match (&f.team, &f.team2) {
                (Some(t1), Some(t2)) => {
                    let direct = team_matches(t1, &m.home_key) && team_matches(t2, &m.away_key);
                    let swapped = team_matches(t1, &m.away_key) && team_matches(t2, &m.home_key);
                    if !(direct || swapped) {
                        return false;
                    }
                }
                (Some(t), None) => {
                    let home = team_matches(t, &m.home_key);
                    let away = team_matches(t, &m.away_key);
                    let ok = match venue {
                        Venue::Home => home,
                        Venue::Away => away,
                        Venue::Either => home || away,
                    };
                    if !ok {
                        return false;
                    }
                }
                _ => {}
            }
            true
        })
        .collect();

    result.sort_by(|a, b| b.date.cmp(&a.date));
    result
}

// ---------------------------------------------------------------------------
// Team queries
// ---------------------------------------------------------------------------

/// Aggregated win/draw/loss and goal record for one team.
#[derive(Debug, Clone, Default)]
pub struct TeamStats {
    pub team: String,
    pub matches: usize,
    pub wins: usize,
    pub draws: usize,
    pub losses: usize,
    pub goals_for: i32,
    pub goals_against: i32,
}

impl TeamStats {
    pub fn goal_diff(&self) -> i32 {
        self.goals_for - self.goals_against
    }
    pub fn points(&self) -> usize {
        self.wins * 3 + self.draws
    }
    pub fn win_rate(&self) -> f64 {
        if self.matches == 0 {
            0.0
        } else {
            self.wins as f64 / self.matches as f64 * 100.0
        }
    }
}

/// Compute a team's record, optionally restricted by season, competition and
/// venue (home / away / either).
pub fn team_stats(
    db: &Database,
    team: &str,
    season: Option<i32>,
    competition: Option<&str>,
    venue: Venue,
) -> TeamStats {
    let mut stats = TeamStats {
        team: team.to_string(),
        ..Default::default()
    };

    for m in db.canonical_matches() {
        if let Some(s) = season {
            if m.season != s {
                continue;
            }
        }
        if let Some(c) = competition {
            if !competition_matches(c, &m.competition) {
                continue;
            }
        }
        let is_home = team_matches(team, &m.home_key);
        let is_away = team_matches(team, &m.away_key);
        let counts = match venue {
            Venue::Home => is_home,
            Venue::Away => is_away,
            Venue::Either => is_home || is_away,
        };
        if !counts {
            continue;
        }
        // A team should not be counted twice if it somehow appears on both
        // sides; prefer the home perspective.
        let (gf, ga, win, loss) = if is_home {
            (
                m.home_goal,
                m.away_goal,
                m.outcome() == Outcome::HomeWin,
                m.outcome() == Outcome::AwayWin,
            )
        } else {
            (
                m.away_goal,
                m.home_goal,
                m.outcome() == Outcome::AwayWin,
                m.outcome() == Outcome::HomeWin,
            )
        };
        stats.matches += 1;
        stats.goals_for += gf;
        stats.goals_against += ga;
        if win {
            stats.wins += 1;
        } else if loss {
            stats.losses += 1;
        } else {
            stats.draws += 1;
        }
    }
    stats
}

/// Head-to-head summary between two clubs.
#[derive(Debug, Clone)]
pub struct HeadToHead<'a> {
    pub team1: String,
    pub team2: String,
    pub team1_wins: usize,
    pub team2_wins: usize,
    pub draws: usize,
    pub team1_goals: i32,
    pub team2_goals: i32,
    pub matches: Vec<&'a Match>,
}

/// Compute the head-to-head record between `team1` and `team2`.
pub fn head_to_head<'a>(db: &'a Database, team1: &str, team2: &str) -> HeadToHead<'a> {
    let mut h = HeadToHead {
        team1: team1.to_string(),
        team2: team2.to_string(),
        team1_wins: 0,
        team2_wins: 0,
        draws: 0,
        team1_goals: 0,
        team2_goals: 0,
        matches: Vec::new(),
    };

    for m in db.canonical_matches() {
        let t1_home = team_matches(team1, &m.home_key);
        let t2_home = team_matches(team2, &m.home_key);
        let t1_away = team_matches(team1, &m.away_key);
        let t2_away = team_matches(team2, &m.away_key);

        let (t1_is_home, t1_is_away) = if t1_home && t2_away {
            (true, false)
        } else if t1_away && t2_home {
            (false, true)
        } else {
            continue;
        };

        let (t1_goals, t2_goals, t1_win, t2_win) = if t1_is_home {
            (
                m.home_goal,
                m.away_goal,
                m.outcome() == Outcome::HomeWin,
                m.outcome() == Outcome::AwayWin,
            )
        } else {
            let _ = t1_is_away;
            (
                m.away_goal,
                m.home_goal,
                m.outcome() == Outcome::AwayWin,
                m.outcome() == Outcome::HomeWin,
            )
        };

        h.team1_goals += t1_goals;
        h.team2_goals += t2_goals;
        if t1_win {
            h.team1_wins += 1;
        } else if t2_win {
            h.team2_wins += 1;
        } else {
            h.draws += 1;
        }
        h.matches.push(m);
    }

    h.matches.sort_by(|a, b| b.date.cmp(&a.date));
    h
}

// ---------------------------------------------------------------------------
// Player queries
// ---------------------------------------------------------------------------

/// Sort order for player query results.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PlayerSort {
    Overall,
    Potential,
    Age,
    Name,
}

impl PlayerSort {
    pub fn parse(s: Option<&str>) -> PlayerSort {
        match s.map(|v| v.trim().to_lowercase()).as_deref() {
            Some("potential") => PlayerSort::Potential,
            Some("age") => PlayerSort::Age,
            Some("name") => PlayerSort::Name,
            _ => PlayerSort::Overall,
        }
    }
}

/// Criteria for `find_players`.
#[derive(Debug, Default, Clone)]
pub struct PlayerFilter {
    pub name: Option<String>,
    pub nationality: Option<String>,
    pub club: Option<String>,
    pub position: Option<String>,
    pub min_overall: Option<i32>,
}

/// Find players matching the filter, sorted by `sort`.
pub fn find_players<'a>(
    db: &'a Database,
    f: &PlayerFilter,
    sort: PlayerSort,
) -> Vec<&'a Player> {
    let name_q = f.name.as_deref().map(fold);
    let nat_q = f.nationality.as_deref().map(fold);
    let club_q = f.club.as_deref().map(fold);
    let pos_q = f.position.as_deref().map(fold);

    let mut result: Vec<&Player> = db
        .players
        .iter()
        .filter(|p| {
            if let Some(q) = &name_q {
                if !p.name_key.contains(q.as_str()) {
                    return false;
                }
            }
            if let Some(q) = &nat_q {
                let n = fold(&p.nationality);
                if !(n.contains(q.as_str()) || q.contains(n.as_str())) {
                    return false;
                }
            }
            if let Some(q) = &club_q {
                if !fold(&p.club).contains(q.as_str()) {
                    return false;
                }
            }
            if let Some(q) = &pos_q {
                if !fold(&p.position).contains(q.as_str()) {
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

    match sort {
        PlayerSort::Overall => result.sort_by(|a, b| {
            b.overall.cmp(&a.overall).then(b.potential.cmp(&a.potential))
        }),
        PlayerSort::Potential => result.sort_by(|a, b| {
            b.potential.cmp(&a.potential).then(b.overall.cmp(&a.overall))
        }),
        PlayerSort::Age => result.sort_by(|a, b| a.age.cmp(&b.age)),
        PlayerSort::Name => result.sort_by(|a, b| a.name_key.cmp(&b.name_key)),
    }
    result
}

// ---------------------------------------------------------------------------
// Competition queries
// ---------------------------------------------------------------------------

/// One row of a calculated league table.
#[derive(Debug, Clone, Default)]
pub struct StandingRow {
    pub team: String,
    pub played: u32,
    pub wins: u32,
    pub draws: u32,
    pub losses: u32,
    pub goals_for: i32,
    pub goals_against: i32,
}

impl StandingRow {
    pub fn points(&self) -> u32 {
        self.wins * 3 + self.draws
    }
    pub fn goal_diff(&self) -> i32 {
        self.goals_for - self.goals_against
    }
}

/// Resolve a free-form competition query to one canonical competition name.
///
/// When the query is ambiguous (e.g. "brasileirão" matches Séries A/B/C) the
/// resolver prefers an exact fold-match, then Série A, then the first
/// alphabetical candidate.
pub fn resolve_competition(db: &Database, query: &str) -> Option<String> {
    let comps: BTreeSet<&str> = db.matches.iter().map(|m| m.competition.as_str()).collect();
    let matching: Vec<&str> = comps
        .iter()
        .copied()
        .filter(|c| competition_matches(query, c))
        .collect();

    match matching.len() {
        0 => None,
        1 => Some(matching[0].to_string()),
        _ => {
            let qf = fold(query);
            matching
                .iter()
                .find(|c| fold(c) == qf)
                .or_else(|| matching.iter().find(|c| c.contains("Série A")))
                .or_else(|| matching.first())
                .map(|c| c.to_string())
        }
    }
}

/// Build a league table for a competition+season, calculated from results.
///
/// Rows are sorted by points, then goal difference, then goals scored, then
/// team name — the standard tie-break order for Brazilian league tables.
pub fn standings(db: &Database, competition: &str, season: i32) -> Vec<StandingRow> {
    let mut table: HashMap<String, StandingRow> = HashMap::new();

    for m in db.canonical_matches() {
        if m.season != season || m.competition != competition {
            continue;
        }
        let home = table.entry(m.home_key.clone()).or_insert_with(|| StandingRow {
            team: m.home.clone(),
            ..Default::default()
        });
        home.played += 1;
        home.goals_for += m.home_goal;
        home.goals_against += m.away_goal;
        match m.outcome() {
            Outcome::HomeWin => home.wins += 1,
            Outcome::AwayWin => home.losses += 1,
            Outcome::Draw => home.draws += 1,
        }

        let away = table.entry(m.away_key.clone()).or_insert_with(|| StandingRow {
            team: m.away.clone(),
            ..Default::default()
        });
        away.played += 1;
        away.goals_for += m.away_goal;
        away.goals_against += m.home_goal;
        match m.outcome() {
            Outcome::AwayWin => away.wins += 1,
            Outcome::HomeWin => away.losses += 1,
            Outcome::Draw => away.draws += 1,
        }
    }

    let mut rows: Vec<StandingRow> = table.into_values().collect();
    rows.sort_by(|a, b| {
        b.points()
            .cmp(&a.points())
            .then(b.goal_diff().cmp(&a.goal_diff()))
            .then(b.goals_for.cmp(&a.goals_for))
            .then(a.team.cmp(&b.team))
    });
    rows
}

/// Metadata about one competition present in the data.
#[derive(Debug, Clone)]
pub struct CompetitionInfo {
    pub name: String,
    pub matches: usize,
    pub first_season: i32,
    pub last_season: i32,
}

/// List every competition in the (de-duplicated) data with coverage info.
pub fn list_competitions(db: &Database) -> Vec<CompetitionInfo> {
    let mut acc: HashMap<&str, (usize, i32, i32)> = HashMap::new();
    for m in db.canonical_matches() {
        let entry = acc
            .entry(m.competition.as_str())
            .or_insert((0, i32::MAX, i32::MIN));
        entry.0 += 1;
        if m.season > 0 {
            entry.1 = entry.1.min(m.season);
            entry.2 = entry.2.max(m.season);
        }
    }
    let mut out: Vec<CompetitionInfo> = acc
        .into_iter()
        .map(|(name, (matches, first, last))| CompetitionInfo {
            name: name.to_string(),
            matches,
            first_season: if first == i32::MAX { 0 } else { first },
            last_season: if last == i32::MIN { 0 } else { last },
        })
        .collect();
    out.sort_by(|a, b| b.matches.cmp(&a.matches).then(a.name.cmp(&b.name)));
    out
}

// ---------------------------------------------------------------------------
// Statistical analysis
// ---------------------------------------------------------------------------

/// Aggregate statistics over a set of matches.
#[derive(Debug, Clone)]
pub struct CompetitionStats<'a> {
    pub label: String,
    pub matches: usize,
    pub total_goals: i32,
    pub home_wins: usize,
    pub away_wins: usize,
    pub draws: usize,
    /// Highest-margin results, biggest first.
    pub biggest_wins: Vec<&'a Match>,
    /// Teams with the most goals scored: (team, goals).
    pub top_scoring_teams: Vec<(String, i32)>,
}

impl CompetitionStats<'_> {
    pub fn avg_goals(&self) -> f64 {
        if self.matches == 0 {
            0.0
        } else {
            self.total_goals as f64 / self.matches as f64
        }
    }
    pub fn pct(&self, count: usize) -> f64 {
        if self.matches == 0 {
            0.0
        } else {
            count as f64 / self.matches as f64 * 100.0
        }
    }
}

/// Compute aggregate statistics, optionally scoped to a competition and/or
/// season. With no scope it covers the whole de-duplicated dataset.
pub fn competition_stats<'a>(
    db: &'a Database,
    competition: Option<&str>,
    season: Option<i32>,
) -> CompetitionStats<'a> {
    let selected: Vec<&Match> = db
        .canonical_matches()
        .into_iter()
        .filter(|m| {
            competition.map_or(true, |c| competition_matches(c, &m.competition))
                && season.map_or(true, |s| m.season == s)
        })
        .collect();

    let mut stats = CompetitionStats {
        label: scope_label(competition, season),
        matches: selected.len(),
        total_goals: 0,
        home_wins: 0,
        away_wins: 0,
        draws: 0,
        biggest_wins: Vec::new(),
        top_scoring_teams: Vec::new(),
    };

    let mut goals_by_team: HashMap<&str, i32> = HashMap::new();
    for m in &selected {
        stats.total_goals += m.total_goals();
        match m.outcome() {
            Outcome::HomeWin => stats.home_wins += 1,
            Outcome::AwayWin => stats.away_wins += 1,
            Outcome::Draw => stats.draws += 1,
        }
        *goals_by_team.entry(m.home_key.as_str()).or_default() += m.home_goal;
        *goals_by_team.entry(m.away_key.as_str()).or_default() += m.away_goal;
    }

    let mut biggest = selected.clone();
    biggest.sort_by(|a, b| {
        b.margin()
            .cmp(&a.margin())
            .then(b.total_goals().cmp(&a.total_goals()))
            .then(a.date.cmp(&b.date))
    });
    biggest.truncate(10);
    stats.biggest_wins = biggest;

    // Resolve goal totals back to a display name for each team key.
    let mut display: HashMap<&str, &str> = HashMap::new();
    for m in &selected {
        display.entry(m.home_key.as_str()).or_insert(m.home.as_str());
        display.entry(m.away_key.as_str()).or_insert(m.away.as_str());
    }
    let mut scorers: Vec<(String, i32)> = goals_by_team
        .into_iter()
        .map(|(k, g)| (display.get(k).copied().unwrap_or(k).to_string(), g))
        .collect();
    scorers.sort_by(|a, b| b.1.cmp(&a.1).then(a.0.cmp(&b.0)));
    scorers.truncate(10);
    stats.top_scoring_teams = scorers;

    stats
}

fn scope_label(competition: Option<&str>, season: Option<i32>) -> String {
    match (competition, season) {
        (Some(c), Some(s)) => format!("{c} {s}"),
        (Some(c), None) => c.to_string(),
        (None, Some(s)) => format!("All competitions, {s}"),
        (None, None) => "All competitions, all seasons".to_string(),
    }
}

/// List the distinct seasons present for a competition (ascending).
pub fn seasons_for(db: &Database, competition: &str) -> Vec<i32> {
    let mut set: BTreeSet<i32> = BTreeSet::new();
    for m in db.canonical_matches() {
        if m.competition == competition && m.season > 0 {
            set.insert(m.season);
        }
    }
    set.into_iter().collect()
}

/// Resolve a team query to the most common display name found in the data,
/// falling back to the supplied query when no match exists.
pub fn canonical_team_name(db: &Database, query: &str) -> String {
    let mut counts: HashMap<&str, usize> = HashMap::new();
    for m in &db.matches {
        if team_matches(query, &m.home_key) {
            *counts.entry(m.home.as_str()).or_default() += 1;
        }
        if team_matches(query, &m.away_key) {
            *counts.entry(m.away.as_str()).or_default() += 1;
        }
    }
    counts
        .into_iter()
        .max_by_key(|(_, c)| *c)
        .map(|(name, _)| name.to_string())
        .unwrap_or_else(|| query.to_string())
}
