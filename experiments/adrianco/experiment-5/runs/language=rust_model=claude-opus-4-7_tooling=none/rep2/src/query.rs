//! Query layer over [`Dataset`]. The MCP server exposes thin wrappers over
//! these functions as tools.

use std::collections::HashMap;

use serde::{Deserialize, Serialize};

use crate::data::{Dataset, Match, MatchOutcome, Player};
use crate::normalize::{normalize_team, strip_accents, team_matches};

fn comp_key(s: &str) -> String {
    strip_accents(s).to_lowercase()
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct MatchQuery {
    /// Match if either team matches.
    pub team: Option<String>,
    pub home_team: Option<String>,
    pub away_team: Option<String>,
    /// Substring match on the competition name.
    pub competition: Option<String>,
    pub season: Option<i32>,
    /// Inclusive lower bound `YYYY-MM-DD`.
    pub date_from: Option<String>,
    /// Inclusive upper bound `YYYY-MM-DD`.
    pub date_to: Option<String>,
    pub limit: Option<usize>,
}

impl MatchQuery {
    pub fn filter<'a>(&self, ds: &'a Dataset) -> Vec<&'a Match> {
        let from = self.date_from.as_deref().and_then(date_key);
        let to = self.date_to.as_deref().and_then(date_key);

        let want_team = self.team.as_deref().map(normalize_team);
        let want_home = self.home_team.as_deref().map(normalize_team);
        let want_away = self.away_team.as_deref().map(normalize_team);
        let want_comp = self.competition.as_deref().map(comp_key);

        let mut out: Vec<&Match> = ds
            .matches
            .iter()
            .filter(|m| {
                if let Some(season) = self.season {
                    if m.season != Some(season) {
                        return false;
                    }
                }
                if let Some(ref comp) = want_comp {
                    if !comp_key(&m.competition).contains(comp) {
                        return false;
                    }
                }
                if let Some(ref t) = want_team {
                    if !(normalize_team(&m.home_team).contains(t)
                        || normalize_team(&m.away_team).contains(t))
                    {
                        return false;
                    }
                }
                if let Some(ref h) = want_home {
                    if !normalize_team(&m.home_team).contains(h) {
                        return false;
                    }
                }
                if let Some(ref a) = want_away {
                    if !normalize_team(&m.away_team).contains(a) {
                        return false;
                    }
                }
                if from.is_some() || to.is_some() {
                    let k = m.date.map(date_tuple_key);
                    match (from, to, k) {
                        (Some(f), _, Some(d)) if d < f => return false,
                        (_, Some(t), Some(d)) if d > t => return false,
                        (Some(_), _, None) => return false,
                        (_, Some(_), None) => return false,
                        _ => {}
                    }
                }
                true
            })
            .collect();

        out.sort_by_key(|m| m.date.map(date_tuple_key));
        if let Some(lim) = self.limit {
            out.truncate(lim);
        }
        out
    }
}

fn date_tuple_key(d: (i32, u32, u32)) -> (i32, u32, u32) {
    d
}

