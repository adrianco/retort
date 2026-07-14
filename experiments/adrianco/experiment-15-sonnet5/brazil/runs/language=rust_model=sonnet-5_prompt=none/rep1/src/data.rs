//! CSV loaders for the six provided Kaggle datasets.
//!
//! Every loader is defensive: a malformed row is logged and skipped rather
//! than aborting the whole load, since these are hand-curated public
//! datasets with occasional gaps (missing scores, stray encoding issues).

use std::collections::HashMap;
use std::path::Path;

use anyhow::{Context, Result};
use csv::StringRecord;

use crate::model::{MatchRecord, Player};
use crate::normalize::{extract_state_suffix, normalize_team_name, parse_flexible_date, parse_goal};

/// Maps CSV header name -> column index, so rows can be read by name
/// instead of brittle positional indexing.
struct Header(HashMap<String, usize>);

impl Header {
    fn from_record(record: StringRecord) -> Self {
        let mut map = HashMap::new();
        for (i, name) in record.iter().enumerate() {
            // Strip a UTF-8 BOM that shows up on the first header of some files.
            let clean = name.trim_start_matches('\u{feff}').trim();
            map.insert(clean.to_string(), i);
        }
        Header(map)
    }

    fn get<'a>(&self, record: &'a StringRecord, name: &str) -> &'a str {
        self.0
            .get(name)
            .and_then(|&i| record.get(i))
            .unwrap_or("")
            .trim()
    }
}

fn open_reader(path: &Path) -> Result<csv::Reader<std::fs::File>> {
    csv::ReaderBuilder::new()
        .flexible(true)
        .from_path(path)
        .with_context(|| format!("opening {}", path.display()))
}

/// Team name plus, when the source dataset embeds one, its two-letter
/// state code (e.g. "Atletico-MG" -> key "atletico", state "MG").
struct TeamPair {
    home_key: String,
    away_key: String,
    home_state: Option<String>,
    away_state: Option<String>,
}

fn team_pair_stateful(home: &str, away: &str) -> TeamPair {
    TeamPair {
        home_key: normalize_team_name(home),
        away_key: normalize_team_name(away),
        home_state: extract_state_suffix(home),
        away_state: extract_state_suffix(away),
    }
}

fn team_pair_stateless(home: &str, away: &str) -> TeamPair {
    TeamPair {
        home_key: normalize_team_name(home),
        away_key: normalize_team_name(away),
        home_state: None,
        away_state: None,
    }
}

/// `Brasileirao_Matches.csv`
pub fn load_brasileirao(path: &Path) -> Result<Vec<MatchRecord>> {
    let mut reader = open_reader(path)?;
    let header = Header::from_record(reader.headers()?.clone());
    let mut out = Vec::new();
    for result in reader.records() {
        let Ok(record) = result else { continue };
        let home = header.get(&record, "home_team");
        let away = header.get(&record, "away_team");
        if home.is_empty() || away.is_empty() {
            continue;
        }
        let teams = team_pair_stateful(home, away);
        let datetime = header.get(&record, "datetime");
        out.push(MatchRecord {
            source_file: "Brasileirao_Matches.csv",
            competition: "Brasileirao Serie A".to_string(),
            date: parse_flexible_date(datetime),
            date_display: datetime.to_string(),
            season: header.get(&record, "season").parse().ok(),
            round: non_empty(header.get(&record, "round")),
            stage: None,
            venue: None,
            home_team: home.to_string(),
            away_team: away.to_string(),
            home_identity: teams.home_key.clone(),
            away_identity: teams.away_key.clone(),
            home_team_key: teams.home_key,
            away_team_key: teams.away_key,
            home_state: teams.home_state,
            away_state: teams.away_state,
            home_goal: parse_goal(header.get(&record, "home_goal")),
            away_goal: parse_goal(header.get(&record, "away_goal")),
        });
    }
    Ok(out)
}

/// `Brazilian_Cup_Matches.csv`
pub fn load_cup(path: &Path) -> Result<Vec<MatchRecord>> {
    let mut reader = open_reader(path)?;
    let header = Header::from_record(reader.headers()?.clone());
    let mut out = Vec::new();
    for result in reader.records() {
        let Ok(record) = result else { continue };
        let home = header.get(&record, "home_team");
        let away = header.get(&record, "away_team");
        if home.is_empty() || away.is_empty() {
            continue;
        }
        let teams = team_pair_stateful(home, away);
        let datetime = header.get(&record, "datetime");
        out.push(MatchRecord {
            source_file: "Brazilian_Cup_Matches.csv",
            competition: "Copa do Brasil".to_string(),
            date: parse_flexible_date(datetime),
            date_display: datetime.to_string(),
            season: header.get(&record, "season").parse().ok(),
            round: non_empty(header.get(&record, "round")),
            stage: None,
            venue: None,
            home_team: home.to_string(),
            away_team: away.to_string(),
            home_identity: teams.home_key.clone(),
            away_identity: teams.away_key.clone(),
            home_team_key: teams.home_key,
            away_team_key: teams.away_key,
            home_state: teams.home_state,
            away_state: teams.away_state,
            home_goal: parse_goal(header.get(&record, "home_goal")),
            away_goal: parse_goal(header.get(&record, "away_goal")),
        });
    }
    Ok(out)
}

