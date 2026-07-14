//! ============================================================================
//! Module: loader
//!
//! Context
//! -------
//! Reads the six provided Kaggle CSV files into the in-memory domain model.
//! Each file has a different schema, so a dedicated parser per file maps its
//! columns onto the common `Match` / `Player` types. Loading is tolerant: a
//! malformed row is skipped rather than aborting the whole import, so a single
//! bad record never takes the server down.
//!
//! Files handled (source CSV -> competition):
//!   Brasileirao_Matches.csv          Brasileirão Série A
//!   Brazilian_Cup_Matches.csv        Copa do Brasil
//!   Libertadores_Matches.csv         Copa Libertadores
//!   BR-Football-Dataset.csv          Série B / Série C (+ extended stats)
//!   novo_campeonato_brasileiro.csv   Brasileirão Série A (historical 2003-2019)
//!   fifa_data.csv                    FIFA player database
//! ============================================================================

use std::collections::HashMap;
use std::path::Path;

use csv::StringRecord;

use crate::model::{Match, MatchExtras, Player};
use crate::normalize::{search_key, team_key};

/// Convert the various source date formats into a plain `YYYY-MM-DD` string.
///
/// Handles:
///   * "2019-10-27 18:30:00" / "2019-10-27" (ISO, optional time) -> "2019-10-27"
///   * "29/03/2003"          (Brazilian DD/MM/YYYY)              -> "2003-03-29"
pub fn normalize_date(raw: &str) -> String {
    let raw = raw.trim();
    if raw.is_empty() {
        return String::new();
    }
    // Strip a trailing time component.
    let date_part = raw.split_whitespace().next().unwrap_or(raw);

    if date_part.contains('/') {
        let parts: Vec<&str> = date_part.split('/').collect();
        if parts.len() == 3 {
            let (d, m, y) = (parts[0], parts[1], parts[2]);
            // DD/MM/YYYY
            if y.len() == 4 {
                return format!("{}-{:0>2}-{:0>2}", y, m, d);
            }
        }
        return date_part.to_string();
    }
    date_part.to_string()
}

/// Parse an integer-like field that may arrive quoted or as a float ("1.0").
fn parse_goals(s: &str) -> Option<i32> {
    let s = s.trim().trim_matches('"').trim();
    if s.is_empty() {
        return None;
    }
    if let Ok(v) = s.parse::<i32>() {
        return Some(v);
    }
    s.parse::<f64>().ok().map(|f| f.round() as i32)
}

fn parse_int(s: &str) -> Option<i32> {
    let s = s.trim().trim_matches('"').trim();
    if s.is_empty() {
        return None;
    }
    s.parse::<i32>().ok().or_else(|| s.parse::<f64>().ok().map(|f| f.round() as i32))
}

fn parse_float(s: &str) -> Option<f64> {
    let s = s.trim().trim_matches('"').trim();
    if s.is_empty() {
        return None;
    }
    s.parse::<f64>().ok()
}

/// Build a column-name -> index map from a CSV header record.
fn header_map(headers: &StringRecord) -> HashMap<String, usize> {
    headers
        .iter()
        .enumerate()
        .map(|(i, h)| (h.trim().trim_start_matches('\u{feff}').to_string(), i))
        .collect()
}

/// Fetch a trimmed, unquoted field by header name.
fn get<'a>(rec: &'a StringRecord, map: &HashMap<String, usize>, col: &str) -> &'a str {
    map.get(col)
        .and_then(|&i| rec.get(i))
        .map(|s| s.trim().trim_matches('"'))
        .unwrap_or("")
}

#[allow(clippy::too_many_arguments)]
fn make_match(
    competition: &str,
    season: i32,
    stage: String,
    date: String,
    home: &str,
    away: &str,
    home_goal: i32,
    away_goal: i32,
    source: &str,
    extras: MatchExtras,
) -> Match {
    Match {
        competition: competition.to_string(),
        season,
        stage,
        date,
        home_key: team_key(home),
        away_key: team_key(away),
        home_team: crate::normalize::display_name(home),
        away_team: crate::normalize::display_name(away),
        home_goal,
        away_goal,
        source: source.to_string(),
        extras,
    }
}

/// Open a CSV file with flexible record lengths and UTF-8 handling.
fn open_reader(path: &Path) -> std::io::Result<csv::Reader<std::fs::File>> {
    csv::ReaderBuilder::new()
        .flexible(true)
        .from_path(path)
        .map_err(|e| std::io::Error::other(e.to_string()))
}

