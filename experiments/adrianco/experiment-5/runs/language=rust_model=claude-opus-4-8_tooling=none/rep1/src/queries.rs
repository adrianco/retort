//! Query and analysis functions over a [`Dataset`]. Each public function
//! returns a human-readable, formatted answer string.

use std::collections::HashMap;

use crate::data::Dataset;
use crate::model::Match;
use crate::normalize::{
    canon, club_matches, key_matches, resolve_competition, strip_accents,
};

// ---------------------------------------------------------------------------
// Shared helpers
// ---------------------------------------------------------------------------

/// True when the user's competition query selects the match's competition.
fn competition_selected(query: &str, comp: &str) -> bool {
    match resolve_competition(query) {
        Some(canonical) => comp == canonical,
        None => strip_accents(comp).to_lowercase().contains(&strip_accents(query).to_lowercase()),
    }
}

fn match_context(m: &Match) -> String {
    if let Some(stage) = &m.stage {
        format!("{} {}", m.competition, stage)
    } else if let Some(round) = &m.round {
        format!("{} Round {}", m.competition, round)
    } else {
        m.competition.clone()
    }
}

fn format_match_line(m: &Match) -> String {
    let date = if m.date.is_empty() { "????-??-??" } else { &m.date };
    format!(
        "- {}: {} {}-{} {} ({})",
        date, m.home_display, m.home_goal, m.away_goal, m.away_display, match_context(m),
    )
}

/// All matches passing the optional team / competition / season / date filters.
#[allow(clippy::too_many_arguments)]
fn filter_matches<'a>(
    ds: &'a Dataset,
    team: Option<&str>,
    team2: Option<&str>,
    competition: Option<&str>,
    season: Option<i32>,
    date_from: Option<&str>,
    date_to: Option<&str>,
) -> Vec<&'a Match> {
    let team_key = team.map(|t| canon(t).key);
    let team2_key = team2.map(|t| canon(t).key);
    ds.matches
        .iter()
        .filter(|m| {
            if let Some(t) = &team_key {
                if !(key_matches(t, &m.home_key) || key_matches(t, &m.away_key)) {
                    return false;
                }
            }
            if let Some(t) = &team2_key {
                if !(key_matches(t, &m.home_key) || key_matches(t, &m.away_key)) {
                    return false;
                }
            }
            if let Some(c) = competition {
                if !competition_selected(c, &m.competition) {
                    return false;
                }
            }
            if let Some(s) = season {
                if m.season != Some(s) {
                    return false;
                }
            }
            if let Some(from) = date_from {
                if m.date.as_str() < from {
                    return false;
                }
            }
            if let Some(to) = date_to {
                if m.date.as_str() > to {
                    return false;
                }
            }
            true
        })
        .collect()
}

fn sort_recent(matches: &mut [&Match]) {
    matches.sort_by(|a, b| b.date.cmp(&a.date));
}

// ---------------------------------------------------------------------------
// Match queries
// ---------------------------------------------------------------------------

#[derive(Default)]
pub struct MatchQuery<'a> {
    pub team: Option<&'a str>,
    pub team2: Option<&'a str>,
    pub competition: Option<&'a str>,
    pub season: Option<i32>,
    pub date_from: Option<&'a str>,
    pub date_to: Option<&'a str>,
    pub limit: usize,
}

pub fn search_matches(ds: &Dataset, q: &MatchQuery) -> String {
    let mut matches = filter_matches(
        ds, q.team, q.team2, q.competition, q.season, q.date_from, q.date_to,
    );
    if matches.is_empty() {
        return "No matches found for the given criteria.".to_string();
    }
    sort_recent(&mut matches);

    let limit = if q.limit == 0 { 25 } else { q.limit };
    let total = matches.len();

    let mut out = String::new();
    match (q.team, q.team2) {
        (Some(a), Some(b)) => {
            out.push_str(&format!("Matches: {} vs {}\n", canon(a).display, canon(b).display))
        }
        (Some(a), None) => out.push_str(&format!("Matches involving {}\n", canon(a).display)),
        _ => out.push_str("Matches\n"),
    }
    out.push_str(&format!("({total} found in dataset)\n\n"));

    for m in matches.iter().take(limit) {
        out.push_str(&format_match_line(m));
        out.push('\n');
    }
    if total > limit {
        out.push_str(&format!("... and {} more\n", total - limit));
    }

    if let (Some(a), Some(b)) = (q.team, q.team2) {
        out.push('\n');
        out.push_str(&head_to_head_summary(&matches, a, b));
    }
    out
}

