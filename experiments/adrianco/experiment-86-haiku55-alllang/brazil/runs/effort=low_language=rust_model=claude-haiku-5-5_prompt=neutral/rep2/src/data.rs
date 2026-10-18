//! Context: loads the six Kaggle CSV files in `data/kaggle/` into one unified
//! in-memory dataset of matches and players.
//!
//! Matches from all four match files are merged into a single list. When the
//! same fixture (date + home + away) appears in more than one file, only the
//! first occurrence is kept, so overlapping seasons are not double counted.
//! Player records come from the FIFA file.

use std::collections::{BTreeMap, HashMap, HashSet};
use std::fs;
use std::path::{Path, PathBuf};

use crate::normalize::{display_name, iso_date, team_key};

pub const COMP_SERIE_A: &str = "Brasileirão Série A";
pub const COMP_SERIE_B: &str = "Brasileirão Série B";
pub const COMP_SERIE_C: &str = "Brasileirão Série C";
pub const COMP_COPA_DO_BRASIL: &str = "Copa do Brasil";
pub const COMP_LIBERTADORES: &str = "Copa Libertadores";

#[derive(Debug, Clone, PartialEq)]
pub struct Match {
    /// ISO date, `YYYY-MM-DD`.
    pub date: String,
    pub competition: String,
    pub season: i32,
    /// Round number or tournament stage, when the source provides one.
    pub round: Option<String>,
    pub home_key: String,
    pub away_key: String,
    pub home_goals: u32,
    pub away_goals: u32,
}

#[derive(Debug, Clone, PartialEq)]
pub struct Player {
    pub id: String,
    pub name: String,
    pub age: u32,
    pub nationality: String,
    pub overall: u32,
    pub potential: u32,
    pub club: String,
    pub position: String,
    pub jersey_number: Option<u32>,
    pub value: String,
    pub wage: String,
    pub height: String,
    pub weight: String,
}

#[derive(Debug, Default)]
pub struct Dataset {
    pub matches: Vec<Match>,
    pub players: Vec<Player>,
    /// Team key -> display name (most common spelling in the sources).
    pub team_names: BTreeMap<String, String>,
}

#[derive(Debug)]
pub enum LoadError {
    Io(PathBuf, std::io::Error),
    Csv(PathBuf, csv::Error),
    MissingColumn(PathBuf, &'static str),
}

impl std::fmt::Display for LoadError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            LoadError::Io(p, e) => write!(f, "cannot read {}: {e}", p.display()),
            LoadError::Csv(p, e) => write!(f, "cannot parse {}: {e}", p.display()),
            LoadError::MissingColumn(p, c) => write!(f, "{} is missing column '{c}'", p.display()),
        }
    }
}

impl std::error::Error for LoadError {}

/// File names expected inside the data directory.
pub const BRASILEIRAO_FILE: &str = "Brasileirao_Matches.csv";
pub const CUP_FILE: &str = "Brazilian_Cup_Matches.csv";
pub const LIBERTADORES_FILE: &str = "Libertadores_Matches.csv";
pub const EXTENDED_FILE: &str = "BR-Football-Dataset.csv";
pub const HISTORICAL_FILE: &str = "novo_campeonato_brasileiro.csv";
pub const FIFA_FILE: &str = "fifa_data.csv";

impl Dataset {
    /// Load every dataset file from `dir`.
    pub fn load_from_dir(dir: &Path) -> Result<Self, LoadError> {
        let mut builder = Builder::default();
        builder.load_matches(dir, BRASILEIRAO_FILE, load_brasileirao)?;
        builder.load_matches(dir, HISTORICAL_FILE, load_historical)?;
        builder.load_matches(dir, CUP_FILE, load_cup)?;
        builder.load_matches(dir, LIBERTADORES_FILE, load_libertadores)?;
        builder.load_matches(dir, EXTENDED_FILE, load_extended)?;
        builder.players = load_players(&dir.join(FIFA_FILE))?;
        Ok(builder.finish())
    }

    /// Display name for a team key, or the key itself when unknown.
    pub fn team_display(&self, key: &str) -> String {
        self.team_names
            .get(key)
            .cloned()
            .unwrap_or_else(|| key.to_string())
    }
}

#[derive(Default)]
struct Builder {
    matches: Vec<Match>,
    seen: HashSet<(i32, String, String, String)>,
    /// Team key -> how often each display spelling was seen, so the most common wins.
    spellings: HashMap<String, BTreeMap<String, usize>>,
    players: Vec<Player>,
}

/// One raw row from a match file, before it is merged into the dataset.
struct RawMatch {
    date: String,
    competition: String,
    round: Option<String>,
    home: String,
    away: String,
    home_goals: u32,
    away_goals: u32,
}

