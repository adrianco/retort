// ============================================================================
// CONTEXT: Brazilian Soccer MCP Server - query & aggregation engine
//
// Purpose:  Implements every capability the MCP tools expose, working purely
//           on the in-memory Dataset:
//             search_matches  - filter by team/opponent/competition/season/date
//             team_stats      - W/D/L, goals, win rate, home/away split
//             head_to_head    - rivalry record between two clubs
//             standings       - league table computed from match results
//             search_players / get_player - FIFA database lookups
//             analyze_stats   - averages, home advantage, biggest wins
//             best_records    - team rankings by win rate (home/away/overall)
//
// Dedup:    Serie A 2012-2019 exists in three source files. Whenever results
//           are aggregated or listed, fixtures are deduplicated by
//           (date, home, away) keeping the highest-priority source
//           (see data::Source ordering).
//
// Output:   serde_json::Value, rendered to text by the MCP layer; numbers are
//           pre-formatted (rates as percentages with one decimal).
// ============================================================================

use crate::data::{Dataset, Match, Source};
use crate::normalize::{canonical_team, normalize_competition, team_matches, SERIE_A};
use serde_json::{json, Value};
use std::collections::HashMap;

/// Deduplicate fixtures appearing in several source files; keep the
/// highest-priority source for each (date, home, away) key.
pub fn dedup<'a>(matches: impl Iterator<Item = &'a Match>) -> Vec<&'a Match> {
    let mut best: HashMap<(String, String, String), &Match> = HashMap::new();
    for m in matches {
        let key = m.dedup_key();
        match best.get(&key) {
            Some(existing) if existing.source <= m.source => {}
            _ => {
                best.insert(key, m);
            }
        }
    }
    let mut out: Vec<&Match> = best.into_values().collect();
    out.sort_by(|a, b| b.date.cmp(&a.date).then(a.home.cmp(&b.home)));
    out
}

fn pct(part: usize, total: usize) -> f64 {
    if total == 0 {
        0.0
    } else {
        (part as f64 * 1000.0 / total as f64).round() / 10.0
    }
}

fn match_json(m: &Match) -> Value {
    let mut v = json!({
        "date": if m.date.is_empty() { Value::Null } else { json!(m.date) },
        "competition": m.competition,
        "season": m.season,
        "home_team": m.home_raw,
        "away_team": m.away_raw,
        "score": format!("{}-{}", m.home_goals, m.away_goals),
        "home_goals": m.home_goals,
        "away_goals": m.away_goals,
        "source": m.source.label(),
    });
    if !m.round.is_empty() {
        v["round"] = json!(m.round);
    }
    if let Some(s) = &m.extra.stadium {
        v["stadium"] = json!(s);
    }
    if let (Some(hc), Some(ac)) = (m.extra.home_corners, m.extra.away_corners) {
        v["corners"] = json!(format!("{}-{}", hc, ac));
    }
    if let (Some(hs), Some(as_)) = (m.extra.home_shots, m.extra.away_shots) {
        v["shots"] = json!(format!("{}-{}", hs, as_));
    }
    v
}

/// Resolve an optional competition filter; returns Err for unknown names.
fn competition_filter(arg: Option<&str>) -> Result<Option<&'static str>, String> {
    match arg {
        None => Ok(None),
        Some(q) => normalize_competition(q)
            .map(Some)
            .ok_or_else(|| format!("Unknown competition '{}'. Try: Brasileirão Série A/B/C, Copa do Brasil, Copa Libertadores.", q)),
    }
}

pub struct MatchFilters<'a> {
    pub team: Option<&'a str>,
    pub opponent: Option<&'a str>,
    pub competition: Option<&'a str>,
    pub season: Option<i32>,
    pub date_from: Option<&'a str>,
    pub date_to: Option<&'a str>,
    pub limit: usize,
}

