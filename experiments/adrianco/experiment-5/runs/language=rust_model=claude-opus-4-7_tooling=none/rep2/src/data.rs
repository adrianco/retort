//! CSV loaders for every dataset described in TASK.md.
//!
//! Each loader returns owned, normalized records that the query layer can
//! consume without re-parsing CSV.

use anyhow::{anyhow, Context, Result};
use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};

use crate::normalize::parse_date;

/// Identifier for the source file a match came from.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum Source {
    Brasileirao,
    BrazilianCup,
    Libertadores,
    BrFootball,
    NovoBrasileirao,
}

impl Source {
    pub fn as_str(&self) -> &'static str {
        match self {
            Source::Brasileirao => "Brasileirao_Matches.csv",
            Source::BrazilianCup => "Brazilian_Cup_Matches.csv",
            Source::Libertadores => "Libertadores_Matches.csv",
            Source::BrFootball => "BR-Football-Dataset.csv",
            Source::NovoBrasileirao => "novo_campeonato_brasileiro.csv",
        }
    }
}

/// One unified match record assembled from any source file.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Match {
    pub competition: String,
    pub source: Source,
    pub season: Option<i32>,
    pub round: Option<String>,
    pub stage: Option<String>,
    pub date_raw: String,
    pub date: Option<(i32, u32, u32)>,
    pub home_team: String,
    pub home_team_state: Option<String>,
    pub away_team: String,
    pub away_team_state: Option<String>,
    pub home_goal: Option<i32>,
    pub away_goal: Option<i32>,
    pub arena: Option<String>,
}

impl Match {
    pub fn date_iso(&self) -> Option<String> {
        self.date
            .map(|(y, m, d)| crate::normalize::format_iso(y, m, d))
    }

