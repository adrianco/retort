//! ============================================================================
//! Module: db
//!
//! Context
//! -------
//! The in-memory knowledge graph and query engine. `Database` owns all matches
//! and players loaded from the CSV datasets and exposes typed query methods that
//! the MCP tool layer (`mcp`) turns into natural-language answers.
//!
//! Team identity is resolved through normalized keys (see `normalize`); a
//! key -> canonical-display-name index lets fuzzy user input ("palmeiras",
//! "São Paulo", "flamengo-rj") map onto a single club node. All aggregate
//! queries (records, standings, league stats) are computed on demand from the
//! match edges so results always reflect exactly the provided data.
//! ============================================================================

use std::collections::HashMap;
use std::path::Path;

use serde::Serialize;

use crate::loader::{self, LoadReport};
use crate::model::{Match, Outcome, Player};
use crate::normalize::{search_key, team_key};

/// Filter criteria for [`Database::find_matches`].
#[derive(Debug, Default, Clone)]
pub struct MatchFilter {
    /// Normalized key of a team that must appear (home or away).
    pub team: Option<String>,
    /// Normalized key of an opponent (combined with `team` for head-to-head).
    pub opponent: Option<String>,
    /// Case-insensitive substring on the competition name.
    pub competition: Option<String>,
    pub season: Option<i32>,
    /// Inclusive ISO date lower bound ("2019-01-01").
    pub date_from: Option<String>,
    /// Inclusive ISO date upper bound.
    pub date_to: Option<String>,
    /// "home" or "away" to restrict `team`'s venue.
    pub venue: Option<String>,
}

/// Win/draw/loss aggregate for a team.
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
    pub fn points(&self) -> u32 {
        self.wins * 3 + self.draws
    }
    pub fn goal_diff(&self) -> i32 {
        self.goals_for - self.goals_against
    }
    pub fn win_rate(&self) -> f64 {
        if self.matches == 0 {
            0.0
        } else {
            self.wins as f64 / self.matches as f64 * 100.0
        }
    }
    fn add(&mut self, scored: i32, conceded: i32, outcome: Outcome) {
        self.matches += 1;
        self.goals_for += scored;
        self.goals_against += conceded;
        match outcome {
            Outcome::Win => self.wins += 1,
            Outcome::Draw => self.draws += 1,
            Outcome::Loss => self.losses += 1,
        }
    }
}

/// One row of a computed league table.
#[derive(Debug, Clone, Serialize)]
pub struct StandingRow {
    pub team: String,
    pub record: Record,
}

/// Head-to-head summary between two teams.
#[derive(Debug, Clone, Serialize)]
pub struct HeadToHead {
    pub team_a: String,
    pub team_b: String,
    pub total: u32,
    pub a_wins: u32,
    pub b_wins: u32,
    pub draws: u32,
    pub a_goals: i32,
    pub b_goals: i32,
}

/// Aggregate statistics across a set of matches.
#[derive(Debug, Clone, Serialize)]
pub struct LeagueStats {
    pub matches: u32,
    pub total_goals: i32,
    pub avg_goals_per_match: f64,
    pub home_wins: u32,
    pub away_wins: u32,
    pub draws: u32,
    pub home_win_rate: f64,
}

/// Player search criteria for [`Database::search_players`].
#[derive(Debug, Default, Clone)]
pub struct PlayerFilter {
    pub name: Option<String>,
    pub nationality: Option<String>,
    pub club: Option<String>,
    pub position: Option<String>,
    pub min_overall: Option<i32>,
}

/// The knowledge graph: matches, players, and a team-name index.
pub struct Database {
    matches: Vec<Match>,
    players: Vec<Player>,
    /// Normalized key -> canonical display name (most frequent spelling).
    team_names: HashMap<String, String>,
    report: LoadReport,
}

impl Database {
    /// Build a database from already-parsed records (used by tests).
    pub fn from_parts(matches: Vec<Match>, players: Vec<Player>, report: LoadReport) -> Self {
        let matches = Self::dedup_matches(matches);
        let team_names = Self::index_team_names(&matches);
        Database {
            matches,
            players,
            team_names,
            report,
        }
    }

