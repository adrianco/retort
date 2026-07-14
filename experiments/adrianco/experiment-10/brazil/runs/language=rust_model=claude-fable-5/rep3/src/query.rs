// =============================================================================
// CONTEXT: Brazilian Soccer MCP Server — query engine
//
// Implements all the query capabilities required by the specification on top
// of the loaded `Data`:
//   * search_matches      — by team / opponent / competition / season /
//                           date range / stage (incl. finals detection)
//   * team_stats          — W/D/L, goals for/against, win rate, optionally
//                           filtered by season, competition and venue
//   * head_to_head        — record between two teams + recent meetings
//   * standings           — league table computed from match results
//   * competition_stats   — avg goals, home/draw/away rates, biggest wins,
//                           highest-scoring games
//   * search_players /    — FIFA player database filtering (name, nationality,
//     player_profile        club, position group, rating) and detailed profile
//   * data_summary        — dataset inventory for grounding the LLM
//
// De-duplication: the same fixture can appear in up to three CSVs. Every
// aggregate/listing operation first collapses matches by
// (date, home_key, away_key), keeping the record from the highest-priority
// source (`Source` ordering). Standings additionally restrict to the single
// source that has the most matches for the requested season, so a season is
// never double-counted.
// =============================================================================

use crate::data::{fold, team_key, team_matches, Data, Match, Source};
use chrono::NaiveDate;
use std::collections::{HashMap, HashSet};
use std::fmt::Write as _;

pub struct QueryEngine<'a> {
    data: &'a Data,
}

/// Filters accepted by `search_matches`.
#[derive(Debug, Default, Clone)]
pub struct MatchFilter {
    pub team: Option<String>,
    pub opponent: Option<String>,
    pub competition: Option<String>,
    pub season: Option<i32>,
    pub date_from: Option<NaiveDate>,
    pub date_to: Option<NaiveDate>,
    pub stage: Option<String>,
    pub limit: usize,
}

/// Aggregate W/D/L record from one team's perspective.
#[derive(Debug, Default, Clone, Copy)]
pub struct Record {
    pub played: u32,
    pub wins: u32,
    pub draws: u32,
    pub losses: u32,
    pub goals_for: u32,
    pub goals_against: u32,
}

impl Record {
    fn add(&mut self, gf: i32, ga: i32) {
        self.played += 1;
        self.goals_for += gf as u32;
        self.goals_against += ga as u32;
        if gf > ga {
            self.wins += 1;
        } else if gf < ga {
            self.losses += 1;
        } else {
            self.draws += 1;
        }
    }

    pub fn win_rate(&self) -> f64 {
        if self.played == 0 {
            0.0
        } else {
            self.wins as f64 * 100.0 / self.played as f64
        }
    }

    pub fn points(&self) -> u32 {
        self.wins * 3 + self.draws
    }
}

/// Normalize a competition query: "Brasileirão"/"Serie A" should both hit
/// "Brasileirão Série A", "Libertadores" hits "Copa Libertadores", etc.
fn competition_query_key(q: &str) -> String {
    let f = fold(q);
    match f.as_str() {
        "brasileirao" | "campeonato brasileiro" => "brasileirao serie a".to_string(),
        "copa libertadores" | "libertadores" => "libertadores".to_string(),
        _ => f,
    }
}

fn competition_matches(competition: &str, query: &str) -> bool {
    let comp = fold(competition);
    let q = competition_query_key(query);
    comp.contains(&q) || q.contains(&comp)
}

/// Stage filter matching: exact, or prefix in either direction so that
/// "group" matches "group stage" — but "final" does NOT match "semifinals".
fn stage_matches(stage: &str, query: &str) -> bool {
    let s = fold(stage);
    let q = fold(query);
    s == q || s.starts_with(&q) || q.starts_with(&s)
}

impl<'a> QueryEngine<'a> {
    pub fn new(data: &'a Data) -> Self {
        QueryEngine { data }
    }

    // -----------------------------------------------------------------------
    // De-duplication
    // -----------------------------------------------------------------------