    pub fn winner(&self) -> Option<MatchOutcome> {
        match (self.home_goal, self.away_goal) {
            (Some(h), Some(a)) if h > a => Some(MatchOutcome::Home),
            (Some(h), Some(a)) if h < a => Some(MatchOutcome::Away),
            (Some(_), Some(_)) => Some(MatchOutcome::Draw),
            _ => None,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MatchOutcome {
    Home,
    Away,
    Draw,
}

/// One FIFA player record. Most fields are optional because the source CSV is
/// sparse and we only need the subset relevant to TASK.md.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Player {
    pub id: Option<u64>,
    pub name: String,
    pub age: Option<u32>,
    pub nationality: String,
    pub overall: Option<u32>,
    pub potential: Option<u32>,
    pub club: String,
    pub position: Option<String>,
    pub jersey_number: Option<String>,
    pub height: Option<String>,
    pub weight: Option<String>,
}

/// Container for everything loaded from disk.
#[derive(Debug, Default, Clone, Serialize, Deserialize)]
pub struct Dataset {
    pub matches: Vec<Match>,
    pub players: Vec<Player>,
}

impl Dataset {
    pub fn load_from_dir(dir: &Path) -> Result<Self> {
        let mut matches = Vec::new();
        matches.extend(load_brasileirao(&dir.join("Brasileirao_Matches.csv"))?);
        matches.extend(load_brazilian_cup(&dir.join("Brazilian_Cup_Matches.csv"))?);
        matches.extend(load_libertadores(&dir.join("Libertadores_Matches.csv"))?);
        matches.extend(load_br_football(&dir.join("BR-Football-Dataset.csv"))?);
        matches.extend(load_novo_brasileirao(
            &dir.join("novo_campeonato_brasileiro.csv"),
        )?);

        let players = load_fifa(&dir.join("fifa_data.csv"))?;

        Ok(Dataset { matches, players })
    }
}

/// Default location for data: `<workdir>/data/kaggle`.
pub fn default_data_dir() -> PathBuf {
    if let Ok(env) = std::env::var("BR_SOCCER_DATA_DIR") {
        return PathBuf::from(env);
    }
    PathBuf::from("data/kaggle")
}

fn canonical_competition(name: &str) -> String {
    let lc = name.to_lowercase();
    match lc.as_str() {
        "serie a" => "Brasileirão Série A".to_string(),
        "serie b" => "Brasileirão Série B".to_string(),
        "serie c" => "Brasileirão Série C".to_string(),
        _ => name.to_string(),
    }
}

fn open_reader(path: &Path) -> Result<csv::Reader<std::fs::File>> {
    csv::ReaderBuilder::new()
        .has_headers(true)
        .flexible(true)
        .from_path(path)
        .with_context(|| format!("opening {}", path.display()))
}

fn parse_int(s: &str) -> Option<i32> {
    let s = s.trim();
    if s.is_empty() {
        return None;
    }
    // Some files have floats like "1.0"
    if let Ok(v) = s.parse::<i32>() {
        return Some(v);
    }
    if let Ok(v) = s.parse::<f64>() {
        return Some(v as i32);
    }
    None
}

fn parse_uint(s: &str) -> Option<u32> {
    let s = s.trim();
    if s.is_empty() {
        return None;
    }
    if let Ok(v) = s.parse::<u32>() {
        return Some(v);
    }
    if let Ok(v) = s.parse::<f64>() {
        if v.is_finite() && v >= 0.0 {
            return Some(v as u32);
        }
    }
    None
}

fn opt_string(s: &str) -> Option<String> {
    let s = s.trim();
    if s.is_empty() {
        None
    } else {
        Some(s.to_string())
    }
}

#[derive(Debug, Deserialize)]
struct BrasileiraoRow {
    datetime: String,
    home_team: String,
    home_team_state: String,
    away_team: String,
    away_team_state: String,
    home_goal: String,
    away_goal: String,
    season: String,
    round: String,
}

fn load_brasileirao(path: &Path) -> Result<Vec<Match>> {
    let mut out = Vec::new();
    let mut rdr = open_reader(path)?;
    for rec in rdr.deserialize() {
        let row: BrasileiraoRow = rec?;
        let date = parse_date(&row.datetime);
        out.push(Match {
            competition: "Brasileirão Série A".to_string(),
            source: Source::Brasileirao,
            season: parse_int(&row.season),
            round: opt_string(&row.round),
            stage: None,
            date_raw: row.datetime,
            date,
            home_team: row.home_team,
            home_team_state: opt_string(&row.home_team_state),
            away_team: row.away_team,
            away_team_state: opt_string(&row.away_team_state),
            home_goal: parse_int(&row.home_goal),
            away_goal: parse_int(&row.away_goal),
            arena: None,
        });
    }
    Ok(out)
}

#[derive(Debug, Deserialize)]
struct BrazilianCupRow {
    round: String,
    datetime: String,
    home_team: String,
    away_team: String,
    home_goal: String,
    away_goal: String,
    season: String,
}

fn load_brazilian_cup(path: &Path) -> Result<Vec<Match>> {
    let mut out = Vec::new();
    let mut rdr = open_reader(path)?;
    for rec in rdr.deserialize() {
        let row: BrazilianCupRow = rec?;
        let date = parse_date(&row.datetime);
        out.push(Match {
            competition: "Copa do Brasil".to_string(),
            source: Source::BrazilianCup,
            season: parse_int(&row.season),
            round: opt_string(&row.round),
            stage: None,
            date_raw: row.datetime,
            date,
            home_team: row.home_team,
            home_team_state: None,
            away_team: row.away_team,
            away_team_state: None,
            home_goal: parse_int(&row.home_goal),
            away_goal: parse_int(&row.away_goal),
            arena: None,
        });
    }
    Ok(out)
}

#[derive(Debug, Deserialize)]
struct LibertadoresRow {
    datetime: String,
    home_team: String,
    away_team: String,
    home_goal: String,
    away_goal: String,
    season: String,
    stage: String,
}

fn load_libertadores(path: &Path) -> Result<Vec<Match>> {
    let mut out = Vec::new();
    let mut rdr = open_reader(path)?;
    for rec in rdr.deserialize() {
        let row: LibertadoresRow = rec?;
        let date = parse_date(&row.datetime);
        out.push(Match {
            competition: "Copa Libertadores".to_string(),
            source: Source::Libertadores,
            season: parse_int(&row.season),
            round: None,
            stage: opt_string(&row.stage),
            date_raw: row.datetime,
            date,
            home_team: row.home_team,
            home_team_state: None,
            away_team: row.away_team,
            away_team_state: None,
            home_goal: parse_int(&row.home_goal),
            away_goal: parse_int(&row.away_goal),
            arena: None,
        });
    }
    Ok(out)
}

#[derive(Debug, Deserialize)]
struct BrFootballRow {
    tournament: String,
    home: String,
    home_goal: String,
    away_goal: String,
    away: String,
    #[serde(default)]
    time: String,
    date: String,
}

fn load_br_football(path: &Path) -> Result<Vec<Match>> {
    let mut out = Vec::new();
    let mut rdr = open_reader(path)?;
    for rec in rdr.deserialize() {
        let row: BrFootballRow = rec?;
        let date = parse_date(&row.date);
        let raw = if row.time.trim().is_empty() {
            row.date.clone()
        } else {
            format!("{} {}", row.date, row.time)
        };
        let competition = canonical_competition(&row.tournament);
        out.push(Match {
            competition,
            source: Source::BrFootball,
            season: date.map(|(y, _, _)| y),
            round: None,
            stage: None,
            date_raw: raw,
            date,
            home_team: row.home,
            home_team_state: None,
            away_team: row.away,
            away_team_state: None,
            home_goal: parse_int(&row.home_goal),
            away_goal: parse_int(&row.away_goal),
            arena: None,
        });
    }
    Ok(out)
}

#[derive(Debug, Deserialize)]
struct NovoBrasileiraoRow {
    #[serde(rename = "ID")]
    _id: String,
    #[serde(rename = "Data")]
    data: String,
    #[serde(rename = "Ano")]
    ano: String,
    #[serde(rename = "Rodada")]
    rodada: String,
    #[serde(rename = "Equipe_mandante")]
    home_team: String,
    #[serde(rename = "Equipe_visitante")]
    away_team: String,
    #[serde(rename = "Gols_mandante")]
    home_goal: String,
    #[serde(rename = "Gols_visitante")]
    away_goal: String,
    #[serde(rename = "Mandante_UF")]
    mandante_uf: String,
    #[serde(rename = "Visitante_UF")]
    visitante_uf: String,
    #[serde(rename = "Vencedor", default)]
    _vencedor: String,
    #[serde(rename = "Arena", default)]
    arena: String,
    #[serde(rename = "OBS", default)]
    _obs: String,
}

fn load_novo_brasileirao(path: &Path) -> Result<Vec<Match>> {
    let mut out = Vec::new();
    let mut rdr = open_reader(path)?;
    for rec in rdr.deserialize() {
        let row: NovoBrasileiraoRow = rec?;
        let date = parse_date(&row.data);
        out.push(Match {
            competition: "Brasileirão Série A".to_string(),
            source: Source::NovoBrasileirao,
            season: parse_int(&row.ano),
            round: opt_string(&row.rodada),
            stage: None,
            date_raw: row.data,
            date,
            home_team: row.home_team,
            home_team_state: opt_string(&row.mandante_uf),
            away_team: row.away_team,
            away_team_state: opt_string(&row.visitante_uf),
            home_goal: parse_int(&row.home_goal),
            away_goal: parse_int(&row.away_goal),
            arena: opt_string(&row.arena),
        });
    }
    Ok(out)
}

fn load_fifa(path: &Path) -> Result<Vec<Player>> {
    let mut rdr = open_reader(path)?;
    let headers = rdr.headers()?.clone();

    let idx_of = |name: &str| -> Option<usize> {
        headers.iter().position(|h| h.eq_ignore_ascii_case(name))
    };

    let i_id = idx_of("ID").ok_or_else(|| anyhow!("fifa CSV missing ID column"))?;
    let i_name = idx_of("Name").ok_or_else(|| anyhow!("fifa CSV missing Name column"))?;
    let i_age = idx_of("Age");
    let i_nat = idx_of("Nationality")
        .ok_or_else(|| anyhow!("fifa CSV missing Nationality column"))?;
    let i_overall = idx_of("Overall");
    let i_potential = idx_of("Potential");
    let i_club = idx_of("Club").ok_or_else(|| anyhow!("fifa CSV missing Club column"))?;
    let i_position = idx_of("Position");
    let i_jersey = idx_of("Jersey Number");
    let i_height = idx_of("Height");
    let i_weight = idx_of("Weight");

    let mut out = Vec::new();
    for rec in rdr.records() {
        let r = rec?;
        let get = |i: Option<usize>| -> String {
            i.and_then(|idx| r.get(idx)).unwrap_or("").to_string()
        };
        out.push(Player {
            id: r.get(i_id).and_then(|s| s.trim().parse::<u64>().ok()),
            name: r.get(i_name).unwrap_or("").to_string(),
            age: i_age.and_then(|idx| r.get(idx)).and_then(parse_uint),
            nationality: r.get(i_nat).unwrap_or("").to_string(),
            overall: i_overall.and_then(|idx| r.get(idx)).and_then(parse_uint),
            potential: i_potential.and_then(|idx| r.get(idx)).and_then(parse_uint),
            club: r.get(i_club).unwrap_or("").to_string(),
            position: opt_string(&get(i_position)),
            jersey_number: opt_string(&get(i_jersey)),
            height: opt_string(&get(i_height)),
            weight: opt_string(&get(i_weight)),
        });
    }
    Ok(out)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn data_dir() -> PathBuf {
        PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("data/kaggle")
    }

    #[test]
    fn loads_all_csvs() {
        let ds = Dataset::load_from_dir(&data_dir()).expect("load dataset");
        assert!(ds.matches.len() > 20_000, "matches loaded: {}", ds.matches.len());
        assert!(ds.players.len() > 15_000, "players loaded: {}", ds.players.len());
    }

    #[test]
    fn matches_have_dates() {
        let ds = Dataset::load_from_dir(&data_dir()).expect("load dataset");
        let dated = ds.matches.iter().filter(|m| m.date.is_some()).count();
        let total = ds.matches.len();
        assert!(dated * 10 >= total * 9, "{} of {} dated", dated, total);
    }
}
