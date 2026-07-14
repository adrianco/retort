// query - the in-memory `Database` and every query / statistics operation.
//
// The MCP tool layer (see `mcp`) is a thin formatter on top of these methods.
// Everything works off normalized team keys (`normalize::normalize_team`) so
// that "Flamengo", "Flamengo-RJ" and "Flamengo - RJ" all resolve to the same
// club. Standings are derived from match results (3 points per win, 1 per
// draw), matching how the spec asks competitions to be reconstructed.

use std::collections::HashMap;
use std::error::Error;
use std::path::Path;

use crate::data;
use crate::model::{Competition, Match, MatchResult, Player};
use crate::normalize::normalize_team;

/// A win/draw/loss + goals record for a team over some set of matches.
#[derive(Debug, Clone, Default, PartialEq)]
pub struct TeamRecord {
    pub played: u32,
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

    pub fn goal_difference(&self) -> i32 {
        self.goals_for as i32 - self.goals_against as i32
    }

    /// Win rate as a fraction in [0, 1]; 0 when no matches played.
    pub fn win_rate(&self) -> f64 {
        if self.played == 0 {
            0.0
        } else {
            self.wins as f64 / self.played as f64
        }
    }
}

/// Head-to-head summary between two teams (a's perspective first).
#[derive(Debug, Clone, PartialEq)]
pub struct HeadToHead {
    pub a_wins: u32,
    pub b_wins: u32,
    pub draws: u32,
    pub total: u32,
}

/// One row of a calculated league table.
#[derive(Debug, Clone, PartialEq)]
pub struct StandingRow {
    pub team: String,
    pub record: TeamRecord,
}

/// Optional filters applied when selecting matches.
#[derive(Debug, Clone, Default)]
pub struct MatchFilter {
    /// Normalized key; match must involve this team.
    pub team: Option<String>,
    /// Normalized key; if set with `team`, restrict to head-to-head.
    pub opponent: Option<String>,
    pub season: Option<i32>,
    pub competition: Option<Competition>,
}

impl MatchFilter {
    pub fn new() -> Self {
        Self::default()
    }
    pub fn team(mut self, name: &str) -> Self {
        self.team = Some(normalize_team(name));
        self
    }
    pub fn opponent(mut self, name: &str) -> Self {
        self.opponent = Some(normalize_team(name));
        self
    }
    pub fn season(mut self, season: i32) -> Self {
        self.season = Some(season);
        self
    }
    pub fn competition(mut self, c: Competition) -> Self {
        self.competition = Some(c);
        self
    }

    fn accepts(&self, m: &Match) -> bool {
        if let Some(s) = self.season {
            if m.season != s {
                return false;
            }
        }
        if let Some(c) = &self.competition {
            if &m.competition != c {
                return false;
            }
        }
        if let Some(t) = &self.team {
            if !m.involves(t) {
                return false;
            }
        }
        if let Some(o) = &self.opponent {
            if !m.involves(o) {
                return false;
            }
        }
        true
    }
}

/// Collapse the heavy overlap between the match datasets.
///
/// The five files cover overlapping competitions and seasons but spell team
/// names differently ("Atletico-MG" vs "Atletico Mineiro", "Bahia" vs "EC
/// Bahia") and even disagree on match dates, so naive fixture matching leaves
/// duplicates and inflates standings. Instead we pick, for each
/// (competition, season), the single most authoritative source present (the
/// lowest `source_priority`) and drop the others for that season. Because the
/// union of sources still covers every season, no season is lost — e.g. the
/// Brasileirão comes from `Brasileirao_Matches` for 2012-2022, the historical
/// file for 2003-2011, and the extended file for 2023.
///
/// Within the winning source, fixtures are additionally deduped by
/// (competition, season, home, away). Rows with an unknown season (0) cannot
/// be grouped and are all kept.
fn dedup_matches(matches: Vec<Match>) -> Vec<Match> {
    use std::collections::HashSet;

    // Pass 1: best (lowest) source_priority available per competition+season.
    let mut best: HashMap<(String, i32), u8> = HashMap::new();
    for m in &matches {
        if m.season == 0 {
            continue;
        }
        let gk = (m.competition.display_name(), m.season);
        best.entry(gk)
            .and_modify(|p| {
                if m.source_priority < *p {
                    *p = m.source_priority;
                }
            })
            .or_insert(m.source_priority);
    }

    // Pass 2: keep only winning-source rows, collapsing exact-duplicate rows.
    // The fixture key includes the date: within a single source the dates are
    // self-consistent, and some seasons legitimately stage the same ordered
    // pair twice at one venue (e.g. the 2009 Botafogo-RJ vs Flamengo derby on
    // two dates), which the date keeps distinct. Dateless rows are always kept.
    let mut seen: HashSet<(String, i32, String, String, String)> = HashSet::new();
    let mut out = Vec::with_capacity(matches.len());
    for m in matches {
        if m.season == 0 {
            out.push(m);
            continue;
        }
        let gk = (m.competition.display_name(), m.season);
        if best.get(&gk).copied() != Some(m.source_priority) {
            continue;
        }
        match &m.date {
            Some(date) => {
                let fk = (
                    m.competition.display_name(),
                    m.season,
                    m.home_id(),
                    m.away_id(),
                    date.clone(),
                );
                if seen.insert(fk) {
                    out.push(m);
                }
            }
            None => out.push(m),
        }
    }
    out
}