fn filtered<'a>(ds: &'a Dataset, f: &MatchFilters) -> Result<Vec<&'a Match>, String> {
    let comp = competition_filter(f.competition)?;
    let team_q = f.team.map(canonical_team);
    let opp_q = f.opponent.map(canonical_team);
    let date_from = f.date_from.map(normalize_date_bound_low);
    let date_to = f.date_to.map(normalize_date_bound_high);

    let it = ds.matches.iter().filter(|m| {
        if let Some(c) = comp {
            if m.competition != c {
                return false;
            }
        }
        if let Some(s) = f.season {
            if m.season != s {
                return false;
            }
        }
        if let Some(from) = &date_from {
            if m.date.is_empty() || m.date.as_str() < from.as_str() {
                return false;
            }
        }
        if let Some(to) = &date_to {
            if m.date.is_empty() || m.date.as_str() > to.as_str() {
                return false;
            }
        }
        match (&team_q, &opp_q) {
            (Some(t), Some(o)) => {
                (team_matches(&m.home, t) && team_matches(&m.away, o))
                    || (team_matches(&m.home, o) && team_matches(&m.away, t))
            }
            (Some(t), None) => m.involves(t),
            (None, Some(o)) => m.involves(o),
            (None, None) => true,
        }
    });
    Ok(dedup(it))
}

/// Accept "YYYY" or "YYYY-MM-DD" bounds.
fn normalize_date_bound_low(s: &str) -> String {
    if s.len() == 4 { format!("{}-01-01", s) } else { s.to_string() }
}
fn normalize_date_bound_high(s: &str) -> String {
    if s.len() == 4 { format!("{}-12-31", s) } else { s.to_string() }
}

pub fn search_matches(ds: &Dataset, f: &MatchFilters) -> Result<Value, String> {
    let all = filtered(ds, f)?;
    let limit = f.limit.clamp(1, 100);
    let shown: Vec<Value> = all.iter().take(limit).map(|m| match_json(m)).collect();

    let mut result = json!({
        "total_matches_found": all.len(),
        "returned": shown.len(),
        "matches": shown,
    });

    // When two teams are given, add the head-to-head summary inline.
    if let (Some(t), Some(o)) = (f.team, f.opponent) {
        let tq = canonical_team(t);
        let (mut tw, mut ow, mut d) = (0, 0, 0);
        for m in &all {
            let home_is_t = team_matches(&m.home, &tq);
            if m.home_goals == m.away_goals {
                d += 1;
            } else if (m.home_goals > m.away_goals) == home_is_t {
                tw += 1;
            } else {
                ow += 1;
            }
        }
        result["head_to_head"] = json!({
            "team1": t, "team1_wins": tw,
            "team2": o, "team2_wins": ow,
            "draws": d,
        });
    }
    Ok(result)
}

struct Tally {
    matches: usize,
    wins: usize,
    draws: usize,
    losses: usize,
    goals_for: i64,
    goals_against: i64,
}

impl Tally {
    fn new() -> Self {
        Tally { matches: 0, wins: 0, draws: 0, losses: 0, goals_for: 0, goals_against: 0 }
    }
    fn add(&mut self, gf: i32, ga: i32) {
        self.matches += 1;
        self.goals_for += gf as i64;
        self.goals_against += ga as i64;
        if gf > ga {
            self.wins += 1;
        } else if gf == ga {
            self.draws += 1;
        } else {
            self.losses += 1;
        }
    }
    fn json(&self) -> Value {
        json!({
            "matches": self.matches,
            "wins": self.wins,
            "draws": self.draws,
            "losses": self.losses,
            "goals_for": self.goals_for,
            "goals_against": self.goals_against,
            "goal_difference": self.goals_for - self.goals_against,
            "win_rate_pct": pct(self.wins, self.matches),
        })
    }
}

pub fn team_stats(
    ds: &Dataset,
    team: &str,
    season: Option<i32>,
    competition: Option<&str>,
) -> Result<Value, String> {
    let f = MatchFilters {
        team: Some(team),
        opponent: None,
        competition,
        season,
        date_from: None,
        date_to: None,
        limit: 100,
    };
    let all = filtered(ds, &f)?;
    if all.is_empty() {
        return Err(format!("No matches found for team '{}'", team));
    }
    let tq = canonical_team(team);
    let (mut overall, mut home, mut away) = (Tally::new(), Tally::new(), Tally::new());
    let mut by_comp: HashMap<&str, Tally> = HashMap::new();
    for m in &all {
        let at_home = team_matches(&m.home, &tq);
        let (gf, ga) = if at_home { (m.home_goals, m.away_goals) } else { (m.away_goals, m.home_goals) };
        overall.add(gf, ga);
        if at_home { home.add(gf, ga) } else { away.add(gf, ga) };
        by_comp.entry(m.competition.as_str()).or_insert_with(Tally::new).add(gf, ga);
    }
    let mut comps: Vec<(&str, Tally)> = by_comp.into_iter().collect();
    comps.sort_by(|a, b| b.1.matches.cmp(&a.1.matches));
    Ok(json!({
        "team": team,
        "season": season,
        "competition_filter": competition,
        "overall": overall.json(),
        "home": home.json(),
        "away": away.json(),
        "by_competition": comps.into_iter()
            .map(|(c, t)| { let mut v = t.json(); v["competition"] = json!(c); v })
            .collect::<Vec<_>>(),
    }))
}