    /// Collapse the same fixture appearing in multiple source files into one
    /// match. The Série A and Copa do Brasil seasons overlap across datasets, so
    /// without this a 2019 standings query would triple-count every result.
    ///
    /// Two records are considered the same fixture when competition, season,
    /// date, both teams and the final score all match. The surviving record is
    /// enriched: a round/stage label and extended stats (shots/corners) are
    /// kept from whichever duplicate carries them.
    fn dedup_matches(matches: Vec<Match>) -> Vec<Match> {
        use std::collections::HashMap;
        let mut index: HashMap<String, usize> = HashMap::new();
        let mut out: Vec<Match> = Vec::with_capacity(matches.len());

        for m in matches {
            // Fixtures without a date can't be reliably de-duplicated against
            // other datasets, so keep them as-is.
            let key = if m.date.is_empty() {
                None
            } else {
                Some(format!(
                    "{}|{}|{}|{}|{}|{}-{}",
                    m.competition, m.season, m.date, m.home_key, m.away_key, m.home_goal, m.away_goal
                ))
            };

            match key.as_ref().and_then(|k| index.get(k)).copied() {
                Some(i) => {
                    // Merge useful fields into the already-stored record.
                    if out[i].stage.is_empty() && !m.stage.is_empty() {
                        out[i].stage = m.stage;
                    }
                    if out[i].extras.is_empty() && !m.extras.is_empty() {
                        out[i].extras = m.extras;
                    }
                }
                None => {
                    if let Some(k) = key {
                        index.insert(k, out.len());
                    }
                    out.push(m);
                }
            }
        }
        out
    }

    /// Load every dataset under `data_dir` and build the database.
    pub fn load_from_dir(data_dir: &Path) -> Self {
        let mut matches = Vec::new();
        let mut players = Vec::new();
        let report = loader::load_all(data_dir, &mut matches, &mut players);
        Self::from_parts(matches, players, report)
    }

    /// Build the key -> display-name index, choosing the most common spelling
    /// (with a tie-break preferring names that carry accents/longer forms).
    fn index_team_names(matches: &[Match]) -> HashMap<String, String> {
        let mut counts: HashMap<String, HashMap<String, u32>> = HashMap::new();
        for m in matches {
            *counts
                .entry(m.home_key.clone())
                .or_default()
                .entry(m.home_team.clone())
                .or_default() += 1;
            *counts
                .entry(m.away_key.clone())
                .or_default()
                .entry(m.away_team.clone())
                .or_default() += 1;
        }
        counts
            .into_iter()
            .map(|(key, spellings)| {
                let best = spellings
                    .into_iter()
                    .max_by(|a, b| {
                        a.1.cmp(&b.1)
                            .then(a.0.chars().count().cmp(&b.0.chars().count()))
                    })
                    .map(|(name, _)| name)
                    .unwrap_or_else(|| key.clone());
                (key, best)
            })
            .collect()
    }

    pub fn report(&self) -> &LoadReport {
        &self.report
    }
    pub fn match_count(&self) -> usize {
        self.matches.len()
    }
    pub fn player_count(&self) -> usize {
        self.players.len()
    }
    pub fn matches(&self) -> &[Match] {
        &self.matches
    }

    /// Canonical display name for a normalized key, if the team is known.
    pub fn display_for_key(&self, key: &str) -> Option<&str> {
        self.team_names.get(key).map(|s| s.as_str())
    }

    /// Resolve free-text user input to a known team key.
    ///
    /// Tries, in order: exact key match, then unique substring match against
    /// known team keys. Returns the resolved (key, display_name).
    pub fn resolve_team(&self, input: &str) -> Option<(String, String)> {
        let key = team_key(input);
        if let Some(name) = self.team_names.get(&key) {
            return Some((key, name.clone()));
        }
        // Substring search: collect keys that contain the query (or vice versa).
        let mut hits: Vec<&String> = self
            .team_names
            .keys()
            .filter(|k| k.contains(&key) || key.contains(k.as_str()))
            .collect();
        hits.sort();
        hits.dedup();
        // Prefer the shortest matching key (most specific full-name match).
        hits.into_iter()
            .min_by_key(|k| (k.len() as i64 - key.len() as i64).abs())
            .map(|k| (k.clone(), self.team_names[k].clone()))
    }

