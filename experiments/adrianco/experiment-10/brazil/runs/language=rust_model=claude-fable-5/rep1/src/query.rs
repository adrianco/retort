//! Query engine: filtering, aggregation and human-readable formatting on
//! top of the loaded [`Store`].

use std::collections::HashMap;
use std::fmt::Write as _;

use chrono::NaiveDate;

use crate::data::{Match, Player, Store, SERIE_A};
use crate::normalize::{canonical_team, fold_text, team_key_matches};

/// Filters accepted by match-search style queries.
#[derive(Debug, Default, Clone)]
pub struct MatchFilter {
    pub team: Option<String>,
    pub opponent: Option<String>,
    pub competition: Option<String>,
    pub season: Option<i32>,
    pub date_from: Option<NaiveDate>,
    pub date_to: Option<NaiveDate>,
    pub stage: Option<String>,
}

/// Does the canonical competition name satisfy a loose user query like
/// "brasileirao", "serie a", "copa do brasil" or "libertadores"?
pub fn competition_matches(query: &str, competition: &str) -> bool {
    let q = fold_text(query);
    let c = fold_text(competition);
    if c.contains(&q) {
        return true;
    }
    // "brasileirao" alone means the top flight.
    if (q == "brasileirao" || q == "campeonato brasileiro") && c == fold_text(SERIE_A) {
        return true;
    }
    false
}

impl MatchFilter {
    fn matches(&self, m: &Match) -> bool {
        if let Some(season) = self.season {
            if m.season != season {
                return false;
            }
        }
        if let Some(comp) = &self.competition {
            if !competition_matches(comp, m.competition) {
                return false;
            }
        }
        if let Some(from) = self.date_from {
            match m.date {
                Some(d) if d >= from => {}
                _ => return false,
            }
        }
        if let Some(to) = self.date_to {
            match m.date {
                Some(d) if d <= to => {}
                _ => return false,
            }
        }
        if let Some(stage) = &self.stage {
            let q = fold_text(stage);
            let s = m.stage.as_deref().map(fold_text).unwrap_or_default();
            let r = m.round.as_deref().map(fold_text).unwrap_or_default();
            if !s.contains(&q) && !r.contains(&q) {
                return false;
            }
        }
        match (&self.team, &self.opponent) {
            (Some(t), Some(o)) => {
                let tk = canonical_team(t).key;
                let ok = canonical_team(o).key;
                (team_key_matches(&tk, &m.home_key) && team_key_matches(&ok, &m.away_key))
                    || (team_key_matches(&tk, &m.away_key) && team_key_matches(&ok, &m.home_key))
            }
            (Some(t), None) => {
                let tk = canonical_team(t).key;
                team_key_matches(&tk, &m.home_key) || team_key_matches(&tk, &m.away_key)
            }
            (None, Some(o)) => {
                let ok = canonical_team(o).key;
                team_key_matches(&ok, &m.home_key) || team_key_matches(&ok, &m.away_key)
            }
            (None, None) => true,
        }
    }
}

/// Find matches, most recent first.
pub fn find_matches<'a>(store: &'a Store, filter: &MatchFilter) -> Vec<&'a Match> {
    let mut found: Vec<&Match> = store
        .matches
        .iter()
        .filter(|m| filter.matches(m))
        .collect();
    found.sort_by_key(|m| std::cmp::Reverse(m.date));
    found
}

fn describe_round(m: &Match) -> String {
    if let Some(stage) = &m.stage {
        return format!(", {}", stage);
    }
    if let Some(round) = &m.round {
        if !round.is_empty() {
            return format!(" Round {}", round);
        }
    }
    String::new()
}

/// One line per match: `2023-09-03: Flamengo 2-1 Fluminense (Brasileirão Série A Round 22)`.
pub fn format_match_line(m: &Match) -> String {
    let mut line = format!(
        "{}: {} {}-{} {} ({}{})",
        m.date_str(),
        m.home,
        m.home_goals,
        m.away_goals,
        m.away,
        m.competition,
        describe_round(m)
    );
    if let Some(stadium) = &m.stadium {
        let _ = write!(line, " @ {}", stadium);
    }
    line
}