impl Builder {
    fn load_matches(
        &mut self,
        dir: &Path,
        file: &str,
        loader: fn(&Table) -> Result<Vec<RawMatch>, LoadError>,
    ) -> Result<(), LoadError> {
        let path = dir.join(file);
        let table = Table::read(&path)?;
        for raw in loader(&table)? {
            self.add(raw);
        }
        Ok(())
    }

    fn add(&mut self, raw: RawMatch) {
        let home_key = team_key(&raw.home);
        let away_key = team_key(&raw.away);
        if home_key.is_empty() || away_key.is_empty() {
            return;
        }
        // The sources disagree on dates by a day or so, so a fixture is identified by
        // season, competition and the ordered pair of teams rather than by exact date.
        let season: i32 = raw.date[..4].parse().unwrap_or_default();
        let fixture = (
            season,
            raw.competition.clone(),
            home_key.clone(),
            away_key.clone(),
        );
        if !self.seen.insert(fixture) {
            return;
        }
        self.note_spelling(&home_key, &raw.home);
        self.note_spelling(&away_key, &raw.away);
        self.matches.push(Match {
            date: raw.date,
            competition: raw.competition,
            season,
            round: raw.round,
            home_key,
            away_key,
            home_goals: raw.home_goals,
            away_goals: raw.away_goals,
        });
    }

    fn note_spelling(&mut self, key: &str, raw: &str) {
        let count = self
            .spellings
            .entry(key.to_string())
            .or_default()
            .entry(display_name(raw))
            .or_insert(0);
        *count += 1;
    }

    fn finish(mut self) -> Dataset {
        self.matches.sort_by(|a, b| a.date.cmp(&b.date));
        // Most common spelling wins; ties go to the alphabetically first spelling.
        let team_names = self
            .spellings
            .into_iter()
            .filter_map(|(key, names)| {
                let best = names
                    .into_iter()
                    .max_by(|a, b| a.1.cmp(&b.1).then_with(|| b.0.cmp(&a.0)))?
                    .0;
                Some((key, best))
            })
            .collect();
        Dataset {
            matches: self.matches,
            players: self.players,
            team_names,
        }
    }
}

/// A parsed CSV file with header-name lookup.
struct Table {
    path: PathBuf,
    columns: HashMap<String, usize>,
    rows: Vec<csv::StringRecord>,
}

impl Table {
    fn read(path: &Path) -> Result<Self, LoadError> {
        let bytes = fs::read(path).map_err(|e| LoadError::Io(path.to_path_buf(), e))?;
        // Some files carry a UTF-8 byte-order mark that would corrupt the first header.
        let bytes = bytes.strip_prefix("\u{feff}".as_bytes()).unwrap_or(&bytes);
        let mut reader = csv::ReaderBuilder::new().flexible(true).from_reader(bytes);
        let headers = reader
            .headers()
            .map_err(|e| LoadError::Csv(path.to_path_buf(), e))?
            .clone();
        let columns = headers
            .iter()
            .enumerate()
            .map(|(i, h)| (h.trim().to_string(), i))
            .collect();
        let mut rows = Vec::new();
        for record in reader.records() {
            rows.push(record.map_err(|e| LoadError::Csv(path.to_path_buf(), e))?);
        }
        Ok(Table {
            path: path.to_path_buf(),
            columns,
            rows,
        })
    }

    fn require(&self, column: &'static str) -> Result<usize, LoadError> {
        self.columns
            .get(column)
            .copied()
            .ok_or_else(|| LoadError::MissingColumn(self.path.clone(), column))
    }

    fn optional(&self, column: &str) -> Option<usize> {
        self.columns.get(column).copied()
    }
}

fn cell(record: &csv::StringRecord, index: usize) -> &str {
    record.get(index).unwrap_or("").trim()
}

/// Parse a goal count that may be written as "2", "2.0" or be blank.
fn goals(raw: &str) -> Option<u32> {
    let value: f64 = raw.trim().parse().ok()?;
    if value.is_finite() && value >= 0.0 {
        Some(value.round() as u32)
    } else {
        None
    }
}

fn raw_match(
    record: &csv::StringRecord,
    cols: &MatchColumns,
    date: &str,
    competition: &str,
    round: Option<String>,
) -> Option<RawMatch> {
    let date = iso_date(date)?;
    let home_goals = goals(cell(record, cols.home_goals))?;
    let away_goals = goals(cell(record, cols.away_goals))?;
    Some(RawMatch {
        date,
        competition: competition.to_string(),
        round,
        home: cell(record, cols.home).to_string(),
        away: cell(record, cols.away).to_string(),
        home_goals,
        away_goals,
    })
}

struct MatchColumns {
    home: usize,
    away: usize,
    home_goals: usize,
    away_goals: usize,
}

fn match_columns(
    table: &Table,
    home: &'static str,
    away: &'static str,
    hg: &'static str,
    ag: &'static str,
) -> Result<MatchColumns, LoadError> {
    Ok(MatchColumns {
        home: table.require(home)?,
        away: table.require(away)?,
        home_goals: table.require(hg)?,
        away_goals: table.require(ag)?,
    })
}

