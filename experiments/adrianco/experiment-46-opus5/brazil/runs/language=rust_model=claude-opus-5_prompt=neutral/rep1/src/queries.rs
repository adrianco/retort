//! Analytical queries over the knowledge graph.
//!
//! Every function takes resolved graph ids and returns plain data structures;
//! rendering lives in [`crate::format`] and argument parsing in
//! [`crate::tools`]. Aggregates consider canonical matches only (see
//! [`crate::graph`]) unless `include_all_sources` is set, so overlapping files
//! never double-count a fixture.

use std::collections::{BTreeMap, HashMap, HashSet};

use crate::graph::KnowledgeGraph;
use crate::model::*;

/// Home/away restriction shared by several queries.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Venue {
    All,
    Home,
    Away,
}

impl Venue {
    pub fn parse(raw: &str) -> Option<Venue> {
        match raw.trim().to_lowercase().as_str() {
            "" | "all" | "any" | "both" => Some(Venue::All),
            "home" => Some(Venue::Home),
            "away" => Some(Venue::Away),
            _ => None,
        }
    }

    pub fn label(&self) -> &'static str {
        match self {
            Venue::All => "all matches",
            Venue::Home => "home matches",
            Venue::Away => "away matches",
        }
    }
}

/// Filter set for [`search_matches`].
#[derive(Debug, Clone, Default)]
pub struct MatchQuery {
    pub team: Option<TeamId>,
    pub opponent: Option<TeamId>,
    pub home_team: Option<TeamId>,
    pub away_team: Option<TeamId>,
    pub competition: Option<Competition>,
    pub season: Option<i32>,
    pub date_from: Option<Date>,
    pub date_to: Option<Date>,
    pub stage_contains: Option<String>,
    pub min_goal_difference: Option<i32>,
    pub include_all_sources: bool,
    pub limit: usize,
    /// Chronological instead of most-recent-first.
    pub oldest_first: bool,
}

impl MatchQuery {
    pub fn new() -> MatchQuery {
        MatchQuery {
            limit: 20,
            ..Default::default()
        }
    }
}

/// Matches selected by [`search_matches`].
pub struct MatchSearch {
    /// Ids after filtering and sorting, truncated to `limit`.
    pub matches: Vec<MatchId>,
    /// Number of matches before truncation.
    pub total: usize,
    /// Head-to-head tally when both `team` and `opponent` were supplied.
    pub head_to_head: Option<HeadToHead>,
}

fn matches_filter(graph: &KnowledgeGraph, query: &MatchQuery, m: &Match) -> bool {
    if !query.include_all_sources && !m.canonical {
        return false;
    }
    if let Some(team) = query.team {
        if !m.involves(team) {
            return false;
        }
    }
    if let Some(opponent) = query.opponent {
        if !m.involves(opponent) {
            return false;
        }
        if query.team.is_some() && m.home == m.away {
            return false;
        }
    }
    if let Some(home) = query.home_team {
        if m.home != home {
            return false;
        }
    }
    if let Some(away) = query.away_team {
        if m.away != away {
            return false;
        }
    }
    if let Some(competition) = query.competition {
        if m.competition != competition {
            return false;
        }
    }
    if let Some(season) = query.season {
        if m.season != season {
            return false;
        }
    }
    if let Some(from) = query.date_from {
        match m.date {
            Some(date) if date >= from => {}
            _ => return false,
        }
    }
    if let Some(to) = query.date_to {
        match m.date {
            Some(date) if date <= to => {}
            _ => return false,
        }
    }
    if let Some(needle) = &query.stage_contains {
        let needle = crate::normalize::simplify(needle);
        let haystack = crate::normalize::simplify(&format!(
            "{} {}",
            m.stage.clone().unwrap_or_default(),
            m.round.clone().unwrap_or_default()
        ));
        // Whole-word matching, so "final" does not also select "semifinals";
        // multi-word needles ("group stage") fall back to a substring test.
        let matched = haystack.split_whitespace().any(|word| word == needle)
            || (needle.contains(' ') && haystack.contains(&needle));
        if !matched {
            return false;
        }
    }
    if let Some(min_diff) = query.min_goal_difference {
        match m.goal_difference() {
            Some(diff) if diff >= min_diff => {}
            _ => return false,
        }
    }
    let _ = graph;
    true
}