/// The loaded dataset and all query operations.
pub struct Database {
    matches: Vec<Match>,
    players: Vec<Player>,
    /// Loose normalized key -> a representative display name.
    display_names: HashMap<String, String>,
    /// Strict canonical id -> a representative display name (for standings).
    canonical_display: HashMap<String, String>,
}

impl Database {
    /// Build a database from already-loaded matches and players.
    ///
    /// The five match datasets overlap heavily (e.g. a Brasileirão game appears
    /// in `Brasileirao_Matches.csv`, the historical file, and BR-Football's
    /// "Serie A" rows), so identical fixtures are collapsed here. Without this,
    /// standings and head-to-head counts would be inflated several-fold.
    pub fn new(matches: Vec<Match>, players: Vec<Player>) -> Self {
        let matches = dedup_matches(matches);
        let mut display_names = HashMap::new();
        let mut canonical_display = HashMap::new();
        for m in &matches {
            display_names
                .entry(m.home_key())
                .or_insert_with(|| m.home_team.clone());
            display_names
                .entry(m.away_key())
                .or_insert_with(|| m.away_team.clone());
            canonical_display
                .entry(m.home_id())
                .or_insert_with(|| m.home_team.clone());
            canonical_display
                .entry(m.away_id())
                .or_insert_with(|| m.away_team.clone());
        }
        Database {
            matches,
            players,
            display_names,
            canonical_display,
        }
    }

    /// Load every dataset from `dir` (the `data/kaggle` directory).
    pub fn load(dir: &Path) -> Result<Self, Box<dyn Error>> {
        let matches = data::load_all_matches(dir)?;
        let players = data::load_players(&dir.join("fifa_data.csv"))?;
        Ok(Database::new(matches, players))
    }

    pub fn match_count(&self) -> usize {
        self.matches.len()
    }
    pub fn player_count(&self) -> usize {
        self.players.len()
    }

    /// A readable display name for a loose normalized team key.
    pub fn display_name(&self, key: &str) -> String {
        self.display_names
            .get(key)
            .cloned()
            .unwrap_or_else(|| key.to_string())
    }

    /// A readable display name for a strict canonical club id.
    pub fn display_canonical(&self, id: &str) -> String {
        self.canonical_display
            .get(id)
            .cloned()
            .unwrap_or_else(|| id.to_string())
    }

    // ---- Match queries -------------------------------------------------

    /// All matches passing `filter`, in dataset order.
    pub fn find_matches(&self, filter: &MatchFilter) -> Vec<&Match> {
        self.matches.iter().filter(|m| filter.accepts(m)).collect()
    }

    /// All matches between two teams (either may be home or away).
    pub fn matches_between(&self, team_a: &str, team_b: &str) -> Vec<&Match> {
        let f = MatchFilter::new().team(team_a).opponent(team_b);
        self.find_matches(&f)
    }

    // ---- Team records & head-to-head -----------------------------------

    /// Record for a team over the matches passing `filter`.
    /// `home_only` / `away_only` further restrict the venue.
    pub fn team_record(
        &self,
        team: &str,
        filter: &MatchFilter,
        home_only: bool,
        away_only: bool,
    ) -> TeamRecord {
        let key = normalize_team(team);
        let mut rec = TeamRecord::default();
        for m in self.matches.iter().filter(|m| filter.accepts(m)) {
            let is_home = m.home_key() == key;
            let is_away = m.away_key() == key;
            if !is_home && !is_away {
                continue;
            }
            if home_only && !is_home {
                continue;
            }
            if away_only && !is_away {
                continue;
            }
            rec.played += 1;
            let (gf, ga) = if is_home {
                (m.home_goal, m.away_goal)
            } else {
                (m.away_goal, m.home_goal)
            };
            rec.goals_for += gf;
            rec.goals_against += ga;
            match (m.result(), is_home) {
                (MatchResult::HomeWin, true) | (MatchResult::AwayWin, false) => rec.wins += 1,
                (MatchResult::AwayWin, true) | (MatchResult::HomeWin, false) => rec.losses += 1,
                (MatchResult::Draw, _) => rec.draws += 1,
            }
        }
        rec
    }

