use crate::{
    domain::{MatchMetrics, Player, SoccerMatch},
    normalize::{competition_key, parse_date, season_from_date, team_key},
};
use csv::StringRecord;
use serde::Serialize;
use std::{
    collections::{BTreeMap, HashMap},
    path::{Path, PathBuf},
};
use thiserror::Error;

const MATCH_FILES: &[(&str, SourceKind)] = &[
    ("Brasileirao_Matches.csv", SourceKind::Brasileirao),
    ("Brazilian_Cup_Matches.csv", SourceKind::BrazilianCup),
    ("Libertadores_Matches.csv", SourceKind::Libertadores),
    ("BR-Football-Dataset.csv", SourceKind::Extended),
    ("novo_campeonato_brasileiro.csv", SourceKind::Historical),
];

#[derive(Debug, Error)]
pub enum DataError {
    #[error("failed to read {path}: {source}")]
    Csv { path: PathBuf, source: csv::Error },
    #[error("{path}, row {row}: {message}")]
    InvalidRow {
        path: PathBuf,
        row: usize,
        message: String,
    },
    #[error("required dataset does not exist: {0}")]
    MissingFile(PathBuf),
}

#[derive(Clone, Debug, Default, Serialize)]
pub struct LoadReport {
    pub files_loaded: usize,
    pub matches_by_source: BTreeMap<String, usize>,
    pub player_rows: usize,
    pub duplicate_matches_merged: usize,
    pub incomplete_matches_skipped: usize,
}

#[derive(Clone, Debug, Default)]
pub struct DataStore {
    pub matches: Vec<SoccerMatch>,
    pub players: Vec<Player>,
    pub team_names: BTreeMap<String, String>,
    pub report: LoadReport,
}

#[derive(Clone, Copy)]
enum SourceKind {
    Brasileirao,
    BrazilianCup,
    Libertadores,
    Extended,
    Historical,
}

impl DataStore {
    pub fn load(dir: impl AsRef<Path>) -> Result<(Self, LoadReport), DataError> {
        let dir = dir.as_ref();
        let mut report = LoadReport::default();
        let mut merged: BTreeMap<String, SoccerMatch> = BTreeMap::new();

        for &(filename, kind) in MATCH_FILES {
            let path = dir.join(filename);
            ensure_exists(&path)?;
            let (rows, skipped) = load_matches(&path, kind)?;
            report.files_loaded += 1;
            report.matches_by_source.insert(filename.into(), rows.len());
            report.incomplete_matches_skipped += skipped;
            for item in rows {
                let key = dedup_key(&item);
                if let Some(existing) = merged.get_mut(&key) {
                    if !existing.sources.contains(&filename.to_owned()) {
                        existing.sources.push(filename.to_owned());
                    }
                    merge_optional_fields(existing, &item);
                    report.duplicate_matches_merged += 1;
                } else {
                    merged.insert(key, item);
                }
            }
        }

        let player_path = dir.join("fifa_data.csv");
        ensure_exists(&player_path)?;
        let players = load_players(&player_path)?;
        report.files_loaded += 1;
        report.player_rows = players.len();

        let mut matches: Vec<_> = merged.into_values().collect();
        matches.sort_by(|a, b| a.date.cmp(&b.date).then_with(|| a.id.cmp(&b.id)));
        let mut team_names = BTreeMap::new();
        for item in &matches {
            team_names
                .entry(item.home_team_key.clone())
                .or_insert_with(|| clean_display(&item.home_team));
            team_names
                .entry(item.away_team_key.clone())
                .or_insert_with(|| clean_display(&item.away_team));
        }
        let store = Self {
            matches,
            players,
            team_names,
            report: report.clone(),
        };
        Ok((store, report))
    }
}

fn ensure_exists(path: &Path) -> Result<(), DataError> {
    if path.is_file() {
        Ok(())
    } else {
        Err(DataError::MissingFile(path.to_owned()))
    }
}

fn load_matches(path: &Path, kind: SourceKind) -> Result<(Vec<SoccerMatch>, usize), DataError> {
    let mut reader = csv::ReaderBuilder::new()
        .flexible(true)
        .from_path(path)
        .map_err(|source| DataError::Csv {
            path: path.to_owned(),
            source,
        })?;
    let headers = reader
        .headers()
        .map_err(|source| DataError::Csv {
            path: path.to_owned(),
            source,
        })?
        .clone();
    let index = HeaderIndex::new(&headers);
    let source = path
        .file_name()
        .unwrap_or_default()
        .to_string_lossy()
        .into_owned();
    let mut result = Vec::new();
    let mut skipped = 0;
    for (zero_row, record) in reader.records().enumerate() {
        let row = zero_row + 2;
        let record = record.map_err(|source| DataError::Csv {
            path: path.to_owned(),
            source,
        })?;
        let parsed = parse_match(kind, &index, &record, &source).map_err(|message| {
            DataError::InvalidRow {
                path: path.to_owned(),
                row,
                message,
            }
        })?;
        if let Some(item) = parsed {
            result.push(item);
        } else {
            skipped += 1;
        }
    }
    Ok((result, skipped))
}

