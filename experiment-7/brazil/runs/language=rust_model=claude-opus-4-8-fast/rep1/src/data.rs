// =============================================================================
// Context: Brazilian Soccer MCP Server
// File:    src/data.rs
// Purpose: Load and unify the five match CSVs and the FIFA player CSV into an
//          in-memory `Database`. Each source has a different schema, column
//          order, date format and naming convention; this module is the single
//          place that knows about those quirks and produces clean `Match` /
//          `Player` values for the rest of the system.
//
//          Highlights:
//            - `parse_date` accepts ISO ("2023-09-24"), ISO+time
//              ("2012-05-19 18:30:00") and Brazilian ("29/03/2003") formats.
//            - Matches appearing in more than one file (Serie A is covered by
//              three datasets) are de-duplicated by `Match::dedup_key`.
//            - All reads are UTF-8; the FIFA file's leading BOM column is
//              tolerated by addressing columns by header name.
// =============================================================================

use std::collections::HashMap;
use std::error::Error;
use std::path::Path;

use crate::model::{Match, Player};

/// The loaded, queryable dataset.
#[derive(Debug, Default)]
pub struct Database {
    pub matches: Vec<Match>,
    pub players: Vec<Player>,
}

type Row = HashMap<String, String>;

/// Read a CSV into a vector of header-keyed rows.
fn read_rows(path: &Path) -> Result<Vec<Row>, Box<dyn Error>> {
    let mut rdr = csv::ReaderBuilder::new()
        .flexible(true)
        .has_headers(true)
        .from_path(path)?;
    let mut rows = Vec::new();
    for result in rdr.deserialize() {
        let row: Row = result?;
        rows.push(row);
    }
    Ok(rows)
}

fn get<'a>(row: &'a Row, key: &str) -> Option<&'a str> {
    row.get(key).map(|s| s.trim()).filter(|s| !s.is_empty())
}

fn parse_int(row: &Row, key: &str) -> Option<i32> {
    get(row, key).and_then(|s| {
        // Tolerate floating point integers such as "2.0" from BR-Football.
        if let Ok(v) = s.parse::<i32>() {
            Some(v)
        } else {
            s.parse::<f64>().ok().map(|f| f as i32)
        }
    })
}

/// Normalize the supported date formats to ISO "YYYY-MM-DD".
pub fn parse_date(raw: &str) -> Option<String> {
    let s = raw.trim();
    if s.is_empty() {
        return None;
    }
    // Brazilian DD/MM/YYYY (optionally with a trailing time component).
    if s.contains('/') {
        let date_part = s.split_whitespace().next().unwrap_or(s);
        let parts: Vec<&str> = date_part.split('/').collect();
        if parts.len() == 3 {
            let (d, m, y) = (parts[0], parts[1], parts[2]);
            if d.len() <= 2 && m.len() <= 2 && y.len() == 4 {
                return Some(format!(
                    "{:0>4}-{:0>2}-{:0>2}",
                    y, m, d
                ));
            }
        }
        return None;
    }
    // ISO, optionally followed by a space and a time component.
    let date_part = s.split_whitespace().next().unwrap_or(s);
    let bytes = date_part.as_bytes();
    if date_part.len() >= 10 && bytes[4] == b'-' && bytes[7] == b'-' {
        return Some(date_part[..10].to_string());
    }
    None
}

impl Database {
    /// Load every dataset from `dir` (typically "data/kaggle").
    pub fn load_from_dir<P: AsRef<Path>>(dir: P) -> Result<Database, Box<dyn Error>> {
        let dir = dir.as_ref();
        let mut db = Database::default();

        db.load_brasileirao(&dir.join("Brasileirao_Matches.csv"))?;
        db.load_cup(&dir.join("Brazilian_Cup_Matches.csv"))?;
        db.load_libertadores(&dir.join("Libertadores_Matches.csv"))?;
        db.load_br_football(&dir.join("BR-Football-Dataset.csv"))?;
        db.load_novo(&dir.join("novo_campeonato_brasileiro.csv"))?;
        db.load_fifa(&dir.join("fifa_data.csv"))?;

        db.retain_primary_sources();
        Ok(db)
    }