fn head_to_head_summary(matches: &[&Match], a: &str, b: &str) -> String {
    let a_key = canon(a).key;
    let (mut a_wins, mut b_wins, mut draws, mut a_goals, mut b_goals) = (0, 0, 0, 0, 0);
    for m in matches {
        let (a_for, b_for) = if key_matches(&a_key, &m.home_key) {
            (m.home_goal, m.away_goal)
        } else {
            (m.away_goal, m.home_goal)
        };
        a_goals += a_for;
        b_goals += b_for;
        match a_for.cmp(&b_for) {
            std::cmp::Ordering::Greater => a_wins += 1,
            std::cmp::Ordering::Less => b_wins += 1,
            std::cmp::Ordering::Equal => draws += 1,
        }
    }
    format!(
        "Head-to-head in dataset: {} {} wins, {} {} wins, {} draws (goals {}-{})",
        canon(a).display, a_wins, canon(b).display, b_wins, draws, a_goals, b_goals,
    )
}

pub fn head_to_head(
    ds: &Dataset,
    team1: &str,
    team2: &str,
    competition: Option<&str>,
    season: Option<i32>,
) -> String {
    let q = MatchQuery {
        team: Some(team1),
        team2: Some(team2),
        competition,
        season,
        limit: 10,
        ..Default::default()
    };
    search_matches(ds, &q)
}

// ---------------------------------------------------------------------------
// Team statistics
// ---------------------------------------------------------------------------

#[derive(Default, Clone, Copy)]
struct Record {
    played: u32,
    wins: u32,
    draws: u32,
    losses: u32,
    gf: i32,
    ga: i32,
}

impl Record {
    fn add(&mut self, scored: i32, conceded: i32) {
        self.played += 1;
        self.gf += scored;
        self.ga += conceded;
        match scored.cmp(&conceded) {
            std::cmp::Ordering::Greater => self.wins += 1,
            std::cmp::Ordering::Equal => self.draws += 1,
            std::cmp::Ordering::Less => self.losses += 1,
        }
    }
    fn points(&self) -> u32 {
        self.wins * 3 + self.draws
    }
    fn win_rate(&self) -> f64 {
        if self.played == 0 {
            0.0
        } else {
            self.wins as f64 / self.played as f64 * 100.0
        }
    }
}

#[derive(Clone, Copy, PartialEq)]
pub enum Venue {
    All,
    Home,
    Away,
}

pub fn team_stats(
    ds: &Dataset,
    team: &str,
    season: Option<i32>,
    competition: Option<&str>,
    venue: Venue,
) -> String {
    let team_key = canon(team).key;
    let mut rec = Record::default();
    let mut resolved_name: Option<String> = None;

    for m in filter_matches(ds, Some(team), None, competition, season, None, None) {
        let is_home = key_matches(&team_key, &m.home_key);
        if (venue == Venue::Home && !is_home) || (venue == Venue::Away && is_home) {
            continue;
        }
        if resolved_name.is_none() {
            resolved_name = Some(if is_home { m.home_display.clone() } else { m.away_display.clone() });
        }
        if is_home {
            rec.add(m.home_goal, m.away_goal);
        } else {
            rec.add(m.away_goal, m.home_goal);
        }
    }

    if rec.played == 0 {
        return format!("No matches found for {}.", canon(team).display);
    }

    let name = resolved_name.unwrap_or_else(|| canon(team).display);
    let venue_label = match venue {
        Venue::All => "",
        Venue::Home => "home ",
        Venue::Away => "away ",
    };
    let scope = match (season, competition) {
        (Some(s), Some(c)) => format!(" ({s} {c})"),
        (Some(s), None) => format!(" ({s})"),
        (None, Some(c)) => format!(" ({c})"),
        (None, None) => String::new(),
    };

    format!(
        "{name} {venue_label}record{scope}:\n\
         - Matches: {}\n\
         - Wins: {}, Draws: {}, Losses: {}\n\
         - Goals For: {}, Goals Against: {} (diff {:+})\n\
         - Points: {}\n\
         - Win rate: {:.1}%",
        rec.played, rec.wins, rec.draws, rec.losses, rec.gf, rec.ga,
        rec.gf - rec.ga, rec.points(), rec.win_rate(),
    )
}

// ---------------------------------------------------------------------------
// Standings / league table
// ---------------------------------------------------------------------------

