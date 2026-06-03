use std::path::Path;

use anyhow::{Context, Result};
use chrono::NaiveDate;
use csv::ReaderBuilder;
use serde::{Deserialize, Deserializer};

use crate::data::{Competition, Match, Player};
use crate::normalize::normalize_team;

/// Parse an integer where "", "NA", "N/A", or "-" all mean "unknown".
fn de_lenient_int<'de, D>(d: D) -> Result<Option<i32>, D::Error>
where
    D: Deserializer<'de>,
{
    let raw: Option<String> = Option::deserialize(d)?;
    let Some(s) = raw else {
        return Ok(None);
    };
    let t = s.trim();
    if t.is_empty() || t.eq_ignore_ascii_case("na") || t.eq_ignore_ascii_case("n/a") || t == "-" {
        return Ok(None);
    }
    // Some files store ints as floats (e.g. "1.0"); accept both.
    if let Ok(v) = t.parse::<i32>() {
        return Ok(Some(v));
    }
    if let Ok(v) = t.parse::<f64>() {
        return Ok(Some(v as i32));
    }
    Ok(None)
}

#[derive(Debug, Deserialize)]
struct BrasileiraoRow {
    datetime: String,
    home_team: String,
    home_team_state: Option<String>,
    away_team: String,
    away_team_state: Option<String>,
    #[serde(deserialize_with = "de_lenient_int")]
    home_goal: Option<i32>,
    #[serde(deserialize_with = "de_lenient_int")]
    away_goal: Option<i32>,
    #[serde(deserialize_with = "de_lenient_int")]
    season: Option<i32>,
    round: Option<String>,
}

#[derive(Debug, Deserialize)]
struct CupRow {
    round: String,
    datetime: String,
    home_team: String,
    away_team: String,
    #[serde(deserialize_with = "de_lenient_int")]
    home_goal: Option<i32>,
    #[serde(deserialize_with = "de_lenient_int")]
    away_goal: Option<i32>,
    #[serde(deserialize_with = "de_lenient_int")]
    season: Option<i32>,
}

#[derive(Debug, Deserialize)]
struct LibertadoresRow {
    datetime: String,
    home_team: String,
    away_team: String,
    #[serde(deserialize_with = "de_lenient_int")]
    home_goal: Option<i32>,
    #[serde(deserialize_with = "de_lenient_int")]
    away_goal: Option<i32>,
    #[serde(deserialize_with = "de_lenient_int")]
    season: Option<i32>,
    stage: Option<String>,
}

#[derive(Debug, Deserialize)]
struct BrFootballRow {
    tournament: String,
    home: String,
    home_goal: Option<f64>,
    away_goal: Option<f64>,
    away: String,
    home_corner: Option<f64>,
    away_corner: Option<f64>,
    home_shots: Option<f64>,
    away_shots: Option<f64>,
    date: String,
    #[serde(rename = "time")]
    _time: Option<String>,
}

#[derive(Debug, Deserialize)]
struct HistoricRow {
    #[serde(rename = "ID")]
    _id: String,
    #[serde(rename = "Data")]
    data: String,
    #[serde(rename = "Ano")]
    ano: i32,
    #[serde(rename = "Rodada")]
    rodada: Option<String>,
    #[serde(rename = "Equipe_mandante")]
    home: String,
    #[serde(rename = "Equipe_visitante")]
    away: String,
    #[serde(rename = "Gols_mandante")]
    home_goal: i32,
    #[serde(rename = "Gols_visitante")]
    away_goal: i32,
    #[serde(rename = "Mandante_UF")]
    home_uf: Option<String>,
    #[serde(rename = "Visitante_UF")]
    away_uf: Option<String>,
    #[serde(rename = "Arena")]
    arena: Option<String>,
}

fn parse_date_any(s: &str) -> Option<NaiveDate> {
    let s = s.trim();
    if s.is_empty() {
        return None;
    }
    // Try a few formats
    let candidates = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%Y/%m/%d",
        "%m/%d/%Y",
    ];
    for fmt in candidates {
        if let Ok(dt) = chrono::NaiveDateTime::parse_from_str(s, fmt) {
            return Some(dt.date());
        }
        if let Ok(d) = NaiveDate::parse_from_str(s, fmt) {
            return Some(d);
        }
    }
    // Fall back to picking the leading date part
    let head = s.split_whitespace().next()?;
    for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"] {
        if let Ok(d) = NaiveDate::parse_from_str(head, fmt) {
            return Some(d);
        }
    }
    None
}