fn date_key(s: &str) -> Option<(i32, u32, u32)> {
    crate::normalize::parse_date(s)
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HeadToHead {
    pub team_a: String,
    pub team_b: String,
    pub matches: usize,
    pub team_a_wins: usize,
    pub team_b_wins: usize,
    pub draws: usize,
    pub team_a_goals: i32,
    pub team_b_goals: i32,
}

pub fn head_to_head(ds: &Dataset, a: &str, b: &str) -> HeadToHead {
    let mut h = HeadToHead {
        team_a: a.to_string(),
        team_b: b.to_string(),
        matches: 0,
        team_a_wins: 0,
        team_b_wins: 0,
        draws: 0,
        team_a_goals: 0,
        team_b_goals: 0,
    };
    for m in &ds.matches {
        let (a_is_home, b_is_other) =
            if team_matches(&m.home_team, a) && team_matches(&m.away_team, b) {
                (true, true)
            } else if team_matches(&m.home_team, b) && team_matches(&m.away_team, a) {
                (false, true)
            } else {
                (false, false)
            };
        if !b_is_other {
            continue;
        }
        h.matches += 1;
        if let (Some(hg), Some(ag)) = (m.home_goal, m.away_goal) {
            if a_is_home {
                h.team_a_goals += hg;
                h.team_b_goals += ag;
            } else {
                h.team_a_goals += ag;
                h.team_b_goals += hg;
            }
            match m.winner() {
                Some(MatchOutcome::Home) if a_is_home => h.team_a_wins += 1,
                Some(MatchOutcome::Home) => h.team_b_wins += 1,
                Some(MatchOutcome::Away) if a_is_home => h.team_b_wins += 1,
                Some(MatchOutcome::Away) => h.team_a_wins += 1,
                Some(MatchOutcome::Draw) => h.draws += 1,
                None => {}
            }
        }
    }
    h
}

/// Per-team performance breakdown.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct TeamStats {
    pub team: String,
    pub matches: usize,
    pub wins: usize,
    pub draws: usize,
    pub losses: usize,
    pub goals_for: i32,
    pub goals_against: i32,
    pub home_matches: usize,
    pub home_wins: usize,
    pub home_draws: usize,
    pub home_losses: usize,
    pub home_goals_for: i32,
    pub home_goals_against: i32,
    pub away_matches: usize,
    pub away_wins: usize,
    pub away_draws: usize,
    pub away_losses: usize,
    pub away_goals_for: i32,
    pub away_goals_against: i32,
}

impl TeamStats {
    pub fn win_rate(&self) -> f64 {
        if self.matches == 0 {
            0.0
        } else {
            self.wins as f64 / self.matches as f64
        }
    }
    pub fn home_win_rate(&self) -> f64 {
        if self.home_matches == 0 {
            0.0
        } else {
            self.home_wins as f64 / self.home_matches as f64
        }
    }
    pub fn away_win_rate(&self) -> f64 {
        if self.away_matches == 0 {
            0.0
        } else {
            self.away_wins as f64 / self.away_matches as f64
        }
    }
    pub fn points(&self) -> i32 {
        self.wins as i32 * 3 + self.draws as i32
    }
}

pub fn team_stats(ds: &Dataset, team: &str, season: Option<i32>, competition: Option<&str>) -> TeamStats {
    let mut s = TeamStats {
        team: team.to_string(),
        ..Default::default()
    };
    let comp_lc = competition.map(comp_key);
    for m in &ds.matches {
        if let Some(season) = season {
            if m.season != Some(season) {
                continue;
            }
        }
        if let Some(ref c) = comp_lc {
            if !comp_key(&m.competition).contains(c) {
                continue;
            }
        }
        let is_home = team_matches(&m.home_team, team);
        let is_away = team_matches(&m.away_team, team);
        if !is_home && !is_away {
            continue;
        }
        let (hg, ag) = match (m.home_goal, m.away_goal) {
            (Some(h), Some(a)) => (h, a),
            _ => continue,
        };
        s.matches += 1;
        let (gf, ga) = if is_home { (hg, ag) } else { (ag, hg) };
        s.goals_for += gf;
        s.goals_against += ga;
        let outcome = if gf > ga {
            MatchOutcome::Home
        } else if gf < ga {
            MatchOutcome::Away
        } else {
            MatchOutcome::Draw
        };
        match outcome {
            MatchOutcome::Home => s.wins += 1,
            MatchOutcome::Draw => s.draws += 1,
            MatchOutcome::Away => s.losses += 1,
        }
        if is_home {
            s.home_matches += 1;
            s.home_goals_for += gf;
            s.home_goals_against += ga;
            match outcome {
                MatchOutcome::Home => s.home_wins += 1,
                MatchOutcome::Draw => s.home_draws += 1,
                MatchOutcome::Away => s.home_losses += 1,
            }
        } else {
            s.away_matches += 1;
            s.away_goals_for += gf;
            s.away_goals_against += ga;
            match outcome {
                MatchOutcome::Home => s.away_wins += 1,
                MatchOutcome::Draw => s.away_draws += 1,
                MatchOutcome::Away => s.away_losses += 1,
            }
        }
    }
    s
}