    /// Head-to-head record between two teams (optionally filtered).
    pub fn head_to_head(&self, team_a: &str, team_b: &str, filter: &MatchFilter) -> HeadToHead {
        let a = normalize_team(team_a);
        let b = normalize_team(team_b);
        let mut h = HeadToHead {
            a_wins: 0,
            b_wins: 0,
            draws: 0,
            total: 0,
        };
        for m in self.matches.iter().filter(|m| filter.accepts(m)) {
            if !(m.involves(&a) && m.involves(&b)) {
                continue;
            }
            h.total += 1;
            let a_is_home = m.home_key() == a;
            match m.result() {
                MatchResult::Draw => h.draws += 1,
                MatchResult::HomeWin => {
                    if a_is_home {
                        h.a_wins += 1
                    } else {
                        h.b_wins += 1
                    }
                }
                MatchResult::AwayWin => {
                    if a_is_home {
                        h.b_wins += 1
                    } else {
                        h.a_wins += 1
                    }
                }
            }
        }
        h
    }

    // ---- Competition standings -----------------------------------------

    /// Calculated league table for a competition + season, sorted by points,
    /// then goal difference, then goals for, then name.
    pub fn standings(&self, competition: Competition, season: i32) -> Vec<StandingRow> {
        let filter = MatchFilter::new().competition(competition).season(season);
        let mut records: HashMap<String, TeamRecord> = HashMap::new();
        for m in self.matches.iter().filter(|m| filter.accepts(m)) {
            for (key, gf, ga, res_is_win, res_is_loss, is_draw) in [
                (
                    m.home_id(),
                    m.home_goal,
                    m.away_goal,
                    m.result() == MatchResult::HomeWin,
                    m.result() == MatchResult::AwayWin,
                    m.result() == MatchResult::Draw,
                ),
                (
                    m.away_id(),
                    m.away_goal,
                    m.home_goal,
                    m.result() == MatchResult::AwayWin,
                    m.result() == MatchResult::HomeWin,
                    m.result() == MatchResult::Draw,
                ),
            ] {
                let r = records.entry(key).or_default();
                r.played += 1;
                r.goals_for += gf;
                r.goals_against += ga;
                if res_is_win {
                    r.wins += 1;
                } else if res_is_loss {
                    r.losses += 1;
                } else if is_draw {
                    r.draws += 1;
                }
            }
        }
        let mut rows: Vec<StandingRow> = records
            .into_iter()
            .map(|(key, record)| StandingRow {
                team: self.display_canonical(&key),
                record,
            })
            .collect();
        rows.sort_by(|a, b| {
            b.record
                .points()
                .cmp(&a.record.points())
                .then(b.record.goal_difference().cmp(&a.record.goal_difference()))
                .then(b.record.goals_for.cmp(&a.record.goals_for))
                .then(a.team.cmp(&b.team))
        });
        rows
    }

    // ---- Player queries ------------------------------------------------

    /// Players whose name contains `query` (case-insensitive).
    pub fn players_by_name(&self, query: &str) -> Vec<&Player> {
        let q = query.to_lowercase();
        self.players
            .iter()
            .filter(|p| p.name.to_lowercase().contains(&q))
            .collect()
    }

    /// Players of a given nationality (case-insensitive exact match).
    pub fn players_by_nationality(&self, nationality: &str) -> Vec<&Player> {
        let q = nationality.to_lowercase();
        self.players
            .iter()
            .filter(|p| p.nationality.to_lowercase() == q)
            .collect()
    }

    /// Players whose club contains `query` (case-insensitive).
    pub fn players_by_club(&self, query: &str) -> Vec<&Player> {
        let q = query.to_lowercase();
        self.players
            .iter()
            .filter(|p| p.club.to_lowercase().contains(&q))
            .collect()
    }