pub fn head_to_head(
    ds: &Dataset,
    team1: &str,
    team2: &str,
    competition: Option<&str>,
) -> Result<Value, String> {
    let f = MatchFilters {
        team: Some(team1),
        opponent: Some(team2),
        competition,
        season: None,
        date_from: None,
        date_to: None,
        limit: 100,
    };
    let all = filtered(ds, &f)?;
    if all.is_empty() {
        return Err(format!("No matches found between '{}' and '{}'", team1, team2));
    }
    let t1 = canonical_team(team1);
    let (mut w1, mut w2, mut d, mut g1, mut g2) = (0usize, 0usize, 0usize, 0i64, 0i64);
    for m in &all {
        let home_is_t1 = team_matches(&m.home, &t1);
        let (gf, ga) = if home_is_t1 { (m.home_goals, m.away_goals) } else { (m.away_goals, m.home_goals) };
        g1 += gf as i64;
        g2 += ga as i64;
        if gf > ga {
            w1 += 1;
        } else if gf == ga {
            d += 1;
        } else {
            w2 += 1;
        }
    }
    Ok(json!({
        "team1": team1,
        "team2": team2,
        "total_matches": all.len(),
        "team1_wins": w1,
        "team2_wins": w2,
        "draws": d,
        "team1_goals": g1,
        "team2_goals": g2,
        "recent_matches": all.iter().take(10).map(|m| match_json(m)).collect::<Vec<_>>(),
    }))
}

pub fn standings(ds: &Dataset, season: i32, competition: Option<&str>) -> Result<Value, String> {
    let comp = competition_filter(competition)?.unwrap_or(SERIE_A);
    if comp == crate::normalize::COPA_DO_BRASIL || comp == crate::normalize::LIBERTADORES {
        return Err(format!(
            "{} is a knockout competition - standings are not applicable. Use search_matches with the round/stage instead.",
            comp
        ));
    }
    // Pick the most reliable single source per season to avoid partial overlap.
    let source = if comp == SERIE_A {
        if (2012..=2022).contains(&season) {
            Source::Brasileirao
        } else if (2003..=2019).contains(&season) {
            Source::NovoCampeonato
        } else {
            Source::BrFootball
        }
    } else {
        Source::BrFootball
    };
    let rows: Vec<&Match> = ds
        .matches
        .iter()
        .filter(|m| m.source == source && m.competition == comp && m.season == season)
        .collect();
    if rows.is_empty() {
        return Err(format!("No {} match data for season {}", comp, season));
    }
    struct Row {
        display: String,
        t: Tally,
    }
    let mut table: HashMap<String, Row> = HashMap::new();
    for m in rows {
        for (key, display, gf, ga) in [
            (&m.home, &m.home_raw, m.home_goals, m.away_goals),
            (&m.away, &m.away_raw, m.away_goals, m.home_goals),
        ] {
            table
                .entry(key.clone())
                .or_insert_with(|| Row { display: display.clone(), t: Tally::new() })
                .t
                .add(gf, ga);
        }
    }
    let mut rows: Vec<Row> = table.into_values().collect();
    rows.sort_by(|a, b| {
        let pa = 3 * a.t.wins + a.t.draws;
        let pb = 3 * b.t.wins + b.t.draws;
        pb.cmp(&pa)
            .then(b.t.wins.cmp(&a.t.wins))
            .then((b.t.goals_for - b.t.goals_against).cmp(&(a.t.goals_for - a.t.goals_against)))
            .then(b.t.goals_for.cmp(&a.t.goals_for))
    });
    let n = rows.len();
    Ok(json!({
        "competition": comp,
        "season": season,
        "source": source.label(),
        "note": "Standings computed from match results: 3 pts/win, 1 pt/draw. Tie-breakers: wins, goal difference, goals for.",
        "table": rows.iter().enumerate().map(|(i, r)| json!({
            "position": i + 1,
            "team": r.display,
            "points": 3 * r.t.wins + r.t.draws,
            "played": r.t.matches,
            "wins": r.t.wins,
            "draws": r.t.draws,
            "losses": r.t.losses,
            "goals_for": r.t.goals_for,
            "goals_against": r.t.goals_against,
            "goal_difference": r.t.goals_for - r.t.goals_against,
            "status": if i == 0 { "Champion" } else if i >= n.saturating_sub(4) { "Relegation zone" } else { "" },
        })).collect::<Vec<_>>(),
    }))
}