    fn load_brasileirao(&mut self, path: &Path) -> Result<(), Box<dyn Error>> {
        for row in read_rows(path)? {
            let (hg, ag) = match (parse_int(&row, "home_goal"), parse_int(&row, "away_goal")) {
                (Some(h), Some(a)) => (h, a),
                _ => continue,
            };
            let home = match get(&row, "home_team") {
                Some(v) => v.to_string(),
                None => continue,
            };
            let away = match get(&row, "away_team") {
                Some(v) => v.to_string(),
                None => continue,
            };
            self.matches.push(Match {
                competition: "Brasileirão Série A".to_string(),
                date: get(&row, "datetime").and_then(parse_date),
                season: parse_int(&row, "season").unwrap_or(0),
                round: get(&row, "round").map(|s| s.to_string()),
                stage: None,
                home_team: home,
                away_team: away,
                home_goal: hg,
                away_goal: ag,
                arena: None,
                source: "Brasileirao_Matches.csv".to_string(),
            });
        }
        Ok(())
    }

    fn load_cup(&mut self, path: &Path) -> Result<(), Box<dyn Error>> {
        for row in read_rows(path)? {
            let (hg, ag) = match (parse_int(&row, "home_goal"), parse_int(&row, "away_goal")) {
                (Some(h), Some(a)) => (h, a),
                _ => continue,
            };
            let home = match get(&row, "home_team") {
                Some(v) => v.to_string(),
                None => continue,
            };
            let away = match get(&row, "away_team") {
                Some(v) => v.to_string(),
                None => continue,
            };
            self.matches.push(Match {
                competition: "Copa do Brasil".to_string(),
                date: get(&row, "datetime").and_then(parse_date),
                season: parse_int(&row, "season").unwrap_or(0),
                round: get(&row, "round").map(|s| s.to_string()),
                stage: None,
                home_team: home,
                away_team: away,
                home_goal: hg,
                away_goal: ag,
                arena: None,
                source: "Brazilian_Cup_Matches.csv".to_string(),
            });
        }
        Ok(())
    }

    fn load_libertadores(&mut self, path: &Path) -> Result<(), Box<dyn Error>> {
        for row in read_rows(path)? {
            let (hg, ag) = match (parse_int(&row, "home_goal"), parse_int(&row, "away_goal")) {
                (Some(h), Some(a)) => (h, a),
                _ => continue,
            };
            let home = match get(&row, "home_team") {
                Some(v) => v.to_string(),
                None => continue,
            };
            let away = match get(&row, "away_team") {
                Some(v) => v.to_string(),
                None => continue,
            };
            self.matches.push(Match {
                competition: "Copa Libertadores".to_string(),
                date: get(&row, "datetime").and_then(parse_date),
                season: parse_int(&row, "season").unwrap_or(0),
                round: None,
                stage: get(&row, "stage").map(|s| s.to_string()),
                home_team: home,
                away_team: away,
                home_goal: hg,
                away_goal: ag,
                arena: None,
                source: "Libertadores_Matches.csv".to_string(),
            });
        }
        Ok(())
    }

    fn load_br_football(&mut self, path: &Path) -> Result<(), Box<dyn Error>> {
        for row in read_rows(path)? {
            let (hg, ag) = match (parse_int(&row, "home_goal"), parse_int(&row, "away_goal")) {
                (Some(h), Some(a)) => (h, a),
                _ => continue,
            };
            let home = match get(&row, "home") {
                Some(v) => v.to_string(),
                None => continue,
            };
            let away = match get(&row, "away") {
                Some(v) => v.to_string(),
                None => continue,
            };
            let date = get(&row, "date").and_then(parse_date);
            // Season is not a column here; derive it from the match year.
            let season = date
                .as_deref()
                .and_then(|d| d.get(0..4))
                .and_then(|y| y.parse::<i32>().ok())
                .unwrap_or(0);
            let tournament = get(&row, "tournament").unwrap_or("Unknown").to_string();
            self.matches.push(Match {
                competition: canonical_competition(&tournament),
                date,
                season,
                round: None,
                stage: None,
                home_team: home,
                away_team: away,
                home_goal: hg,
                away_goal: ag,
                arena: None,
                source: "BR-Football-Dataset.csv".to_string(),
            });
        }
        Ok(())
    }

