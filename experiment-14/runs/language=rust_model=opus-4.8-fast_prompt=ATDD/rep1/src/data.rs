//! Data store: loads the six provided CSV datasets into memory once at startup
//! and exposes them as plain `Vec`s for the query tools to scan.
//!
//! Matches from every file are unified into a single `Match` shape and
//! de-duplicated, so the same Brasileirão fixture appearing in several source
//! files is counted once.

use std::collections::HashSet;
use std::path::{Path, PathBuf};

use crate::model::{Match, Player};

pub struct DataStore {
    pub matches: Vec<Match>,
    pub players: Vec<Player>,
}

/// Parse a goal value that may be "2", "2.0" or quoted.
fn parse_goal(s: &str) -> Option<i32> {
    let s = s.trim().trim_matches('"');
    if s.is_empty() {
        return None;
    }
    if let Ok(i) = s.parse::<i32>() {
        return Some(i);
    }
    s.parse::<f64>().ok().map(|f| f.round() as i32)
}

fn parse_int(s: &str) -> i32 {
    let s = s.trim().trim_matches('"');
    s.parse::<i32>()
        .or_else(|_| s.parse::<f64>().map(|f| f.round() as i32))
        .unwrap_or(0)
}

/// Map a header row to a name -> index lookup, stripping BOM/quotes/whitespace.
fn header_index(headers: &csv::StringRecord) -> std::collections::HashMap<String, usize> {
    headers
        .iter()
        .enumerate()
        .map(|(i, h)| {
            let clean = h.trim_start_matches('\u{feff}').trim().trim_matches('"').to_string();
            (clean, i)
        })
        .collect()
}

impl DataStore {
    pub fn load(dir: &Path) -> Result<Self, String> {
        let mut matches: Vec<Match> = Vec::new();
        let mut seen: HashSet<(String, i32, String, String)> = HashSet::new();

        let mut push = |m: Match, matches: &mut Vec<Match>| {
            // Skip rows with no usable goals (would corrupt aggregates).
            if seen.insert(m.dedup_key()) {
                matches.push(m);
            }
        };

        // Order matters: the first file to contribute a given fixture wins, so
        // the authoritative historical Brasileirão source (novo, 2003-2019) is
        // loaded before the overlapping files.
        Self::load_novo(dir, &mut push, &mut matches)?;
        Self::load_brasileirao(dir, &mut push, &mut matches)?;
        Self::load_cup(dir, &mut push, &mut matches)?;
        Self::load_libertadores(dir, &mut push, &mut matches)?;
        Self::load_br_football(dir, &mut push, &mut matches)?;

        let players = Self::load_players(dir)?;

        if matches.is_empty() {
            return Err("no matches were loaded from the data directory".into());
        }
        Ok(DataStore { matches, players })
    }

    fn reader(path: &PathBuf) -> Result<csv::Reader<std::fs::File>, String> {
        csv::ReaderBuilder::new()
            .flexible(true)
            .has_headers(true)
            .from_path(path)
            .map_err(|e| format!("failed to open {}: {e}", path.display()))
    }

    fn load_brasileirao(
        dir: &Path,
        push: &mut impl FnMut(Match, &mut Vec<Match>),
        matches: &mut Vec<Match>,
    ) -> Result<(), String> {
        let path = dir.join("Brasileirao_Matches.csv");
        let mut rdr = Self::reader(&path)?;
        let h = header_index(rdr.headers().map_err(|e| e.to_string())?);
        let get = |r: &csv::StringRecord, k: &str| h.get(k).and_then(|&i| r.get(i)).unwrap_or("").to_string();
        for rec in rdr.records() {
            let r = rec.map_err(|e| e.to_string())?;
            let (hg, ag) = match (parse_goal(&get(&r, "home_goal")), parse_goal(&get(&r, "away_goal"))) {
                (Some(a), Some(b)) => (a, b),
                _ => continue,
            };
            let round = Some(get(&r, "round")).filter(|s| !s.is_empty());
            push(
                Match::new(
                    "Brasileirão",
                    parse_int(&get(&r, "season")),
                    round,
                    None,
                    &get(&r, "datetime"),
                    &get(&r, "home_team"),
                    &get(&r, "away_team"),
                    hg,
                    ag,
                ),
                matches,
            );
        }
        Ok(())
    }

    fn load_novo(
        dir: &Path,
        push: &mut impl FnMut(Match, &mut Vec<Match>),
        matches: &mut Vec<Match>,
    ) -> Result<(), String> {
        let path = dir.join("novo_campeonato_brasileiro.csv");
        let mut rdr = Self::reader(&path)?;
        let h = header_index(rdr.headers().map_err(|e| e.to_string())?);
        let get = |r: &csv::StringRecord, k: &str| h.get(k).and_then(|&i| r.get(i)).unwrap_or("").to_string();
        for rec in rdr.records() {
            let r = rec.map_err(|e| e.to_string())?;
            let (hg, ag) = match (parse_goal(&get(&r, "Gols_mandante")), parse_goal(&get(&r, "Gols_visitante"))) {
                (Some(a), Some(b)) => (a, b),
                _ => continue,
            };
            let round = Some(get(&r, "Rodada")).filter(|s| !s.is_empty());
            push(
                Match::new(
                    "Brasileirão",
                    parse_int(&get(&r, "Ano")),
                    round,
                    None,
                    &get(&r, "Data"),
                    &get(&r, "Equipe_mandante"),
                    &get(&r, "Equipe_visitante"),
                    hg,
                    ag,
                ),
                matches,
            );
        }
        Ok(())
    }