pub fn load_brasileirao<P: AsRef<Path>>(path: P) -> Result<Vec<Match>> {
    let path_ref = path.as_ref();
    let mut rdr = ReaderBuilder::new()
        .from_path(path_ref)
        .with_context(|| format!("opening {}", path_ref.display()))?;
    let mut out = Vec::new();
    for record in rdr.deserialize::<BrasileiraoRow>() {
        let row = record?;
        let (Some(hg), Some(ag)) = (row.home_goal, row.away_goal) else {
            continue; // skip cancelled / unplayed matches
        };
        out.push(Match {
            competition: Competition::Brasileirao,
            date: parse_date_any(&row.datetime),
            home_team_norm: normalize_team(&row.home_team),
            away_team_norm: normalize_team(&row.away_team),
            home_team: row.home_team,
            away_team: row.away_team,
            home_goal: hg,
            away_goal: ag,
            season: row.season,
            round: row.round,
            stage: None,
            arena: None,
            home_state: row.home_team_state,
            away_state: row.away_team_state,
            home_shots: None,
            away_shots: None,
            home_corner: None,
            away_corner: None,
        });
    }
    Ok(out)
}

pub fn load_cup<P: AsRef<Path>>(path: P) -> Result<Vec<Match>> {
    let path_ref = path.as_ref();
    let mut rdr = ReaderBuilder::new()
        .from_path(path_ref)
        .with_context(|| format!("opening {}", path_ref.display()))?;
    let mut out = Vec::new();
    for record in rdr.deserialize::<CupRow>() {
        let row = record?;
        let (Some(hg), Some(ag)) = (row.home_goal, row.away_goal) else {
            continue;
        };
        out.push(Match {
            competition: Competition::CopaDoBrasil,
            date: parse_date_any(&row.datetime),
            home_team_norm: normalize_team(&row.home_team),
            away_team_norm: normalize_team(&row.away_team),
            home_team: row.home_team,
            away_team: row.away_team,
            home_goal: hg,
            away_goal: ag,
            season: row.season,
            round: Some(row.round),
            stage: None,
            arena: None,
            home_state: None,
            away_state: None,
            home_shots: None,
            away_shots: None,
            home_corner: None,
            away_corner: None,
        });
    }
    Ok(out)
}

pub fn load_libertadores<P: AsRef<Path>>(path: P) -> Result<Vec<Match>> {
    let path_ref = path.as_ref();
    let mut rdr = ReaderBuilder::new()
        .from_path(path_ref)
        .with_context(|| format!("opening {}", path_ref.display()))?;
    let mut out = Vec::new();
    for record in rdr.deserialize::<LibertadoresRow>() {
        let row = record?;
        let (Some(hg), Some(ag)) = (row.home_goal, row.away_goal) else {
            continue;
        };
        out.push(Match {
            competition: Competition::Libertadores,
            date: parse_date_any(&row.datetime),
            home_team_norm: normalize_team(&row.home_team),
            away_team_norm: normalize_team(&row.away_team),
            home_team: row.home_team,
            away_team: row.away_team,
            home_goal: hg,
            away_goal: ag,
            season: row.season,
            round: None,
            stage: row.stage,
            arena: None,
            home_state: None,
            away_state: None,
            home_shots: None,
            away_shots: None,
            home_corner: None,
            away_corner: None,
        });
    }
    Ok(out)
}