    /// Find matches satisfying `filter`, newest first.
    pub fn find_matches(&self, filter: &MatchFilter) -> Vec<&Match> {
        let mut out: Vec<&Match> = self
            .matches
            .iter()
            .filter(|m| {
                if let Some(team) = &filter.team {
                    let ok = match filter.venue.as_deref() {
                        Some("home") => &m.home_key == team,
                        Some("away") => &m.away_key == team,
                        _ => m.involves(team),
                    };
                    if !ok {
                        return false;
                    }
                }
                if let Some(opp) = &filter.opponent {
                    if !m.involves(opp) {
                        return false;
                    }
                }
                if let Some(comp) = &filter.competition {
                    if !search_key(&m.competition).contains(&search_key(comp)) {
                        return false;
                    }
                }
                if let Some(season) = filter.season {
                    if m.season != season {
                        return false;
                    }
                }
                if let Some(from) = &filter.date_from {
                    if !m.date.is_empty() && m.date.as_str() < from.as_str() {
                        return false;
                    }
                }
                if let Some(to) = &filter.date_to {
                    if !m.date.is_empty() && m.date.as_str() > to.as_str() {
                        return false;
                    }
                }
                true
            })
            .collect();
        // Newest first; matches without a date sort last.
        out.sort_by(|a, b| b.date.cmp(&a.date));
        out
    }

    /// Compute a team's record over an optional season/competition/venue scope.
    pub fn team_record(&self, filter: &MatchFilter) -> Record {
        let team = match &filter.team {
            Some(t) => t,
            None => return Record::default(),
        };
        let mut rec = Record::default();
        for m in self.find_matches(filter) {
            if let Some(outcome) = m.outcome_for(team) {
                let (scored, conceded) = if &m.home_key == team {
                    (m.home_goal, m.away_goal)
                } else {
                    (m.away_goal, m.home_goal)
                };
                rec.add(scored, conceded, outcome);
            }
        }
        rec
    }

    /// Head-to-head record between two resolved team keys.
    pub fn head_to_head(&self, key_a: &str, key_b: &str) -> HeadToHead {
        let mut h = HeadToHead {
            team_a: self.display_for_key(key_a).unwrap_or(key_a).to_string(),
            team_b: self.display_for_key(key_b).unwrap_or(key_b).to_string(),
            total: 0,
            a_wins: 0,
            b_wins: 0,
            draws: 0,
            a_goals: 0,
            b_goals: 0,
        };
        for m in &self.matches {
            if m.involves(key_a) && m.involves(key_b) && key_a != key_b {
                h.total += 1;
                let (a_scored, b_scored) = if m.home_key == key_a {
                    (m.home_goal, m.away_goal)
                } else {
                    (m.away_goal, m.home_goal)
                };
                h.a_goals += a_scored;
                h.b_goals += b_scored;
                match a_scored.cmp(&b_scored) {
                    std::cmp::Ordering::Greater => h.a_wins += 1,
                    std::cmp::Ordering::Less => h.b_wins += 1,
                    std::cmp::Ordering::Equal => h.draws += 1,
                }
            }
        }
        h
    }

    /// Compute the standings table for a competition + season.
    pub fn standings(&self, competition: &str, season: i32) -> Vec<StandingRow> {
        let comp_key = search_key(competition);
        let mut table: HashMap<String, Record> = HashMap::new();
        for m in &self.matches {
            if m.season != season {
                continue;
            }
            if !search_key(&m.competition).contains(&comp_key) {
                continue;
            }
            if let Some(out) = m.outcome_for(&m.home_key) {
                table
                    .entry(m.home_key.clone())
                    .or_default()
                    .add(m.home_goal, m.away_goal, out);
            }
            if let Some(out) = m.outcome_for(&m.away_key) {
                table
                    .entry(m.away_key.clone())
                    .or_default()
                    .add(m.away_goal, m.home_goal, out);
            }
        }
        let mut rows: Vec<StandingRow> = table
            .into_iter()
            .map(|(key, record)| StandingRow {
                team: self.display_for_key(&key).unwrap_or(&key).to_string(),
                record,
            })
            .collect();
        // Sort by points, then goal difference, then goals for.
        rows.sort_by(|a, b| {
            b.record
                .points()
                .cmp(&a.record.points())
                .then(b.record.goal_diff().cmp(&a.record.goal_diff()))
                .then(b.record.goals_for.cmp(&a.record.goals_for))
                .then(a.team.cmp(&b.team))
        });
        rows
    }