pub fn format_matches(matches: &[&Match], limit: usize) -> String {
    if matches.is_empty() {
        return "No matches found for those criteria.".into();
    }
    let mut out = String::new();
    for m in matches.iter().take(limit) {
        let _ = writeln!(out, "- {}", format_match_line(m));
    }
    if matches.len() > limit {
        let _ = writeln!(out, "... ({} more matches in dataset)", matches.len() - limit);
    }
    out
}

/// Head-to-head record between two teams across all loaded competitions.
pub fn head_to_head(store: &Store, team1: &str, team2: &str, competition: Option<&str>) -> String {
    let filter = MatchFilter {
        team: Some(team1.to_string()),
        opponent: Some(team2.to_string()),
        competition: competition.map(|s| s.to_string()),
        ..Default::default()
    };
    let matches = find_matches(store, &filter);
    if matches.is_empty() {
        return format!("No matches found between {} and {}.", team1, team2);
    }
    let k1 = canonical_team(team1).key;
    let (mut w1, mut w2, mut d, mut g1, mut g2) = (0, 0, 0, 0, 0);
    let mut name1 = team1.to_string();
    let mut name2 = team2.to_string();
    for m in &matches {
        let home_is_1 = team_key_matches(&k1, &m.home_key);
        let (gf, ga) = if home_is_1 {
            name1 = m.home.clone();
            name2 = m.away.clone();
            (m.home_goals, m.away_goals)
        } else {
            name1 = m.away.clone();
            name2 = m.home.clone();
            (m.away_goals, m.home_goals)
        };
        g1 += gf;
        g2 += ga;
        if gf > ga {
            w1 += 1;
        } else if ga > gf {
            w2 += 1;
        } else {
            d += 1;
        }
    }
    let mut out = format!("{} vs {}: {} matches in dataset\n", name1, name2, matches.len());
    let _ = writeln!(
        out,
        "Head-to-head: {} {} wins, {} {} wins, {} draws (goals {}-{})\n",
        name1, w1, name2, w2, d, g1, g2
    );
    out.push_str("Most recent matches:\n");
    out.push_str(&format_matches(&matches, 15));
    out
}

/// Win/draw/loss + goals record for one team.
pub struct TeamRecord {
    pub played: usize,
    pub wins: usize,
    pub draws: usize,
    pub losses: usize,
    pub goals_for: i32,
    pub goals_against: i32,
}

impl TeamRecord {
    pub fn points(&self) -> usize {
        self.wins * 3 + self.draws
    }
    pub fn win_rate(&self) -> f64 {
        if self.played == 0 {
            0.0
        } else {
            self.wins as f64 / self.played as f64 * 100.0
        }
    }
}

/// Compute a team's record over a match subset. `venue`: "home", "away" or "all".
pub fn team_record(matches: &[&Match], team_key: &str, venue: &str) -> TeamRecord {
    let mut rec = TeamRecord {
        played: 0,
        wins: 0,
        draws: 0,
        losses: 0,
        goals_for: 0,
        goals_against: 0,
    };
    for m in matches {
        let at_home = team_key_matches(team_key, &m.home_key);
        let away = team_key_matches(team_key, &m.away_key);
        let (gf, ga) = if at_home && venue != "away" {
            (m.home_goals, m.away_goals)
        } else if away && venue != "home" {
            (m.away_goals, m.home_goals)
        } else {
            continue;
        };
        rec.played += 1;
        rec.goals_for += gf;
        rec.goals_against += ga;
        if gf > ga {
            rec.wins += 1;
        } else if gf < ga {
            rec.losses += 1;
        } else {
            rec.draws += 1;
        }
    }
    rec
}