fn parse_match(
    kind: SourceKind,
    h: &HeaderIndex,
    r: &StringRecord,
    source: &str,
) -> Result<Option<SoccerMatch>, String> {
    let (date_raw, home, away, hg, ag, competition, season, round, stage, arena, time, metrics) =
        match kind {
            SourceKind::Brasileirao => (
                h.get(r, "datetime"),
                h.get(r, "home_team"),
                h.get(r, "away_team"),
                h.get(r, "home_goal"),
                h.get(r, "away_goal"),
                "Brasileirão".into(),
                h.get(r, "season"),
                opt(h.get(r, "round")),
                None,
                None,
                time_part(h.get(r, "datetime")),
                None,
            ),
            SourceKind::BrazilianCup => (
                h.get(r, "datetime"),
                h.get(r, "home_team"),
                h.get(r, "away_team"),
                h.get(r, "home_goal"),
                h.get(r, "away_goal"),
                "Copa do Brasil".into(),
                h.get(r, "season"),
                opt(h.get(r, "round")),
                None,
                None,
                time_part(h.get(r, "datetime")),
                None,
            ),
            SourceKind::Libertadores => (
                h.get(r, "datetime"),
                h.get(r, "home_team"),
                h.get(r, "away_team"),
                h.get(r, "home_goal"),
                h.get(r, "away_goal"),
                "Copa Libertadores".into(),
                h.get(r, "season"),
                None,
                opt(h.get(r, "stage")),
                None,
                time_part(h.get(r, "datetime")),
                None,
            ),
            SourceKind::Extended => {
                let m = MatchMetrics {
                    home_corners: num_opt(h.get(r, "home_corner")),
                    away_corners: num_opt(h.get(r, "away_corner")),
                    home_attacks: num_opt(h.get(r, "home_attack")),
                    away_attacks: num_opt(h.get(r, "away_attack")),
                    home_shots: num_opt(h.get(r, "home_shots")),
                    away_shots: num_opt(h.get(r, "away_shots")),
                };
                (
                    h.get(r, "date"),
                    h.get(r, "home"),
                    h.get(r, "away"),
                    h.get(r, "home_goal"),
                    h.get(r, "away_goal"),
                    h.get(r, "tournament").to_owned(),
                    "",
                    None,
                    None,
                    None,
                    opt(h.get(r, "time")),
                    Some(m),
                )
            }
            SourceKind::Historical => (
                h.get(r, "Data"),
                h.get(r, "Equipe_mandante"),
                h.get(r, "Equipe_visitante"),
                h.get(r, "Gols_mandante"),
                h.get(r, "Gols_visitante"),
                "Brasileirão".into(),
                h.get(r, "Ano"),
                opt(h.get(r, "Rodada")),
                None,
                opt(h.get(r, "Arena")),
                None,
                None,
            ),
        };
    if home.trim().is_empty() || away.trim().is_empty() {
        return Ok(None);
    }
    let Some(date) = parse_date(date_raw) else {
        return Ok(None);
    };
    let (Some(home_goals), Some(away_goals)) = (parse_score(hg), parse_score(ag)) else {
        return Ok(None);
    };
    let season = season
        .trim()
        .parse()
        .unwrap_or_else(|_| season_from_date(date));
    let home_key = team_key(home);
    let away_key = team_key(away);
    if home_key.is_empty() || away_key.is_empty() {
        return Err("empty normalized team name".into());
    }
    let mut item = SoccerMatch {
        id: String::new(),
        date,
        time,
        season,
        competition,
        round,
        stage,
        home_team: clean_display(home),
        home_team_key: home_key,
        away_team: clean_display(away),
        away_team_key: away_key,
        home_goals,
        away_goals,
        arena,
        metrics,
        sources: vec![source.into()],
    };
    item.id = dedup_key(&item);
    Ok(Some(item))
}