    /// Aggregate goal/result statistics over a filtered match set.
    pub fn league_stats(&self, filter: &MatchFilter) -> LeagueStats {
        let matches = self.find_matches(filter);
        let mut stats = LeagueStats {
            matches: matches.len() as u32,
            total_goals: 0,
            avg_goals_per_match: 0.0,
            home_wins: 0,
            away_wins: 0,
            draws: 0,
            home_win_rate: 0.0,
        };
        for m in &matches {
            stats.total_goals += m.total_goals();
            match m.home_goal.cmp(&m.away_goal) {
                std::cmp::Ordering::Greater => stats.home_wins += 1,
                std::cmp::Ordering::Less => stats.away_wins += 1,
                std::cmp::Ordering::Equal => stats.draws += 1,
            }
        }
        if stats.matches > 0 {
            stats.avg_goals_per_match = stats.total_goals as f64 / stats.matches as f64;
            stats.home_win_rate = stats.home_wins as f64 / stats.matches as f64 * 100.0;
        }
        stats
    }

    /// Largest-margin victories within a filtered match set.
    pub fn biggest_wins(&self, filter: &MatchFilter, limit: usize) -> Vec<&Match> {
        let mut matches = self.find_matches(filter);
        matches.sort_by(|a, b| {
            b.margin()
                .cmp(&a.margin())
                .then(b.total_goals().cmp(&a.total_goals()))
                .then(b.date.cmp(&a.date))
        });
        matches.truncate(limit);
        matches
    }

    /// Search players by any combination of name/nationality/club/position/rating.
    pub fn search_players(&self, filter: &PlayerFilter) -> Vec<&Player> {
        let name_q = filter.name.as_ref().map(|s| search_key(s));
        let nat_q = filter.nationality.as_ref().map(|s| search_key(s));
        let club_q = filter.club.as_ref().map(|s| search_key(s));
        let pos_q = filter.position.as_ref().map(|s| search_key(s));

        let mut out: Vec<&Player> = self
            .players
            .iter()
            .filter(|p| {
                if let Some(q) = &name_q {
                    if !p.name_key.contains(q.as_str()) {
                        return false;
                    }
                }
                if let Some(q) = &nat_q {
                    if !p.nationality_key.contains(q.as_str()) {
                        return false;
                    }
                }
                if let Some(q) = &club_q {
                    if !p.club_key.contains(q.as_str()) {
                        return false;
                    }
                }
                if let Some(q) = &pos_q {
                    if search_key(&p.position) != *q {
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
            .collect();
        // Highest overall first.
        out.sort_by_key(|p| std::cmp::Reverse(p.overall.unwrap_or(0)));
        out
    }

    /// Distinct competitions a team has appeared in, with match counts.
    pub fn competitions_for_team(&self, key: &str) -> Vec<(String, u32)> {
        let mut counts: HashMap<String, u32> = HashMap::new();
        for m in &self.matches {
            if m.involves(key) {
                *counts.entry(m.competition.clone()).or_default() += 1;
            }
        }
        let mut v: Vec<(String, u32)> = counts.into_iter().collect();
        v.sort_by(|a, b| b.1.cmp(&a.1).then(a.0.cmp(&b.0)));
        v
    }

    /// List available competition names with their season ranges.
    pub fn competitions(&self) -> Vec<(String, i32, i32, u32)> {
        let mut agg: HashMap<String, (i32, i32, u32)> = HashMap::new();
        for m in &self.matches {
            let e = agg.entry(m.competition.clone()).or_insert((i32::MAX, i32::MIN, 0));
            if m.season > 0 {
                e.0 = e.0.min(m.season);
                e.1 = e.1.max(m.season);
            }
            e.2 += 1;
        }
        let mut v: Vec<(String, i32, i32, u32)> = agg
            .into_iter()
            .map(|(name, (min, max, n))| (name, if min == i32::MAX { 0 } else { min }, if max == i32::MIN { 0 } else { max }, n))
            .collect();
        v.sort_by(|a, b| b.3.cmp(&a.3).then(a.0.cmp(&b.0)));
        v
    }
}