/// Formatted team statistics, optionally restricted by season/competition/venue.
pub fn team_stats(
    store: &Store,
    team: &str,
    season: Option<i32>,
    competition: Option<&str>,
    venue: &str,
) -> String {
    let filter = MatchFilter {
        team: Some(team.to_string()),
        season,
        competition: competition.map(|s| s.to_string()),
        ..Default::default()
    };
    let matches = find_matches(store, &filter);
    if matches.is_empty() {
        return format!("No matches found for {}.", team);
    }
    let key = canonical_team(team).key;
    let display = matches
        .first()
        .map(|m| {
            if team_key_matches(&key, &m.home_key) {
                m.home.clone()
            } else {
                m.away.clone()
            }
        })
        .unwrap_or_else(|| team.to_string());
    let rec = team_record(&matches, &key, venue);

    let mut scope = Vec::new();
    if let Some(s) = season {
        scope.push(s.to_string());
    }
    scope.push(competition.map(|c| c.to_string()).unwrap_or_else(|| "all competitions".into()));
    let venue_label = match venue {
        "home" => "home record",
        "away" => "away record",
        _ => "record",
    };
    let mut out = format!("{} {} ({}):\n", display, venue_label, scope.join(" "));
    let _ = writeln!(out, "- Matches: {}", rec.played);
    let _ = writeln!(
        out,
        "- Wins: {}, Draws: {}, Losses: {}",
        rec.wins, rec.draws, rec.losses
    );
    let _ = writeln!(
        out,
        "- Goals For: {}, Goals Against: {} (diff {:+})",
        rec.goals_for,
        rec.goals_against,
        rec.goals_for - rec.goals_against
    );
    let _ = writeln!(out, "- Win rate: {:.1}%", rec.win_rate());

    // Per-competition breakdown when not already filtered to one.
    if competition.is_none() {
        let mut comps: Vec<&str> = matches.iter().map(|m| m.competition).collect();
        comps.sort();
        comps.dedup();
        if comps.len() > 1 {
            out.push_str("\nBy competition:\n");
            for comp in comps {
                let subset: Vec<&Match> = matches
                    .iter()
                    .filter(|m| m.competition == comp)
                    .copied()
                    .collect();
                let r = team_record(&subset, &key, venue);
                let _ = writeln!(
                    out,
                    "- {}: {}M {}W {}D {}L, goals {}-{}",
                    comp, r.played, r.wins, r.draws, r.losses, r.goals_for, r.goals_against
                );
            }
        }
    }
    out
}

/// One row of a calculated league table.
pub struct TableRow {
    pub team: String,
    pub rec: TeamRecord,
}

/// Compute Série A standings for a season (3 pts/win, Brazilian tiebreaks:
/// points, wins, goal difference, goals for).
pub fn standings(store: &Store, season: i32) -> Vec<TableRow> {
    let matches = store.serie_a_season(season);
    let mut teams: HashMap<String, (String, TeamRecord)> = HashMap::new();
    for m in &matches {
        for (key, display) in [(&m.home_key, &m.home), (&m.away_key, &m.away)] {
            teams.entry(key.clone()).or_insert_with(|| {
                (
                    display.clone(),
                    TeamRecord {
                        played: 0,
                        wins: 0,
                        draws: 0,
                        losses: 0,
                        goals_for: 0,
                        goals_against: 0,
                    },
                )
            });
        }
        for (key, gf, ga) in [
            (m.home_key.clone(), m.home_goals, m.away_goals),
            (m.away_key.clone(), m.away_goals, m.home_goals),
        ] {
            let entry = &mut teams.get_mut(&key).unwrap().1;
            entry.played += 1;
            entry.goals_for += gf;
            entry.goals_against += ga;
            if gf > ga {
                entry.wins += 1;
            } else if gf < ga {
                entry.losses += 1;
            } else {
                entry.draws += 1;
            }
        }
    }
    let mut rows: Vec<TableRow> = teams
        .into_values()
        .map(|(team, rec)| TableRow { team, rec })
        .collect();
    rows.sort_by(|a, b| {
        b.rec
            .points()
            .cmp(&a.rec.points())
            .then(b.rec.wins.cmp(&a.rec.wins))
            .then(
                (b.rec.goals_for - b.rec.goals_against)
                    .cmp(&(a.rec.goals_for - a.rec.goals_against)),
            )
            .then(b.rec.goals_for.cmp(&a.rec.goals_for))
            .then(a.team.cmp(&b.team))
    });
    rows
}

