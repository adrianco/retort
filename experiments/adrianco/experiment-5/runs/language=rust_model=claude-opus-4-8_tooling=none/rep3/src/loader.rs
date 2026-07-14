//! ============================================================================
//! Module: loader
//! Project: Brazilian Soccer MCP Server (Rust)
//!
//! Context:
//!   Reads the six provided CSV files from `data/kaggle/` and converts each row
//!   into the normalized `Match` / `Player` domain types. Each source file has
//!   its own quirks that are handled here:
//!     - Brasileirao_Matches.csv  : team names carry "-UF" suffix, int goals.
//!     - Brazilian_Cup_Matches.csv: long club names, no state column.
//!     - Libertadores_Matches.csv : goals are quoted strings, has `stage`.
//!     - BR-Football-Dataset.csv  : goals are floats ("1.0"), `tournament`
//!                                  column distinguishes Serie A/B/C & Cup.
//!     - novo_campeonato_brasileiro.csv : Portuguese headers, DD/MM/YYYY dates.
//!     - fifa_data.csv            : 89-column player table; we keep a subset.
//!
//!   Parsing is deliberately lenient: a row that fails to parse a numeric field
//!   is skipped rather than aborting the whole load, so a few dirty rows never
//!   take down the server. Goal fields are parsed via `parse_goal` which copes
//!   with ints, floats and quoted values.
//! ============================================================================

use crate::model::{Competition, Match, Player};
use crate::normalize::{normalize_date, normalize_team};
use std::error::Error;
use std::path::Path;

/// Parse a goal count that may be an int ("2"), float ("2.0") or empty.
fn parse_goal(s: &str) -> Option<i32> {
    let t = s.trim();
    if t.is_empty() {
        return None;
    }
    if let Ok(i) = t.parse::<i32>() {
        return Some(i);
    }
    t.parse::<f64>().ok().map(|f| f.round() as i32)
}

fn parse_season(s: &str) -> Option<i32> {
    s.trim().parse::<i32>().ok()
}

/// Build a CSV reader for a path with flexible field counts.
fn reader(path: &Path) -> Result<csv::Reader<std::fs::File>, Box<dyn Error>> {
    let rdr = csv::ReaderBuilder::new()
        .has_headers(true)
        .flexible(true)
        .from_path(path)?;
    Ok(rdr)
}

/// Map header names to indices for robust, order-independent access.
fn header_index(headers: &csv::StringRecord) -> std::collections::HashMap<String, usize> {
    headers
        .iter()
        .enumerate()
        .map(|(i, h)| (h.trim().trim_start_matches('\u{feff}').to_lowercase(), i))
        .collect()
}

fn get<'a>(rec: &'a csv::StringRecord, idx: &std::collections::HashMap<String, usize>, key: &str) -> &'a str {
    idx.get(key).and_then(|&i| rec.get(i)).unwrap_or("").trim()
}

/// Load the Brasileirão Serie A matches file.
pub fn load_brasileirao(path: &Path) -> Result<Vec<Match>, Box<dyn Error>> {
    let mut rdr = reader(path)?;
    let idx = header_index(rdr.headers()?);
    let mut out = Vec::new();
    for rec in rdr.records() {
        let rec = rec?;
        let (h, a) = (get(&rec, &idx, "home_team"), get(&rec, &idx, "away_team"));
        let (hg, ag) = (
            parse_goal(get(&rec, &idx, "home_goal")),
            parse_goal(get(&rec, &idx, "away_goal")),
        );
        if h.is_empty() || a.is_empty() {
            continue;
        }
        let (hg, ag) = match (hg, ag) {
            (Some(x), Some(y)) => (x, y),
            _ => continue,
        };
        let date = normalize_date(get(&rec, &idx, "datetime"));
        let round = get(&rec, &idx, "round");
        out.push(Match {
            competition: Competition::Brasileirao,
            date,
            home_team: normalize_team(h),
            away_team: normalize_team(a),
            home_team_raw: h.to_string(),
            away_team_raw: a.to_string(),
            home_goal: hg,
            away_goal: ag,
            season: parse_season(get(&rec, &idx, "season")),
            round: if round.is_empty() { None } else { Some(round.to_string()) },
            source: "Brasileirao_Matches.csv",
        });
    }
    Ok(out)
}

/// Load the Copa do Brasil matches file.
pub fn load_cup(path: &Path) -> Result<Vec<Match>, Box<dyn Error>> {
    let mut rdr = reader(path)?;
    let idx = header_index(rdr.headers()?);
    let mut out = Vec::new();
    for rec in rdr.records() {
        let rec = rec?;
        let (h, a) = (get(&rec, &idx, "home_team"), get(&rec, &idx, "away_team"));
        let (hg, ag) = match (
            parse_goal(get(&rec, &idx, "home_goal")),
            parse_goal(get(&rec, &idx, "away_goal")),
        ) {
            (Some(x), Some(y)) => (x, y),
            _ => continue,
        };
        if h.is_empty() || a.is_empty() {
            continue;
        }
        let round = get(&rec, &idx, "round");
        out.push(Match {
            competition: Competition::CopaDoBrasil,
            date: normalize_date(get(&rec, &idx, "datetime")),
            home_team: normalize_team(h),
            away_team: normalize_team(a),
            home_team_raw: h.to_string(),
            away_team_raw: a.to_string(),
            home_goal: hg,
            away_goal: ag,
            season: parse_season(get(&rec, &idx, "season")),
            round: if round.is_empty() { None } else { Some(round.to_string()) },
            source: "Brazilian_Cup_Matches.csv",
        });
    }
    Ok(out)
}