    fn load_cup(
        dir: &Path,
        push: &mut impl FnMut(Match, &mut Vec<Match>),
        matches: &mut Vec<Match>,
    ) -> Result<(), String> {
        let path = dir.join("Brazilian_Cup_Matches.csv");
        let mut rdr = Self::reader(&path)?;
        let h = header_index(rdr.headers().map_err(|e| e.to_string())?);
        let get = |r: &csv::StringRecord, k: &str| h.get(k).and_then(|&i| r.get(i)).unwrap_or("").to_string();
        for rec in rdr.records() {
            let r = rec.map_err(|e| e.to_string())?;
            let (hg, ag) = match (parse_goal(&get(&r, "home_goal")), parse_goal(&get(&r, "away_goal"))) {
                (Some(a), Some(b)) => (a, b),
                _ => continue,
            };
            let round = Some(get(&r, "round")).filter(|s| !s.is_empty());
            push(
                Match::new(
                    "Copa do Brasil",
                    parse_int(&get(&r, "season")),
                    round.clone(),
                    round, // cup round doubles as the stage
                    &get(&r, "datetime"),
                    &get(&r, "home_team"),
                    &get(&r, "away_team"),
                    hg,
                    ag,
                ),
                matches,
            );
        }
        Ok(())
    }

    fn load_libertadores(
        dir: &Path,
        push: &mut impl FnMut(Match, &mut Vec<Match>),
        matches: &mut Vec<Match>,
    ) -> Result<(), String> {
        let path = dir.join("Libertadores_Matches.csv");
        let mut rdr = Self::reader(&path)?;
        let h = header_index(rdr.headers().map_err(|e| e.to_string())?);
        let get = |r: &csv::StringRecord, k: &str| h.get(k).and_then(|&i| r.get(i)).unwrap_or("").to_string();
        for rec in rdr.records() {
            let r = rec.map_err(|e| e.to_string())?;
            let (hg, ag) = match (parse_goal(&get(&r, "home_goal")), parse_goal(&get(&r, "away_goal"))) {
                (Some(a), Some(b)) => (a, b),
                _ => continue,
            };
            let stage = Some(get(&r, "stage")).filter(|s| !s.is_empty());
            push(
                Match::new(
                    "Copa Libertadores",
                    parse_int(&get(&r, "season")),
                    None,
                    stage,
                    &get(&r, "datetime"),
                    &get(&r, "home_team"),
                    &get(&r, "away_team"),
                    hg,
                    ag,
                ),
                matches,
            );
        }
        Ok(())
    }

    fn load_br_football(
        dir: &Path,
        push: &mut impl FnMut(Match, &mut Vec<Match>),
        matches: &mut Vec<Match>,
    ) -> Result<(), String> {
        let path = dir.join("BR-Football-Dataset.csv");
        let mut rdr = Self::reader(&path)?;
        let h = header_index(rdr.headers().map_err(|e| e.to_string())?);
        let get = |r: &csv::StringRecord, k: &str| h.get(k).and_then(|&i| r.get(i)).unwrap_or("").to_string();
        for rec in rdr.records() {
            let r = rec.map_err(|e| e.to_string())?;
            let (hg, ag) = match (parse_goal(&get(&r, "home_goal")), parse_goal(&get(&r, "away_goal"))) {
                (Some(a), Some(b)) => (a, b),
                _ => continue,
            };
            let competition = match get(&r, "tournament").as_str() {
                "Serie A" => "Brasileirão".to_string(),
                "Serie B" => "Brasileirão Série B".to_string(),
                "Serie C" => "Brasileirão Série C".to_string(),
                "Copa do Brasil" => "Copa do Brasil".to_string(),
                // Keep any unexpected tournament name verbatim.
                other => other.to_string(),
            };
            let date = get(&r, "date");
            let season = crate::normalize::parse_date(&date).map(|(_, y)| y).unwrap_or(0);
            push(
                Match::new(
                    &competition,
                    season,
                    None,
                    None,
                    &date,
                    &get(&r, "home"),
                    &get(&r, "away"),
                    hg,
                    ag,
                ),
                matches,
            );
        }
        Ok(())
    }

    fn load_players(dir: &Path) -> Result<Vec<Player>, String> {
        let path = dir.join("fifa_data.csv");
        let mut rdr = Self::reader(&path)?;
        let h = header_index(rdr.headers().map_err(|e| e.to_string())?);
        let get = |r: &csv::StringRecord, k: &str| h.get(k).and_then(|&i| r.get(i)).unwrap_or("").to_string();
        let mut players = Vec::new();
        for rec in rdr.records() {
            let r = rec.map_err(|e| e.to_string())?;
            let name = get(&r, "Name");
            if name.trim().is_empty() {
                continue;
            }
            players.push(Player {
                name,
                age: parse_int(&get(&r, "Age")),
                nationality: get(&r, "Nationality"),
                overall: parse_int(&get(&r, "Overall")),
                potential: parse_int(&get(&r, "Potential")),
                club: get(&r, "Club"),
                position: get(&r, "Position"),
                jersey_number: get(&r, "Jersey Number"),
                height: get(&r, "Height"),
                weight: get(&r, "Weight"),
            });
        }
        Ok(players)
    }
}
