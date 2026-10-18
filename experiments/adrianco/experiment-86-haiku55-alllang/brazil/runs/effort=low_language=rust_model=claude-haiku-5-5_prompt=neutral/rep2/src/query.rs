//! Context: pure query functions over `Dataset`. No I/O, no formatting; the
//! tool layer turns these results into text. Team arguments are resolved from
//! user text (e.g. "flamengo", "Sao Paulo") to canonical keys before use.

use std::collections::BTreeMap;

use crate::data::{Dataset, Match, Player};
use crate::normalize::team_key;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum Venue {
    #[default]
    Any,
    Home,
    Away,
}

impl Venue {
    pub fn parse(raw: &str) -> Option<Self> {
        match raw.trim().to_lowercase().as_str() {
            "" | "any" | "either" => Some(Venue::Any),
            "home" => Some(Venue::Home),
            "away" => Some(Venue::Away),
            _ => None,
        }
    }
}

#[derive(Debug, Clone, Default)]
pub struct MatchFilter {
    /// Canonical team key; matches where this team plays (subject to `venue`).
    pub team: Option<String>,
    /// Canonical opponent key; restricts to fixtures between `team` and this team.
    pub opponent: Option<String>,
    pub venue: Venue,
    /// Case-insensitive substring of the competition name.
    pub competition: Option<String>,
    pub season: Option<i32>,
    /// Round or stage label, compared case-insensitively. The special value
    /// `"final"` selects the last numbered round of each competition-season.
    pub round: Option<String>,
    /// Inclusive ISO date bounds.
    pub start_date: Option<String>,
    pub end_date: Option<String>,
}

impl MatchFilter {
    pub fn matches(&self, m: &Match) -> bool {
        if let Some(season) = self.season {
            if m.season != season {
                return false;
            }
        }
        if let Some(round) = &self.round {
            if !is_final_request(round) {
                let same = m
                    .round
                    .as_deref()
                    .is_some_and(|r| r.eq_ignore_ascii_case(round.trim()));
                if !same {
                    return false;
                }
            }
        }
        if let Some(comp) = &self.competition {
            if !m.competition.to_lowercase().contains(&comp.to_lowercase()) {
                return false;
            }
        }
        if let Some(start) = &self.start_date {
            if m.date.as_str() < start.as_str() {
                return false;
            }
        }
        if let Some(end) = &self.end_date {
            if m.date.as_str() > end.as_str() {
                return false;
            }
        }
        if let Some(team) = &self.team {
            let at_home = &m.home_key == team;
            let at_away = &m.away_key == team;
            let venue_ok = match self.venue {
                Venue::Any => at_home || at_away,
                Venue::Home => at_home,
                Venue::Away => at_away,
            };
            if !venue_ok {
                return false;
            }
        }
        if let Some(opp) = &self.opponent {
            let a = self.team.as_deref();
            let pair = (m.home_key.as_str(), m.away_key.as_str());
            let between = match a {
                Some(team) => {
                    (pair.0 == team && pair.1 == opp) || (pair.0 == opp && pair.1 == team)
                }
                None => pair.0 == opp || pair.1 == opp,
            };
            if !between {
                return false;
            }
        }
        true
    }
}

/// Resolve free text to a canonical team key that exists in the dataset.
///
/// Exact keys win. Otherwise a unique substring match is accepted. Ambiguous or
/// unknown names produce an error message listing candidates.
pub fn resolve_team(ds: &Dataset, query: &str) -> Result<String, String> {
    let key = team_key(query);
    if key.is_empty() {
        return Err("team name is empty".to_string());
    }
    if ds.team_names.contains_key(&key) {
        return Ok(key);
    }
    let candidates: Vec<&String> = ds.team_names.keys().filter(|k| k.contains(&key)).collect();
    match candidates.as_slice() {
        [only] => Ok((*only).clone()),
        [] => Err(format!("no team matches '{query}'")),
        many => {
            let names: Vec<String> = many.iter().take(10).map(|k| ds.team_display(k)).collect();
            Err(format!(
                "'{query}' is ambiguous; did you mean: {}",
                names.join(", ")
            ))
        }
    }
}