pub struct PlayerFilters<'a> {
    pub name: Option<&'a str>,
    pub nationality: Option<&'a str>,
    pub club: Option<&'a str>,
    pub position: Option<&'a str>,
    pub min_overall: Option<i32>,
    pub limit: usize,
}

fn player_json(p: &crate::data::Player) -> Value {
    json!({
        "name": p.name,
        "age": p.age,
        "nationality": p.nationality,
        "overall": p.overall,
        "potential": p.potential,
        "club": p.club,
        "position": p.position,
        "jersey_number": p.jersey_number,
        "value": p.value,
    })
}

pub fn search_players(ds: &Dataset, f: &PlayerFilters) -> Result<Value, String> {
    let name_q = f.name.map(|n| crate::normalize::deaccent(n).to_lowercase());
    let nat_q = f.nationality.map(|n| n.trim().to_lowercase());
    let club_q = f.club.map(canonical_team);
    let pos_q = f.position.map(|p| p.trim().to_uppercase());

    let mut hits: Vec<&crate::data::Player> = ds
        .players
        .iter()
        .filter(|p| {
            if let Some(n) = &name_q {
                if !p.canonical_name.contains(n.as_str()) {
                    return false;
                }
            }
            if let Some(n) = &nat_q {
                if p.nationality.to_lowercase() != *n {
                    return false;
                }
            }
            if let Some(c) = &club_q {
                if !team_matches(&p.canonical_club, c) {
                    return false;
                }
            }
            if let Some(pos) = &pos_q {
                if !p.position.to_uppercase().split(|c: char| !c.is_alphanumeric()).any(|t| t == pos) {
                    return false;
                }
            }
            if let Some(mo) = f.min_overall {
                if p.overall < mo {
                    return false;
                }
            }
            true
        })
        .collect();
    hits.sort_by(|a, b| b.overall.cmp(&a.overall).then(a.name.cmp(&b.name)));
    let limit = f.limit.clamp(1, 100);
    Ok(json!({
        "total_players_found": hits.len(),
        "returned": hits.len().min(limit),
        "players": hits.iter().take(limit).map(|p| player_json(p)).collect::<Vec<_>>(),
    }))
}

pub fn get_player(ds: &Dataset, name: &str) -> Result<Value, String> {
    let q = crate::normalize::deaccent(name).to_lowercase();
    let p = ds
        .players
        .iter()
        .find(|p| p.canonical_name == q)
        .or_else(|| {
            let mut hits: Vec<&crate::data::Player> =
                ds.players.iter().filter(|p| p.canonical_name.contains(&q)).collect();
            hits.sort_by(|a, b| b.overall.cmp(&a.overall));
            hits.into_iter().next()
        })
        .ok_or_else(|| format!("No player found matching '{}'", name))?;
    let mut v = player_json(p);
    v["height"] = json!(p.height);
    v["weight"] = json!(p.weight);
    v["wage"] = json!(p.wage);
    v["preferred_foot"] = json!(p.preferred_foot);
    v["skills"] = json!(p.skills.iter().map(|(k, s)| json!({"skill": k, "rating": s})).collect::<Vec<_>>());
    Ok(v)
}