/// Narrowest index that still covers the query, so filtering stays cheap.
fn candidates(graph: &KnowledgeGraph, query: &MatchQuery) -> Vec<MatchId> {
    if let Some(team) = query.team.or(query.home_team).or(query.away_team) {
        return graph.team_matches(team).to_vec();
    }
    if let Some(opponent) = query.opponent {
        return graph.team_matches(opponent).to_vec();
    }
    if let Some(competition) = query.competition {
        return graph.competition_matches(competition).to_vec();
    }
    (0..graph.matches.len()).collect()
}

/// Finds matches by team, opponent, competition, season and date range.
pub fn search_matches(graph: &KnowledgeGraph, query: &MatchQuery) -> MatchSearch {
    let mut hits: Vec<MatchId> = candidates(graph, query)
        .into_iter()
        .filter(|id| matches_filter(graph, query, graph.match_by_id(*id)))
        .collect();
    hits.sort_by(|a, b| {
        let (ma, mb) = (graph.match_by_id(*a), graph.match_by_id(*b));
        if query.oldest_first {
            ma.date.cmp(&mb.date).then(ma.id.cmp(&mb.id))
        } else {
            mb.date.cmp(&ma.date).then(mb.id.cmp(&ma.id))
        }
    });
    let total = hits.len();
    let head_to_head = match (query.team, query.opponent) {
        (Some(a), Some(b)) => Some(head_to_head_from(graph, a, b, &hits)),
        _ => None,
    };
    if query.limit > 0 {
        hits.truncate(query.limit);
    }
    MatchSearch {
        matches: hits,
        total,
        head_to_head,
    }
}

/// Head-to-head summary between two clubs, from `team_a`'s perspective.
pub struct HeadToHead {
    pub team_a: TeamId,
    pub team_b: TeamId,
    pub record: Record,
    pub by_competition: Vec<(Competition, Record)>,
    pub matches: Vec<MatchId>,
    pub biggest_a: Option<MatchId>,
    pub biggest_b: Option<MatchId>,
    pub last_meeting: Option<MatchId>,
}

fn head_to_head_from(
    graph: &KnowledgeGraph,
    team_a: TeamId,
    team_b: TeamId,
    ids: &[MatchId],
) -> HeadToHead {
    let mut record = Record::default();
    let mut by_competition: BTreeMap<Competition, Record> = BTreeMap::new();
    let mut biggest_a: Option<(i32, MatchId)> = None;
    let mut biggest_b: Option<(i32, MatchId)> = None;
    let mut ordered: Vec<MatchId> = ids.to_vec();
    ordered.sort_by_key(|id| graph.match_by_id(*id).date);

    for id in &ordered {
        let m = graph.match_by_id(*id);
        let Some((goals_for, goals_against)) = m.goals_for(team_a) else {
            continue;
        };
        record.add(goals_for, goals_against);
        by_competition
            .entry(m.competition)
            .or_default()
            .add(goals_for, goals_against);
        let margin = goals_for - goals_against;
        if margin > 0 && biggest_a.map(|(best, _)| margin > best).unwrap_or(true) {
            biggest_a = Some((margin, *id));
        }
        if margin < 0 && biggest_b.map(|(best, _)| -margin > best).unwrap_or(true) {
            biggest_b = Some((-margin, *id));
        }
    }
    let last_meeting = ordered.last().copied();
    HeadToHead {
        team_a,
        team_b,
        record,
        by_competition: by_competition.into_iter().collect(),
        matches: ordered,
        biggest_a: biggest_a.map(|(_, id)| id),
        biggest_b: biggest_b.map(|(_, id)| id),
        last_meeting,
    }
}

/// Head-to-head across every competition (optionally narrowed).
pub fn head_to_head(
    graph: &KnowledgeGraph,
    team_a: TeamId,
    team_b: TeamId,
    competition: Option<Competition>,
    season: Option<i32>,
    include_all_sources: bool,
) -> HeadToHead {
    let query = MatchQuery {
        team: Some(team_a),
        opponent: Some(team_b),
        competition,
        season,
        include_all_sources,
        limit: 0,
        ..MatchQuery::new()
    };
    let ids: Vec<MatchId> = candidates(graph, &query)
        .into_iter()
        .filter(|id| matches_filter(graph, &query, graph.match_by_id(*id)))
        .collect();
    head_to_head_from(graph, team_a, team_b, &ids)
}

/// Full statistical picture of one club.
pub struct TeamStats {
    pub team: TeamId,
    pub venue: Venue,
    pub season: Option<i32>,
    pub competition: Option<Competition>,
    pub overall: Record,
    pub home: Record,
    pub away: Record,
    pub by_competition: Vec<(Competition, Record)>,
    pub by_season: Vec<(i32, Record)>,
    pub biggest_win: Option<MatchId>,
    pub biggest_defeat: Option<MatchId>,
    pub first_match: Option<MatchId>,
    pub last_match: Option<MatchId>,
    pub matches_considered: Vec<MatchId>,
}