fn load_players(path: &Path) -> Result<Vec<Player>, DataError> {
    let mut reader = csv::ReaderBuilder::new()
        .flexible(true)
        .from_path(path)
        .map_err(|source| DataError::Csv {
            path: path.into(),
            source,
        })?;
    let headers = reader
        .headers()
        .map_err(|source| DataError::Csv {
            path: path.into(),
            source,
        })?
        .clone();
    let h = HeaderIndex::new(&headers);
    let attrs = [
        "Crossing",
        "Finishing",
        "Dribbling",
        "ShortPassing",
        "LongPassing",
        "BallControl",
        "Acceleration",
        "SprintSpeed",
        "Strength",
        "Stamina",
    ];
    let mut result = Vec::new();
    for (zero_row, rec) in reader.records().enumerate() {
        let rec = rec.map_err(|source| DataError::Csv {
            path: path.into(),
            source,
        })?;
        let required = |name: &str| -> Result<&str, DataError> {
            let value = h.get(&rec, name);
            if value.trim().is_empty() {
                Err(DataError::InvalidRow {
                    path: path.into(),
                    row: zero_row + 2,
                    message: format!("missing {name}"),
                })
            } else {
                Ok(value)
            }
        };
        let mut attributes = BTreeMap::new();
        for attr in attrs {
            if let Ok(v) = h.get(&rec, attr).parse::<u8>() {
                attributes.insert(attr.into(), v);
            }
        }
        result.push(Player {
            id: required("ID")?.parse().map_err(|_| DataError::InvalidRow {
                path: path.into(),
                row: zero_row + 2,
                message: "invalid ID".into(),
            })?,
            name: required("Name")?.into(),
            age: required("Age")?
                .parse()
                .map_err(|_| DataError::InvalidRow {
                    path: path.into(),
                    row: zero_row + 2,
                    message: "invalid Age".into(),
                })?,
            nationality: required("Nationality")?.into(),
            overall: required("Overall")?
                .parse()
                .map_err(|_| DataError::InvalidRow {
                    path: path.into(),
                    row: zero_row + 2,
                    message: "invalid Overall".into(),
                })?,
            potential: required("Potential")?
                .parse()
                .map_err(|_| DataError::InvalidRow {
                    path: path.into(),
                    row: zero_row + 2,
                    message: "invalid Potential".into(),
                })?,
            club: opt(h.get(&rec, "Club")),
            position: opt(h.get(&rec, "Position")),
            jersey_number: num_opt(h.get(&rec, "Jersey Number")),
            height: opt(h.get(&rec, "Height")),
            weight: opt(h.get(&rec, "Weight")),
            preferred_foot: opt(h.get(&rec, "Preferred Foot")),
            attributes,
        });
    }
    Ok(result)
}

struct HeaderIndex(HashMap<String, usize>);
impl HeaderIndex {
    fn new(headers: &StringRecord) -> Self {
        Self(
            headers
                .iter()
                .enumerate()
                .map(|(i, s)| (s.trim_start_matches('\u{feff}').to_owned(), i))
                .collect(),
        )
    }
    fn get<'a>(&self, record: &'a StringRecord, name: &str) -> &'a str {
        self.0.get(name).and_then(|i| record.get(*i)).unwrap_or("")
    }
}
fn parse_score(s: &str) -> Option<u16> {
    s.trim()
        .parse::<f64>()
        .ok()
        .filter(|v| v.fract() == 0.0 && *v >= 0.0)
        .map(|v| v as u16)
}
fn num_opt<T: std::str::FromStr>(s: &str) -> Option<T> {
    s.trim().trim_end_matches(".0").parse().ok()
}
fn opt(s: &str) -> Option<String> {
    let s = s.trim();
    if s.is_empty() {
        None
    } else {
        Some(s.into())
    }
}
fn time_part(s: &str) -> Option<String> {
    s.split_once(' ').map(|(_, v)| v.to_owned())
}
fn clean_display(s: &str) -> String {
    s.trim().trim_matches('"').to_owned()
}
fn dedup_key(m: &SoccerMatch) -> String {
    let competition = competition_key(&m.competition);
    if competition == "brasileirao" {
        // Each league pairing has one home fixture per season. Some overlapping
        // sources disagree by one day, so season is a safer identity component.
        format!(
            "{competition}:{}:{}:{}:{}-{}",
            m.season, m.home_team_key, m.away_team_key, m.home_goals, m.away_goals
        )
    } else {
        format!(
            "{competition}:{}:{}:{}:{}:{}-{}",
            m.season, m.date, m.home_team_key, m.away_team_key, m.home_goals, m.away_goals
        )
    }
}
fn merge_optional_fields(a: &mut SoccerMatch, b: &SoccerMatch) {
    if a.round.is_none() {
        a.round = b.round.clone()
    }
    if a.stage.is_none() {
        a.stage = b.stage.clone()
    }
    if a.arena.is_none() {
        a.arena = b.arena.clone()
    }
    if a.metrics.is_none() {
        a.metrics = b.metrics.clone()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn score_accepts_integer_float() {
        assert_eq!(parse_score("3.0"), Some(3));
        assert_eq!(parse_score("2"), Some(2));
        assert_eq!(parse_score(""), None)
    }
}