pub fn standings(ds: &Dataset, season: i32, competition: Option<&str>) -> String {
    let comp = competition.unwrap_or("Brasileirão");
    let matches = filter_matches(ds, None, None, Some(comp), Some(season), None, None);
    if matches.is_empty() {
        return format!("No matches found for {comp} in {season}.");
    }
    // Resolve the competition label for the heading.
    let comp_label = resolve_competition(comp).unwrap_or(comp);

    let mut table: HashMap<String, (String, Record)> = HashMap::new();
    for m in &matches {
        let home = table
            .entry(m.home_key.clone())
            .or_insert_with(|| (m.home_display.clone(), Record::default()));
        home.1.add(m.home_goal, m.away_goal);
        let away = table
            .entry(m.away_key.clone())
            .or_insert_with(|| (m.away_display.clone(), Record::default()));
        away.1.add(m.away_goal, m.home_goal);
    }

    let mut rows: Vec<(String, Record)> = table.into_values().collect();
    // Brazilian tiebreakers: points, then wins, then goal difference, then
    // goals for (then name for stable ordering).
    rows.sort_by(|a, b| {
        b.1.points()
            .cmp(&a.1.points())
            .then(b.1.wins.cmp(&a.1.wins))
            .then((b.1.gf - b.1.ga).cmp(&(a.1.gf - a.1.ga)))
            .then(b.1.gf.cmp(&a.1.gf))
            .then(a.0.cmp(&b.0))
    });

    let mut out = format!(
        "{season} {comp_label} standings (calculated from {} matches):\n",
        matches.len()
    );
    for (i, (name, rec)) in rows.iter().enumerate() {
        let tag = if i == 0 { " - Champion" } else { "" };
        out.push_str(&format!(
            "{:>2}. {} - {} pts ({}W {}D {}L, GF {} GA {} GD {:+}){}\n",
            i + 1, name, rec.points(), rec.wins, rec.draws, rec.losses,
            rec.gf, rec.ga, rec.gf - rec.ga, tag,
        ));
    }
    out
}

// ---------------------------------------------------------------------------
// Competition / aggregate statistics
// ---------------------------------------------------------------------------

pub fn competition_stats(ds: &Dataset, competition: Option<&str>, season: Option<i32>) -> String {
    let matches = filter_matches(ds, None, None, competition, season, None, None);
    if matches.is_empty() {
        return "No matches found for the given criteria.".to_string();
    }
    let total = matches.len();
    let total_goals: i32 = matches.iter().map(|m| m.total_goals()).sum();
    let home_wins = matches.iter().filter(|m| m.home_goal > m.away_goal).count();
    let away_wins = matches.iter().filter(|m| m.home_goal < m.away_goal).count();
    let draws = total - home_wins - away_wins;

    let mut by_margin: Vec<&Match> = matches.clone();
    by_margin.sort_by(|a, b| {
        (b.home_goal - b.away_goal)
            .abs()
            .cmp(&(a.home_goal - a.away_goal).abs())
            .then(b.total_goals().cmp(&a.total_goals()))
            .then(b.date.cmp(&a.date))
    });

    let mut goals_for: HashMap<String, (String, i32)> = HashMap::new();
    for m in &matches {
        let h = goals_for
            .entry(m.home_key.clone())
            .or_insert_with(|| (m.home_display.clone(), 0));
        h.1 += m.home_goal;
        let a = goals_for
            .entry(m.away_key.clone())
            .or_insert_with(|| (m.away_display.clone(), 0));
        a.1 += m.away_goal;
    }
    let mut top_scorers: Vec<(String, i32)> = goals_for.into_values().collect();
    top_scorers.sort_by(|a, b| b.1.cmp(&a.1).then(a.0.cmp(&b.0)));

    let scope = match (competition, season) {
        (Some(c), Some(s)) => format!("{} {s}", resolve_competition(c).unwrap_or(c)),
        (Some(c), None) => resolve_competition(c).unwrap_or(c).to_string(),
        (None, Some(s)) => format!("{s} (all competitions)"),
        (None, None) => "all competitions".to_string(),
    };

    let mut out = format!("Statistics for {scope}:\n");
    out.push_str(&format!("- Matches: {total}\n"));
    out.push_str(&format!(
        "- Average goals per match: {:.2}\n",
        total_goals as f64 / total as f64
    ));
    out.push_str(&format!(
        "- Home wins: {} ({:.1}%), Draws: {} ({:.1}%), Away wins: {} ({:.1}%)\n",
        home_wins, home_wins as f64 / total as f64 * 100.0,
        draws, draws as f64 / total as f64 * 100.0,
        away_wins, away_wins as f64 / total as f64 * 100.0,
    ));

    out.push_str("\nBiggest victories:\n");
    for m in by_margin.iter().take(5) {
        out.push_str(&format_match_line(m));
        out.push('\n');
    }

    out.push_str("\nTop scoring teams (goals for):\n");
    for (i, (name, goals)) in top_scorers.iter().take(5).enumerate() {
        out.push_str(&format!("{}. {} - {} goals\n", i + 1, name, goals));
    }
    out
}