/// One row of a league standings table.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StandingsRow {
    pub rank: usize,
    pub team: String,
    pub matches: usize,
    pub wins: usize,
    pub draws: usize,
    pub losses: usize,
    pub goals_for: i32,
    pub goals_against: i32,
    pub goal_difference: i32,
    pub points: i32,
}

pub fn standings(ds: &Dataset, season: i32, competition: Option<&str>) -> Vec<StandingsRow> {
    let comp_lc = competition.map(comp_key);
    let mut by_team: HashMap<String, (String, TeamStats)> = HashMap::new();

    for m in &ds.matches {
        if m.season != Some(season) {
            continue;
        }
        if let Some(ref c) = comp_lc {
            if !comp_key(&m.competition).contains(c) {
                continue;
            }
        }
        let (hg, ag) = match (m.home_goal, m.away_goal) {
            (Some(h), Some(a)) => (h, a),
            _ => continue,
        };
        for (team, gf, ga) in [
            (&m.home_team, hg, ag),
            (&m.away_team, ag, hg),
        ] {
            let key = normalize_team(team);
            if key.is_empty() {
                continue;
            }
            let entry = by_team
                .entry(key)
                .or_insert_with(|| (team.clone(), TeamStats::default()));
            let s = &mut entry.1;
            s.matches += 1;
            s.goals_for += gf;
            s.goals_against += ga;
            if gf > ga {
                s.wins += 1;
            } else if gf < ga {
                s.losses += 1;
            } else {
                s.draws += 1;
            }
        }
    }

    let mut rows: Vec<StandingsRow> = by_team
        .into_iter()
        .map(|(_, (display, s))| StandingsRow {
            rank: 0,
            team: display,
            matches: s.matches,
            wins: s.wins,
            draws: s.draws,
            losses: s.losses,
            goals_for: s.goals_for,
            goals_against: s.goals_against,
            goal_difference: s.goals_for - s.goals_against,
            points: s.wins as i32 * 3 + s.draws as i32,
        })
        .collect();

    rows.sort_by(|a, b| {
        b.points
            .cmp(&a.points)
            .then(b.goal_difference.cmp(&a.goal_difference))
            .then(b.goals_for.cmp(&a.goals_for))
            .then(a.team.cmp(&b.team))
    });
    for (i, row) in rows.iter_mut().enumerate() {
        row.rank = i + 1;
    }
    rows
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct PlayerQuery {
    pub name: Option<String>,
    pub nationality: Option<String>,
    pub club: Option<String>,
    pub position: Option<String>,
    pub min_overall: Option<u32>,
    pub limit: Option<usize>,
}

impl PlayerQuery {
    pub fn filter<'a>(&self, ds: &'a Dataset) -> Vec<&'a Player> {
        let want_name = self.name.as_ref().map(|s| s.to_lowercase());
        let want_nat = self.nationality.as_ref().map(|s| s.to_lowercase());
        let want_club = self.club.as_ref().map(|s| s.to_lowercase());
        let want_position = self.position.as_ref().map(|s| s.to_uppercase());
        let mut out: Vec<&Player> = ds
            .players
            .iter()
            .filter(|p| {
                if let Some(ref n) = want_name {
                    if !p.name.to_lowercase().contains(n) {
                        return false;
                    }
                }
                if let Some(ref nat) = want_nat {
                    if !p.nationality.to_lowercase().contains(nat) {
                        return false;
                    }
                }
                if let Some(ref c) = want_club {
                    if !p.club.to_lowercase().contains(c) {
                        return false;
                    }
                }
                if let Some(ref pos) = want_position {
                    match &p.position {
                        Some(actual) => {
                            if !actual.to_uppercase().contains(pos) {
                                return false;
                            }
                        }
                        None => return false,
                    }
                }
                if let Some(min) = self.min_overall {
                    if p.overall.unwrap_or(0) < min {
                        return false;
                    }
                }
                true
            })
            .collect();
        out.sort_by(|a, b| b.overall.unwrap_or(0).cmp(&a.overall.unwrap_or(0)));
        if let Some(lim) = self.limit {
            out.truncate(lim);
        }
        out
    }
}