pub fn analyze_stats(
    ds: &Dataset,
    competition: Option<&str>,
    season: Option<i32>,
    top_n: usize,
) -> Result<Value, String> {
    let f = MatchFilters {
        team: None,
        opponent: None,
        competition,
        season,
        date_from: None,
        date_to: None,
        limit: 100,
    };
    let all = filtered(ds, &f)?;
    if all.is_empty() {
        return Err("No matches found for the given filters".into());
    }
    let total = all.len();
    let goals: i64 = all.iter().map(|m| (m.home_goals + m.away_goals) as i64).sum();
    let home_wins = all.iter().filter(|m| m.home_goals > m.away_goals).count();
    let draws = all.iter().filter(|m| m.home_goals == m.away_goals).count();
    let away_wins = total - home_wins - draws;

    let mut by_margin: Vec<&&Match> = all.iter().collect();
    by_margin.sort_by(|a, b| {
        let ma = (a.home_goals - a.away_goals).abs();
        let mb = (b.home_goals - b.away_goals).abs();
        mb.cmp(&ma).then((b.home_goals + b.away_goals).cmp(&(a.home_goals + a.away_goals)))
    });
    let top_n = top_n.clamp(1, 25);
    Ok(json!({
        "filters": { "competition": competition, "season": season },
        "total_matches": total,
        "total_goals": goals,
        "avg_goals_per_match": (goals as f64 * 100.0 / total as f64).round() / 100.0,
        "home_win_rate_pct": pct(home_wins, total),
        "draw_rate_pct": pct(draws, total),
        "away_win_rate_pct": pct(away_wins, total),
        "biggest_wins": by_margin.iter().take(top_n).map(|m| match_json(m)).collect::<Vec<_>>(),
    }))
}

pub fn best_records(
    ds: &Dataset,
    venue: &str,
    competition: Option<&str>,
    season: Option<i32>,
    min_matches: usize,
    limit: usize,
) -> Result<Value, String> {
    let f = MatchFilters {
        team: None,
        opponent: None,
        competition,
        season,
        date_from: None,
        date_to: None,
        limit: 100,
    };
    let all = filtered(ds, &f)?;
    let venue = venue.to_lowercase();
    if !["home", "away", "overall"].contains(&venue.as_str()) {
        return Err("venue must be one of: home, away, overall".into());
    }
    struct Row {
        display: String,
        t: Tally,
    }
    let mut table: HashMap<String, Row> = HashMap::new();
    for m in &all {
        if venue == "home" || venue == "overall" {
            table
                .entry(m.home.clone())
                .or_insert_with(|| Row { display: m.home_raw.clone(), t: Tally::new() })
                .t
                .add(m.home_goals, m.away_goals);
        }
        if venue == "away" || venue == "overall" {
            table
                .entry(m.away.clone())
                .or_insert_with(|| Row { display: m.away_raw.clone(), t: Tally::new() })
                .t
                .add(m.away_goals, m.home_goals);
        }
    }
    let mut rows: Vec<Row> = table.into_values().filter(|r| r.t.matches >= min_matches.max(1)).collect();
    rows.sort_by(|a, b| {
        pct(b.t.wins, b.t.matches)
            .partial_cmp(&pct(a.t.wins, a.t.matches))
            .unwrap()
            .then(b.t.matches.cmp(&a.t.matches))
    });
    Ok(json!({
        "venue": venue,
        "filters": { "competition": competition, "season": season, "min_matches": min_matches },
        "teams": rows.iter().take(limit.clamp(1, 50)).map(|r| {
            let mut v = r.t.json();
            v["team"] = json!(r.display);
            v
        }).collect::<Vec<_>>(),
    }))
}

pub fn list_competitions(ds: &Dataset) -> Value {
    let mut by_comp: HashMap<&str, (usize, i32, i32)> = HashMap::new();
    for m in &ds.matches {
        let e = by_comp.entry(m.competition.as_str()).or_insert((0, i32::MAX, i32::MIN));
        e.0 += 1;
        if m.season > 0 {
            e.1 = e.1.min(m.season);
            e.2 = e.2.max(m.season);
        }
    }
    let mut comps: Vec<Value> = by_comp
        .into_iter()
        .map(|(c, (n, lo, hi))| {
            json!({
                "competition": c,
                "match_records": n,
                "first_season": if lo == i32::MAX { Value::Null } else { json!(lo) },
                "last_season": if hi == i32::MIN { Value::Null } else { json!(hi) },
            })
        })
        .collect();
    comps.sort_by_key(|v| std::cmp::Reverse(v["match_records"].as_u64()));
    json!({
        "competitions": comps,
        "players_in_fifa_database": ds.players.len(),
        "files_loaded": ds.file_counts,
        "note": "Match records overlap across files for Série A 2012-2019; queries deduplicate automatically.",
    })
}