pub fn format_standings(store: &Store, season: i32) -> String {
    let rows = standings(store, season);
    if rows.is_empty() {
        return format!("No Brasileirão Série A match data for season {}.", season);
    }
    let n = rows.len();
    let mut out = format!("{} Brasileirão Série A standings (calculated from matches):\n", season);
    for (i, row) in rows.iter().enumerate() {
        let mut note = "";
        if i == 0 {
            note = " - Champion";
        } else if i >= n.saturating_sub(4) {
            note = " - Relegated";
        }
        let _ = writeln!(
            out,
            "{:2}. {} - {} pts ({}W, {}D, {}L, GF {}, GA {}){}",
            i + 1,
            row.team,
            row.rec.points(),
            row.rec.wins,
            row.rec.draws,
            row.rec.losses,
            row.rec.goals_for,
            row.rec.goals_against,
            note
        );
    }
    out
}

/// Aggregate goal statistics for an optional competition/season slice.
pub fn competition_overview(
    store: &Store,
    competition: Option<&str>,
    season: Option<i32>,
) -> String {
    let filter = MatchFilter {
        competition: competition.map(|s| s.to_string()),
        season,
        ..Default::default()
    };
    let matches = find_matches(store, &filter);
    if matches.is_empty() {
        return "No matches found for those criteria.".into();
    }
    let total: i64 = matches
        .iter()
        .map(|m| (m.home_goals + m.away_goals) as i64)
        .sum();
    let home_wins = matches.iter().filter(|m| m.home_goals > m.away_goals).count();
    let away_wins = matches.iter().filter(|m| m.away_goals > m.home_goals).count();
    let draws = matches.len() - home_wins - away_wins;

    let mut scope = Vec::new();
    if let Some(c) = competition {
        scope.push(c.to_string());
    }
    if let Some(s) = season {
        scope.push(s.to_string());
    }
    let scope = if scope.is_empty() {
        "all loaded competitions".to_string()
    } else {
        scope.join(" ")
    };

    let mut out = format!("Overview ({}):\n", scope);
    let _ = writeln!(out, "- Matches: {}", matches.len());
    let _ = writeln!(
        out,
        "- Average goals per match: {:.2}",
        total as f64 / matches.len() as f64
    );
    let _ = writeln!(
        out,
        "- Home wins: {} ({:.1}%), Draws: {} ({:.1}%), Away wins: {} ({:.1}%)",
        home_wins,
        home_wins as f64 / matches.len() as f64 * 100.0,
        draws,
        draws as f64 / matches.len() as f64 * 100.0,
        away_wins,
        away_wins as f64 / matches.len() as f64 * 100.0
    );

    // Top scoring teams in this slice.
    let mut goals_by_team: HashMap<String, (String, i32)> = HashMap::new();
    for m in &matches {
        let e = goals_by_team
            .entry(m.home_key.clone())
            .or_insert_with(|| (m.home.clone(), 0));
        e.1 += m.home_goals;
        let e = goals_by_team
            .entry(m.away_key.clone())
            .or_insert_with(|| (m.away.clone(), 0));
        e.1 += m.away_goals;
    }
    let mut top: Vec<(String, i32)> = goals_by_team.into_values().collect();
    top.sort_by(|a, b| b.1.cmp(&a.1).then(a.0.cmp(&b.0)));
    out.push_str("- Top scoring teams: ");
    let tops: Vec<String> = top
        .iter()
        .take(5)
        .map(|(t, g)| format!("{} ({})", t, g))
        .collect();
    out.push_str(&tops.join(", "));
    out.push('\n');
    out
}