#[derive(Debug, Clone, Serialize)]
pub struct BiggestWin<'a> {
    pub margin: i32,
    #[serde(rename = "match")]
    pub match_: &'a Match,
}

pub fn biggest_wins<'a>(
    ds: &'a Dataset,
    limit: usize,
    competition: Option<&str>,
) -> Vec<BiggestWin<'a>> {
    let comp_lc = competition.map(comp_key);
    let mut rows: Vec<BiggestWin> = ds
        .matches
        .iter()
        .filter_map(|m| {
            if let Some(ref c) = comp_lc {
                if !comp_key(&m.competition).contains(c) {
                    return None;
                }
            }
            match (m.home_goal, m.away_goal) {
                (Some(h), Some(a)) => Some(BiggestWin {
                    margin: (h - a).abs(),
                    match_: m,
                }),
                _ => None,
            }
        })
        .collect();
    rows.sort_by(|a, b| b.margin.cmp(&a.margin));
    rows.truncate(limit);
    rows
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OverallStats {
    pub competition: Option<String>,
    pub season: Option<i32>,
    pub matches: usize,
    pub goals: i64,
    pub avg_goals_per_match: f64,
    pub home_wins: usize,
    pub away_wins: usize,
    pub draws: usize,
    pub home_win_rate: f64,
    pub away_win_rate: f64,
    pub draw_rate: f64,
}

pub fn overall_stats(
    ds: &Dataset,
    season: Option<i32>,
    competition: Option<&str>,
) -> OverallStats {
    let comp_lc = competition.map(comp_key);
    let mut matches = 0usize;
    let mut goals = 0i64;
    let mut hw = 0usize;
    let mut aw = 0usize;
    let mut dr = 0usize;
    for m in &ds.matches {
        if let Some(season) = season {
            if m.season != Some(season) {
                continue;
            }
        }
        if let Some(ref c) = comp_lc {
            if !comp_key(&m.competition).contains(c) {
                continue;
            }
        }
        let (h, a) = match (m.home_goal, m.away_goal) {
            (Some(h), Some(a)) => (h, a),
            _ => continue,
        };
        matches += 1;
        goals += (h + a) as i64;
        if h > a {
            hw += 1;
        } else if a > h {
            aw += 1;
        } else {
            dr += 1;
        }
    }
    let f = matches as f64;
    OverallStats {
        competition: competition.map(|c| c.to_string()),
        season,
        matches,
        goals,
        avg_goals_per_match: if matches > 0 { goals as f64 / f } else { 0.0 },
        home_wins: hw,
        away_wins: aw,
        draws: dr,
        home_win_rate: if matches > 0 { hw as f64 / f } else { 0.0 },
        away_win_rate: if matches > 0 { aw as f64 / f } else { 0.0 },
        draw_rate: if matches > 0 { dr as f64 / f } else { 0.0 },
    }
}

