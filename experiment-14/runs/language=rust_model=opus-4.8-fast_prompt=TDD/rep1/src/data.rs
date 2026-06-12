// data - CSV loaders for the six provided Kaggle datasets.
//
// Each match dataset has a different column layout, so loaders resolve columns
// by header name (tolerating the UTF-8 BOM on the FIFA file and the quoting
// styles used across files) and fold every row into the unified `Match` type.
// Goals are parsed leniently because some files store them as floats ("1.0")
// and others as quoted integers ("2"). Rows whose scores cannot be parsed are
// skipped rather than aborting the whole load.

use std::collections::HashMap;
use std::error::Error;
use std::path::Path;

use csv::ReaderBuilder;

use crate::model::{parse_date, Competition, Match, Player};

/// Maps trimmed header names to their column index.
struct Headers {
    index: HashMap<String, usize>,
}

impl Headers {
    fn from_record(rec: &csv::StringRecord) -> Headers {
        let mut index = HashMap::new();
        for (i, name) in rec.iter().enumerate() {
            // Strip a leading BOM and surrounding whitespace from header names.
            let clean = name.trim_start_matches('\u{feff}').trim().to_string();
            index.insert(clean, i);
        }
        Headers { index }
    }

    fn get<'a>(&self, rec: &'a csv::StringRecord, name: &str) -> &'a str {
        match self.index.get(name) {
            Some(&i) => rec.get(i).unwrap_or("").trim(),
            None => "",
        }
    }
}

/// Parse a goal count tolerating "2", "1.0" and surrounding quotes/space.
pub fn parse_goal(raw: &str) -> Option<u32> {
    let s = raw.trim().trim_matches('"').trim();
    if s.is_empty() || s.eq_ignore_ascii_case("NA") {
        return None;
    }
    if let Ok(n) = s.parse::<u32>() {
        return Some(n);
    }
    if let Ok(f) = s.parse::<f64>() {
        if f >= 0.0 {
            return Some(f.round() as u32);
        }
    }
    None
}

/// Parse a season year, optionally falling back to the year in `date`.
fn parse_season(raw: &str, date: &Option<String>) -> i32 {
    if let Ok(y) = raw.trim().parse::<i32>() {
        return y;
    }
    if let Some(d) = date {
        if let Some(y) = d.get(0..4).and_then(|s| s.parse::<i32>().ok()) {
            return y;
        }
    }
    0
}

fn opt(s: &str) -> Option<String> {
    let t = s.trim();
    if t.is_empty() {
        None
    } else {
        Some(t.to_string())
    }
}

fn open(path: &Path) -> Result<csv::Reader<std::fs::File>, Box<dyn Error>> {
    let rdr = ReaderBuilder::new().flexible(true).from_path(path)?;
    Ok(rdr)
}

/// Load `Brasileirao_Matches.csv`.
pub fn load_brasileirao(path: &Path) -> Result<Vec<Match>, Box<dyn Error>> {
    let mut rdr = open(path)?;
    let headers = Headers::from_record(&rdr.headers()?.clone());
    let mut out = Vec::new();
    for rec in rdr.records() {
        let rec = rec?;
        let (hg, ag) = match (
            parse_goal(headers.get(&rec, "home_goal")),
            parse_goal(headers.get(&rec, "away_goal")),
        ) {
            (Some(h), Some(a)) => (h, a),
            _ => continue,
        };
        let date = parse_date(headers.get(&rec, "datetime"));
        out.push(Match {
            competition: Competition::Brasileirao,
            season: parse_season(headers.get(&rec, "season"), &date),
            date,
            round: opt(headers.get(&rec, "round")),
            stage: None,
            home_team: headers.get(&rec, "home_team").to_string(),
            away_team: headers.get(&rec, "away_team").to_string(),
            home_state: opt(headers.get(&rec, "home_team_state")),
            away_state: opt(headers.get(&rec, "away_team_state")),
            home_goal: hg,
            away_goal: ag,
            source_priority: 0,
        });
    }
    Ok(out)
}

/// Load `Brazilian_Cup_Matches.csv`.
pub fn load_copa_do_brasil(path: &Path) -> Result<Vec<Match>, Box<dyn Error>> {
    let mut rdr = open(path)?;
    let headers = Headers::from_record(&rdr.headers()?.clone());
    let mut out = Vec::new();
    for rec in rdr.records() {
        let rec = rec?;
        let (hg, ag) = match (
            parse_goal(headers.get(&rec, "home_goal")),
            parse_goal(headers.get(&rec, "away_goal")),
        ) {
            (Some(h), Some(a)) => (h, a),
            _ => continue,
        };
        let date = parse_date(headers.get(&rec, "datetime"));
        out.push(Match {
            competition: Competition::CopaDoBrasil,
            season: parse_season(headers.get(&rec, "season"), &date),
            date,
            round: opt(headers.get(&rec, "round")),
            stage: None,
            home_team: headers.get(&rec, "home_team").to_string(),
            away_team: headers.get(&rec, "away_team").to_string(),
            home_state: None,
            away_state: None,
            home_goal: hg,
            away_goal: ag,
            source_priority: 0,
        });
    }
    Ok(out)
}