/// Load Brasileirao_Matches.csv (round is a number) into matches.
fn load_brasileirao(path: &Path, out: &mut Vec<Match>) -> std::io::Result<usize> {
    let mut rdr = open_reader(path)?;
    let map = header_map(&rdr.headers().cloned().unwrap_or_default());
    let mut n = 0;
    let source = "Brasileirao_Matches.csv";
    for rec in rdr.records().flatten() {
        let (Some(hg), Some(ag)) = (parse_goals(get(&rec, &map, "home_goal")), parse_goals(get(&rec, &map, "away_goal"))) else { continue };
        let round = get(&rec, &map, "round");
        let stage = if round.is_empty() { String::new() } else { format!("Round {}", round) };
        out.push(make_match(
            "Brasileirão Série A",
            parse_int(get(&rec, &map, "season")).unwrap_or(0),
            stage,
            normalize_date(get(&rec, &map, "datetime")),
            get(&rec, &map, "home_team"),
            get(&rec, &map, "away_team"),
            hg,
            ag,
            source,
            MatchExtras::default(),
        ));
        n += 1;
    }
    Ok(n)
}

/// Load Brazilian_Cup_Matches.csv (Copa do Brasil).
fn load_cup(path: &Path, out: &mut Vec<Match>) -> std::io::Result<usize> {
    let mut rdr = open_reader(path)?;
    let map = header_map(&rdr.headers().cloned().unwrap_or_default());
    let mut n = 0;
    let source = "Brazilian_Cup_Matches.csv";
    for rec in rdr.records().flatten() {
        let (Some(hg), Some(ag)) = (parse_goals(get(&rec, &map, "home_goal")), parse_goals(get(&rec, &map, "away_goal"))) else { continue };
        let round = get(&rec, &map, "round");
        let stage = if round.is_empty() { String::new() } else { format!("Round {}", round) };
        out.push(make_match(
            "Copa do Brasil",
            parse_int(get(&rec, &map, "season")).unwrap_or(0),
            stage,
            normalize_date(get(&rec, &map, "datetime")),
            get(&rec, &map, "home_team"),
            get(&rec, &map, "away_team"),
            hg,
            ag,
            source,
            MatchExtras::default(),
        ));
        n += 1;
    }
    Ok(n)
}

/// Load Libertadores_Matches.csv (stage is a label).
fn load_libertadores(path: &Path, out: &mut Vec<Match>) -> std::io::Result<usize> {
    let mut rdr = open_reader(path)?;
    let map = header_map(&rdr.headers().cloned().unwrap_or_default());
    let mut n = 0;
    let source = "Libertadores_Matches.csv";
    for rec in rdr.records().flatten() {
        let (Some(hg), Some(ag)) = (parse_goals(get(&rec, &map, "home_goal")), parse_goals(get(&rec, &map, "away_goal"))) else { continue };
        out.push(make_match(
            "Copa Libertadores",
            parse_int(get(&rec, &map, "season")).unwrap_or(0),
            get(&rec, &map, "stage").to_string(),
            normalize_date(get(&rec, &map, "datetime")),
            get(&rec, &map, "home_team"),
            get(&rec, &map, "away_team"),
            hg,
            ag,
            source,
            MatchExtras::default(),
        ));
        n += 1;
    }
    Ok(n)
}

/// Load BR-Football-Dataset.csv (tournament column + extended stats).
fn load_br_football(path: &Path, out: &mut Vec<Match>) -> std::io::Result<usize> {
    let mut rdr = open_reader(path)?;
    let map = header_map(&rdr.headers().cloned().unwrap_or_default());
    let mut n = 0;
    let source = "BR-Football-Dataset.csv";
    for rec in rdr.records().flatten() {
        let (Some(hg), Some(ag)) = (parse_goals(get(&rec, &map, "home_goal")), parse_goals(get(&rec, &map, "away_goal"))) else { continue };
        // Série A and Copa do Brasil are already covered authoritatively by the
        // dedicated files (Brasileirao_Matches / Brazilian_Cup_Matches) with
        // consistent team names and dates. This file's copies of them use
        // divergent names/dates and would double-count, so we load only its
        // UNIQUE competitions — Série B and Série C — from here. The extended
        // shot/corner stats it carries come along for those divisions.
        let tournament = get(&rec, &map, "tournament");
        let competition = match tournament {
            "Serie B" => "Brasileirão Série B".to_string(),
            "Serie C" => "Brasileirão Série C".to_string(),
            _ => continue,
        };
        let date = normalize_date(get(&rec, &map, "date"));
        let season = date.split('-').next().and_then(|y| y.parse::<i32>().ok()).unwrap_or(0);
        let extras = MatchExtras {
            home_shots: parse_float(get(&rec, &map, "home_shots")),
            away_shots: parse_float(get(&rec, &map, "away_shots")),
            home_corner: parse_float(get(&rec, &map, "home_corner")),
            away_corner: parse_float(get(&rec, &map, "away_corner")),
            total_corners: parse_float(get(&rec, &map, "total_corners")),
        };
        out.push(make_match(
            &competition,
            season,
            String::new(),
            date,
            get(&rec, &map, "home"),
            get(&rec, &map, "away"),
            hg,
            ag,
            source,
            extras,
        ));
        n += 1;
    }
    Ok(n)
}