fn is_final_request(round: &str) -> bool {
    round.trim().eq_ignore_ascii_case("final")
}

/// Matches in the filter, most recent first.
pub fn find_matches<'a>(ds: &'a Dataset, filter: &MatchFilter) -> Vec<&'a Match> {
    let mut found: Vec<&Match> = ds.matches.iter().filter(|m| filter.matches(m)).collect();
    if filter.round.as_deref().is_some_and(is_final_request) {
        found = keep_finals(ds, filter, found);
    }
    found.sort_by(|a, b| b.date.cmp(&a.date));
    found
}

/// Keep only matches in the last numbered round of their competition-season.
/// The maximum is taken over the whole competition, not the team-filtered subset.
fn keep_finals<'a>(ds: &Dataset, filter: &MatchFilter, found: Vec<&'a Match>) -> Vec<&'a Match> {
    let mut scope = filter.clone();
    scope.team = None;
    scope.opponent = None;
    scope.venue = Venue::Any;
    scope.round = None;
    let mut last_round: BTreeMap<(i32, &str), u32> = BTreeMap::new();
    for m in ds.matches.iter().filter(|m| scope.matches(m)) {
        if let Some(n) = m
            .round
            .as_deref()
            .and_then(|r| r.trim().parse::<u32>().ok())
        {
            let entry = last_round
                .entry((m.season, m.competition.as_str()))
                .or_insert(0);
            *entry = (*entry).max(n);
        }
    }
    found
        .into_iter()
        .filter(|m| {
            let round = m
                .round
                .as_deref()
                .and_then(|r| r.trim().parse::<u32>().ok());
            round.is_some_and(|n| last_round.get(&(m.season, m.competition.as_str())) == Some(&n))
        })
        .collect()
}

/// Win/draw/loss tallies from one team's point of view.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct Record {
    pub played: u32,
    pub wins: u32,
    pub draws: u32,
    pub losses: u32,
    pub goals_for: u32,
    pub goals_against: u32,
}

impl Record {
    pub fn points(&self) -> u32 {
        self.wins * 3 + self.draws
    }

    pub fn win_rate(&self) -> f64 {
        if self.played == 0 {
            0.0
        } else {
            f64::from(self.wins) / f64::from(self.played) * 100.0
        }
    }

    pub fn goal_difference(&self) -> i64 {
        i64::from(self.goals_for) - i64::from(self.goals_against)
    }

    fn add(&mut self, gf: u32, ga: u32) {
        self.played += 1;
        self.goals_for += gf;
        self.goals_against += ga;
        match gf.cmp(&ga) {
            std::cmp::Ordering::Greater => self.wins += 1,
            std::cmp::Ordering::Equal => self.draws += 1,
            std::cmp::Ordering::Less => self.losses += 1,
        }
    }
}

/// Record for `team` over the matches allowed by `filter`.
pub fn team_record(ds: &Dataset, team: &str, filter: &MatchFilter) -> Record {
    let mut record = Record::default();
    let mut scoped = filter.clone();
    scoped.team = Some(team.to_string());
    for m in ds.matches.iter().filter(|m| scoped.matches(m)) {
        let (gf, ga) = if m.home_key == team {
            (m.home_goals, m.away_goals)
        } else {
            (m.away_goals, m.home_goals)
        };
        record.add(gf, ga);
    }
    record
}