fn load_brasileirao(table: &Table) -> Result<Vec<RawMatch>, LoadError> {
    let cols = match_columns(table, "home_team", "away_team", "home_goal", "away_goal")?;
    let date_col = table.require("datetime")?;
    let round_col = table.require("round")?;
    Ok(table
        .rows
        .iter()
        .filter_map(|r| {
            let round = Some(cell(r, round_col).to_string()).filter(|s| !s.is_empty());
            raw_match(r, &cols, cell(r, date_col), COMP_SERIE_A, round)
        })
        .collect())
}

fn load_historical(table: &Table) -> Result<Vec<RawMatch>, LoadError> {
    let cols = match_columns(
        table,
        "Equipe_mandante",
        "Equipe_visitante",
        "Gols_mandante",
        "Gols_visitante",
    )?;
    let date_col = table.require("Data")?;
    let round_col = table.require("Rodada")?;
    Ok(table
        .rows
        .iter()
        .filter_map(|r| {
            let round = Some(cell(r, round_col).to_string()).filter(|s| !s.is_empty());
            raw_match(r, &cols, cell(r, date_col), COMP_SERIE_A, round)
        })
        .collect())
}

fn load_cup(table: &Table) -> Result<Vec<RawMatch>, LoadError> {
    let cols = match_columns(table, "home_team", "away_team", "home_goal", "away_goal")?;
    let date_col = table.require("datetime")?;
    let round_col = table.require("round")?;
    Ok(table
        .rows
        .iter()
        .filter_map(|r| {
            let round = Some(cell(r, round_col).to_string()).filter(|s| !s.is_empty());
            raw_match(r, &cols, cell(r, date_col), COMP_COPA_DO_BRASIL, round)
        })
        .collect())
}

fn load_libertadores(table: &Table) -> Result<Vec<RawMatch>, LoadError> {
    let cols = match_columns(table, "home_team", "away_team", "home_goal", "away_goal")?;
    let date_col = table.require("datetime")?;
    let stage_col = table.optional("stage");
    Ok(table
        .rows
        .iter()
        .filter_map(|r| {
            let round = stage_col
                .map(|c| cell(r, c).to_string())
                .filter(|s| !s.is_empty());
            raw_match(r, &cols, cell(r, date_col), COMP_LIBERTADORES, round)
        })
        .collect())
}

fn load_extended(table: &Table) -> Result<Vec<RawMatch>, LoadError> {
    let cols = match_columns(table, "home", "away", "home_goal", "away_goal")?;
    let date_col = table.require("date")?;
    let tournament_col = table.require("tournament")?;
    Ok(table
        .rows
        .iter()
        .filter_map(|r| {
            let competition = match cell(r, tournament_col) {
                "Serie A" => COMP_SERIE_A,
                "Serie B" => COMP_SERIE_B,
                "Serie C" => COMP_SERIE_C,
                "Copa do Brasil" => COMP_COPA_DO_BRASIL,
                _ => return None,
            };
            raw_match(r, &cols, cell(r, date_col), competition, None)
        })
        .collect())
}

fn load_players(path: &Path) -> Result<Vec<Player>, LoadError> {
    let table = Table::read(path)?;
    let name = table.require("Name")?;
    let id = table.require("ID")?;
    let age = table.require("Age")?;
    let nationality = table.require("Nationality")?;
    let overall = table.require("Overall")?;
    let potential = table.require("Potential")?;
    let club = table.require("Club")?;
    let position = table.require("Position")?;
    let jersey = table.optional("Jersey Number");
    let value = table.optional("Value");
    let wage = table.optional("Wage");
    let height = table.optional("Height");
    let weight = table.optional("Weight");
    let opt = |r: &csv::StringRecord, c: Option<usize>| {
        c.map(|i| cell(r, i).to_string()).unwrap_or_default()
    };
    Ok(table
        .rows
        .iter()
        .filter_map(|r| {
            let name = cell(r, name);
            if name.is_empty() {
                return None;
            }
            Some(Player {
                id: cell(r, id).to_string(),
                name: name.to_string(),
                age: cell(r, age).parse().unwrap_or(0),
                nationality: cell(r, nationality).to_string(),
                overall: cell(r, overall).parse().unwrap_or(0),
                potential: cell(r, potential).parse().unwrap_or(0),
                club: cell(r, club).to_string(),
                position: cell(r, position).to_string(),
                jersey_number: opt(r, jersey).parse().ok(),
                value: opt(r, value),
                wage: opt(r, wage),
                height: opt(r, height),
                weight: opt(r, weight),
            })
        })
        .collect())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn given_goal_strings_when_parsed_then_whole_numbers_result() {
        assert_eq!(goals("2"), Some(2));
        assert_eq!(goals("2.0"), Some(2));
        assert_eq!(goals(""), None);
        assert_eq!(goals("-1"), None);
    }
}