/// Load novo_campeonato_brasileiro.csv (historical Brasileirão 2003-2019).
fn load_novo(path: &Path, out: &mut Vec<Match>) -> std::io::Result<usize> {
    let mut rdr = open_reader(path)?;
    let map = header_map(&rdr.headers().cloned().unwrap_or_default());
    let mut n = 0;
    let source = "novo_campeonato_brasileiro.csv";
    for rec in rdr.records().flatten() {
        let (Some(hg), Some(ag)) = (parse_goals(get(&rec, &map, "Gols_mandante")), parse_goals(get(&rec, &map, "Gols_visitante"))) else { continue };
        let round = get(&rec, &map, "Rodada");
        let stage = if round.is_empty() { String::new() } else { format!("Round {}", round) };
        out.push(make_match(
            "Brasileirão Série A",
            parse_int(get(&rec, &map, "Ano")).unwrap_or(0),
            stage,
            normalize_date(get(&rec, &map, "Data")),
            get(&rec, &map, "Equipe_mandante"),
            get(&rec, &map, "Equipe_visitante"),
            hg,
            ag,
            source,
            MatchExtras::default(),
        ));
        n += 1;
    }
    Ok(n)
}

/// Load fifa_data.csv into the player list.
fn load_players(path: &Path, out: &mut Vec<Player>) -> std::io::Result<usize> {
    let mut rdr = open_reader(path)?;
    let map = header_map(&rdr.headers().cloned().unwrap_or_default());
    let mut n = 0;
    for rec in rdr.records().flatten() {
        let name = get(&rec, &map, "Name");
        if name.is_empty() {
            continue;
        }
        let nationality = get(&rec, &map, "Nationality");
        let club = get(&rec, &map, "Club");
        out.push(Player {
            id: get(&rec, &map, "ID").to_string(),
            age: parse_int(get(&rec, &map, "Age")),
            overall: parse_int(get(&rec, &map, "Overall")),
            potential: parse_int(get(&rec, &map, "Potential")),
            position: get(&rec, &map, "Position").to_string(),
            jersey: get(&rec, &map, "Jersey Number").to_string(),
            height: get(&rec, &map, "Height").to_string(),
            weight: get(&rec, &map, "Weight").to_string(),
            name_key: search_key(name),
            nationality_key: search_key(nationality),
            club_key: search_key(club),
            name: name.to_string(),
            nationality: nationality.to_string(),
            club: club.to_string(),
        });
        n += 1;
    }
    Ok(n)
}

/// Summary of what was loaded, returned by [`load_all`].
#[derive(Debug, Default, Clone)]
pub struct LoadReport {
    pub matches: usize,
    pub players: usize,
    pub files_loaded: Vec<String>,
    pub files_missing: Vec<String>,
}

/// Load every dataset found under `data_dir` into `matches`/`players`.
///
/// Missing files are recorded but do not cause an error, so the server can run
/// against a partial dataset (useful for tests with fixture subsets).
pub fn load_all(data_dir: &Path, matches: &mut Vec<Match>, players: &mut Vec<Player>) -> LoadReport {
    let mut report = LoadReport::default();

    type MatchLoader = fn(&Path, &mut Vec<Match>) -> std::io::Result<usize>;
    let match_files: &[(&str, MatchLoader)] = &[
        ("Brasileirao_Matches.csv", load_brasileirao),
        ("Brazilian_Cup_Matches.csv", load_cup),
        ("Libertadores_Matches.csv", load_libertadores),
        ("BR-Football-Dataset.csv", load_br_football),
        ("novo_campeonato_brasileiro.csv", load_novo),
    ];

    for (file, loader) in match_files {
        let path = data_dir.join(file);
        if !path.exists() {
            report.files_missing.push(file.to_string());
            continue;
        }
        match loader(&path, matches) {
            Ok(n) => {
                report.matches += n;
                report.files_loaded.push(file.to_string());
            }
            Err(e) => {
                eprintln!("warning: failed to load {}: {}", file, e);
                report.files_missing.push(file.to_string());
            }
        }
    }

    let fifa = data_dir.join("fifa_data.csv");
    if fifa.exists() {
        match load_players(&fifa, players) {
            Ok(n) => {
                report.players += n;
                report.files_loaded.push("fifa_data.csv".to_string());
            }
            Err(e) => {
                eprintln!("warning: failed to load fifa_data.csv: {}", e);
                report.files_missing.push("fifa_data.csv".to_string());
            }
        }
    } else {
        report.files_missing.push("fifa_data.csv".to_string());
    }

    report
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn brazilian_date_is_reordered() {
        assert_eq!(normalize_date("29/03/2003"), "2003-03-29");
    }

    #[test]
    fn iso_datetime_drops_time() {
        assert_eq!(normalize_date("2012-05-19 18:30:00"), "2012-05-19");
        assert_eq!(normalize_date("2023-09-24"), "2023-09-24");
    }

    #[test]
    fn goals_parse_from_quoted_and_float() {
        assert_eq!(parse_goals("\"2\""), Some(2));
        assert_eq!(parse_goals("1.0"), Some(1));
        assert_eq!(parse_goals(""), None);
    }
}