/// Wins/draws/losses/goals for a club, optionally per season, competition and
/// venue.
pub fn team_stats(
    graph: &KnowledgeGraph,
    team: TeamId,
    competition: Option<Competition>,
    season: Option<i32>,
    venue: Venue,
    include_all_sources: bool,
) -> TeamStats {
    let mut overall = Record::default();
    let mut home = Record::default();
    let mut away = Record::default();
    let mut by_competition: BTreeMap<Competition, Record> = BTreeMap::new();
    let mut by_season: BTreeMap<i32, Record> = BTreeMap::new();
    let mut biggest_win: Option<(i32, MatchId)> = None;
    let mut biggest_defeat: Option<(i32, MatchId)> = None;
    let mut considered = Vec::new();

    for id in graph.team_matches(team) {
        let m = graph.match_by_id(*id);
        if !include_all_sources && !m.canonical {
            continue;
        }
        if competition.map(|c| m.competition != c).unwrap_or(false) {
            continue;
        }
        if season.map(|s| m.season != s).unwrap_or(false) {
            continue;
        }
        let is_home = m.home == team;
        match venue {
            Venue::Home if !is_home => continue,
            Venue::Away if is_home => continue,
            _ => {}
        }
        let Some((goals_for, goals_against)) = m.goals_for(team) else {
            continue;
        };
        considered.push(*id);
        overall.add(goals_for, goals_against);
        if is_home {
            home.add(goals_for, goals_against);
        } else {
            away.add(goals_for, goals_against);
        }
        by_competition
            .entry(m.competition)
            .or_default()
            .add(goals_for, goals_against);
        by_season
            .entry(m.season)
            .or_default()
            .add(goals_for, goals_against);
        let margin = goals_for - goals_against;
        if margin > 0 && biggest_win.map(|(best, _)| margin > best).unwrap_or(true) {
            biggest_win = Some((margin, *id));
        }
        if margin < 0
            && biggest_defeat
                .map(|(best, _)| -margin > best)
                .unwrap_or(true)
        {
            biggest_defeat = Some((-margin, *id));
        }
    }
    considered.sort_by_key(|id| graph.match_by_id(*id).date);

    TeamStats {
        team,
        venue,
        season,
        competition,
        overall,
        home,
        away,
        by_competition: by_competition.into_iter().collect(),
        by_season: by_season.into_iter().collect(),
        biggest_win: biggest_win.map(|(_, id)| id),
        biggest_defeat: biggest_defeat.map(|(_, id)| id),
        first_match: considered.first().copied(),
        last_match: considered.last().copied(),
        matches_considered: considered,
    }
}

/// One line of a league table.
pub struct StandingRow {
    pub position: usize,
    pub team: TeamId,
    pub record: Record,
    pub home: Record,
    pub away: Record,
}

/// Calculated league table.
pub struct Standings {
    pub competition: Competition,
    pub season: i32,
    pub rows: Vec<StandingRow>,
    pub matches_counted: usize,
    /// Matches a full double round-robin between these clubs would produce.
    pub matches_expected: usize,
    pub rounds_played: Option<i32>,
    /// True when the season looks complete (every side played 2N-2 matches).
    pub complete: bool,
    pub source: Option<Source>,
}

impl Standings {
    /// Bottom four of a 20-team Série A/B season.
    pub fn relegated(&self) -> Vec<&StandingRow> {
        if !self.complete
            || self.rows.len() != 20
            || !matches!(self.competition, Competition::SerieA | Competition::SerieB)
        {
            return Vec::new();
        }
        self.rows.iter().rev().take(4).rev().collect()
    }

    pub fn champion(&self) -> Option<&StandingRow> {
        if self.complete {
            self.rows.first()
        } else {
            None
        }
    }
}