// ---------------------------------------------------------------------------
// Player queries
// ---------------------------------------------------------------------------

#[derive(Default)]
pub struct PlayerQuery<'a> {
    pub name: Option<&'a str>,
    pub nationality: Option<&'a str>,
    pub club: Option<&'a str>,
    pub position: Option<&'a str>,
    pub min_overall: Option<i32>,
    pub limit: usize,
}

pub fn search_players(ds: &Dataset, q: &PlayerQuery) -> String {
    let name_q = q.name.map(|s| strip_accents(s).to_lowercase());
    let nat_q = q.nationality.map(|s| strip_accents(s).to_lowercase());
    let pos_q = q.position.map(|s| s.to_lowercase());

    let mut players: Vec<&crate::model::Player> = ds
        .players
        .iter()
        .filter(|p| {
            if let Some(n) = &name_q {
                if !strip_accents(&p.name).to_lowercase().contains(n) {
                    return false;
                }
            }
            if let Some(n) = &nat_q {
                if strip_accents(&p.nationality).to_lowercase() != *n {
                    return false;
                }
            }
            if let Some(c) = q.club {
                if !club_matches(c, &p.club) {
                    return false;
                }
            }
            if let Some(pos) = &pos_q {
                if p.position.to_lowercase() != *pos {
                    return false;
                }
            }
            if let Some(min) = q.min_overall {
                if p.overall.unwrap_or(0) < min {
                    return false;
                }
            }
            true
        })
        .collect();

    if players.is_empty() {
        return "No players found for the given criteria.".to_string();
    }

    players.sort_by(|a, b| b.overall.cmp(&a.overall).then(a.name.cmp(&b.name)));
    let total = players.len();
    let limit = if q.limit == 0 { 20 } else { q.limit };

    let mut out = format!("Players ({total} found):\n");
    for (i, p) in players.iter().take(limit).enumerate() {
        out.push_str(&format!(
            "{}. {} - Overall: {}, Potential: {}, Position: {}, Club: {}, Nationality: {}{}\n",
            i + 1,
            p.name,
            p.overall.map(|v| v.to_string()).unwrap_or_else(|| "?".into()),
            p.potential.map(|v| v.to_string()).unwrap_or_else(|| "?".into()),
            if p.position.is_empty() { "?" } else { &p.position },
            if p.club.is_empty() { "Free agent" } else { &p.club },
            p.nationality,
            p.age.map(|a| format!(", Age: {a}")).unwrap_or_default(),
        ));
    }
    if total > limit {
        out.push_str(&format!("... and {} more\n", total - limit));
    }
    out
}

/// Top-rated players plus, when a nationality is given, a per-club breakdown.
pub fn top_players(
    ds: &Dataset,
    nationality: Option<&str>,
    club: Option<&str>,
    position: Option<&str>,
    limit: usize,
) -> String {
    let q = PlayerQuery {
        nationality,
        club,
        position,
        limit,
        ..Default::default()
    };
    let mut out = search_players(ds, &q);

    if let Some(nat) = nationality {
        let nat_q = strip_accents(nat).to_lowercase();
        let mut by_club: HashMap<String, (String, u32, u64)> = HashMap::new();
        for p in ds.players.iter().filter(|p| {
            strip_accents(&p.nationality).to_lowercase() == nat_q && !p.club.is_empty()
        }) {
            let e = by_club
                .entry(p.club_norm.clone())
                .or_insert_with(|| (p.club.clone(), 0, 0));
            e.1 += 1;
            e.2 += p.overall.unwrap_or(0) as u64;
        }
        if !by_club.is_empty() {
            let mut rows: Vec<(String, u32, u64)> = by_club.into_values().collect();
            rows.sort_by(|a, b| b.1.cmp(&a.1).then(a.0.cmp(&b.0)));
            out.push_str(&format!("\n{} players by club:\n", nat));
            for (name, count, sum) in rows.iter().take(15) {
                out.push_str(&format!(
                    "- {}: {} players (avg rating: {:.0})\n",
                    name, count, *sum as f64 / *count as f64
                ));
            }
        }
    }
    out
}

// ---------------------------------------------------------------------------
// Dataset overview
// ---------------------------------------------------------------------------

pub fn list_datasets(ds: &Dataset) -> String {
    let mut out = String::from("Loaded Brazilian soccer datasets:\n");
    for (label, count) in &ds.source_counts {
        out.push_str(&format!("- {label}: {count} rows\n"));
    }
    out.push_str(&format!(
        "\nTotal unique matches after de-duplication: {}\n",
        ds.matches.len()
    ));
    out.push_str(&format!("Total players: {}\n", ds.players.len()));
    out
}