/// Load `Libertadores_Matches.csv`.
pub fn load_libertadores(path: &Path) -> Result<Vec<Match>, Box<dyn Error>> {
    let mut rdr = open(path)?;
    let headers = Headers::from_record(&rdr.headers()?.clone());
    let mut out = Vec::new();
    for rec in rdr.records() {
        let rec = rec?;
        let (hg, ag) = match (
            parse_goal(headers.get(&rec, "home_goal")),
            parse_goal(headers.get(&rec, "away_goal")),
        ) {
            (Some(h), Some(a)) => (h, a),
            _ => continue,
        };
        let date = parse_date(headers.get(&rec, "datetime"));
        out.push(Match {
            competition: Competition::Libertadores,
            season: parse_season(headers.get(&rec, "season"), &date),
            date,
            round: None,
            stage: opt(headers.get(&rec, "stage")),
            home_team: headers.get(&rec, "home_team").to_string(),
            away_team: headers.get(&rec, "away_team").to_string(),
            home_state: None,
            away_state: None,
            home_goal: hg,
            away_goal: ag,
            source_priority: 0,
        });
    }
    Ok(out)
}

/// Load the extended `BR-Football-Dataset.csv` (tournament label per row).
pub fn load_br_football(path: &Path) -> Result<Vec<Match>, Box<dyn Error>> {
    let mut rdr = open(path)?;
    let headers = Headers::from_record(&rdr.headers()?.clone());
    let mut out = Vec::new();
    for rec in rdr.records() {
        let rec = rec?;
        let (hg, ag) = match (
            parse_goal(headers.get(&rec, "home_goal")),
            parse_goal(headers.get(&rec, "away_goal")),
        ) {
            (Some(h), Some(a)) => (h, a),
            _ => continue,
        };
        let date = parse_date(headers.get(&rec, "date"));
        let competition = Competition::from_label(headers.get(&rec, "tournament"));
        out.push(Match {
            competition,
            season: parse_season("", &date),
            date,
            round: None,
            stage: None,
            home_team: headers.get(&rec, "home").to_string(),
            away_team: headers.get(&rec, "away").to_string(),
            home_state: None,
            away_state: None,
            home_goal: hg,
            away_goal: ag,
            // Extended dataset: least authoritative for Brasileirão/Copa, but
            // the only source for some recent seasons and the lower divisions.
            source_priority: 2,
        });
    }
    Ok(out)
}

/// Load the historical `novo_campeonato_brasileiro.csv` (Portuguese columns).
pub fn load_historical(path: &Path) -> Result<Vec<Match>, Box<dyn Error>> {
    let mut rdr = open(path)?;
    let headers = Headers::from_record(&rdr.headers()?.clone());
    let mut out = Vec::new();
    for rec in rdr.records() {
        let rec = rec?;
        let (hg, ag) = match (
            parse_goal(headers.get(&rec, "Gols_mandante")),
            parse_goal(headers.get(&rec, "Gols_visitante")),
        ) {
            (Some(h), Some(a)) => (h, a),
            _ => continue,
        };
        let date = parse_date(headers.get(&rec, "Data"));
        out.push(Match {
            competition: Competition::Brasileirao,
            season: parse_season(headers.get(&rec, "Ano"), &date),
            date,
            round: opt(headers.get(&rec, "Rodada")),
            stage: None,
            home_team: headers.get(&rec, "Equipe_mandante").to_string(),
            away_team: headers.get(&rec, "Equipe_visitante").to_string(),
            home_state: opt(headers.get(&rec, "Mandante_UF")),
            away_state: opt(headers.get(&rec, "Visitante_UF")),
            home_goal: hg,
            away_goal: ag,
            // Historical file: authoritative for 2003-2011, otherwise overlaps
            // the cleaner Brasileirao_Matches dataset.
            source_priority: 1,
        });
    }
    Ok(out)
}

/// Load the FIFA player database `fifa_data.csv`.
pub fn load_players(path: &Path) -> Result<Vec<Player>, Box<dyn Error>> {
    let mut rdr = open(path)?;
    let headers = Headers::from_record(&rdr.headers()?.clone());
    let mut out = Vec::new();
    for rec in rdr.records() {
        let rec = rec?;
        let id = match headers.get(&rec, "ID").parse::<i64>() {
            Ok(v) => v,
            Err(_) => continue,
        };
        let overall = headers.get(&rec, "Overall").parse::<u32>().unwrap_or(0);
        let potential = headers.get(&rec, "Potential").parse::<u32>().unwrap_or(0);
        let age = headers.get(&rec, "Age").parse::<u32>().ok();
        out.push(Player {
            id,
            name: headers.get(&rec, "Name").to_string(),
            age,
            nationality: headers.get(&rec, "Nationality").to_string(),
            overall,
            potential,
            club: headers.get(&rec, "Club").to_string(),
            position: headers.get(&rec, "Position").to_string(),
        });
    }
    Ok(out)
}

