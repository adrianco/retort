//! ============================================================================
//! Module: store
//! Project: Brazilian Soccer MCP Server (Rust)
//!
//! Context:
//!   The in-memory "knowledge graph" over all loaded data and the query engine
//!   that powers every MCP tool. `Store` owns the full `Vec<Match>` (from all
//!   five match files) and `Vec<Player>` (FIFA), and exposes typed query
//!   methods used by the MCP layer and the BDD test-suite alike:
//!
//!     - search_matches / head_to_head            (Match Queries)
//!     - team_stats                               (Team Queries)
//!     - search_players                           (Player Queries)
//!     - standings                                (Competition Queries)
//!     - biggest_wins / average_goals / summary   (Statistical Analysis)
//!
//!   All team matching goes through `normalize::team_matches`, so callers can
//!   pass "Flamengo" and still match "Flamengo-RJ". Standings are *computed*
//!   from match results (3pts win / 1 draw), exactly as the spec requires.
//!   Results are returned as plain owned structs so they serialize cleanly to
//!   JSON and are trivial to assert on in tests.
//! ============================================================================

use crate::loader;
use crate::model::{Competition, Match, Player};
use crate::normalize::{normalize_team, team_matches, year_of};
use serde::Serialize;
use std::collections::HashMap;
use std::error::Error;
use std::path::Path;

/// Optional competition filter expressed as a free-text label from callers.
fn competition_filter(comp: Option<&str>) -> Option<Competition> {
    comp.map(Competition::from_text)
}

/// Remove duplicate matches in place, keeping the first occurrence. Two matches
/// are considered the same game when their normalized date, normalized team
/// keys and score all coincide. This collapses the overlap between the
/// different source CSVs without merging genuinely distinct fixtures.
fn dedup_matches(matches: &mut Vec<Match>) {
    use std::collections::HashSet;
    let mut seen: HashSet<(String, String, String, i32, i32)> = HashSet::new();
    matches.retain(|m| {
        // Without a date we cannot safely tell two same-team games apart, so
        // keep them all rather than risk merging distinct fixtures.
        if m.date.is_empty() {
            return true;
        }
        // De-dup on *base* (suffix-stripped) names so the same fixture written
        // "Flamengo-RJ" in one file and "Flamengo" in another still collapses.
        // Order the two team keys so home/away swaps between sources also
        // collapse, with the score oriented to the (lo, hi) team pair.
        let hb = crate::normalize::base_team(&m.home_team);
        let ab = crate::normalize::base_team(&m.away_team);
        let (t1, g1, t2, g2) = if hb <= ab {
            (hb, m.home_goal, ab, m.away_goal)
        } else {
            (ab, m.away_goal, hb, m.home_goal)
        };
        let key = (m.date.clone(), t1, t2, g1, g2);
        seen.insert(key)
    });
}

/// Which venue(s) to consider for a team in `team_stats`.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Venue {
    Home,
    Away,
    Any,
}

/// Aggregated record for a team (used by team_stats and standings).
#[derive(Debug, Clone, Serialize, Default)]
pub struct TeamRecord {
    pub team: String,
    pub matches: i32,
    pub wins: i32,
    pub draws: i32,
    pub losses: i32,
    pub goals_for: i32,
    pub goals_against: i32,
    pub points: i32,
}

impl TeamRecord {
    pub fn win_rate(&self) -> f64 {
        if self.matches == 0 {
            0.0
        } else {
            self.wins as f64 / self.matches as f64 * 100.0
        }
    }
    pub fn goal_difference(&self) -> i32 {
        self.goals_for - self.goals_against
    }
    fn record_result(&mut self, gf: i32, ga: i32) {
        self.matches += 1;
        self.goals_for += gf;
        self.goals_against += ga;
        if gf > ga {
            self.wins += 1;
            self.points += 3;
        } else if gf == ga {
            self.draws += 1;
            self.points += 1;
        } else {
            self.losses += 1;
        }
    }
}

/// Head-to-head summary between two teams.
#[derive(Debug, Clone, Serialize)]
pub struct HeadToHead {
    pub team_a: String,
    pub team_b: String,
    pub total: usize,
    pub team_a_wins: i32,
    pub team_b_wins: i32,
    pub draws: i32,
    pub team_a_goals: i32,
    pub team_b_goals: i32,
    pub matches: Vec<Match>,
}