    fn load_novo(&mut self, path: &Path) -> Result<(), Box<dyn Error>> {
        for row in read_rows(path)? {
            let (hg, ag) = match (
                parse_int(&row, "Gols_mandante"),
                parse_int(&row, "Gols_visitante"),
            ) {
                (Some(h), Some(a)) => (h, a),
                _ => continue,
            };
            let home = match get(&row, "Equipe_mandante") {
                Some(v) => v.to_string(),
                None => continue,
            };
            let away = match get(&row, "Equipe_visitante") {
                Some(v) => v.to_string(),
                None => continue,
            };
            self.matches.push(Match {
                competition: "Brasileirão Série A".to_string(),
                date: get(&row, "Data").and_then(parse_date),
                season: parse_int(&row, "Ano").unwrap_or(0),
                round: get(&row, "Rodada").map(|s| s.to_string()),
                stage: None,
                home_team: home,
                away_team: away,
                home_goal: hg,
                away_goal: ag,
                arena: get(&row, "Arena").map(|s| s.to_string()),
                source: "novo_campeonato_brasileiro.csv".to_string(),
            });
        }
        Ok(())
    }

    fn load_fifa(&mut self, path: &Path) -> Result<(), Box<dyn Error>> {
        for row in read_rows(path)? {
            let name = match get(&row, "Name") {
                Some(v) => v.to_string(),
                None => continue,
            };
            let overall = parse_int(&row, "Overall").unwrap_or(0);
            self.players.push(Player {
                id: get(&row, "ID").unwrap_or("").to_string(),
                name,
                age: parse_int(&row, "Age"),
                nationality: get(&row, "Nationality").unwrap_or("").to_string(),
                overall,
                potential: parse_int(&row, "Potential").unwrap_or(0),
                club: get(&row, "Club").unwrap_or("").to_string(),
                position: get(&row, "Position").unwrap_or("").to_string(),
                jersey_number: get(&row, "Jersey Number").map(|s| s.to_string()),
                height: get(&row, "Height").map(|s| s.to_string()),
                weight: get(&row, "Weight").map(|s| s.to_string()),
            });
        }
        Ok(())
    }

    /// Several datasets cover the same competition+season with incompatible
    /// team-naming conventions, so simply merging them would double-count
    /// fixtures and split clubs across spellings. Instead we keep, for each
    /// (competition, season), the single source that contributes the most
    /// matches — yielding an internally-consistent canonical view with correct
    /// counts. Because each source covers a different range of seasons, their
    /// union still spans the full dataset.
    fn retain_primary_sources(&mut self) {
        // Count matches per (competition, season, source).
        let mut counts: HashMap<(String, i32), HashMap<String, usize>> = HashMap::new();
        for m in &self.matches {
            *counts
                .entry((m.competition.clone(), m.season))
                .or_default()
                .entry(m.source.clone())
                .or_insert(0) += 1;
        }
        // Choose the winning source for each group (most matches, ties broken
        // deterministically by source name).
        let mut winner: HashMap<(String, i32), String> = HashMap::new();
        for (group, sources) in counts {
            if let Some((src, _)) = sources
                .into_iter()
                .max_by(|a, b| a.1.cmp(&b.1).then_with(|| b.0.cmp(&a.0)))
            {
                winner.insert(group, src);
            }
        }
        self.matches.retain(|m| {
            winner
                .get(&(m.competition.clone(), m.season))
                .map(|w| w == &m.source)
                .unwrap_or(false)
        });
    }
}

/// Map a raw tournament label onto a canonical competition name.
fn canonical_competition(raw: &str) -> String {
    let low = raw.to_lowercase();
    if low.contains("copa do brasil") {
        "Copa do Brasil".to_string()
    } else if low.contains("libertadores") {
        "Copa Libertadores".to_string()
    } else if low.contains("serie a") || low.contains("série a") {
        "Brasileirão Série A".to_string()
    } else if low.contains("serie b") || low.contains("série b") {
        "Brasileirão Série B".to_string()
    } else if low.contains("serie c") || low.contains("série c") {
        "Brasileirão Série C".to_string()
    } else {
        raw.to_string()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_iso_with_time() {
        assert_eq!(parse_date("2012-05-19 18:30:00").as_deref(), Some("2012-05-19"));
    }

    #[test]
    fn parses_plain_iso() {
        assert_eq!(parse_date("2023-09-24").as_deref(), Some("2023-09-24"));
    }

    #[test]
    fn parses_brazilian_format() {
        assert_eq!(parse_date("29/03/2003").as_deref(), Some("2003-03-29"));
        assert_eq!(parse_date("9/3/2003").as_deref(), Some("2003-03-09"));
    }

    #[test]
    fn rejects_garbage() {
        assert_eq!(parse_date(""), None);
        assert_eq!(parse_date("not-a-date"), None);
    }
}