/// Builds a league table from match results (3 points for a win).
///
/// Only meaningful for the round-robin competitions; knockout competitions
/// return a table of results without positions being a "title".
pub fn standings(
    graph: &KnowledgeGraph,
    competition: Competition,
    season: i32,
    include_all_sources: bool,
) -> Standings {
    let mut totals: HashMap<TeamId, (Record, Record, Record)> = HashMap::new();
    let mut counted = 0usize;
    let mut max_round = None;
    let mut source = None;
    for id in graph.competition_matches(competition) {
        let m = graph.match_by_id(*id);
        if m.season != season || (!include_all_sources && !m.canonical) || !m.played() {
            continue;
        }
        source.get_or_insert(m.source);
        counted += 1;
        if let Some(round) = m.round.as_ref().and_then(|r| r.parse::<i32>().ok()) {
            max_round = Some(max_round.map_or(round, |current: i32| current.max(round)));
        }
        let (home_goals, away_goals) = (m.home_goals.unwrap(), m.away_goals.unwrap());
        {
            let entry = totals.entry(m.home).or_default();
            entry.0.add(home_goals, away_goals);
            entry.1.add(home_goals, away_goals);
        }
        {
            let entry = totals.entry(m.away).or_default();
            entry.0.add(away_goals, home_goals);
            entry.2.add(away_goals, home_goals);
        }
    }

    let mut rows: Vec<StandingRow> = totals
        .into_iter()
        .map(|(team, (record, home, away))| StandingRow {
            position: 0,
            team,
            record,
            home,
            away,
        })
        .collect();
    rows.sort_by(|a, b| {
        b.record
            .points()
            .cmp(&a.record.points())
            .then(b.record.wins.cmp(&a.record.wins))
            .then(b.record.goal_difference().cmp(&a.record.goal_difference()))
            .then(b.record.goals_for.cmp(&a.record.goals_for))
            .then(graph.team(a.team).name.cmp(&graph.team(b.team).name))
    });
    for (idx, row) in rows.iter_mut().enumerate() {
        row.position = idx + 1;
    }

    let teams = rows.len();
    let expected = if teams > 1 { teams * (teams - 1) } else { 0 };
    // A couple of fixtures are missing from some source files; 98% of a full
    // double round-robin is still enough to name a champion.
    let complete = matches!(
        competition,
        Competition::SerieA | Competition::SerieB | Competition::SerieC
    ) && teams >= 16
        && counted as f64 >= expected as f64 * 0.98;

    Standings {
        competition,
        season,
        rows,
        matches_counted: counted,
        matches_expected: expected,
        rounds_played: max_round,
        complete,
        source,
    }
}

/// Aggregate numbers for one competition-season.
#[derive(Debug, Clone)]
pub struct SeasonSummary {
    pub season: i32,
    pub matches: usize,
    pub goals: i32,
    pub home_wins: usize,
    pub draws: usize,
    pub away_wins: usize,
    pub teams: usize,
}

impl SeasonSummary {
    pub fn goals_per_match(&self) -> f64 {
        if self.matches == 0 {
            0.0
        } else {
            self.goals as f64 / self.matches as f64
        }
    }

    pub fn rate(&self, count: usize) -> f64 {
        if self.matches == 0 {
            0.0
        } else {
            count as f64 * 100.0 / self.matches as f64
        }
    }

    fn merge(&mut self, other: &SeasonSummary) {
        self.matches += other.matches;
        self.goals += other.goals;
        self.home_wins += other.home_wins;
        self.draws += other.draws;
        self.away_wins += other.away_wins;
    }
}

/// Competition-level statistics, per season and in total.
pub struct CompetitionStats {
    pub competition: Competition,
    pub seasons: Vec<SeasonSummary>,
    pub total: SeasonSummary,
    pub highest_scoring: Option<MatchId>,
    pub biggest_margin: Option<MatchId>,
}

/// Goals per match, home/draw/away split, per season and overall.
pub fn competition_stats(
    graph: &KnowledgeGraph,
    competition: Competition,
    seasons: Option<&[i32]>,
    include_all_sources: bool,
) -> CompetitionStats {
    let mut per_season: BTreeMap<i32, (SeasonSummary, HashSet<TeamId>)> = BTreeMap::new();
    let mut highest: Option<(i32, MatchId)> = None;
    let mut widest: Option<(i32, MatchId)> = None;

    for id in graph.competition_matches(competition) {
        let m = graph.match_by_id(*id);
        if !include_all_sources && !m.canonical {
            continue;
        }
        if let Some(filter) = seasons {
            if !filter.contains(&m.season) {
                continue;
            }
        }
        if !m.played() {
            continue;
        }
        let entry = per_season.entry(m.season).or_insert_with(|| {
            (
                SeasonSummary {
                    season: m.season,
                    matches: 0,
                    goals: 0,
                    home_wins: 0,
                    draws: 0,
                    away_wins: 0,
                    teams: 0,
                },
                HashSet::new(),
            )
        });
        entry.0.matches += 1;
        entry.0.goals += m.total_goals().unwrap_or(0);
        match m.outcome() {
            Some(Outcome::HomeWin) => entry.0.home_wins += 1,
            Some(Outcome::Draw) => entry.0.draws += 1,
            Some(Outcome::AwayWin) => entry.0.away_wins += 1,
            None => {}
        }
        entry.1.insert(m.home);
        entry.1.insert(m.away);

        let goals = m.total_goals().unwrap_or(0);
        if highest.map(|(best, _)| goals > best).unwrap_or(true) {
            highest = Some((goals, *id));
        }
        let margin = m.goal_difference().unwrap_or(0);
        if widest.map(|(best, _)| margin > best).unwrap_or(true) {
            widest = Some((margin, *id));
        }
    }

    let mut total = SeasonSummary {
        season: 0,
        matches: 0,
        goals: 0,
        home_wins: 0,
        draws: 0,
        away_wins: 0,
        teams: 0,
    };
    let mut seasons_out = Vec::new();
    let mut all_teams = HashSet::new();
    for (_, (mut summary, teams)) in per_season {
        summary.teams = teams.len();
        all_teams.extend(teams);
        total.merge(&summary);
        seasons_out.push(summary);
    }
    total.teams = all_teams.len();

    CompetitionStats {
        competition,
        seasons: seasons_out,
        total,
        highest_scoring: highest.map(|(_, id)| id),
        biggest_margin: widest.map(|(_, id)| id),
    }
}

