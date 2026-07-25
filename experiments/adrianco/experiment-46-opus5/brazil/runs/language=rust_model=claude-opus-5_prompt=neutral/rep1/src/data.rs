//! CSV ingestion for the six Kaggle files.
//!
//! Every file is read through a small header-indexed [`Table`] rather than a
//! bespoke serde struct, because the files disagree on column count, column
//! order, quoting, BOM presence and null spellings. Rows that cannot be
//! interpreted (missing teams, unparseable dates, `-` scores) are reported as
//! skipped rather than aborting the load.

use std::collections::HashMap;
use std::fmt;
use std::path::{Path, PathBuf};

use crate::model::{Competition, Date, MatchStats, Source, ATTRIBUTE_NAMES};
use crate::normalize::{normalize_team, TeamKey};

/// Error raised while loading the datasets.
#[derive(Debug)]
pub enum DataError {
    /// The file could not be opened or is not valid CSV/UTF-8. The `csv` crate
    /// reports missing files and I/O failures through the same error type.
    Csv {
        path: PathBuf,
        source: csv::Error,
    },
    MissingColumn {
        path: PathBuf,
        column: String,
    },
}

impl fmt::Display for DataError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            DataError::Csv { path, source } => {
                write!(f, "cannot read {}: {source}", path.display())
            }
            DataError::MissingColumn { path, column } => {
                write!(f, "{} is missing the '{column}' column", path.display())
            }
        }
    }
}

impl std::error::Error for DataError {}

/// A CSV file loaded into memory with a case-insensitive header index.
pub struct Table {
    pub path: PathBuf,
    headers: HashMap<String, usize>,
    pub rows: Vec<csv::StringRecord>,
}

impl Table {
    pub fn load(path: &Path) -> Result<Table, DataError> {
        let mut reader = csv::ReaderBuilder::new()
            .flexible(true)
            .from_path(path)
            .map_err(|source| DataError::Csv {
                path: path.to_path_buf(),
                source,
            })?;
        let mut headers = HashMap::new();
        let header_record = reader.headers().map_err(|source| DataError::Csv {
            path: path.to_path_buf(),
            source,
        })?;
        for (idx, name) in header_record.iter().enumerate() {
            headers.insert(header_key(name), idx);
        }
        let mut rows = Vec::new();
        for row in reader.records() {
            let row = row.map_err(|source| DataError::Csv {
                path: path.to_path_buf(),
                source,
            })?;
            rows.push(row);
        }
        Ok(Table {
            path: path.to_path_buf(),
            headers,
            rows,
        })
    }

    pub fn require(&self, column: &str) -> Result<usize, DataError> {
        self.headers
            .get(&header_key(column))
            .copied()
            .ok_or_else(|| DataError::MissingColumn {
                path: self.path.clone(),
                column: column.to_string(),
            })
    }

    pub fn index(&self, column: &str) -> Option<usize> {
        self.headers.get(&header_key(column)).copied()
    }

    /// Trimmed cell value, or `None` when absent/empty/`-`/`NA`.
    pub fn cell<'a>(&self, row: &'a csv::StringRecord, idx: Option<usize>) -> Option<&'a str> {
        let value = row.get(idx?)?.trim().trim_matches('"').trim();
        match value {
            "" | "-" | "NA" | "N/A" | "null" | "NaN" => None,
            other => Some(other),
        }
    }
}

/// Header names carry a UTF-8 BOM in `fifa_data.csv`; strip and casefold.
fn header_key(raw: &str) -> String {
    raw.trim_start_matches('\u{feff}')
        .trim()
        .trim_matches('"')
        .to_lowercase()
}

/// Parses `"3"`, `3`, `3.0` and `-` into an optional goal count.
fn parse_goals(raw: Option<&str>) -> Option<i32> {
    let raw = raw?;
    if let Ok(v) = raw.parse::<i32>() {
        return Some(v);
    }
    let v = raw.parse::<f64>().ok()?;
    if v.is_finite() && v >= 0.0 {
        Some(v.round() as i32)
    } else {
        None
    }
}

fn parse_number(raw: Option<&str>) -> Option<f64> {
    raw?.parse::<f64>().ok()
}