pub fn load_br_football<P: AsRef<Path>>(path: P) -> Result<Vec<Match>> {
    let path_ref = path.as_ref();
    let mut rdr = ReaderBuilder::new()
        .from_path(path_ref)
        .with_context(|| format!("opening {}", path_ref.display()))?;
    let mut out = Vec::new();
    for record in rdr.deserialize::<BrFootballRow>() {
        let row = record?;
        // BR-Football overlaps with the other CSVs by season, so keep all of
        // its rows under their own competition bucket to avoid double-counting
        // standings/stats. The `tournament` label is preserved in `stage`.
        let competition = Competition::BrFootball;
        let stage = Some(row.tournament.clone());
        let date = parse_date_any(&row.date);
        let season = date.map(|d| d.format("%Y").to_string().parse().unwrap_or(0));
        out.push(Match {
            competition,
            date,
            home_team_norm: normalize_team(&row.home),
            away_team_norm: normalize_team(&row.away),
            home_team: row.home,
            away_team: row.away,
            home_goal: row.home_goal.unwrap_or(0.0) as i32,
            away_goal: row.away_goal.unwrap_or(0.0) as i32,
            season,
            round: None,
            stage,
            arena: None,
            home_state: None,
            away_state: None,
            home_shots: row.home_shots.map(|v| v as i32),
            away_shots: row.away_shots.map(|v| v as i32),
            home_corner: row.home_corner.map(|v| v as i32),
            away_corner: row.away_corner.map(|v| v as i32),
        });
    }
    Ok(out)
}

pub fn load_historic<P: AsRef<Path>>(path: P) -> Result<Vec<Match>> {
    let path_ref = path.as_ref();
    let mut rdr = ReaderBuilder::new()
        .from_path(path_ref)
        .with_context(|| format!("opening {}", path_ref.display()))?;
    let mut out = Vec::new();
    for record in rdr.deserialize::<HistoricRow>() {
        let row = record?;
        out.push(Match {
            competition: Competition::BrasileiraoHistoric,
            date: parse_date_any(&row.data),
            home_team_norm: normalize_team(&row.home),
            away_team_norm: normalize_team(&row.away),
            home_team: row.home,
            away_team: row.away,
            home_goal: row.home_goal,
            away_goal: row.away_goal,
            season: Some(row.ano),
            round: row.rodada,
            stage: None,
            arena: row.arena,
            home_state: row.home_uf,
            away_state: row.away_uf,
            home_shots: None,
            away_shots: None,
            home_corner: None,
            away_corner: None,
        });
    }
    Ok(out)
}

#[derive(Debug, Deserialize)]
struct FifaRow {
    #[serde(rename = "ID")]
    id: u64,
    #[serde(rename = "Name")]
    name: String,
    #[serde(rename = "Age")]
    age: Option<i32>,
    #[serde(rename = "Nationality")]
    nationality: String,
    #[serde(rename = "Overall")]
    overall: Option<i32>,
    #[serde(rename = "Potential")]
    potential: Option<i32>,
    #[serde(rename = "Club")]
    club: Option<String>,
    #[serde(rename = "Position")]
    position: Option<String>,
    #[serde(rename = "Jersey Number")]
    jersey: Option<String>,
    #[serde(rename = "Height")]
    height: Option<String>,
    #[serde(rename = "Weight")]
    weight: Option<String>,
    #[serde(rename = "Preferred Foot")]
    preferred_foot: Option<String>,
    #[serde(rename = "Wage")]
    wage: Option<String>,
    #[serde(rename = "Value")]
    value: Option<String>,
}

pub fn load_players<P: AsRef<Path>>(path: P) -> Result<Vec<Player>> {
    let path_ref = path.as_ref();
    let mut rdr = ReaderBuilder::new()
        .flexible(true)
        .from_path(path_ref)
        .with_context(|| format!("opening {}", path_ref.display()))?;
    let mut out = Vec::new();
    for record in rdr.deserialize::<FifaRow>() {
        let row = match record {
            Ok(r) => r,
            Err(_) => continue, // some FIFA rows have ragged tail fields; skip silently
        };
        let club = row.club.unwrap_or_default();
        let club_norm = normalize_team(&club);
        out.push(Player {
            id: row.id,
            name: row.name,
            age: row.age,
            nationality: row.nationality,
            overall: row.overall,
            potential: row.potential,
            club,
            club_norm,
            position: row.position,
            jersey_number: row.jersey,
            height: row.height,
            weight: row.weight,
            preferred_foot: row.preferred_foot,
            wage: row.wage,
            value: row.value,
        });
    }
    Ok(out)
}