    /// Top `n` players matching an optional nationality and/or club filter,
    /// sorted by Overall rating descending.
    pub fn top_players(
        &self,
        nationality: Option<&str>,
        club: Option<&str>,
        n: usize,
    ) -> Vec<&Player> {
        let nat = nationality.map(|s| s.to_lowercase());
        let club = club.map(|s| s.to_lowercase());
        let mut v: Vec<&Player> = self
            .players
            .iter()
            .filter(|p| match &nat {
                Some(q) => p.nationality.to_lowercase() == *q,
                None => true,
            })
            .filter(|p| match &club {
                Some(q) => p.club.to_lowercase().contains(q),
                None => true,
            })
            .collect();
        v.sort_by(|a, b| b.overall.cmp(&a.overall).then(a.name.cmp(&b.name)));
        v.truncate(n);
        v
    }

    // ---- Aggregate statistics ------------------------------------------

    /// Average total goals per match over the filtered set (0.0 if empty).
    pub fn average_goals(&self, filter: &MatchFilter) -> f64 {
        let mut total = 0u64;
        let mut count = 0u64;
        for m in self.matches.iter().filter(|m| filter.accepts(m)) {
            total += m.total_goals() as u64;
            count += 1;
        }
        if count == 0 {
            0.0
        } else {
            total as f64 / count as f64
        }
    }

    /// Fraction of filtered matches won by the home side (0.0 if empty).
    pub fn home_win_rate(&self, filter: &MatchFilter) -> f64 {
        let mut home_wins = 0u64;
        let mut count = 0u64;
        for m in self.matches.iter().filter(|m| filter.accepts(m)) {
            if m.result() == MatchResult::HomeWin {
                home_wins += 1;
            }
            count += 1;
        }
        if count == 0 {
            0.0
        } else {
            home_wins as f64 / count as f64
        }
    }

    /// The `n` biggest victories (by goal margin) in the filtered set.
    pub fn biggest_wins(&self, filter: &MatchFilter, n: usize) -> Vec<&Match> {
        let mut v: Vec<&Match> = self
            .matches
            .iter()
            .filter(|m| filter.accepts(m))
            .filter(|m| m.home_goal != m.away_goal)
            .collect();
        v.sort_by(|a, b| {
            let ma = a.home_goal.abs_diff(a.away_goal);
            let mb = b.home_goal.abs_diff(b.away_goal);
            mb.cmp(&ma).then(b.total_goals().cmp(&a.total_goals()))
        });
        v.truncate(n);
        v
    }

    /// Team (display name) with the most goals scored in the filtered set,
    /// along with the goal tally. `None` if no matches.
    pub fn most_goals_team(&self, filter: &MatchFilter) -> Option<(String, u32)> {
        let mut goals: HashMap<String, u32> = HashMap::new();
        for m in self.matches.iter().filter(|m| filter.accepts(m)) {
            *goals.entry(m.home_id()).or_default() += m.home_goal;
            *goals.entry(m.away_id()).or_default() += m.away_goal;
        }
        goals
            .into_iter()
            .max_by(|a, b| a.1.cmp(&b.1).then(b.0.cmp(&a.0)))
            .map(|(k, g)| (self.display_canonical(&k), g))
    }

    /// Team with the best home (or away) win rate among teams with at least
    /// `min_matches` qualifying matches in the filtered set.
    pub fn best_venue_record(
        &self,
        filter: &MatchFilter,
        away: bool,
        min_matches: u32,
    ) -> Option<(String, TeamRecord)> {
        let mut records: HashMap<String, TeamRecord> = HashMap::new();
        for m in self.matches.iter().filter(|m| filter.accepts(m)) {
            let key = if away { m.away_id() } else { m.home_id() };
            let r = records.entry(key).or_default();
            r.played += 1;
            let (gf, ga) = if away {
                (m.away_goal, m.home_goal)
            } else {
                (m.home_goal, m.away_goal)
            };
            r.goals_for += gf;
            r.goals_against += ga;
            let win = if away {
                m.result() == MatchResult::AwayWin
            } else {
                m.result() == MatchResult::HomeWin
            };
            let draw = m.result() == MatchResult::Draw;
            if win {
                r.wins += 1;
            } else if draw {
                r.draws += 1;
            } else {
                r.losses += 1;
            }
        }
        records
            .into_iter()
            .filter(|(_, r)| r.played >= min_matches)
            .max_by(|a, b| {
                a.1.win_rate()
                    .partial_cmp(&b.1.win_rate())
                    .unwrap_or(std::cmp::Ordering::Equal)
                    .then(a.1.wins.cmp(&b.1.wins))
            })
            .map(|(k, r)| (self.display_canonical(&k), r))
    }

