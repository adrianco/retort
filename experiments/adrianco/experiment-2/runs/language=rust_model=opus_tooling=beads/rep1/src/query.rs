use serde::Serialize;

use crate::data::{Competition, Dataset, Match, Player, Winner};
use crate::normalize::normalize_team;

#[derive(Debug, Default, Clone)]
pub struct MatchFilter<'a> {
    pub team: Option<&'a str>,
    pub home_team: Option<&'a str>,
    pub away_team: Option<&'a str>,
    pub opponent: Option<&'a str>,
    pub season: Option<i32>,
    pub date_from: Option<&'a str>,
    pub date_to: Option<&'a str>,
    pub competition: Option<Competition>,
}

pub fn find_matches<'a>(ds: &'a Dataset, f: &MatchFilter) -> Vec<&'a Match> {
    let team_key = f.team.map(normalize_team);
    let home_key = f.home_team.map(normalize_team);
    let away_key = f.away_team.map(normalize_team);
    let opp_key = f.opponent.map(normalize_team);

    ds.matches.iter().filter(|m| {
        if let Some(ref k) = team_key {
            if &m.home_team_key != k && &m.away_team_key != k { return false; }
        }
        if let Some(ref k) = home_key {
            if &m.home_team_key != k { return false; }
        }
        if let Some(ref k) = away_key {
            if &m.away_team_key != k { return false; }
        }
        if let (Some(ref tk), Some(ref ok)) = (&team_key, &opp_key) {
            let a = &m.home_team_key == tk && &m.away_team_key == ok;
            let b = &m.away_team_key == tk && &m.home_team_key == ok;
            if !a && !b { return false; }
        } else if let Some(ref ok) = opp_key {
            if &m.home_team_key != ok && &m.away_team_key != ok { return false; }
        }
        if let Some(s) = f.season { if m.season != s { return false; } }
        if let Some(df) = f.date_from { if m.date.as_str() < df { return false; } }
        if let Some(dt) = f.date_to { if m.date.as_str() > dt { return false; } }
        if let Some(c) = f.competition { if m.competition != c { return false; } }
        true
    }).collect()
}

#[derive(Debug, Default, Serialize)]
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
    pub away_matches: usize,
    pub away_wins: usize,
    pub away_draws: usize,
    pub away_losses: usize,
}

impl TeamStats {
    pub fn win_rate(&self) -> f64 {
        if self.matches == 0 { 0.0 } else { self.wins as f64 / self.matches as f64 }
    }
    pub fn points(&self) -> i32 { (self.wins as i32) * 3 + (self.draws as i32) }
}

pub fn team_stats(matches: &[&Match], team: &str) -> TeamStats {
    let key = normalize_team(team);
    let mut s = TeamStats { team: team.to_string(), ..Default::default() };
    for m in matches {
        let is_home = m.home_team_key == key;
        let is_away = m.away_team_key == key;
        if !is_home && !is_away { continue; }
        s.matches += 1;
        let (gf, ga) = if is_home { (m.home_goal, m.away_goal) } else { (m.away_goal, m.home_goal) };
        s.goals_for += gf;
        s.goals_against += ga;
        let win = gf > ga;
        let draw = gf == ga;
        if is_home {
            s.home_matches += 1;
            if win { s.home_wins += 1; s.wins += 1; }
            else if draw { s.home_draws += 1; s.draws += 1; }
            else { s.home_losses += 1; s.losses += 1; }
        } else {
            s.away_matches += 1;
            if win { s.away_wins += 1; s.wins += 1; }
            else if draw { s.away_draws += 1; s.draws += 1; }
            else { s.away_losses += 1; s.losses += 1; }
        }
    }
    s
}

#[derive(Debug, Serialize)]
pub struct HeadToHead {
    pub team_a: String,
    pub team_b: String,
    pub matches: usize,
    pub a_wins: usize,
    pub b_wins: usize,
    pub draws: usize,
    pub a_goals: i32,
    pub b_goals: i32,
}