/// Format a match list for textual display.
pub fn format_match_list(matches: &[&Match], max: usize) -> String {
    let mut s = String::new();
    for m in matches.iter().take(max) {
        let date = m.date_iso().unwrap_or_else(|| m.date_raw.clone());
        let hg = m
            .home_goal
            .map(|v| v.to_string())
            .unwrap_or_else(|| "?".to_string());
        let ag = m
            .away_goal
            .map(|v| v.to_string())
            .unwrap_or_else(|| "?".to_string());
        let mut tail = format!(" ({}", m.competition);
        if let Some(ref r) = m.round {
            tail.push_str(&format!(" Round {}", r));
        }
        if let Some(ref st) = m.stage {
            tail.push_str(&format!(" {}", st));
        }
        tail.push(')');
        s.push_str(&format!(
            "- {}: {} {}-{} {}{}\n",
            date, m.home_team, hg, ag, m.away_team, tail
        ));
    }
    if matches.len() > max {
        s.push_str(&format!("... ({} more)\n", matches.len() - max));
    }
    s
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;

    fn ds() -> Dataset {
        let dir = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("data/kaggle");
        Dataset::load_from_dir(&dir).expect("load dataset")
    }

    #[test]
    fn match_query_by_team() {
        let ds = ds();
        let q = MatchQuery {
            team: Some("Flamengo".into()),
            ..Default::default()
        };
        let res = q.filter(&ds);
        assert!(res.len() > 100, "got {} matches", res.len());
        for m in &res {
            let h = normalize_team(&m.home_team);
            let a = normalize_team(&m.away_team);
            assert!(h.contains("flamengo") || a.contains("flamengo"));
        }
    }

    #[test]
    fn match_query_between_two_teams() {
        let ds = ds();
        let q = MatchQuery {
            home_team: Some("Flamengo".into()),
            away_team: Some("Fluminense".into()),
            ..Default::default()
        };
        let res = q.filter(&ds);
        assert!(!res.is_empty(), "expected Fla-Flu matches");
    }

    #[test]
    fn head_to_head_works() {
        let ds = ds();
        let h2h = head_to_head(&ds, "Flamengo", "Fluminense");
        assert!(h2h.matches > 0);
        assert_eq!(h2h.matches, h2h.team_a_wins + h2h.team_b_wins + h2h.draws);
    }

    #[test]
    fn team_stats_home_record() {
        let ds = ds();
        let s = team_stats(&ds, "Corinthians", Some(2022), Some("Brasileir"));
        assert!(s.matches > 0);
        assert_eq!(
            s.matches,
            s.wins + s.draws + s.losses,
            "matches accounting"
        );
        assert_eq!(
            s.home_matches,
            s.home_wins + s.home_draws + s.home_losses,
        );
    }

    #[test]
    fn standings_brasileirao_2019() {
        let ds = ds();
        let table = standings(&ds, 2019, Some("Brasileir"));
        assert!(!table.is_empty());
        let champ = &table[0];
        assert!(
            normalize_team(&champ.team).contains("flamengo"),
            "expected Flamengo champion, got {}",
            champ.team
        );
    }

    #[test]
    fn brazilian_players() {
        let ds = ds();
        let q = PlayerQuery {
            nationality: Some("Brazil".into()),
            limit: Some(10),
            ..Default::default()
        };
        let res = q.filter(&ds);
        assert_eq!(res.len(), 10);
        for p in &res {
            assert!(p.nationality.eq_ignore_ascii_case("brazil"));
        }
        let first_overall = res[0].overall.unwrap_or(0);
        let second_overall = res[1].overall.unwrap_or(0);
        assert!(first_overall >= second_overall);
    }

    #[test]
    fn player_by_name() {
        let ds = ds();
        let q = PlayerQuery {
            name: Some("Neymar".into()),
            ..Default::default()
        };
        let res = q.filter(&ds);
        assert!(!res.is_empty());
        assert!(res[0].name.to_lowercase().contains("neymar"));
    }

    #[test]
    fn overall_stats_sane() {
        let ds = ds();
        let s = overall_stats(&ds, None, Some("Brasileir"));
        assert!(s.matches > 0);
        let total_rate = s.home_win_rate + s.away_win_rate + s.draw_rate;
        assert!((total_rate - 1.0).abs() < 0.01);
        assert!(s.avg_goals_per_match > 0.0 && s.avg_goals_per_match < 10.0);
    }

    #[test]
    fn biggest_wins_sorted() {
        let ds = ds();
        let bw = biggest_wins(&ds, 5, None);
        assert_eq!(bw.len(), 5);
        for i in 1..bw.len() {
            assert!(bw[i - 1].margin >= bw[i].margin);
        }
        assert!(bw[0].margin >= 5);
    }

    #[test]
    fn date_range_filter() {
        let ds = ds();
        let q = MatchQuery {
            team: Some("Palmeiras".into()),
            date_from: Some("2023-01-01".into()),
            date_to: Some("2023-12-31".into()),
            ..Default::default()
        };
        let res = q.filter(&ds);
        assert!(!res.is_empty());
        for m in &res {
            assert!(m.date.unwrap().0 == 2023);
        }
    }
}