/// A match row before team identities have been resolved to graph ids.
#[derive(Debug, Clone)]
pub struct PendingMatch {
    pub competition: Competition,
    pub season: i32,
    pub date: Option<Date>,
    pub time: Option<String>,
    pub home_key: TeamKey,
    pub away_key: TeamKey,
    pub home_raw: String,
    pub away_raw: String,
    pub home_goals: Option<i32>,
    pub away_goals: Option<i32>,
    pub round: Option<String>,
    pub stage: Option<String>,
    pub venue: Option<String>,
    pub source: Source,
    pub stats: Option<MatchStats>,
}

/// A player row before its club has been linked to a graph team.
#[derive(Debug, Clone)]
pub struct PendingPlayer {
    pub fifa_id: Option<i64>,
    pub name: String,
    pub age: Option<i32>,
    pub nationality: String,
    pub overall: i32,
    pub potential: i32,
    pub club: Option<String>,
    pub position: Option<String>,
    pub jersey_number: Option<i32>,
    pub height: Option<String>,
    pub weight: Option<String>,
    pub value: Option<String>,
    pub wage: Option<String>,
    pub preferred_foot: Option<String>,
    pub attributes: Vec<u8>,
}

/// What a single file contributed to the graph.
#[derive(Debug, Clone)]
pub struct SourceReport {
    pub source: Source,
    pub rows_read: usize,
    pub rows_used: usize,
    pub rows_skipped: usize,
}

/// Everything parsed out of `data/kaggle`.
pub struct RawData {
    pub matches: Vec<PendingMatch>,
    pub players: Vec<PendingPlayer>,
    pub reports: Vec<SourceReport>,
}

/// Loads all six CSV files from `dir`.
pub fn load_all(dir: &Path) -> Result<RawData, DataError> {
    let mut matches = Vec::new();
    let mut players = Vec::new();
    let mut reports = Vec::new();

    let (mut rows, report) = load_brasileirao(dir)?;
    matches.append(&mut rows);
    reports.push(report);

    let (mut rows, report) = load_brazilian_cup(dir)?;
    matches.append(&mut rows);
    reports.push(report);

    let (mut rows, report) = load_libertadores(dir)?;
    matches.append(&mut rows);
    reports.push(report);

    let (mut rows, report) = load_br_football(dir)?;
    matches.append(&mut rows);
    reports.push(report);

    let (mut rows, report) = load_novo_brasileirao(dir)?;
    matches.append(&mut rows);
    reports.push(report);

    let (mut rows, report) = load_fifa(dir)?;
    players.append(&mut rows);
    reports.push(report);

    Ok(RawData {
        matches,
        players,
        reports,
    })
}

fn season_of(date: Option<Date>, explicit: Option<&str>) -> Option<i32> {
    if let Some(raw) = explicit {
        if let Ok(year) = raw.trim().parse::<i32>() {
            return Some(year);
        }
    }
    date.map(|d| d.year)
}

fn load_brasileirao(dir: &Path) -> Result<(Vec<PendingMatch>, SourceReport), DataError> {
    let path = dir.join(Source::Brasileirao.file_name());
    let table = Table::load(&path)?;
    let (dt, home, away, hg, ag) = (
        table.require("datetime")?,
        table.require("home_team")?,
        table.require("away_team")?,
        table.require("home_goal")?,
        table.require("away_goal")?,
    );
    let home_state = table.index("home_team_state");
    let away_state = table.index("away_team_state");
    let season_idx = table.index("season");
    let round_idx = table.index("round");

    let mut out = Vec::new();
    let mut skipped = 0;
    for row in &table.rows {
        let (Some(home_raw), Some(away_raw)) =
            (table.cell(row, Some(home)), table.cell(row, Some(away)))
        else {
            skipped += 1;
            continue;
        };
        let datetime = table.cell(row, Some(dt));
        let date = datetime.and_then(Date::parse);
        let Some(season) = season_of(date, table.cell(row, season_idx)) else {
            skipped += 1;
            continue;
        };
        out.push(PendingMatch {
            competition: Competition::SerieA,
            season,
            date,
            time: datetime.and_then(Date::parse_time),
            home_key: normalize_team(home_raw, table.cell(row, home_state)),
            away_key: normalize_team(away_raw, table.cell(row, away_state)),
            home_raw: home_raw.to_string(),
            away_raw: away_raw.to_string(),
            home_goals: parse_goals(table.cell(row, Some(hg))),
            away_goals: parse_goals(table.cell(row, Some(ag))),
            round: table.cell(row, round_idx).map(str::to_string),
            stage: None,
            venue: None,
            source: Source::Brasileirao,
            stats: None,
        });
    }
    let report = SourceReport {
        source: Source::Brasileirao,
        rows_read: table.rows.len(),
        rows_used: out.len(),
        rows_skipped: skipped,
    };
    Ok((out, report))
}