/// Biggest margins of victory.
pub fn biggest_wins(
    store: &Store,
    competition: Option<&str>,
    season: Option<i32>,
    limit: usize,
) -> String {
    let filter = MatchFilter {
        competition: competition.map(|s| s.to_string()),
        season,
        ..Default::default()
    };
    let mut matches = find_matches(store, &filter);
    matches.sort_by(|a, b| {
        let ma = (a.home_goals - a.away_goals).abs();
        let mb = (b.home_goals - b.away_goals).abs();
        mb.cmp(&ma)
            .then((b.home_goals + b.away_goals).cmp(&(a.home_goals + a.away_goals)))
            .then(b.date.cmp(&a.date))
    });
    if matches.is_empty() {
        return "No matches found for those criteria.".into();
    }
    let mut out = String::from("Biggest victories in dataset:\n");
    for (i, m) in matches.iter().take(limit).enumerate() {
        let _ = writeln!(out, "{}. {}", i + 1, format_match_line(m));
    }
    out
}

/// Player search filters.
#[derive(Debug, Default, Clone)]
pub struct PlayerFilter {
    pub name: Option<String>,
    pub nationality: Option<String>,
    pub club: Option<String>,
    pub position: Option<String>,
    pub min_overall: Option<i32>,
}

pub fn find_players<'a>(store: &'a Store, filter: &PlayerFilter, sort_by: &str) -> Vec<&'a Player> {
    let name_q = filter.name.as_deref().map(fold_text);
    let nat_q = filter.nationality.as_deref().map(fold_text);
    let club_q = filter.club.as_deref().map(fold_text);
    let pos_q = filter.position.as_deref().map(|p| p.trim().to_uppercase());
    let mut found: Vec<&Player> = store
        .players
        .iter()
        .filter(|p| {
            if let Some(q) = &name_q {
                if !p.name_folded.contains(q.as_str()) {
                    return false;
                }
            }
            if let Some(q) = &nat_q {
                if !p.nationality_folded.contains(q.as_str()) {
                    return false;
                }
            }
            if let Some(q) = &club_q {
                if !p.club_folded.contains(q.as_str()) {
                    return false;
                }
            }
            if let Some(q) = &pos_q {
                let pos = p.position.to_uppercase();
                let matched = match q.as_str() {
                    // Friendly groups in addition to exact FIFA codes.
                    "FORWARD" | "ATTACKER" | "STRIKER" => {
                        ["ST", "CF", "LF", "RF", "LW", "RW", "LS", "RS"].contains(&pos.as_str())
                    }
                    "MIDFIELDER" => pos.ends_with('M') && pos != "GK",
                    "DEFENDER" => pos.ends_with('B') && pos != "GK",
                    "GOALKEEPER" => pos == "GK",
                    exact => pos == exact,
                };
                if !matched {
                    return false;
                }
            }
            if let Some(min) = filter.min_overall {
                if p.overall < min {
                    return false;
                }
            }
            true
        })
        .collect();
    match sort_by {
        "potential" => found.sort_by(|a, b| b.potential.cmp(&a.potential).then(a.name.cmp(&b.name))),
        "age" => found.sort_by(|a, b| a.age.cmp(&b.age).then(a.name.cmp(&b.name))),
        "name" => found.sort_by(|a, b| a.name.cmp(&b.name)),
        _ => found.sort_by(|a, b| b.overall.cmp(&a.overall).then(a.name.cmp(&b.name))),
    }
    found
}