/// Load the Copa Libertadores matches file (goals quoted, has `stage`).
pub fn load_libertadores(path: &Path) -> Result<Vec<Match>, Box<dyn Error>> {
    let mut rdr = reader(path)?;
    let idx = header_index(rdr.headers()?);
    let mut out = Vec::new();
    for rec in rdr.records() {
        let rec = rec?;
        let (h, a) = (get(&rec, &idx, "home_team"), get(&rec, &idx, "away_team"));
        let (hg, ag) = match (
            parse_goal(get(&rec, &idx, "home_goal")),
            parse_goal(get(&rec, &idx, "away_goal")),
        ) {
            (Some(x), Some(y)) => (x, y),
            _ => continue,
        };
        if h.is_empty() || a.is_empty() {
            continue;
        }
        let stage = get(&rec, &idx, "stage");
        out.push(Match {
            competition: Competition::Libertadores,
            date: normalize_date(get(&rec, &idx, "datetime")),
            home_team: normalize_team(h),
            away_team: normalize_team(a),
            home_team_raw: h.to_string(),
            away_team_raw: a.to_string(),
            home_goal: hg,
            away_goal: ag,
            season: parse_season(get(&rec, &idx, "season")),
            round: if stage.is_empty() { None } else { Some(stage.to_string()) },
            source: "Libertadores_Matches.csv",
        });
    }
    Ok(out)
}

/// Load the extended BR-Football statistics file (float goals, `tournament`).
pub fn load_br_football(path: &Path) -> Result<Vec<Match>, Box<dyn Error>> {
    let mut rdr = reader(path)?;
    let idx = header_index(rdr.headers()?);
    let mut out = Vec::new();
    for rec in rdr.records() {
        let rec = rec?;
        let (h, a) = (get(&rec, &idx, "home"), get(&rec, &idx, "away"));
        let (hg, ag) = match (
            parse_goal(get(&rec, &idx, "home_goal")),
            parse_goal(get(&rec, &idx, "away_goal")),
        ) {
            (Some(x), Some(y)) => (x, y),
            _ => continue,
        };
        if h.is_empty() || a.is_empty() {
            continue;
        }
        let tournament = get(&rec, &idx, "tournament");
        let date = normalize_date(get(&rec, &idx, "date"));
        out.push(Match {
            competition: Competition::from_text(tournament),
            season: date.split('-').next().and_then(|y| y.parse().ok()),
            date,
            home_team: normalize_team(h),
            away_team: normalize_team(a),
            home_team_raw: h.to_string(),
            away_team_raw: a.to_string(),
            home_goal: hg,
            away_goal: ag,
            round: None,
            source: "BR-Football-Dataset.csv",
        });
    }
    Ok(out)
}

/// Load the historical Brasileirão 2003-2019 file (Portuguese headers).
pub fn load_novo(path: &Path) -> Result<Vec<Match>, Box<dyn Error>> {
    let mut rdr = reader(path)?;
    let idx = header_index(rdr.headers()?);
    let mut out = Vec::new();
    for rec in rdr.records() {
        let rec = rec?;
        let h = get(&rec, &idx, "equipe_mandante");
        let a = get(&rec, &idx, "equipe_visitante");
        let (hg, ag) = match (
            parse_goal(get(&rec, &idx, "gols_mandante")),
            parse_goal(get(&rec, &idx, "gols_visitante")),
        ) {
            (Some(x), Some(y)) => (x, y),
            _ => continue,
        };
        if h.is_empty() || a.is_empty() {
            continue;
        }
        let round = get(&rec, &idx, "rodada");
        out.push(Match {
            competition: Competition::Brasileirao,
            date: normalize_date(get(&rec, &idx, "data")),
            home_team: normalize_team(h),
            away_team: normalize_team(a),
            home_team_raw: h.to_string(),
            away_team_raw: a.to_string(),
            home_goal: hg,
            away_goal: ag,
            season: parse_season(get(&rec, &idx, "ano")),
            round: if round.is_empty() { None } else { Some(round.to_string()) },
            source: "novo_campeonato_brasileiro.csv",
        });
    }
    Ok(out)
}

/// Load the FIFA player database (keep a useful subset of columns).
pub fn load_players(path: &Path) -> Result<Vec<Player>, Box<dyn Error>> {
    let mut rdr = reader(path)?;
    let idx = header_index(rdr.headers()?);
    let mut out = Vec::new();
    for rec in rdr.records() {
        let rec = rec?;
        let name = get(&rec, &idx, "name");
        if name.is_empty() {
            continue;
        }
        let overall = get(&rec, &idx, "overall").parse::<i32>().unwrap_or(0);
        let potential = get(&rec, &idx, "potential").parse::<i32>().unwrap_or(overall);
        out.push(Player {
            id: get(&rec, &idx, "id").parse::<i64>().unwrap_or(0),
            name: name.to_string(),
            age: get(&rec, &idx, "age").parse::<i32>().ok(),
            nationality: get(&rec, &idx, "nationality").to_string(),
            overall,
            potential,
            club: get(&rec, &idx, "club").to_string(),
            position: get(&rec, &idx, "position").to_string(),
            jersey_number: get(&rec, &idx, "jersey number").parse::<i32>().ok(),
            height: get(&rec, &idx, "height").to_string(),
            weight: get(&rec, &idx, "weight").to_string(),
        });
    }
    Ok(out)
}