    /// Collapse duplicate fixtures across sources, preferring the
    /// highest-priority (lowest `Source`) record. Order is preserved for
    /// undated matches, which are always kept.
    fn dedup<'m>(&self, matches: Vec<&'m Match>) -> Vec<&'m Match> {
        let mut best: HashMap<String, &'m Match> = HashMap::new();
        let mut undated: Vec<&'m Match> = Vec::new();
        for m in matches {
            match m.dedup_key() {
                Some(k) => {
                    best.entry(k)
                        .and_modify(|cur| {
                            if m.source < cur.source {
                                *cur = m;
                            }
                        })
                        .or_insert(m);
                }
                None => undated.push(m),
            }
        }
        let mut out: Vec<&Match> = best.into_values().collect();
        out.extend(undated);
        out.sort_by_key(|m| std::cmp::Reverse(m.date));
        out
    }

    /// Final round number of the Copa do Brasil for a season (the max round).
    fn cup_final_round(&self, season: i32) -> Option<i32> {
        self.data
            .matches
            .iter()
            .filter(|m| m.source == Source::Cup && m.season == Some(season))
            .filter_map(|m| m.round)
            .max()
    }

    fn filter_matches(&self, f: &MatchFilter) -> Vec<&Match> {
        let team_q = f.team.as_deref().map(team_key);
        let opp_q = f.opponent.as_deref().map(team_key);
        let selected: Vec<&Match> = self
            .data
            .matches
            .iter()
            .filter(|m| {
                if let Some(season) = f.season {
                    if m.season != Some(season) {
                        return false;
                    }
                }
                if let Some(comp) = &f.competition {
                    if !competition_matches(&m.competition, comp) {
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
                if let Some(stage) = &f.stage {
                    let q = fold(stage);
                    let by_stage = m
                        .stage
                        .as_deref()
                        .map(|s| stage_matches(s, stage))
                        .unwrap_or(false);
                    // Copa do Brasil has no stage column; the final is the
                    // highest round of the season.
                    let by_round = q == "final"
                        && m.source == Source::Cup
                        && m.season.is_some()
                        && m.round.is_some()
                        && m.round == m.season.and_then(|s| self.cup_final_round(s));
                    if !(by_stage || by_round) {
                        return false;
                    }
                }
                match (&team_q, &opp_q) {
                    (Some(t), Some(o)) => {
                        (team_matches(&m.home_key, t) && team_matches(&m.away_key, o))
                            || (team_matches(&m.home_key, o) && team_matches(&m.away_key, t))
                    }
                    (Some(t), None) => {
                        team_matches(&m.home_key, t) || team_matches(&m.away_key, t)
                    }
                    (None, Some(o)) => {
                        team_matches(&m.home_key, o) || team_matches(&m.away_key, o)
                    }
                    (None, None) => true,
                }
            })
            .collect();
        self.dedup(selected)
    }

    fn format_match(m: &Match) -> String {
        let date = m
            .date
            .map(|d| d.to_string())
            .unwrap_or_else(|| "unknown date".to_string());
        let score = match (m.home_goals, m.away_goals) {
            (Some(h), Some(a)) => format!("{} {}-{} {}", m.home_team, h, a, m.away_team),
            _ => format!("{} vs {} (no score recorded)", m.home_team, m.away_team),
        };
        let mut extras = Vec::new();
        extras.push(m.competition.clone());
        if let Some(r) = m.round {
            extras.push(format!("Round {}", r));
        }
        if let Some(s) = &m.stage {
            extras.push(s.clone());
        }
        if let Some(st) = &m.stadium {
            extras.push(st.clone());
        }
        format!("- {}: {} ({})", date, score, extras.join(", "))
    }

    // -----------------------------------------------------------------------
    // Tools
    // -----------------------------------------------------------------------

    pub fn search_matches(&self, f: &MatchFilter) -> String {
        let matches = self.filter_matches(f);
        if matches.is_empty() {
            return "No matches found for the given criteria.".to_string();
        }
        let limit = if f.limit == 0 { 20 } else { f.limit };
        let mut out = String::new();
        let _ = writeln!(out, "Found {} match(es):", matches.len());
        for m in matches.iter().take(limit) {
            let _ = writeln!(out, "{}", Self::format_match(m));
        }
        if matches.len() > limit {
            let _ = writeln!(out, "... ({} more matches not shown)", matches.len() - limit);
        }
        // When both teams are given, append the head-to-head summary.
        if let (Some(t), Some(o)) = (&f.team, &f.opponent) {
            let _ = writeln!(out);
            out.push_str(&self.h2h_summary(t, o, &matches));
        }
        out
    }

    fn h2h_summary(&self, team1: &str, team2: &str, matches: &[&Match]) -> String {
        let k1 = team_key(team1);
        let mut r1 = Record::default();
        for m in matches {
            let (Some(h), Some(a)) = (m.home_goals, m.away_goals) else {
                continue;
            };
            if team_matches(&m.home_key, &k1) {
                r1.add(h, a);
            } else {
                r1.add(a, h);
            }
        }
        format!(
            "Head-to-head in dataset: {} {} wins, {} {} wins, {} draws (goals {}-{})",
            team1, r1.wins, team2, r1.losses, r1.draws, r1.goals_for, r1.goals_against
        )
    }

    pub fn head_to_head(&self, team1: &str, team2: &str, competition: Option<String>) -> String {
        let f = MatchFilter {
            team: Some(team1.to_string()),
            opponent: Some(team2.to_string()),
            competition,
            limit: 10,
            ..Default::default()
        };
        let matches = self.filter_matches(&f);
        if matches.is_empty() {
            return format!("No matches found between {} and {}.", team1, team2);
        }
        let mut out = String::new();
        let _ = writeln!(out, "{} vs {}:", team1, team2);
        out.push_str(&self.h2h_summary(team1, team2, &matches));
        let _ = writeln!(out, "\n\nMost recent meetings:");
        for m in matches.iter().take(10) {
            let _ = writeln!(out, "{}", Self::format_match(m));
        }
        if matches.len() > 10 {
            let _ = writeln!(out, "... ({} more matches in dataset)", matches.len() - 10);
        }
        out
    }

    pub fn team_stats(
        &self,
        team: &str,
        season: Option<i32>,
        competition: Option<String>,
        venue: Option<String>,
    ) -> String {
        let key = team_key(team);
        let f = MatchFilter {
            team: Some(team.to_string()),
            season,
            competition: competition.clone(),
            ..Default::default()
        };
        let matches = self.filter_matches(&f);
        let venue = venue.map(|v| fold(&v)).unwrap_or_default();
        let mut overall = Record::default();
        let mut home = Record::default();
        let mut away = Record::default();
        let mut by_comp: HashMap<String, Record> = HashMap::new();
        for m in &matches {
            let (Some(hg), Some(ag)) = (m.home_goals, m.away_goals) else {
                continue;
            };
            let is_home = team_matches(&m.home_key, &key);
            if venue == "home" && !is_home {
                continue;
            }
            if venue == "away" && is_home {
                continue;
            }
            let (gf, ga) = if is_home { (hg, ag) } else { (ag, hg) };
            overall.add(gf, ga);
            if is_home {
                home.add(gf, ga);
            } else {
                away.add(gf, ga);
            }
            by_comp.entry(m.competition.clone()).or_default().add(gf, ga);
        }
        if overall.played == 0 {
            return format!("No completed matches found for {} with the given filters.", team);
        }
        let mut out = String::new();
        let mut scope = Vec::new();
        if let Some(s) = season {
            scope.push(s.to_string());
        }
        if let Some(c) = &competition {
            scope.push(c.clone());
        }
        if !venue.is_empty() {
            scope.push(format!("{} matches only", venue));
        }
        let scope_str = if scope.is_empty() {
            "all data".to_string()
        } else {
            scope.join(", ")
        };
        let _ = writeln!(out, "{} record ({}):", team, scope_str);
        let _ = writeln!(out, "- Matches: {}", overall.played);
        let _ = writeln!(
            out,
            "- Wins: {}, Draws: {}, Losses: {}",
            overall.wins, overall.draws, overall.losses
        );
        let _ = writeln!(
            out,
            "- Goals For: {}, Goals Against: {}",
            overall.goals_for, overall.goals_against
        );
        let _ = writeln!(out, "- Win rate: {:.1}%", overall.win_rate());
        if venue.is_empty() {
            let _ = writeln!(
                out,
                "- Home: {}W-{}D-{}L (GF {}, GA {}), Away: {}W-{}D-{}L (GF {}, GA {})",
                home.wins, home.draws, home.losses, home.goals_for, home.goals_against,
                away.wins, away.draws, away.losses, away.goals_for, away.goals_against
            );
        }
        if by_comp.len() > 1 {
            let _ = writeln!(out, "\nBy competition:");
            let mut comps: Vec<_> = by_comp.into_iter().collect();
            comps.sort_by_key(|c| std::cmp::Reverse(c.1.played));
            for (comp, r) in comps {
                let _ = writeln!(
                    out,
                    "- {}: {} matches, {}W-{}D-{}L, GF {}, GA {}",
                    comp, r.played, r.wins, r.draws, r.losses, r.goals_for, r.goals_against
                );
            }
        }
        out
    }

    /// League standings computed from match results (3 pts/win, 1/draw).
    /// Restricted to the single source with the most matches for the season,
    /// so overlapping datasets are never double-counted.
    pub fn standings(&self, season: i32, competition: Option<String>) -> String {
        let comp = competition.unwrap_or_else(|| "Brasileirão Série A".to_string());
        let candidates: Vec<&Match> = self
            .data
            .matches
            .iter()
            .filter(|m| {
                m.season == Some(season)
                    && competition_matches(&m.competition, &comp)
                    && m.has_score()
            })
            .collect();
        if candidates.is_empty() {
            return format!("No {} match data for season {}.", comp, season);
        }
        let mut per_source: HashMap<Source, usize> = HashMap::new();
        for m in &candidates {
            *per_source.entry(m.source).or_default() += 1;
        }
        // Most matches wins; ties broken by source priority.
        let chosen = *per_source
            .iter()
            .max_by(|a, b| a.1.cmp(b.1).then_with(|| b.0.cmp(a.0)))
            .map(|(s, _)| s)
            .unwrap();
        let mut table: HashMap<String, (String, Record)> = HashMap::new();
        for m in candidates.iter().filter(|m| m.source == chosen) {
            let (hg, ag) = (m.home_goals.unwrap(), m.away_goals.unwrap());
            let home = table
                .entry(m.home_key.clone())
                .or_insert_with(|| (m.home_team.clone(), Record::default()));
            home.1.add(hg, ag);
            let away = table
                .entry(m.away_key.clone())
                .or_insert_with(|| (m.away_team.clone(), Record::default()));
            away.1.add(ag, hg);
        }
        let mut rows: Vec<(String, Record)> = table.into_values().collect();
        rows.sort_by(|a, b| {
            b.1.points()
                .cmp(&a.1.points())
                .then(b.1.wins.cmp(&a.1.wins))
                .then(
                    (b.1.goals_for as i64 - b.1.goals_against as i64)
                        .cmp(&(a.1.goals_for as i64 - a.1.goals_against as i64)),
                )
                .then(b.1.goals_for.cmp(&a.1.goals_for))
        });
        let mut out = String::new();
        let _ = writeln!(
            out,
            "{} {} standings (calculated from {} matches in {}):",
            season,
            comp,
            rows.iter().map(|r| r.1.played).sum::<u32>() / 2,
            chosen.label()
        );
        let n = rows.len();
        for (i, (name, r)) in rows.iter().enumerate() {
            let mut tag = String::new();
            if i == 0 {
                tag = " - Champion".to_string();
            } else if n >= 16 && i >= n - 4 {
                tag = " - Relegation zone".to_string();
            }
            let _ = writeln!(
                out,
                "{}. {} - {} pts ({}W, {}D, {}L, GF {}, GA {}, GD {:+}){}",
                i + 1,
                name,
                r.points(),
                r.wins,
                r.draws,
                r.losses,
                r.goals_for,
                r.goals_against,
                r.goals_for as i64 - r.goals_against as i64,
                tag
            );
        }
        out
    }

    pub fn competition_stats(&self, competition: Option<String>, season: Option<i32>) -> String {
        let f = MatchFilter {
            competition: competition.clone(),
            season,
            ..Default::default()
        };
        let matches = self.filter_matches(&f);
        let played: Vec<&&Match> = matches.iter().filter(|m| m.has_score()).collect();
        if played.is_empty() {
            return "No completed matches found for the given criteria.".to_string();
        }
        let total = played.len() as f64;
        let mut goals = 0i64;
        let mut home_wins = 0u32;
        let mut draws = 0u32;
        let mut away_wins = 0u32;
        for m in &played {
            let (h, a) = (m.home_goals.unwrap(), m.away_goals.unwrap());
            goals += (h + a) as i64;
            if h > a {
                home_wins += 1;
            } else if h < a {
                away_wins += 1;
            } else {
                draws += 1;
            }
        }
        let mut biggest: Vec<&&Match> = played.clone();
        biggest.sort_by_key(|m| -(m.home_goals.unwrap() - m.away_goals.unwrap()).abs());
        let mut highest: Vec<&&Match> = played.clone();
        highest.sort_by_key(|m| -(m.home_goals.unwrap() + m.away_goals.unwrap()));

        let scope = match (&competition, season) {
            (Some(c), Some(s)) => format!("{} {}", c, s),
            (Some(c), None) => c.clone(),
            (None, Some(s)) => format!("all competitions, season {}", s),
            (None, None) => "all competitions".to_string(),
        };
        let mut out = String::new();
        let _ = writeln!(out, "Statistics for {} ({} completed matches):", scope, played.len());
        let _ = writeln!(out, "- Average goals per match: {:.2}", goals as f64 / total);
        let _ = writeln!(
            out,
            "- Home wins: {:.1}%, Draws: {:.1}%, Away wins: {:.1}%",
            home_wins as f64 * 100.0 / total,
            draws as f64 * 100.0 / total,
            away_wins as f64 * 100.0 / total
        );
        let _ = writeln!(out, "\nBiggest victories:");
        for m in biggest.iter().take(5) {
            let _ = writeln!(out, "{}", Self::format_match(m));
        }
        let _ = writeln!(out, "\nHighest-scoring matches:");
        for m in highest.iter().take(5) {
            let _ = writeln!(out, "{}", Self::format_match(m));
        }
        out
    }

    // -----------------------------------------------------------------------
    // Players
    // -----------------------------------------------------------------------

    fn position_group(query: &str) -> Option<Vec<&'static str>> {
        let q = fold(query);
        let group: &[&str] = match q.as_str() {
            "forward" | "forwards" | "striker" | "strikers" | "attacker" | "attackers"
            | "atacante" => &["ST", "CF", "LW", "RW", "LS", "RS", "LF", "RF"],
            "midfielder" | "midfielders" | "midfield" | "meia" => &[
                "CM", "CDM", "CAM", "LM", "RM", "LCM", "RCM", "LDM", "RDM", "LAM", "RAM",
            ],
            "defender" | "defenders" | "defence" | "defense" | "back" | "zagueiro" => {
                &["CB", "LB", "RB", "LCB", "RCB", "LWB", "RWB"]
            }
            "goalkeeper" | "goalkeepers" | "keeper" | "gk" | "goleiro" => &["GK"],
            _ => return None,
        };
        Some(group.to_vec())
    }

    pub fn search_players(
        &self,
        name: Option<String>,
        nationality: Option<String>,
        club: Option<String>,
        position: Option<String>,
        min_overall: Option<i32>,
        limit: usize,
    ) -> String {
        let name_q = name.as_deref().map(fold);
        let nat_q = nationality.as_deref().map(fold);
        let club_q = club.as_deref().map(team_key);
        let pos_group = position.as_deref().and_then(Self::position_group);
        let pos_exact = position.as_deref().map(|p| p.trim().to_uppercase());
        let mut found: Vec<&crate::data::Player> = self
            .data
            .players
            .iter()
            .filter(|p| {
                if let Some(q) = &name_q {
                    if !p.name_key.contains(q.as_str()) {
                        return false;
                    }
                }
                if let Some(q) = &nat_q {
                    if fold(&p.nationality) != *q {
                        return false;
                    }
                }
                if let Some(q) = &club_q {
                    if !team_matches(&p.club_key, q) {
                        return false;
                    }
                }
                if let Some(group) = &pos_group {
                    if !group.contains(&p.position.as_str()) {
                        return false;
                    }
                } else if let Some(pq) = &pos_exact {
                    if !pq.is_empty() && p.position != *pq {
                        return false;
                    }
                }
                if let Some(min) = min_overall {
                    if p.overall.unwrap_or(0) < min {
                        return false;
                    }
                }
                true
            })
            .collect();
        if found.is_empty() {
            return "No players found for the given criteria.".to_string();
        }
        found.sort_by_key(|p| std::cmp::Reverse(p.overall));
        let limit = if limit == 0 { 15 } else { limit };
        let mut out = String::new();
        let _ = writeln!(out, "Found {} player(s):", found.len());
        for (i, p) in found.iter().take(limit).enumerate() {
            let _ = writeln!(
                out,
                "{}. {} - Overall: {}, Position: {}, Age: {}, Nationality: {}, Club: {}",
                i + 1,
                p.name,
                p.overall.map(|v| v.to_string()).unwrap_or_else(|| "?".into()),
                if p.position.is_empty() { "?" } else { &p.position },
                p.age.map(|v| v.to_string()).unwrap_or_else(|| "?".into()),
                p.nationality,
                if p.club.is_empty() { "no club" } else { &p.club }
            );
        }
        if found.len() > limit {
            let _ = writeln!(out, "... ({} more players not shown)", found.len() - limit);
        }
        out
    }

    pub fn player_profile(&self, name: &str) -> String {
        let q = fold(name);
        let mut candidates: Vec<&crate::data::Player> = self
            .data
            .players
            .iter()
            .filter(|p| p.name_key == q || p.name_key.contains(&q))
            .collect();
        if candidates.is_empty() {
            // Loose match: all query words appear in the name.
            let words: Vec<&str> = q.split(' ').collect();
            candidates = self
                .data
                .players
                .iter()
                .filter(|p| words.iter().all(|w| p.name_key.contains(w)))
                .collect();
        }
        if candidates.is_empty() {
            return format!("No player matching \"{}\" found in the FIFA dataset.", name);
        }
        candidates.sort_by(|a, b| {
            (b.name_key == q)
                .cmp(&(a.name_key == q))
                .then(b.overall.cmp(&a.overall))
        });
        let p = candidates[0];
        let mut out = String::new();
        let _ = writeln!(out, "{}", p.name);
        let _ = writeln!(
            out,
            "- Overall: {} (Potential: {})",
            p.overall.map(|v| v.to_string()).unwrap_or_else(|| "?".into()),
            p.potential.map(|v| v.to_string()).unwrap_or_else(|| "?".into())
        );
        let _ = writeln!(
            out,
            "- Position: {}, Jersey: {}",
            if p.position.is_empty() { "?" } else { &p.position },
            p.jersey.map(|v| v.to_string()).unwrap_or_else(|| "?".into())
        );
        let _ = writeln!(out, "- Age: {}, Nationality: {}",
            p.age.map(|v| v.to_string()).unwrap_or_else(|| "?".into()),
            p.nationality
        );
        let _ = writeln!(out, "- Club: {}", if p.club.is_empty() { "no club" } else { &p.club });
        let _ = writeln!(out, "- Height: {}, Weight: {}, Preferred foot: {}",
            p.height, p.weight, p.preferred_foot
        );
        let _ = writeln!(out, "- Value: {}, Wage: {}", p.value, p.wage);
        if !p.attributes.is_empty() {
            let mut attrs = p.attributes.clone();
            attrs.sort_by_key(|a| std::cmp::Reverse(a.1));
            let top: Vec<String> = attrs
                .iter()
                .take(6)
                .map(|(k, v)| format!("{} {}", k, v))
                .collect();
            let _ = writeln!(out, "- Top attributes: {}", top.join(", "));
        }
        if candidates.len() > 1 {
            let others: Vec<&str> = candidates[1..]
                .iter()
                .take(4)
                .map(|p| p.name.as_str())
                .collect();
            let _ = writeln!(out, "\nOther name matches: {}", others.join(", "));
        }
        out
    }

    // -----------------------------------------------------------------------
    // Summary
    // -----------------------------------------------------------------------

    pub fn data_summary(&self) -> String {
        let mut out = String::new();
        let _ = writeln!(out, "Loaded datasets:");
        let mut counts: Vec<_> = self.data.source_counts.iter().collect();
        counts.sort();
        for (file, n) in counts {
            let _ = writeln!(out, "- {}: {} rows", file, n);
        }
        let mut comps: HashMap<&str, (i32, i32, usize)> = HashMap::new();
        for m in &self.data.matches {
            let e = comps
                .entry(m.competition.as_str())
                .or_insert((i32::MAX, i32::MIN, 0));
            if let Some(s) = m.season {
                e.0 = e.0.min(s);
                e.1 = e.1.max(s);
            }
            e.2 += 1;
        }
        let _ = writeln!(out, "\nCompetitions covered:");
        let mut rows: Vec<_> = comps.into_iter().collect();
        rows.sort_by_key(|r| std::cmp::Reverse(r.1 .2));
        for (comp, (min, max, n)) in rows {
            if min == i32::MAX {
                let _ = writeln!(out, "- {}: {} matches", comp, n);
            } else {
                let _ = writeln!(out, "- {}: {} matches, seasons {}-{}", comp, n, min, max);
            }
        }
        let teams: HashSet<&str> = self
            .data
            .matches
            .iter()
            .flat_map(|m| [m.home_key.as_str(), m.away_key.as_str()])
            .collect();
        let _ = writeln!(out, "\nDistinct teams (normalized): {}", teams.len());
        let brazilians = self
            .data
            .players
            .iter()
            .filter(|p| p.nationality == "Brazil")
            .count();
        let _ = writeln!(
            out,
            "FIFA players: {} total, {} Brazilian",
            self.data.players.len(),
            brazilians
        );
        out
    }
}