/// Aggregate goal statistics over a set of matches.
#[derive(Debug, Clone, Serialize)]
pub struct GoalStats {
    pub matches: usize,
    pub total_goals: i32,
    pub avg_goals_per_match: f64,
    pub home_wins: i32,
    pub away_wins: i32,
    pub draws: i32,
    pub home_win_rate: f64,
}

/// Overview of everything loaded.
#[derive(Debug, Clone, Serialize)]
pub struct Summary {
    pub total_matches: usize,
    pub total_players: usize,
    pub matches_by_source: Vec<(String, usize)>,
    pub seasons_min: Option<i32>,
    pub seasons_max: Option<i32>,
}

/// The loaded dataset plus query engine.
pub struct Store {
    pub matches: Vec<Match>,
    pub players: Vec<Player>,
}

impl Store {
    /// Construct from already-loaded vectors (used by tests with fixtures).
    pub fn new(matches: Vec<Match>, players: Vec<Player>) -> Self {
        Store { matches, players }
    }

    /// Load every CSV from a `data/kaggle` directory.
    pub fn load_from_dir(dir: &Path) -> Result<Self, Box<dyn Error>> {
        let mut matches = Vec::new();
        // Each loader is best-effort: a missing file is tolerated so the server
        // still starts with whatever data is present.
        type LoadFn = dyn Fn(&Path) -> Result<Vec<Match>, Box<dyn Error>>;
        let try_load = |name: &str, f: &LoadFn, out: &mut Vec<Match>| {
            let p = dir.join(name);
            if p.exists() {
                match f(&p) {
                    Ok(mut m) => out.append(&mut m),
                    Err(e) => eprintln!("warning: failed to load {name}: {e}"),
                }
            } else {
                eprintln!("warning: data file not found: {}", p.display());
            }
        };

        try_load("Brasileirao_Matches.csv", &loader::load_brasileirao, &mut matches);
        try_load("Brazilian_Cup_Matches.csv", &loader::load_cup, &mut matches);
        try_load("Libertadores_Matches.csv", &loader::load_libertadores, &mut matches);
        try_load("BR-Football-Dataset.csv", &loader::load_br_football, &mut matches);
        try_load("novo_campeonato_brasileiro.csv", &loader::load_novo, &mut matches);

        // The five files overlap heavily (the same Brasileirão game can appear
        // in three of them), which would otherwise triple-count results and
        // produce nonsensical standings (e.g. 84 wins in a 38-game season).
        // Collapse exact duplicates, keeping the first occurrence so the
        // canonical source files (loaded first) win for display naming.
        dedup_matches(&mut matches);

        let players_path = dir.join("fifa_data.csv");
        let players = if players_path.exists() {
            loader::load_players(&players_path).unwrap_or_else(|e| {
                eprintln!("warning: failed to load fifa_data.csv: {e}");
                Vec::new()
            })
        } else {
            eprintln!("warning: fifa_data.csv not found");
            Vec::new()
        };

        Ok(Store { matches, players })
    }

    // ---- Match Queries ----------------------------------------------------

    /// Find matches by optional team, opponent, competition, season and date
    /// range. When both `team` and `opponent` are given, only games featuring
    /// both are returned (order-independent). Results are sorted by date desc.
    #[allow(clippy::too_many_arguments)]
    pub fn search_matches(
        &self,
        team: Option<&str>,
        opponent: Option<&str>,
        competition: Option<&str>,
        season: Option<i32>,
        date_from: Option<&str>,
        date_to: Option<&str>,
        limit: usize,
    ) -> Vec<Match> {
        let comp = competition_filter(competition);
        let mut found: Vec<Match> = self
            .matches
            .iter()
            .filter(|m| {
                if let Some(c) = comp {
                    if m.competition != c {
                        return false;
                    }
                }
                if let Some(s) = season {
                    if m.season != Some(s) {
                        return false;
                    }
                }
                if let Some(df) = date_from {
                    if !m.date.is_empty() && m.date.as_str() < df {
                        return false;
                    }
                }
                if let Some(dt) = date_to {
                    if !m.date.is_empty() && m.date.as_str() > dt {
                        return false;
                    }
                }
                let team_ok = match team {
                    Some(t) => {
                        team_matches(t, &m.home_team) || team_matches(t, &m.away_team)
                    }
                    None => true,
                };
                let opp_ok = match opponent {
                    Some(o) => {
                        team_matches(o, &m.home_team) || team_matches(o, &m.away_team)
                    }
                    None => true,
                };
                team_ok && opp_ok
            })
            .cloned()
            .collect();

        found.sort_by(|a, b| b.date.cmp(&a.date));
        if limit > 0 && found.len() > limit {
            found.truncate(limit);
        }
        found
    }