fn load_brazilian_cup(dir: &Path) -> Result<(Vec<PendingMatch>, SourceReport), DataError> {
    let path = dir.join(Source::BrazilianCup.file_name());
    let table = Table::load(&path)?;
    let (dt, home, away, hg, ag) = (
        table.require("datetime")?,
        table.require("home_team")?,
        table.require("away_team")?,
        table.require("home_goal")?,
        table.require("away_goal")?,
    );
    let season_idx = table.index("season");
    let round_idx = table.index("round");

    let mut out = Vec::new();
    let mut skipped = 0;
    for row in &table.rows {
        let (Some(home_raw), Some(away_raw)) =
            (table.cell(row, Some(home)), table.cell(row, Some(away)))
        else {
            skipped += 1;
            continue;
        };
        let datetime = table.cell(row, Some(dt));
        let date = datetime.and_then(Date::parse);
        let Some(season) = season_of(date, table.cell(row, season_idx)) else {
            skipped += 1;
            continue;
        };
        out.push(PendingMatch {
            competition: Competition::CopaDoBrasil,
            season,
            date,
            time: datetime.and_then(Date::parse_time),
            home_key: normalize_team(home_raw, None),
            away_key: normalize_team(away_raw, None),
            home_raw: home_raw.to_string(),
            away_raw: away_raw.to_string(),
            home_goals: parse_goals(table.cell(row, Some(hg))),
            away_goals: parse_goals(table.cell(row, Some(ag))),
            round: table.cell(row, round_idx).map(str::to_string),
            stage: None,
            venue: None,
            source: Source::BrazilianCup,
            stats: None,
        });
    }
    let report = SourceReport {
        source: Source::BrazilianCup,
        rows_read: table.rows.len(),
        rows_used: out.len(),
        rows_skipped: skipped,
    };
    Ok((out, report))
}

fn load_libertadores(dir: &Path) -> Result<(Vec<PendingMatch>, SourceReport), DataError> {
    let path = dir.join(Source::Libertadores.file_name());
    let table = Table::load(&path)?;
    let (dt, home, away, hg, ag) = (
        table.require("datetime")?,
        table.require("home_team")?,
        table.require("away_team")?,
        table.require("home_goal")?,
        table.require("away_goal")?,
    );
    let season_idx = table.index("season");
    let stage_idx = table.index("stage");

    let mut out = Vec::new();
    let mut skipped = 0;
    for row in &table.rows {
        let (Some(home_raw), Some(away_raw)) =
            (table.cell(row, Some(home)), table.cell(row, Some(away)))
        else {
            skipped += 1;
            continue;
        };
        let datetime = table.cell(row, Some(dt));
        let date = datetime.and_then(Date::parse);
        let Some(season) = season_of(date, table.cell(row, season_idx)) else {
            skipped += 1;
            continue;
        };
        out.push(PendingMatch {
            competition: Competition::Libertadores,
            season,
            date,
            time: datetime.and_then(Date::parse_time),
            home_key: normalize_team(home_raw, None),
            away_key: normalize_team(away_raw, None),
            home_raw: home_raw.to_string(),
            away_raw: away_raw.to_string(),
            home_goals: parse_goals(table.cell(row, Some(hg))),
            away_goals: parse_goals(table.cell(row, Some(ag))),
            round: None,
            stage: table.cell(row, stage_idx).map(str::to_string),
            venue: None,
            source: Source::Libertadores,
            stats: None,
        });
    }
    let report = SourceReport {
        source: Source::Libertadores,
        rows_read: table.rows.len(),
        rows_used: out.len(),
        rows_skipped: skipped,
    };
    Ok((out, report))
}