/// Head-to-head record of `a` against `b`, from `a`'s perspective.
pub fn head_to_head(ds: &Dataset, a: &str, b: &str, filter: &MatchFilter) -> Record {
    let mut scoped = filter.clone();
    scoped.opponent = Some(b.to_string());
    team_record(ds, a, &scoped)
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StandingRow {
    pub team_key: String,
    pub record: Record,
}

/// League table for matches allowed by `filter`, sorted by points, goal
/// difference, then goals scored.
pub fn standings(ds: &Dataset, filter: &MatchFilter) -> Vec<StandingRow> {
    let mut table: BTreeMap<&str, Record> = BTreeMap::new();
    for m in ds.matches.iter().filter(|m| filter.matches(m)) {
        table
            .entry(m.home_key.as_str())
            .or_default()
            .add(m.home_goals, m.away_goals);
        table
            .entry(m.away_key.as_str())
            .or_default()
            .add(m.away_goals, m.home_goals);
    }
    let mut rows: Vec<StandingRow> = table
        .into_iter()
        .map(|(k, record)| StandingRow {
            team_key: k.to_string(),
            record,
        })
        .collect();
    rows.sort_by(|a, b| {
        b.record
            .points()
            .cmp(&a.record.points())
            .then(b.record.goal_difference().cmp(&a.record.goal_difference()))
            .then(b.record.goals_for.cmp(&a.record.goals_for))
            .then(a.team_key.cmp(&b.team_key))
    });
    rows
}

/// Average total goals per match over the filtered set. `None` when empty.
pub fn average_goals(ds: &Dataset, filter: &MatchFilter) -> Option<(usize, f64)> {
    let mut count = 0usize;
    let mut total = 0u64;
    for m in ds.matches.iter().filter(|m| filter.matches(m)) {
        count += 1;
        total += u64::from(m.home_goals) + u64::from(m.away_goals);
    }
    (count > 0).then(|| (count, total as f64 / count as f64))
}

/// Share of matches in the filter won by the home side. `None` when empty.
pub fn home_win_rate(ds: &Dataset, filter: &MatchFilter) -> Option<(usize, f64)> {
    let mut count = 0usize;
    let mut home_wins = 0usize;
    for m in ds.matches.iter().filter(|m| filter.matches(m)) {
        count += 1;
        if m.home_goals > m.away_goals {
            home_wins += 1;
        }
    }
    (count > 0).then(|| (count, home_wins as f64 / count as f64 * 100.0))
}

/// Matches with the largest goal margin, biggest first.
pub fn biggest_wins<'a>(ds: &'a Dataset, filter: &MatchFilter, limit: usize) -> Vec<&'a Match> {
    let mut found: Vec<&Match> = ds
        .matches
        .iter()
        .filter(|m| m.home_goals != m.away_goals && filter.matches(m))
        .collect();
    found.sort_by(|a, b| margin(b).cmp(&margin(a)).then(b.date.cmp(&a.date)));
    found.truncate(limit);
    found
}

fn margin(m: &Match) -> u32 {
    m.home_goals.abs_diff(m.away_goals)
}

/// Teams ranked by a win-rate measure in one venue, requiring a minimum sample.
/// Returns `(team_key, record)` sorted by win rate, then wins.
pub fn venue_ranking(
    ds: &Dataset,
    venue: Venue,
    filter: &MatchFilter,
    min_matches: u32,
) -> Vec<(String, Record)> {
    let mut by_team: BTreeMap<&str, Record> = BTreeMap::new();
    for m in ds.matches.iter().filter(|m| filter.matches(m)) {
        if matches!(venue, Venue::Any | Venue::Home) {
            by_team
                .entry(m.home_key.as_str())
                .or_default()
                .add(m.home_goals, m.away_goals);
        }
        if matches!(venue, Venue::Any | Venue::Away) {
            by_team
                .entry(m.away_key.as_str())
                .or_default()
                .add(m.away_goals, m.home_goals);
        }
    }
    let mut ranked: Vec<(String, Record)> = by_team
        .into_iter()
        .filter(|(_, r)| r.played >= min_matches)
        .map(|(k, r)| (k.to_string(), r))
        .collect();
    ranked.sort_by(|a, b| {
        b.1.win_rate()
            .partial_cmp(&a.1.win_rate())
            .unwrap_or(std::cmp::Ordering::Equal)
            .then(b.1.wins.cmp(&a.1.wins))
            .then(a.0.cmp(&b.0))
    });
    ranked
}