/// Ranking metric for [`team_rankings`].
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Metric {
    Points,
    Wins,
    WinRate,
    GoalsFor,
    GoalsAgainst,
    GoalDifference,
    GoalsForPerMatch,
    CleanSheets,
    Matches,
}

impl Metric {
    pub fn parse(raw: &str) -> Option<Metric> {
        match crate::normalize::simplify(raw).replace(' ', "_").as_str() {
            "points" | "pts" => Some(Metric::Points),
            "wins" | "most_wins" => Some(Metric::Wins),
            "win_rate" | "winrate" | "best_record" | "record" => Some(Metric::WinRate),
            "goals_for" | "goals" | "goals_scored" | "most_goals" => Some(Metric::GoalsFor),
            "goals_against" | "goals_conceded" => Some(Metric::GoalsAgainst),
            "goal_difference" | "gd" => Some(Metric::GoalDifference),
            "goals_for_per_match" | "goals_per_match" => Some(Metric::GoalsForPerMatch),
            "clean_sheets" | "cleansheets" => Some(Metric::CleanSheets),
            "matches" | "games" => Some(Metric::Matches),
            _ => None,
        }
    }

    pub fn label(&self) -> &'static str {
        match self {
            Metric::Points => "points",
            Metric::Wins => "wins",
            Metric::WinRate => "win rate",
            Metric::GoalsFor => "goals scored",
            Metric::GoalsAgainst => "goals conceded",
            Metric::GoalDifference => "goal difference",
            Metric::GoalsForPerMatch => "goals scored per match",
            Metric::CleanSheets => "clean sheets",
            Metric::Matches => "matches played",
        }
    }

    pub fn value(&self, record: &Record) -> f64 {
        match self {
            Metric::Points => record.points() as f64,
            Metric::Wins => record.wins as f64,
            Metric::WinRate => record.win_rate(),
            Metric::GoalsFor => record.goals_for as f64,
            Metric::GoalsAgainst => record.goals_against as f64,
            Metric::GoalDifference => record.goal_difference() as f64,
            Metric::GoalsForPerMatch => record.goals_for_per_match(),
            Metric::CleanSheets => record.clean_sheets as f64,
            Metric::Matches => record.matches as f64,
        }
    }

    /// Conceding fewer goals is better; everything else ranks descending.
    pub fn ascending(&self) -> bool {
        matches!(self, Metric::GoalsAgainst)
    }
}

pub struct RankedTeam {
    pub team: TeamId,
    pub record: Record,
    pub value: f64,
}

/// Filter set for [`team_rankings`].
pub struct RankingQuery {
    pub competition: Option<Competition>,
    pub season: Option<i32>,
    pub venue: Venue,
    pub metric: Metric,
    /// Clubs with fewer matches are excluded, so a single lucky win cannot top
    /// a win-rate ranking.
    pub min_matches: i32,
    pub limit: usize,
    pub include_all_sources: bool,
}