pub fn head_to_head(ds: &Dataset, a: &str, b: &str) -> HeadToHead {
    let ka = normalize_team(a);
    let kb = normalize_team(b);
    let mut h = HeadToHead {
        team_a: a.to_string(), team_b: b.to_string(),
        matches: 0, a_wins: 0, b_wins: 0, draws: 0, a_goals: 0, b_goals: 0,
    };
    for m in &ds.matches {
        let (a_home, a_away) = (m.home_team_key == ka, m.away_team_key == ka);
        let (b_home, b_away) = (m.home_team_key == kb, m.away_team_key == kb);
        if !((a_home && b_away) || (a_away && b_home)) { continue; }
        h.matches += 1;
        let (a_g, b_g) = if a_home { (m.home_goal, m.away_goal) } else { (m.away_goal, m.home_goal) };
        h.a_goals += a_g; h.b_goals += b_g;
        if a_g > b_g { h.a_wins += 1; }
        else if a_g < b_g { h.b_wins += 1; }
        else { h.draws += 1; }
    }
    h
}

#[derive(Debug, Serialize, Clone)]
pub struct StandingRow {
    pub position: usize,
    pub team: String,
    pub played: usize,
    pub wins: usize,
    pub draws: usize,
    pub losses: usize,
    pub goals_for: i32,
    pub goals_against: i32,
    pub goal_diff: i32,
    pub points: i32,
}

pub fn standings(ds: &Dataset, competition: Competition, season: i32) -> Vec<StandingRow> {
    use std::collections::HashMap;
    let mut by_team: HashMap<String, (String, TeamStats)> = HashMap::new();
    for m in &ds.matches {
        if m.competition != competition || m.season != season { continue; }
        for (key, display, is_home) in [
            (&m.home_team_key, &m.home_team, true),
            (&m.away_team_key, &m.away_team, false),
        ] {
            let entry = by_team.entry(key.clone()).or_insert_with(|| (display.clone(), TeamStats { team: display.clone(), ..Default::default() }));
            let s = &mut entry.1;
            s.matches += 1;
            let (gf, ga) = if is_home { (m.home_goal, m.away_goal) } else { (m.away_goal, m.home_goal) };
            s.goals_for += gf;
            s.goals_against += ga;
            if gf > ga { s.wins += 1; }
            else if gf == ga { s.draws += 1; }
            else { s.losses += 1; }
        }
    }
    let mut rows: Vec<StandingRow> = by_team.into_iter().map(|(_, (display, s))| StandingRow {
        position: 0,
        team: display,
        played: s.matches,
        wins: s.wins, draws: s.draws, losses: s.losses,
        goals_for: s.goals_for, goals_against: s.goals_against,
        goal_diff: s.goals_for - s.goals_against,
        points: s.points(),
    }).collect();
    rows.sort_by(|a, b| b.points.cmp(&a.points)
        .then(b.goal_diff.cmp(&a.goal_diff))
        .then(b.wins.cmp(&a.wins))
        .then(a.team.cmp(&b.team)));
    for (i, r) in rows.iter_mut().enumerate() { r.position = i + 1; }
    rows
}

#[derive(Debug, Default, Clone)]
pub struct PlayerFilter<'a> {
    pub name_contains: Option<&'a str>,
    pub nationality: Option<&'a str>,
    pub club_contains: Option<&'a str>,
    pub position: Option<&'a str>,
    pub min_overall: Option<i32>,
    pub limit: Option<usize>,
    pub sort_by_overall_desc: bool,
}

pub fn find_players<'a>(ds: &'a Dataset, f: &PlayerFilter) -> Vec<&'a Player> {
    let name_l = f.name_contains.map(|s| s.to_lowercase());
    let nat_l = f.nationality.map(|s| s.to_lowercase());
    let club_l = f.club_contains.map(|s| s.to_lowercase());
    let pos_l = f.position.map(|s| s.to_lowercase());

    let mut v: Vec<&Player> = ds.players.iter().filter(|p| {
        if let Some(ref n) = name_l { if !p.name.to_lowercase().contains(n) { return false; } }
        if let Some(ref n) = nat_l { if p.nationality.to_lowercase() != *n { return false; } }
        if let Some(ref c) = club_l { if !p.club.to_lowercase().contains(c) { return false; } }
        if let Some(ref pos) = pos_l { if p.position.to_lowercase() != *pos { return false; } }
        if let Some(mo) = f.min_overall { if p.overall.unwrap_or(0) < mo { return false; } }
        true
    }).collect();

    if f.sort_by_overall_desc {
        v.sort_by(|a, b| b.overall.cmp(&a.overall));
    }
    if let Some(l) = f.limit { v.truncate(l); }
    v
}