/// `Libertadores_Matches.csv`
pub fn load_libertadores(path: &Path) -> Result<Vec<MatchRecord>> {
    let mut reader = open_reader(path)?;
    let header = Header::from_record(reader.headers()?.clone());
    let mut out = Vec::new();
    for result in reader.records() {
        let Ok(record) = result else { continue };
        let home = header.get(&record, "home_team");
        let away = header.get(&record, "away_team");
        if home.is_empty() || away.is_empty() {
            continue;
        }
        let teams = team_pair_stateless(home, away);
        let datetime = header.get(&record, "datetime");
        out.push(MatchRecord {
            source_file: "Libertadores_Matches.csv",
            competition: "Copa Libertadores".to_string(),
            date: parse_flexible_date(datetime),
            date_display: datetime.to_string(),
            season: header.get(&record, "season").parse().ok(),
            round: None,
            stage: non_empty(header.get(&record, "stage")),
            venue: None,
            home_team: home.to_string(),
            away_team: away.to_string(),
            home_identity: teams.home_key.clone(),
            away_identity: teams.away_key.clone(),
            home_team_key: teams.home_key,
            away_team_key: teams.away_key,
            home_state: teams.home_state,
            away_state: teams.away_state,
            home_goal: parse_goal(header.get(&record, "home_goal")),
            away_goal: parse_goal(header.get(&record, "away_goal")),
        });
    }
    Ok(out)
}

/// `BR-Football-Dataset.csv` (extended match statistics; several tournaments).
pub fn load_br_football(path: &Path) -> Result<Vec<MatchRecord>> {
    let mut reader = open_reader(path)?;
    let header = Header::from_record(reader.headers()?.clone());
    let mut out = Vec::new();
    for result in reader.records() {
        let Ok(record) = result else { continue };
        let home = header.get(&record, "home");
        let away = header.get(&record, "away");
        if home.is_empty() || away.is_empty() {
            continue;
        }
        let teams = team_pair_stateless(home, away);
        let date = header.get(&record, "date");
        let time = header.get(&record, "time");
        let date_display = if time.is_empty() {
            date.to_string()
        } else {
            format!("{date} {time}")
        };
        let tournament = header.get(&record, "tournament");
        out.push(MatchRecord {
            source_file: "BR-Football-Dataset.csv",
            competition: if tournament.is_empty() {
                "Unknown".to_string()
            } else {
                tournament.to_string()
            },
            date: parse_flexible_date(date),
            date_display,
            season: parse_flexible_date(date).map(|d| d.format("%Y").to_string().parse().unwrap_or(0)),
            round: None,
            stage: None,
            venue: None,
            home_team: home.to_string(),
            away_team: away.to_string(),
            home_identity: teams.home_key.clone(),
            away_identity: teams.away_key.clone(),
            home_team_key: teams.home_key,
            away_team_key: teams.away_key,
            home_state: teams.home_state,
            away_state: teams.away_state,
            home_goal: parse_goal(header.get(&record, "home_goal")),
            away_goal: parse_goal(header.get(&record, "away_goal")),
        });
    }
    Ok(out)
}

/// `novo_campeonato_brasileiro.csv` (historical Brasileirao, 2003-2019).
pub fn load_historical(path: &Path) -> Result<Vec<MatchRecord>> {
    let mut reader = open_reader(path)?;
    let header = Header::from_record(reader.headers()?.clone());
    let mut out = Vec::new();
    for result in reader.records() {
        let Ok(record) = result else { continue };
        let home = header.get(&record, "Equipe_mandante");
        let away = header.get(&record, "Equipe_visitante");
        if home.is_empty() || away.is_empty() {
            continue;
        }
        let teams = team_pair_stateful(home, away);
        let data = header.get(&record, "Data");
        out.push(MatchRecord {
            source_file: "novo_campeonato_brasileiro.csv",
            competition: "Brasileirao Serie A (historical)".to_string(),
            date: parse_flexible_date(data),
            date_display: data.to_string(),
            season: header.get(&record, "Ano").parse().ok(),
            round: non_empty(header.get(&record, "Rodada")),
            stage: None,
            venue: non_empty(header.get(&record, "Arena")),
            home_team: home.to_string(),
            away_team: away.to_string(),
            home_identity: teams.home_key.clone(),
            away_identity: teams.away_key.clone(),
            home_team_key: teams.home_key,
            away_team_key: teams.away_key,
            home_state: teams.home_state,
            away_state: teams.away_state,
            home_goal: parse_goal(header.get(&record, "Gols_mandante")),
            away_goal: parse_goal(header.get(&record, "Gols_visitante")),
        });
    }
    Ok(out)
}

/// `fifa_data.csv`
pub fn load_players(path: &Path) -> Result<Vec<Player>> {
    let mut reader = open_reader(path)?;
    let header = Header::from_record(reader.headers()?.clone());
    let mut out = Vec::new();
    for result in reader.records() {
        let Ok(record) = result else { continue };
        let name = header.get(&record, "Name");
        if name.is_empty() {
            continue;
        }
        let club = header.get(&record, "Club");
        out.push(Player {
            id: header.get(&record, "ID").parse().unwrap_or(0),
            name: name.to_string(),
            age: header.get(&record, "Age").parse().ok(),
            nationality: header.get(&record, "Nationality").to_string(),
            overall: header.get(&record, "Overall").parse().ok(),
            potential: header.get(&record, "Potential").parse().ok(),
            club: club.to_string(),
            club_key: normalize_team_name(club),
            position: header.get(&record, "Position").to_string(),
        });
    }
    Ok(out)
}

fn non_empty(s: &str) -> Option<String> {
    if s.is_empty() {
        None
    } else {
        Some(s.to_string())
    }
}