/// Ranks clubs by a metric, e.g. "which team has the best away record?".
pub fn team_rankings(graph: &KnowledgeGraph, query: &RankingQuery) -> Vec<RankedTeam> {
    let RankingQuery {
        competition,
        season,
        venue,
        metric,
        min_matches,
        limit,
        include_all_sources,
    } = *query;

    let mut totals: HashMap<TeamId, Record> = HashMap::new();
    let pool: Vec<MatchId> = match competition {
        Some(c) => graph.competition_matches(c).to_vec(),
        None => (0..graph.matches.len()).collect(),
    };
    for id in pool {
        let m = graph.match_by_id(id);
        if !include_all_sources && !m.canonical {
            continue;
        }
        if season.map(|s| m.season != s).unwrap_or(false) || !m.played() {
            continue;
        }
        let (home_goals, away_goals) = (m.home_goals.unwrap(), m.away_goals.unwrap());
        if venue != Venue::Away {
            totals
                .entry(m.home)
                .or_default()
                .add(home_goals, away_goals);
        }
        if venue != Venue::Home {
            totals
                .entry(m.away)
                .or_default()
                .add(away_goals, home_goals);
        }
    }
    let mut ranked: Vec<RankedTeam> = totals
        .into_iter()
        .filter(|(_, record)| record.matches >= min_matches)
        .map(|(team, record)| {
            let value = metric.value(&record);
            RankedTeam {
                team,
                record,
                value,
            }
        })
        .collect();
    ranked.sort_by(|a, b| {
        let ordering = if metric.ascending() {
            a.value.partial_cmp(&b.value).unwrap()
        } else {
            b.value.partial_cmp(&a.value).unwrap()
        };
        ordering
            .then(b.record.points().cmp(&a.record.points()))
            .then(graph.team(a.team).name.cmp(&graph.team(b.team).name))
    });
    if limit > 0 {
        ranked.truncate(limit);
    }
    ranked
}

/// Largest winning margins, optionally scoped to a team/competition/season.
pub fn biggest_wins(
    graph: &KnowledgeGraph,
    competition: Option<Competition>,
    season: Option<i32>,
    team: Option<TeamId>,
    limit: usize,
    include_all_sources: bool,
) -> Vec<MatchId> {
    let pool: Vec<MatchId> = match (team, competition) {
        (Some(t), _) => graph.team_matches(t).to_vec(),
        (None, Some(c)) => graph.competition_matches(c).to_vec(),
        (None, None) => (0..graph.matches.len()).collect(),
    };
    let mut hits: Vec<MatchId> = pool
        .into_iter()
        .filter(|id| {
            let m = graph.match_by_id(*id);
            if !include_all_sources && !m.canonical {
                return false;
            }
            if competition.map(|c| m.competition != c).unwrap_or(false) {
                return false;
            }
            if season.map(|s| m.season != s).unwrap_or(false) {
                return false;
            }
            if let Some(t) = team {
                // Only wins by the requested team.
                return m
                    .goals_for(t)
                    .map(|(scored, conceded)| scored > conceded)
                    .unwrap_or(false);
            }
            m.played()
        })
        .collect();
    hits.sort_by(|a, b| {
        let (ma, mb) = (graph.match_by_id(*a), graph.match_by_id(*b));
        mb.goal_difference()
            .cmp(&ma.goal_difference())
            .then(mb.total_goals().cmp(&ma.total_goals()))
            .then(mb.date.cmp(&ma.date))
    });
    if limit > 0 {
        hits.truncate(limit);
    }
    hits
}

/// Where a club has played: competitions, seasons and overall record.
pub struct TeamProfile {
    pub team: TeamId,
    pub overall: Record,
    pub competitions: Vec<(Competition, Vec<i32>, Record)>,
    pub squad: Vec<PlayerId>,
    pub first_match: Option<MatchId>,
    pub last_match: Option<MatchId>,
}

pub fn team_profile(
    graph: &KnowledgeGraph,
    team: TeamId,
    include_all_sources: bool,
) -> TeamProfile {
    let mut overall = Record::default();
    let mut per_competition: BTreeMap<Competition, (BTreeSetLike, Record)> = BTreeMap::new();
    let mut first: Option<MatchId> = None;
    let mut last: Option<MatchId> = None;

    for id in graph.team_matches(team) {
        let m = graph.match_by_id(*id);
        if !include_all_sources && !m.canonical {
            continue;
        }
        let entry = per_competition
            .entry(m.competition)
            .or_insert_with(|| (BTreeSetLike::default(), Record::default()));
        entry.0.insert(m.season);
        if let Some((goals_for, goals_against)) = m.goals_for(team) {
            overall.add(goals_for, goals_against);
            entry.1.add(goals_for, goals_against);
        }
        if m.date.is_some() {
            if first.is_none() || m.date < graph.match_by_id(first.unwrap()).date {
                first = Some(*id);
            }
            if last.is_none() || m.date > graph.match_by_id(last.unwrap()).date {
                last = Some(*id);
            }
        }
    }

    let mut squad = graph.players_of_team(team).to_vec();
    squad.sort_by_key(|id| std::cmp::Reverse(graph.player(*id).overall));

    TeamProfile {
        team,
        overall,
        competitions: per_competition
            .into_iter()
            .map(|(competition, (seasons, record))| (competition, seasons.into_vec(), record))
            .collect(),
        squad,
        first_match: first,
        last_match: last,
    }
}