fn load_br_football(dir: &Path) -> Result<(Vec<PendingMatch>, SourceReport), DataError> {
    let path = dir.join(Source::BrFootball.file_name());
    let table = Table::load(&path)?;
    let (tournament, home, away, hg, ag, date_idx) = (
        table.require("tournament")?,
        table.require("home")?,
        table.require("away")?,
        table.require("home_goal")?,
        table.require("away_goal")?,
        table.require("date")?,
    );
    let time_idx = table.index("time");
    let stat_idx = |name: &str| table.index(name);

    let mut out = Vec::new();
    let mut skipped = 0;
    for row in &table.rows {
        let (Some(home_raw), Some(away_raw), Some(tournament_raw)) = (
            table.cell(row, Some(home)),
            table.cell(row, Some(away)),
            table.cell(row, Some(tournament)),
        ) else {
            skipped += 1;
            continue;
        };
        let (Some(competition), Some(date)) = (
            Competition::parse(tournament_raw),
            table.cell(row, Some(date_idx)).and_then(Date::parse),
        ) else {
            skipped += 1;
            continue;
        };
        let stats = MatchStats {
            home_corners: parse_number(table.cell(row, stat_idx("home_corner"))),
            away_corners: parse_number(table.cell(row, stat_idx("away_corner"))),
            home_shots: parse_number(table.cell(row, stat_idx("home_shots"))),
            away_shots: parse_number(table.cell(row, stat_idx("away_shots"))),
            home_attacks: parse_number(table.cell(row, stat_idx("home_attack"))),
            away_attacks: parse_number(table.cell(row, stat_idx("away_attack"))),
            total_corners: parse_number(table.cell(row, stat_idx("total_corners"))),
            half_time_home: table.cell(row, stat_idx("ht_result")).map(str::to_string),
            half_time_away: table.cell(row, stat_idx("at_result")).map(str::to_string),
        };
        out.push(PendingMatch {
            competition,
            season: date.year,
            date: Some(date),
            time: table.cell(row, time_idx).map(str::to_string),
            home_key: normalize_team(home_raw, None),
            away_key: normalize_team(away_raw, None),
            home_raw: home_raw.to_string(),
            away_raw: away_raw.to_string(),
            home_goals: parse_goals(table.cell(row, Some(hg))),
            away_goals: parse_goals(table.cell(row, Some(ag))),
            round: None,
            stage: None,
            venue: None,
            source: Source::BrFootball,
            stats: if stats.is_empty() { None } else { Some(stats) },
        });
    }
    let report = SourceReport {
        source: Source::BrFootball,
        rows_read: table.rows.len(),
        rows_used: out.len(),
        rows_skipped: skipped,
    };
    Ok((out, report))
}

fn load_novo_brasileirao(dir: &Path) -> Result<(Vec<PendingMatch>, SourceReport), DataError> {
    let path = dir.join(Source::NovoBrasileirao.file_name());
    let table = Table::load(&path)?;
    let (date_idx, home, away, hg, ag) = (
        table.require("data")?,
        table.require("equipe_mandante")?,
        table.require("equipe_visitante")?,
        table.require("gols_mandante")?,
        table.require("gols_visitante")?,
    );
    let year_idx = table.index("ano");
    let round_idx = table.index("rodada");
    let arena_idx = table.index("arena");
    let home_state = table.index("mandante_uf");
    let away_state = table.index("visitante_uf");

    let mut out = Vec::new();
    let mut skipped = 0;
    for row in &table.rows {
        let (Some(home_raw), Some(away_raw)) =
            (table.cell(row, Some(home)), table.cell(row, Some(away)))
        else {
            skipped += 1;
            continue;
        };
        let date = table.cell(row, Some(date_idx)).and_then(Date::parse);
        let Some(season) = season_of(date, table.cell(row, year_idx)) else {
            skipped += 1;
            continue;
        };
        out.push(PendingMatch {
            competition: Competition::SerieA,
            season,
            date,
            time: None,
            home_key: normalize_team(home_raw, table.cell(row, home_state)),
            away_key: normalize_team(away_raw, table.cell(row, away_state)),
            home_raw: home_raw.to_string(),
            away_raw: away_raw.to_string(),
            home_goals: parse_goals(table.cell(row, Some(hg))),
            away_goals: parse_goals(table.cell(row, Some(ag))),
            round: table.cell(row, round_idx).map(str::to_string),
            stage: None,
            venue: table.cell(row, arena_idx).map(str::to_string),
            source: Source::NovoBrasileirao,
            stats: None,
        });
    }
    let report = SourceReport {
        source: Source::NovoBrasileirao,
        rows_read: table.rows.len(),
        rows_used: out.len(),
        rows_skipped: skipped,
    };
    Ok((out, report))
}