#[derive(Debug, Serialize)]
pub struct BiggestWin<'a> {
    pub date: &'a str,
    pub competition: &'static str,
    pub home_team: &'a str,
    pub away_team: &'a str,
    pub home_goal: i32,
    pub away_goal: i32,
    pub margin: i32,
}

pub fn biggest_wins(ds: &Dataset, competition: Option<Competition>, limit: usize) -> Vec<BiggestWin<'_>> {
    let mut v: Vec<BiggestWin> = ds.matches.iter()
        .filter(|m| competition.map_or(true, |c| m.competition == c))
        .map(|m| BiggestWin {
            date: &m.date,
            competition: m.competition.as_str(),
            home_team: &m.home_team,
            away_team: &m.away_team,
            home_goal: m.home_goal,
            away_goal: m.away_goal,
            margin: (m.home_goal - m.away_goal).abs(),
        })
        .collect();
    v.sort_by(|a, b| b.margin.cmp(&a.margin).then(b.date.cmp(&a.date)));
    v.truncate(limit);
    v
}

#[derive(Debug, Serialize)]
pub struct AggregateStats {
    pub total_matches: usize,
    pub total_goals: i64,
    pub avg_goals_per_match: f64,
    pub home_wins: usize,
    pub away_wins: usize,
    pub draws: usize,
    pub home_win_rate: f64,
}

pub fn aggregate_stats(ds: &Dataset, f: &MatchFilter) -> AggregateStats {
    let ms = find_matches(ds, f);
    let total = ms.len();
    let goals: i64 = ms.iter().map(|m| m.total_goals() as i64).sum();
    let mut hw = 0; let mut aw = 0; let mut d = 0;
    for m in &ms {
        match m.winner() {
            Winner::Home => hw += 1,
            Winner::Away => aw += 1,
            Winner::Draw => d += 1,
        }
    }
    AggregateStats {
        total_matches: total,
        total_goals: goals,
        avg_goals_per_match: if total == 0 { 0.0 } else { goals as f64 / total as f64 },
        home_wins: hw, away_wins: aw, draws: d,
        home_win_rate: if total == 0 { 0.0 } else { hw as f64 / total as f64 },
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn ds() -> Dataset { Dataset::load_default("data/kaggle").unwrap() }

    #[test]
    fn find_team_matches() {
        let d = ds();
        let f = MatchFilter { team: Some("Flamengo"), opponent: Some("Fluminense"), ..Default::default() };
        let ms = find_matches(&d, &f);
        assert!(ms.len() > 0);
        for m in &ms {
            let kf = normalize_team("Flamengo");
            let ku = normalize_team("Fluminense");
            let involves = (m.home_team_key == kf && m.away_team_key == ku)
                || (m.home_team_key == ku && m.away_team_key == kf);
            assert!(involves);
        }
    }

    #[test]
    fn team_stats_palmeiras_2019() {
        let d = ds();
        let f = MatchFilter { team: Some("Palmeiras"), season: Some(2019), competition: Some(Competition::Brasileirao), ..Default::default() };
        let ms = find_matches(&d, &f);
        let s = team_stats(&ms, "Palmeiras");
        assert!(s.matches > 0);
        assert_eq!(s.wins + s.draws + s.losses, s.matches);
    }

    #[test]
    fn standings_2019_has_flamengo_first() {
        let d = ds();
        let rows = standings(&d, Competition::Brasileirao, 2019);
        assert!(!rows.is_empty());
        let top = &rows[0];
        // Flamengo won the 2019 Brasileirão
        assert!(top.team.to_lowercase().contains("flamengo"), "top team: {}", top.team);
    }

    #[test]
    fn find_brazilian_players() {
        let d = ds();
        let f = PlayerFilter { nationality: Some("Brazil"), sort_by_overall_desc: true, limit: Some(5), ..Default::default() };
        let players = find_players(&d, &f);
        assert_eq!(players.len(), 5);
        assert!(players[0].overall.unwrap_or(0) >= players[4].overall.unwrap_or(0));
    }

    #[test]
    fn aggregate_positive() {
        let d = ds();
        let s = aggregate_stats(&d, &MatchFilter::default());
        assert!(s.total_matches > 0);
        assert!(s.avg_goals_per_match > 0.0);
    }

    #[test]
    fn head_to_head_works() {
        let d = ds();
        let h = head_to_head(&d, "Flamengo", "Fluminense");
        assert!(h.matches > 0);
        assert_eq!(h.a_wins + h.b_wins + h.draws, h.matches);
    }
}