#[derive(Debug, Clone, Default)]
pub struct PlayerFilter {
    /// Case-insensitive substring of the player name.
    pub name: Option<String>,
    /// Case-insensitive exact match on nationality.
    pub nationality: Option<String>,
    /// Case-insensitive substring of the club name (accent-insensitive).
    pub club: Option<String>,
    /// Exact position code (e.g. "ST") or a group ("forward", "midfielder", "defender", "goalkeeper").
    pub position: Option<String>,
    pub min_overall: Option<u32>,
}

/// Position codes that belong to a broad position group.
pub fn position_codes(group: &str) -> Option<&'static [&'static str]> {
    match group.trim().to_lowercase().as_str() {
        "forward" | "forwards" | "attacker" | "attackers" | "striker" | "strikers" => {
            Some(&["ST", "CF", "LW", "RW", "LS", "RS", "LF", "RF"])
        }
        "midfielder" | "midfielders" | "midfield" => Some(&[
            "CAM", "CM", "CDM", "LM", "RM", "LCM", "RCM", "LAM", "RAM", "LDM", "RDM",
        ]),
        "defender" | "defenders" | "defence" | "defense" => {
            Some(&["CB", "LB", "RB", "LWB", "RWB", "LCB", "RCB"])
        }
        "goalkeeper" | "goalkeepers" | "keeper" | "gk" => Some(&["GK"]),
        _ => None,
    }
}

fn position_matches(player: &Player, wanted: &str) -> bool {
    let pos = player.position.to_uppercase();
    match position_codes(wanted) {
        Some(codes) => codes.contains(&pos.as_str()),
        None => pos == wanted.trim().to_uppercase(),
    }
}

fn nationality_matches(player: &Player, wanted: &str) -> bool {
    player.nationality.eq_ignore_ascii_case(wanted.trim())
}

/// Players matching the filter, highest overall rating first.
pub fn search_players<'a>(ds: &'a Dataset, filter: &PlayerFilter, limit: usize) -> Vec<&'a Player> {
    let name = filter.name.as_deref().map(|s| s.trim().to_lowercase());
    let club = filter.club.as_deref().map(team_key);
    let mut found: Vec<&Player> = ds
        .players
        .iter()
        .filter(|p| {
            name.as_ref()
                .is_none_or(|n| p.name.to_lowercase().contains(n))
        })
        .filter(|p| {
            filter
                .nationality
                .as_deref()
                .is_none_or(|n| nationality_matches(p, n))
        })
        .filter(|p| {
            club.as_ref()
                .is_none_or(|c| team_key(&p.club).contains(c.as_str()))
        })
        .filter(|p| {
            filter
                .position
                .as_deref()
                .is_none_or(|pos| position_matches(p, pos))
        })
        .filter(|p| filter.min_overall.is_none_or(|min| p.overall >= min))
        .collect();
    found.sort_by(|a, b| b.overall.cmp(&a.overall).then(a.name.cmp(&b.name)));
    found.truncate(limit);
    found
}

#[derive(Debug, Clone, PartialEq)]
pub struct ClubSummary {
    pub club: String,
    pub players: usize,
    pub average_overall: f64,
}

/// Per-club player counts and average overall for one nationality, largest squads first.
pub fn club_summary(ds: &Dataset, nationality: &str) -> Vec<ClubSummary> {
    let mut by_club: BTreeMap<&str, (usize, u64)> = BTreeMap::new();
    for p in ds
        .players
        .iter()
        .filter(|p| nationality_matches(p, nationality))
    {
        let club = p.club.trim();
        if club.is_empty() {
            continue;
        }
        let entry = by_club.entry(club).or_insert((0, 0));
        entry.0 += 1;
        entry.1 += u64::from(p.overall);
    }
    let mut rows: Vec<ClubSummary> = by_club
        .into_iter()
        .map(|(club, (n, total))| ClubSummary {
            club: club.to_string(),
            players: n,
            average_overall: total as f64 / n as f64,
        })
        .collect();
    rows.sort_by(|a, b| b.players.cmp(&a.players).then(a.club.cmp(&b.club)));
    rows
}