    /// Head-to-head record between two teams across all competitions.
    pub fn head_to_head(&self, team_a: &str, team_b: &str) -> HeadToHead {
        let matches = self.search_matches(Some(team_a), Some(team_b), None, None, None, None, 0);
        let key_a = normalize_team(team_a);
        let mut h = HeadToHead {
            team_a: team_a.to_string(),
            team_b: team_b.to_string(),
            total: matches.len(),
            team_a_wins: 0,
            team_b_wins: 0,
            draws: 0,
            team_a_goals: 0,
            team_b_goals: 0,
            matches: matches.clone(),
        };
        for m in &matches {
            // Determine which side is team_a.
            let a_is_home = team_matches(&key_a, &m.home_team);
            let (a_goals, b_goals) = if a_is_home {
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

    // ---- Team Queries -----------------------------------------------------

    /// Aggregate a team's record, optionally filtered by season, competition
    /// and venue (home/away/any).
    pub fn team_stats(
        &self,
        team: &str,
        season: Option<i32>,
        competition: Option<&str>,
        venue: Venue,
    ) -> TeamRecord {
        let comp = competition_filter(competition);
        let mut rec = TeamRecord {
            team: team.to_string(),
            ..Default::default()
        };
        for m in &self.matches {
            if let Some(c) = comp {
                if m.competition != c {
                    continue;
                }
            }
            if let Some(s) = season {
                if m.season != Some(s) {
                    continue;
                }
            }
            let is_home = team_matches(team, &m.home_team);
            let is_away = team_matches(team, &m.away_team);
            match venue {
                Venue::Home if is_home => rec.record_result(m.home_goal, m.away_goal),
                Venue::Away if is_away => rec.record_result(m.away_goal, m.home_goal),
                Venue::Any if is_home => rec.record_result(m.home_goal, m.away_goal),
                Venue::Any if is_away => rec.record_result(m.away_goal, m.home_goal),
                _ => {}
            }
        }
        rec
    }

    // ---- Player Queries ---------------------------------------------------

    /// Search players by optional name substring, nationality, club, position
    /// and minimum overall rating. Results sorted by overall rating desc.
    pub fn search_players(
        &self,
        name: Option<&str>,
        nationality: Option<&str>,
        club: Option<&str>,
        position: Option<&str>,
        min_overall: Option<i32>,
        limit: usize,
    ) -> Vec<Player> {
        let name_l = name.map(|s| s.to_lowercase());
        let nat_l = nationality.map(|s| s.to_lowercase());
        let club_key = club.map(normalize_team);
        let pos_l = position.map(|s| s.to_lowercase());

        let mut found: Vec<Player> = self
            .players
            .iter()
            .filter(|p| {
                if let Some(n) = &name_l {
                    if !p.name.to_lowercase().contains(n) {
                        return false;
                    }
                }
                if let Some(nat) = &nat_l {
                    if p.nationality.to_lowercase() != *nat
                        && !p.nationality.to_lowercase().contains(nat)
                    {
                        return false;
                    }
                }
                if let Some(ck) = &club_key {
                    let pk = normalize_team(&p.club);
                    if !(pk == *ck || pk.contains(ck.as_str()) || ck.contains(&pk)) || pk.is_empty()
                    {
                        return false;
                    }
                }
                if let Some(pos) = &pos_l {
                    if p.position.to_lowercase() != *pos {
                        return false;
                    }
                }
                if let Some(mo) = min_overall {
                    if p.overall < mo {
                        return false;
                    }
                }
                true
            })
            .cloned()
            .collect();

        found.sort_by_key(|p| std::cmp::Reverse(p.overall));
        if limit > 0 && found.len() > limit {
            found.truncate(limit);
        }
        found
    }

    // ---- Competition Queries ----------------------------------------------

    /// Compute final standings for a competition + season from match results.
    /// Sorted by points, then goal difference, then goals for.
    ///
    /// Standings must be exact and complete, so — unlike the other queries that
    /// span every source — they are computed from the *single most complete*
    /// source file for that competition+season. This avoids the cross-file
    /// overlap (the same fixture under slightly different team names/dates)
    /// that would otherwise double-count results into an impossible table.
    pub fn standings(&self, competition: Option<&str>, season: i32) -> Vec<TeamRecord> {
        let comp = competition_filter(competition);

        // Count candidate matches per source, then keep only the best source.
        let mut per_source: HashMap<&'static str, usize> = HashMap::new();
        for m in &self.matches {
            if m.season != Some(season) {
                continue;
            }
            if let Some(c) = comp {
                if m.competition != c {
                    continue;
                }
            }
            *per_source.entry(m.source).or_insert(0) += 1;
        }
        // Pick the source with the most matches; ties broken by source name for
        // determinism.
        let best_source = per_source
            .into_iter()
            .max_by(|a, b| a.1.cmp(&b.1).then(b.0.cmp(a.0)))
            .map(|(s, _)| s);
        let Some(best_source) = best_source else {
            return Vec::new();
        };

        let mut table: HashMap<String, TeamRecord> = HashMap::new();
        for m in &self.matches {
            if m.source != best_source {
                continue;
            }
            if m.season != Some(season) {
                continue;
            }
            if let Some(c) = comp {
                if m.competition != c {
                    continue;
                }
            }
            {
                let e = table
                    .entry(m.home_team.clone())
                    .or_insert_with(|| TeamRecord {
                        team: m.home_team_raw.clone(),
                        ..Default::default()
                    });
                e.record_result(m.home_goal, m.away_goal);
            }
            {
                let e = table
                    .entry(m.away_team.clone())
                    .or_insert_with(|| TeamRecord {
                        team: m.away_team_raw.clone(),
                        ..Default::default()
                    });
                e.record_result(m.away_goal, m.home_goal);
            }
        }
        let mut rows: Vec<TeamRecord> = table.into_values().collect();
        rows.sort_by(|a, b| {
            b.points
                .cmp(&a.points)
                .then(b.goal_difference().cmp(&a.goal_difference()))
                .then(b.goals_for.cmp(&a.goals_for))
                .then(a.team.cmp(&b.team))
        });
        rows
    }

    // ---- Statistical Analysis ---------------------------------------------

    /// The biggest victories (by goal margin) matching optional filters.
    pub fn biggest_wins(
        &self,
        competition: Option<&str>,
        season: Option<i32>,
        limit: usize,
    ) -> Vec<Match> {
        let comp = competition_filter(competition);
        let mut found: Vec<Match> = self
            .matches
            .iter()
            .filter(|m| {
                if let Some(c) = comp {
                    if m.competition != c {
                        return false;
                    }
                }
                if let Some(s) = season {
                    if m.season != Some(s) {
                        return false;
                    }
                }
                (m.home_goal - m.away_goal).abs() > 0
            })
            .cloned()
            .collect();
        found.sort_by(|a, b| {
            (b.home_goal - b.away_goal)
                .abs()
                .cmp(&(a.home_goal - a.away_goal).abs())
                .then(b.total_goals().cmp(&a.total_goals()))
        });
        if limit > 0 && found.len() > limit {
            found.truncate(limit);
        }
        found
    }

    /// Aggregate goal statistics over matches matching optional filters.
    pub fn average_goals(&self, competition: Option<&str>, season: Option<i32>) -> GoalStats {
        let comp = competition_filter(competition);
        let mut stats = GoalStats {
            matches: 0,
            total_goals: 0,
            avg_goals_per_match: 0.0,
            home_wins: 0,
            away_wins: 0,
            draws: 0,
            home_win_rate: 0.0,
        };
        for m in &self.matches {
            if let Some(c) = comp {
                if m.competition != c {
                    continue;
                }
            }
            if let Some(s) = season {
                if m.season != Some(s) {
                    continue;
                }
            }
            stats.matches += 1;
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

    /// Overview of everything loaded.
    pub fn summary(&self) -> Summary {
        let mut by_source: HashMap<&'static str, usize> = HashMap::new();
        let mut min_s: Option<i32> = None;
        let mut max_s: Option<i32> = None;
        for m in &self.matches {
            *by_source.entry(m.source).or_insert(0) += 1;
            let y = m.season.or_else(|| year_of(&m.date));
            if let Some(y) = y {
                min_s = Some(min_s.map_or(y, |c| c.min(y)));
                max_s = Some(max_s.map_or(y, |c| c.max(y)));
            }
        }
        let mut matches_by_source: Vec<(String, usize)> = by_source
            .into_iter()
            .map(|(k, v)| (k.to_string(), v))
            .collect();
        matches_by_source.sort();
        Summary {
            total_matches: self.matches.len(),
            total_players: self.players.len(),
            matches_by_source,
            seasons_min: min_s,
            seasons_max: max_s,
        }
    }
}