/// Tiny ordered-set helper so seasons come out sorted and unique.
#[derive(Default)]
struct BTreeSetLike(std::collections::BTreeSet<i32>);

impl BTreeSetLike {
    fn insert(&mut self, value: i32) {
        self.0.insert(value);
    }

    fn into_vec(self) -> Vec<i32> {
        self.0.into_iter().collect()
    }
}

/// Filter set for [`search_players`].
#[derive(Debug, Clone, Default)]
pub struct PlayerQuery {
    pub name: Option<String>,
    pub nationality: Option<String>,
    pub club: Option<String>,
    pub club_team: Option<TeamId>,
    pub position: Option<String>,
    pub min_overall: Option<i32>,
    pub max_age: Option<i32>,
    pub min_age: Option<i32>,
    pub brazilian_clubs_only: bool,
    pub sort_by: PlayerSort,
    pub limit: usize,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum PlayerSort {
    #[default]
    Overall,
    Potential,
    Age,
    Name,
}

impl PlayerSort {
    pub fn parse(raw: &str) -> Option<PlayerSort> {
        match crate::normalize::simplify(raw).as_str() {
            "" | "overall" | "rating" => Some(PlayerSort::Overall),
            "potential" => Some(PlayerSort::Potential),
            "age" => Some(PlayerSort::Age),
            "name" => Some(PlayerSort::Name),
            _ => None,
        }
    }
}

pub struct PlayerSearch {
    pub players: Vec<PlayerId>,
    pub total: usize,
    /// Average FIFA overall across every match (not just the returned page).
    pub average_overall: f64,
}

/// Searches the FIFA database by name, nationality, club, position and rating.
pub fn search_players(graph: &KnowledgeGraph, query: &PlayerQuery) -> PlayerSearch {
    let base: Vec<PlayerId> = if let Some(name) = &query.name {
        graph.players_by_name(name)
    } else if let Some(team) = query.club_team {
        graph.players_of_team(team).to_vec()
    } else if let Some(nationality) = &query.nationality {
        graph.players_of_nationality(nationality).to_vec()
    } else {
        (0..graph.players.len()).collect()
    };

    let club_key = query.club.as_deref().map(crate::normalize::text_key);
    // Resolve the club name to a graph team once, so "Atlético-MG" also finds
    // players whose FIFA club column spells it "Atlético Mineiro".
    let club_as_team = query
        .club
        .as_deref()
        .and_then(|club| graph.require_team(club).ok());
    let position_key = query.position.as_deref().map(crate::normalize::text_key);
    let nationality_key = query.nationality.as_deref().map(crate::normalize::text_key);

    let mut hits: Vec<PlayerId> = base
        .into_iter()
        .filter(|id| {
            let player = graph.player(*id);
            if let Some(nationality) = &nationality_key {
                if crate::normalize::text_key(&player.nationality) != *nationality {
                    return false;
                }
            }
            if let Some(club) = &club_key {
                let matches_club = player
                    .club
                    .as_deref()
                    .map(|c| crate::normalize::text_key(c).contains(club.as_str()))
                    .unwrap_or(false)
                    || (player.club_team.is_some() && player.club_team == club_as_team);
                if !matches_club {
                    return false;
                }
            }
            if let Some(team) = query.club_team {
                if player.club_team != Some(team) {
                    return false;
                }
            }
            if let Some(position) = &position_key {
                match player.position.as_deref() {
                    Some(actual) if crate::normalize::text_key(actual) == *position => {}
                    _ => return false,
                }
            }
            if let Some(min_overall) = query.min_overall {
                if player.overall < min_overall {
                    return false;
                }
            }
            if let Some(max_age) = query.max_age {
                if player.age.map(|a| a > max_age).unwrap_or(true) {
                    return false;
                }
            }
            if let Some(min_age) = query.min_age {
                if player.age.map(|a| a < min_age).unwrap_or(true) {
                    return false;
                }
            }
            if query.brazilian_clubs_only && player.club_team.is_none() {
                return false;
            }
            true
        })
        .collect();

    // Name searches arrive pre-ranked by relevance; keep that order.
    if query.name.is_none() {
        hits.sort_by(|a, b| {
            let (pa, pb) = (graph.player(*a), graph.player(*b));
            match query.sort_by {
                PlayerSort::Overall => pb.overall.cmp(&pa.overall).then(pa.name.cmp(&pb.name)),
                PlayerSort::Potential => {
                    pb.potential.cmp(&pa.potential).then(pa.name.cmp(&pb.name))
                }
                PlayerSort::Age => pa.age.cmp(&pb.age).then(pa.name.cmp(&pb.name)),
                PlayerSort::Name => pa.name.cmp(&pb.name),
            }
        });
    }

    let total = hits.len();
    let average_overall = if total == 0 {
        0.0
    } else {
        hits.iter()
            .map(|id| graph.player(*id).overall as f64)
            .sum::<f64>()
            / total as f64
    };
    if query.limit > 0 {
        hits.truncate(query.limit);
    }
    PlayerSearch {
        players: hits,
        total,
        average_overall,
    }
}

/// Per-club roster summary for the Brazilian clubs present in the FIFA file.
pub struct ClubSquad {
    pub team: Option<TeamId>,
    pub club_label: String,
    pub players: Vec<PlayerId>,
    pub average_overall: f64,
    pub brazilian_players: usize,
    /// Explains a same-named foreign club that was deliberately not linked.
    pub note: Option<String>,
}

/// Squad of a club in the FIFA file.
///
/// When the name resolves to a Brazilian club in the match graph, only players
/// actually linked to that club are returned — a FIFA entry that merely shares
/// the name (Portugal's Boavista FC vs Boavista-RJ) is reported as a note
/// instead of being passed off as the Brazilian side. Clubs outside Brazil are
/// matched on the raw FIFA club name.
pub fn club_squad(graph: &KnowledgeGraph, club: &str) -> ClubSquad {
    let team = graph.require_team(club).ok();
    let key = crate::normalize::text_key(club);
    let name_matches = |player: &crate::model::Player| {
        player
            .club
            .as_deref()
            .map(|c| crate::normalize::text_key(c).contains(&key))
            .unwrap_or(false)
    };
    let mut note = None;
    let mut players: Vec<PlayerId> = match team {
        Some(team) => {
            let linked = graph.players_of_team(team).to_vec();
            if linked.is_empty() {
                let lookalikes: Vec<&str> = graph
                    .players
                    .iter()
                    .filter(|player| name_matches(player))
                    .filter_map(|player| player.club.as_deref())
                    .collect();
                if let Some(other) = lookalikes.first() {
                    note = Some(format!(
                        "The FIFA file has a club called '{other}', but its squad is not a Brazilian one, so it is kept separate from {}.",
                        graph.team(team).display()
                    ));
                }
            }
            linked
        }
        None => graph
            .players
            .iter()
            .filter(|player| name_matches(player))
            .map(|player| player.id)
            .collect(),
    };
    players.sort_by(|a, b| {
        graph
            .player(*b)
            .overall
            .cmp(&graph.player(*a).overall)
            .then(graph.player(*a).name.cmp(&graph.player(*b).name))
    });
    let average_overall = if players.is_empty() {
        0.0
    } else {
        players
            .iter()
            .map(|id| graph.player(*id).overall as f64)
            .sum::<f64>()
            / players.len() as f64
    };
    let brazilian_players = players
        .iter()
        .filter(|id| graph.player(**id).nationality == "Brazil")
        .count();
    let club_label = match team {
        Some(id) => graph.team(id).display(),
        None => players
            .first()
            .and_then(|id| graph.player(*id).club.clone())
            .unwrap_or_else(|| club.to_string()),
    };
    ClubSquad {
        team,
        club_label,
        players,
        average_overall,
        brazilian_players,
        note,
    }
}

/// Clubs from the FIFA file that are also present in the match graph, i.e. the
/// clubs where player and match data can be cross-referenced.
pub fn linked_clubs(graph: &KnowledgeGraph) -> Vec<(TeamId, usize, f64)> {
    let mut out: Vec<(TeamId, usize, f64)> = graph
        .teams
        .iter()
        .filter_map(|team| {
            let squad = graph.players_of_team(team.id);
            if squad.is_empty() {
                return None;
            }
            let average = squad
                .iter()
                .map(|id| graph.player(*id).overall as f64)
                .sum::<f64>()
                / squad.len() as f64;
            Some((team.id, squad.len(), average))
        })
        .collect();
    out.sort_by(|a, b| b.2.partial_cmp(&a.2).unwrap().then(a.0.cmp(&b.0)));
    out
}