    /// The most recent match (by ISO date) between two teams, if any.
    pub fn last_match_between(&self, team_a: &str, team_b: &str) -> Option<&Match> {
        self.matches_between(team_a, team_b)
            .into_iter()
            .filter(|m| m.date.is_some())
            .max_by(|a, b| a.date.cmp(&b.date))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn m(
        comp: Competition,
        season: i32,
        date: &str,
        home: &str,
        away: &str,
        hg: u32,
        ag: u32,
    ) -> Match {
        Match {
            competition: comp,
            season,
            date: Some(date.to_string()),
            round: None,
            stage: None,
            home_team: home.to_string(),
            away_team: away.to_string(),
            home_state: None,
            away_state: None,
            home_goal: hg,
            away_goal: ag,
            source_priority: 0,
        }
    }

    /// Like `m`, but with an explicit source priority for dedup tests.
    #[allow(clippy::too_many_arguments)]
    fn m_src(
        comp: Competition,
        season: i32,
        date: &str,
        home: &str,
        away: &str,
        hg: u32,
        ag: u32,
        source_priority: u8,
    ) -> Match {
        Match {
            source_priority,
            ..m(comp, season, date, home, away, hg, ag)
        }
    }

    fn player(id: i64, name: &str, nat: &str, club: &str, overall: u32, pos: &str) -> Player {
        Player {
            id,
            name: name.to_string(),
            age: Some(25),
            nationality: nat.to_string(),
            overall,
            potential: overall,
            club: club.to_string(),
            position: pos.to_string(),
        }
    }

    fn sample_db() -> Database {
        use Competition::*;
        let matches = vec![
            // 2019 Brasileirão mini-league: Flamengo, Santos, Palmeiras.
            m(
                Brasileirao,
                2019,
                "2019-05-01",
                "Flamengo-RJ",
                "Santos-SP",
                2,
                0,
            ),
            m(
                Brasileirao,
                2019,
                "2019-06-01",
                "Santos-SP",
                "Flamengo-RJ",
                1,
                1,
            ),
            m(
                Brasileirao,
                2019,
                "2019-07-01",
                "Flamengo-RJ",
                "Palmeiras-SP",
                3,
                0,
            ),
            m(
                Brasileirao,
                2019,
                "2019-08-01",
                "Palmeiras-SP",
                "Santos-SP",
                0,
                0,
            ),
            m(
                Brasileirao,
                2019,
                "2019-09-01",
                "Santos-SP",
                "Palmeiras-SP",
                2,
                1,
            ),
            m(
                Brasileirao,
                2019,
                "2019-10-01",
                "Palmeiras-SP",
                "Flamengo-RJ",
                1,
                2,
            ),
            // A different season / competition that must not leak in.
            m(Libertadores, 2018, "2018-04-01", "Flamengo", "Santos", 5, 0),
        ];
        let players = vec![
            player(1, "Neymar Jr", "Brazil", "Paris Saint-Germain", 92, "LW"),
            player(2, "Gabriel Barbosa", "Brazil", "Flamengo", 80, "ST"),
            player(3, "Bruno Henrique", "Brazil", "Flamengo", 78, "LW"),
            player(4, "L. Messi", "Argentina", "FC Barcelona", 94, "RF"),
            player(5, "Marreta", "Brazil", "Palmeiras", 70, "CB"),
        ];
        Database::new(matches, players)
    }

    #[test]
    fn duplicate_fixtures_within_a_source_collapse() {
        use Competition::*;
        // An exact-duplicate row (same competition, season, teams AND date)
        // must collapse to one.
        let a = m(
            Brasileirao,
            2019,
            "2019-06-09",
            "Flamengo-RJ",
            "Fluminense-RJ",
            2,
            1,
        );
        let a_dup = m(
            Brasileirao,
            2019,
            "2019-06-09",
            "Flamengo-RJ",
            "Fluminense-RJ",
            2,
            1,
        );
        // The reverse leg (Fluminense at home) is a genuinely distinct fixture.
        let leg = m(
            Brasileirao,
            2019,
            "2019-10-20",
            "Fluminense-RJ",
            "Flamengo-RJ",
            0,
            2,
        );
        let db = Database::new(vec![a, a_dup, leg], vec![]);
        assert_eq!(db.match_count(), 2);
        // Head-to-head reflects the deduplicated games: Flamengo won both legs.
        let h = db.head_to_head("Flamengo", "Fluminense", &MatchFilter::new());
        assert_eq!(h.total, 2);
        assert_eq!(h.a_wins, 2);
    }

    #[test]
    fn same_pairing_on_different_dates_is_kept() {
        use Competition::*;
        // Real 2009 quirk: Botafogo-RJ hosted Flamengo twice (shared venue) on
        // different dates with different results. Both must survive de-dup.
        let g1 = m(
            Brasileirao,
            2009,
            "2009-07-19",
            "Botafogo-RJ",
            "Flamengo",
            2,
            2,
        );
        let g2 = m(
            Brasileirao,
            2009,
            "2009-10-25",
            "Botafogo-RJ",
            "Flamengo",
            0,
            1,
        );
        let db = Database::new(vec![g1, g2], vec![]);
        assert_eq!(db.match_count(), 2);
        let h = db.head_to_head("Flamengo", "Botafogo", &MatchFilter::new());
        assert_eq!(h.total, 2);
        assert_eq!(h.a_wins, 1); // Flamengo won the second leg
        assert_eq!(h.draws, 1);
    }

    #[test]
    fn standings_keep_same_named_clubs_from_different_states_separate() {
        use Competition::*;
        // Atlético-MG and Athletico-PR share a loose key but are different
        // clubs; standings must list them as two distinct rows.
        let matches = vec![
            m(
                Brasileirao,
                2019,
                "2019-05-01",
                "Atletico-MG",
                "Atletico-PR",
                1,
                0,
            ),
            m(
                Brasileirao,
                2019,
                "2019-09-01",
                "Atletico-PR",
                "Atletico-MG",
                2,
                2,
            ),
        ];
        let db = Database::new(matches, vec![]);
        let table = db.standings(Brasileirao, 2019);
        assert_eq!(table.len(), 2);
    }

    #[test]
    fn source_priority_picks_one_dataset_per_season() {
        use Competition::*;
        // Same season covered by two sources that spell names differently and
        // disagree on the score. Only the authoritative source (priority 0)
        // should be kept, so the 2-team "league" has exactly 2 fixtures.
        let primary_1 = m_src(
            Brasileirao,
            2019,
            "2019-05-01",
            "Flamengo-RJ",
            "Santos-SP",
            2,
            0,
            0,
        );
        let primary_2 = m_src(
            Brasileirao,
            2019,
            "2019-09-01",
            "Santos-SP",
            "Flamengo-RJ",
            1,
            1,
            0,
        );
        // Secondary source: different spelling + different score, must be dropped.
        let secondary_1 = m_src(
            Brasileirao,
            2019,
            "2019-05-02",
            "Flamengo",
            "Santos",
            3,
            1,
            2,
        );
        let secondary_2 = m_src(
            Brasileirao,
            2019,
            "2019-09-02",
            "Santos",
            "Flamengo",
            0,
            0,
            2,
        );
        let db = Database::new(vec![primary_1, primary_2, secondary_1, secondary_2], vec![]);
        assert_eq!(db.match_count(), 2);
        // The kept score is the primary's 2-0, not the secondary's 3-1.
        let rec = db.team_record(
            "Flamengo",
            &MatchFilter::new().competition(Brasileirao).season(2019),
            false,
            false,
        );
        assert_eq!(rec.goals_for, 3); // 2 (home win) + 1 (away draw)
    }

    #[test]
    fn source_priority_falls_back_when_primary_absent() {
        use Competition::*;
        // A season only the secondary source covers is kept from the secondary.
        let only_secondary = m_src(
            Brasileirao,
            2023,
            "2023-05-01",
            "Flamengo",
            "Santos",
            1,
            0,
            2,
        );
        let db = Database::new(vec![only_secondary], vec![]);
        assert_eq!(db.match_count(), 1);
    }

    #[test]
    fn matches_with_unknown_season_are_kept() {
        use Competition::*;
        // Season 0 means the season could not be determined, so the fixture
        // cannot be identified and rows are kept rather than risk collapsing
        // distinct games from different years.
        let a = m(Brasileirao, 0, "2019-06-09", "Flamengo", "Santos", 1, 0);
        let b = m(Brasileirao, 0, "2018-06-09", "Flamengo", "Santos", 1, 0);
        let db = Database::new(vec![a, b], vec![]);
        assert_eq!(db.match_count(), 2);
    }

    #[test]
    fn distinct_seasons_and_legs_are_not_collapsed() {
        use Competition::*;
        // Same teams, same home/away, but different seasons -> distinct.
        let s2018 = m(Brasileirao, 2018, "2018-06-09", "Flamengo", "Santos", 1, 0);
        let s2019 = m(Brasileirao, 2019, "2019-06-09", "Flamengo", "Santos", 2, 0);
        // Same season, opposite venue -> distinct (the away leg).
        let leg = m(Brasileirao, 2019, "2019-11-09", "Santos", "Flamengo", 1, 1);
        let db = Database::new(vec![s2018, s2019, leg], vec![]);
        assert_eq!(db.match_count(), 3);
    }

    #[test]
    fn finds_matches_between_teams_across_naming() {
        let db = sample_db();
        // "Flamengo" must match "Flamengo-RJ" and "Flamengo".
        let between = db.matches_between("Flamengo", "Santos");
        // 2 in 2019 Brasileirão + 1 in 2018 Libertadores.
        assert_eq!(between.len(), 3);
    }

    #[test]
    fn filter_by_season_and_competition() {
        let db = sample_db();
        let f = MatchFilter::new()
            .competition(Competition::Brasileirao)
            .season(2019);
        assert_eq!(db.find_matches(&f).len(), 6);
        let f2 = MatchFilter::new().team("Flamengo").season(2019);
        // Flamengo plays 4 league matches in 2019 (vs Santos x2, vs Palmeiras x2).
        assert_eq!(db.find_matches(&f2).len(), 4);
    }

    #[test]
    fn team_record_overall_and_home() {
        let db = sample_db();
        let f = MatchFilter::new()
            .competition(Competition::Brasileirao)
            .season(2019);
        // Flamengo 2019: beat Santos (H), drew Santos (A), beat Palmeiras (H),
        // beat Palmeiras (A) 2-1. => 3W 1D 0L, GF 8, GA 2 (1 vs Santos, 1 vs Pal).
        let rec = db.team_record("Flamengo", &f, false, false);
        assert_eq!(rec.wins, 3);
        assert_eq!(rec.draws, 1);
        assert_eq!(rec.losses, 0);
        assert_eq!(rec.goals_for, 8);
        assert_eq!(rec.goals_against, 2);
        assert_eq!(rec.points(), 10);

        // Home only: two home games, both wins.
        let home = db.team_record("Flamengo", &f, true, false);
        assert_eq!(home.played, 2);
        assert_eq!(home.wins, 2);
    }

    #[test]
    fn head_to_head_perspective() {
        let db = sample_db();
        let f = MatchFilter::new()
            .competition(Competition::Brasileirao)
            .season(2019);
        let h = db.head_to_head("Flamengo", "Santos", &f);
        // 2019: Flamengo won one, one draw.
        assert_eq!(h.total, 2);
        assert_eq!(h.a_wins, 1);
        assert_eq!(h.b_wins, 0);
        assert_eq!(h.draws, 1);
        // Symmetry when swapping perspective.
        let h2 = db.head_to_head("Santos", "Flamengo", &f);
        assert_eq!(h2.a_wins, 0);
        assert_eq!(h2.b_wins, 1);
    }

    #[test]
    fn standings_are_calculated_and_sorted() {
        let db = sample_db();
        let table = db.standings(Competition::Brasileirao, 2019);
        assert_eq!(table.len(), 3);
        // Flamengo top with 10 pts.
        assert_eq!(db_key(&table[0].team), "flamengo");
        assert_eq!(table[0].record.points(), 10);
        // Santos: W? Santos drew Fla, beat Palmeiras, drew Palmeiras => 1W 2D 1L?
        // Santos games: lost to Fla(H? away 0-2 -> loss), drew Fla 1-1, drew Pal 0-0, beat Pal 2-1.
        // => 1W 2D 1L = 5 pts.
        assert_eq!(table[1].record.points(), 5);
    }

    fn db_key(name: &str) -> String {
        normalize_team(name)
    }

    #[test]
    fn player_search_by_name_and_nationality() {
        let db = sample_db();
        assert_eq!(db.players_by_name("gabriel").len(), 1);
        assert_eq!(db.players_by_name("GABRIEL")[0].name, "Gabriel Barbosa");
        assert_eq!(db.players_by_nationality("Brazil").len(), 4);
    }

    #[test]
    fn player_search_by_club_and_top() {
        let db = sample_db();
        let fla = db.players_by_club("Flamengo");
        assert_eq!(fla.len(), 2);
        let top_br = db.top_players(Some("Brazil"), None, 2);
        assert_eq!(top_br.len(), 2);
        assert_eq!(top_br[0].name, "Neymar Jr"); // 92 highest among Brazilians
        let top_fla = db.top_players(None, Some("Flamengo"), 5);
        assert_eq!(top_fla[0].name, "Gabriel Barbosa"); // 80 > 78
    }

    #[test]
    fn average_goals_and_home_win_rate() {
        let db = sample_db();
        let f = MatchFilter::new()
            .competition(Competition::Brasileirao)
            .season(2019);
        // Goals: 2,2,3,0,3,3 = 13 over 6 matches.
        assert!((db.average_goals(&f) - (13.0 / 6.0)).abs() < 1e-9);
        // Home wins in 2019 Bra: m1 (Fla 2-0), m3 (Fla 3-0), m5 (Santos 2-1)
        // => 3 of 6.
        assert!((db.home_win_rate(&f) - (3.0 / 6.0)).abs() < 1e-9);
    }

    #[test]
    fn biggest_wins_sorted_by_margin() {
        let db = sample_db();
        let f = MatchFilter::new(); // all competitions
        let top = db.biggest_wins(&f, 1);
        assert_eq!(top.len(), 1);
        // Libertadores 5-0 is the biggest margin.
        assert_eq!(top[0].home_goal, 5);
        assert_eq!(top[0].away_goal, 0);
    }

    #[test]
    fn most_goals_team_in_season() {
        let db = sample_db();
        let f = MatchFilter::new()
            .competition(Competition::Brasileirao)
            .season(2019);
        let (team, goals) = db.most_goals_team(&f).unwrap();
        assert_eq!(normalize_team(&team), "flamengo");
        assert_eq!(goals, 8);
    }

    #[test]
    fn best_home_record_respects_min_matches() {
        let db = sample_db();
        let f = MatchFilter::new()
            .competition(Competition::Brasileirao)
            .season(2019);
        // Each team has 2 home games in 2019. Flamengo won both => best.
        let (team, rec) = db.best_venue_record(&f, false, 2).unwrap();
        assert_eq!(normalize_team(&team), "flamengo");
        assert_eq!(rec.wins, 2);
        // With an impossible threshold, nobody qualifies.
        assert!(db.best_venue_record(&f, false, 99).is_none());
    }

    fn data_dir() -> std::path::PathBuf {
        std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("data/kaggle")
    }

    #[test]
    fn real_2019_brasileirao_standings_match_history() {
        // End-to-end check against the real datasets: after de-duplication the
        // 2019 Brasileirão must be a complete 380-match, 20-team season with
        // Flamengo champions on 90 points (28W 6D 4L) — exactly as recorded.
        let db = Database::load(&data_dir()).expect("load datasets");
        let table = db.standings(Competition::Brasileirao, 2019);
        assert_eq!(table.len(), 20, "a Brasileirão season has 20 teams");
        assert_eq!(normalize_team(&table[0].team), "flamengo");
        let champ = &table[0].record;
        assert_eq!(champ.played, 38);
        assert_eq!((champ.wins, champ.draws, champ.losses), (28, 6, 4));
        assert_eq!(champ.points(), 90);

        let season = MatchFilter::new()
            .competition(Competition::Brasileirao)
            .season(2019);
        assert_eq!(db.find_matches(&season).len(), 380);
    }

    #[test]
    fn real_2009_brasileirao_from_historical_source() {
        // 2009 is only in the historical file and includes the Botafogo-RJ vs
        // Flamengo same-venue double-header; the champion must still be
        // Flamengo on 67 points (the recorded result), not an undercount.
        let db = Database::load(&data_dir()).expect("load datasets");
        let table = db.standings(Competition::Brasileirao, 2009);
        assert_eq!(table.len(), 20);
        assert_eq!(normalize_team(&table[0].team), "flamengo");
        assert_eq!(table[0].record.played, 38);
        assert_eq!(table[0].record.points(), 67);
    }

    #[test]
    fn real_brazilian_player_search_works() {
        let db = Database::load(&data_dir()).expect("load datasets");
        let brazilians = db.players_by_nationality("Brazil");
        assert!(brazilians.len() > 500);
        // The top-rated Brazilian in this FIFA dataset is Neymar.
        let top = db.top_players(Some("Brazil"), None, 1);
        assert_eq!(top[0].name, "Neymar Jr");
    }

    #[test]
    fn last_match_between_picks_latest_date() {
        let db = sample_db();
        let last = db.last_match_between("Flamengo", "Palmeiras").unwrap();
        assert_eq!(last.date.as_deref(), Some("2019-10-01"));
    }
}