pub fn format_players(players: &[&Player], limit: usize) -> String {
    if players.is_empty() {
        return "No players found for those criteria.".into();
    }
    let mut out = String::new();
    for (i, p) in players.iter().take(limit).enumerate() {
        let club = if p.club.is_empty() { "Free agent" } else { &p.club };
        let _ = writeln!(
            out,
            "{}. {} - Overall: {}, Position: {}, Age: {}, Nationality: {}, Club: {}",
            i + 1,
            p.name,
            p.overall,
            if p.position.is_empty() { "?" } else { &p.position },
            p.age.map(|a| a.to_string()).unwrap_or_else(|| "?".into()),
            p.nationality,
            club
        );
    }
    if players.len() > limit {
        let _ = writeln!(out, "... ({} more players match)", players.len() - limit);
    }
    out
}

/// Detailed card for the best name match.
pub fn player_info(store: &Store, name: &str) -> String {
    let filter = PlayerFilter {
        name: Some(name.to_string()),
        ..Default::default()
    };
    let found = find_players(store, &filter, "overall");
    let Some(p) = found.first() else {
        return format!("No player matching \"{}\" found in the FIFA dataset.", name);
    };
    let mut out = format!("{} (FIFA ID {})\n", p.name, p.id);
    let _ = writeln!(
        out,
        "- Age: {}, Nationality: {}",
        p.age.map(|a| a.to_string()).unwrap_or_else(|| "?".into()),
        p.nationality
    );
    let _ = writeln!(out, "- Overall: {}, Potential: {}", p.overall, p.potential);
    let _ = writeln!(
        out,
        "- Club: {}, Position: {}, Jersey: {}",
        if p.club.is_empty() { "Free agent" } else { &p.club },
        if p.position.is_empty() { "?" } else { &p.position },
        p.jersey_number
            .map(|j| j.to_string())
            .unwrap_or_else(|| "?".into())
    );
    let _ = writeln!(
        out,
        "- Height: {}, Weight: {}, Preferred foot: {}",
        p.height, p.weight, p.preferred_foot
    );
    let _ = writeln!(out, "- Value: {}, Wage: {}", p.value, p.wage);
    if !p.skills.is_empty() {
        let skills: Vec<String> = p
            .skills
            .iter()
            .map(|(k, v)| format!("{} {}", k, v))
            .collect();
        let _ = writeln!(out, "- Key attributes: {}", skills.join(", "));
    }
    if found.len() > 1 {
        let others: Vec<&str> = found.iter().skip(1).take(5).map(|p| p.name.as_str()).collect();
        let _ = writeln!(out, "\nOther name matches: {}", others.join(", "));
    }
    out
}

/// Summary of everything that is loaded (competitions, seasons, counts).
pub fn list_competitions(store: &Store) -> String {
    let mut by_comp: HashMap<&str, (usize, i32, i32)> = HashMap::new();
    for m in &store.matches {
        let e = by_comp.entry(m.competition).or_insert((0, i32::MAX, i32::MIN));
        e.0 += 1;
        if m.season > 0 {
            e.1 = e.1.min(m.season);
            e.2 = e.2.max(m.season);
        }
    }
    let mut comps: Vec<(&str, (usize, i32, i32))> = by_comp.into_iter().collect();
    comps.sort_by_key(|(_, (count, _, _))| std::cmp::Reverse(*count));
    let mut out = String::from("Loaded competitions (after cross-file deduplication):\n");
    for (comp, (count, min_s, max_s)) in comps {
        let _ = writeln!(out, "- {}: {} matches, seasons {}-{}", comp, count, min_s, max_s);
    }
    let _ = writeln!(
        out,
        "\nTotal: {} unique matches, {} players.",
        store.matches.len(),
        store.players.len()
    );
    out.push_str("\nSource files:\n");
    for (name, count) in &store.raw_counts {
        let _ = writeln!(out, "- {}: {} rows", name, count);
    }
    let _ = writeln!(out, "- fifa_data.csv: {} rows", store.players.len());
    out
}