/// Load every match dataset from `dir`, concatenated into one vector.
pub fn load_all_matches(dir: &Path) -> Result<Vec<Match>, Box<dyn Error>> {
    let mut all = Vec::new();
    all.extend(load_brasileirao(&dir.join("Brasileirao_Matches.csv"))?);
    all.extend(load_copa_do_brasil(&dir.join("Brazilian_Cup_Matches.csv"))?);
    all.extend(load_libertadores(&dir.join("Libertadores_Matches.csv"))?);
    all.extend(load_br_football(&dir.join("BR-Football-Dataset.csv"))?);
    all.extend(load_historical(
        &dir.join("novo_campeonato_brasileiro.csv"),
    )?);
    Ok(all)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn data_dir() -> std::path::PathBuf {
        std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("data/kaggle")
    }

    #[test]
    fn parse_goal_variants() {
        assert_eq!(parse_goal("2"), Some(2));
        assert_eq!(parse_goal("1.0"), Some(1));
        assert_eq!(parse_goal("\"3\""), Some(3));
        assert_eq!(parse_goal(""), None);
        assert_eq!(parse_goal("NA"), None);
    }

    #[test]
    fn loads_brasileirao() {
        let m = load_brasileirao(&data_dir().join("Brasileirao_Matches.csv")).unwrap();
        // 4180 rows in the file; 82 carry "NA" scores (unplayed fixtures) and
        // are skipped so they cannot pollute statistics with phantom draws.
        assert_eq!(m.len(), 4180 - 82);
        assert!(m.iter().all(|x| x.competition == Competition::Brasileirao));
        // First row: Palmeiras-SP 1-1 Portuguesa-SP, 2012 round 1.
        let first = &m[0];
        assert_eq!(first.home_key(), "palmeiras");
        assert_eq!(first.season, 2012);
        assert_eq!(first.date.as_deref(), Some("2012-05-19"));
    }

    #[test]
    fn loads_copa_do_brasil() {
        let m = load_copa_do_brasil(&data_dir().join("Brazilian_Cup_Matches.csv")).unwrap();
        // 1337 rows; 16 unplayed ("NA") fixtures are skipped.
        assert_eq!(m.len(), 1337 - 16);
        assert!(m.iter().all(|x| x.competition == Competition::CopaDoBrasil));
    }

    #[test]
    fn loads_libertadores() {
        let m = load_libertadores(&data_dir().join("Libertadores_Matches.csv")).unwrap();
        // 1255 rows; 2 unplayed fixtures (scores stored as "-") are skipped.
        assert_eq!(m.len(), 1255 - 2);
        assert!(m.iter().any(|x| x.stage.as_deref() == Some("final")));
        // Quoted-integer goals must parse.
        assert!(m.iter().all(|x| x.home_goal <= 20));
    }

    #[test]
    fn loads_br_football_with_tournament_labels() {
        let m = load_br_football(&data_dir().join("BR-Football-Dataset.csv")).unwrap();
        assert_eq!(m.len(), 10296);
        assert!(m.iter().any(|x| x.competition == Competition::CopaDoBrasil));
        assert!(m.iter().any(|x| x.competition == Competition::Brasileirao));
    }

    #[test]
    fn loads_historical() {
        let m = load_historical(&data_dir().join("novo_campeonato_brasileiro.csv")).unwrap();
        assert_eq!(m.len(), 6886);
        // Brazilian date format converted to ISO.
        let first = &m[0];
        assert_eq!(first.date.as_deref(), Some("2003-03-29"));
        assert_eq!(first.season, 2003);
    }

    #[test]
    fn loads_players() {
        let p = load_players(&data_dir().join("fifa_data.csv")).unwrap();
        assert_eq!(p.len(), 18207);
        let messi = &p[0];
        assert_eq!(messi.name, "L. Messi");
        assert_eq!(messi.overall, 94);
        assert_eq!(messi.nationality, "Argentina");
        // Brazilian players are present.
        assert!(p.iter().filter(|x| x.nationality == "Brazil").count() > 500);
    }

    #[test]
    fn loads_all_matches_combined() {
        let m = load_all_matches(&data_dir()).unwrap();
        // Sum of playable matches across the five datasets (unplayed skipped).
        assert_eq!(
            m.len(),
            (4180 - 82) + (1337 - 16) + (1255 - 2) + 10296 + 6886
        );
    }
}