fn load_fifa(dir: &Path) -> Result<(Vec<PendingPlayer>, SourceReport), DataError> {
    let path = dir.join(Source::Fifa.file_name());
    let table = Table::load(&path)?;
    let name_idx = table.require("name")?;
    let overall_idx = table.require("overall")?;
    let nationality_idx = table.require("nationality")?;
    let attribute_idx: Vec<Option<usize>> =
        ATTRIBUTE_NAMES.iter().map(|a| table.index(a)).collect();
    let id_idx = table.index("id");
    let age_idx = table.index("age");
    let potential_idx = table.index("potential");
    let club_idx = table.index("club");
    let position_idx = table.index("position");
    let jersey_idx = table.index("jersey number");
    let height_idx = table.index("height");
    let weight_idx = table.index("weight");
    let value_idx = table.index("value");
    let wage_idx = table.index("wage");
    let foot_idx = table.index("preferred foot");

    let mut out = Vec::new();
    let mut skipped = 0;
    for row in &table.rows {
        let (Some(name), Some(overall)) = (
            table.cell(row, Some(name_idx)),
            table
                .cell(row, Some(overall_idx))
                .and_then(|v| v.parse::<i32>().ok()),
        ) else {
            skipped += 1;
            continue;
        };
        let attributes = attribute_idx
            .iter()
            .map(|idx| {
                table
                    .cell(row, *idx)
                    .and_then(|v| v.parse::<f64>().ok())
                    .map(|v| v.round().clamp(0.0, 255.0) as u8)
                    .unwrap_or(0)
            })
            .collect();
        out.push(PendingPlayer {
            fifa_id: table.cell(row, id_idx).and_then(|v| v.parse::<i64>().ok()),
            name: name.to_string(),
            age: table.cell(row, age_idx).and_then(|v| v.parse().ok()),
            nationality: table
                .cell(row, Some(nationality_idx))
                .unwrap_or("Unknown")
                .to_string(),
            overall,
            potential: table
                .cell(row, potential_idx)
                .and_then(|v| v.parse().ok())
                .unwrap_or(overall),
            club: table.cell(row, club_idx).map(str::to_string),
            position: table.cell(row, position_idx).map(str::to_string),
            jersey_number: table
                .cell(row, jersey_idx)
                .and_then(|v| v.parse::<f64>().ok().map(|n| n.round() as i32)),
            height: table.cell(row, height_idx).map(str::to_string),
            weight: table.cell(row, weight_idx).map(str::to_string),
            value: table.cell(row, value_idx).map(str::to_string),
            wage: table.cell(row, wage_idx).map(str::to_string),
            preferred_foot: table.cell(row, foot_idx).map(str::to_string),
            attributes,
        });
    }
    let report = SourceReport {
        source: Source::Fifa,
        rows_read: table.rows.len(),
        rows_used: out.len(),
        rows_skipped: skipped,
    };
    Ok((out, report))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn goals_parse_from_every_spelling() {
        assert_eq!(parse_goals(Some("3")), Some(3));
        assert_eq!(parse_goals(Some("3.0")), Some(3));
        assert_eq!(parse_goals(Some("0")), Some(0));
        assert_eq!(parse_goals(None), None);
    }

    #[test]
    fn header_keys_drop_bom_and_case() {
        assert_eq!(header_key("\u{feff}ID"), "id");
        assert_eq!(header_key("\"home_team\""), "home_team");
        assert_eq!(header_key("Jersey Number"), "jersey number");
    }
}
