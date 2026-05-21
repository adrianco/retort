//! CSV loading and the in-memory `Database`.
//!
//! Loads the six Kaggle datasets named in `TASK.md` into a single in-memory
//! store. Each match CSV has its own column layout, date format and team-name
//! convention, so there is a dedicated loader per file; all of them funnel into
//! the shared `Match` model with a canonical competition name.
//!
//! Because several datasets overlap (Brasileirão Série A appears in three of
//! them), `Database::canonical_matches` picks one authoritative source per
//! (competition, season) group so statistics are not double-counted.

use std::collections::HashMap;
use std::error::Error;
use std::path::{Path, PathBuf};

use csv::StringRecord;

use crate::models::{competition, Date, Match, Player};
use crate::normalize::TeamRegistry;

/// The complete in-memory dataset.
pub struct Database {
    pub matches: Vec<Match>,
    pub players: Vec<Player>,
}

/// Parse a date string in any of the formats present in the datasets:
/// `YYYY-MM-DD HH:MM:SS`, `YYYY-MM-DD`, or Brazilian `DD/MM/YYYY`.
pub fn parse_date(s: &str) -> Option<Date> {
    let s = s.trim();
    if s.is_empty() {
        return None;
    }
    let date_part = s.split_whitespace().next().unwrap_or(s);

    if date_part.contains('/') {
        let p: Vec<&str> = date_part.split('/').collect();
        if p.len() == 3 {
            let day = p[0].trim().parse().ok()?;
            let month = p[1].trim().parse().ok()?;
            let year = p[2].trim().parse().ok()?;
            return valid(year, month, day);
        }
    } else if date_part.contains('-') {
        let p: Vec<&str> = date_part.split('-').collect();
        if p.len() == 3 {
            let year = p[0].trim().parse().ok()?;
            let month = p[1].trim().parse().ok()?;
            let day = p[2].trim().parse().ok()?;
            return valid(year, month, day);
        }
    }
    None
}

fn valid(year: i32, month: u32, day: u32) -> Option<Date> {
    if (1900..=2100).contains(&year) && (1..=12).contains(&month) && (1..=31).contains(&day) {
        Some(Date { year, month, day })
    } else {
        None
    }
}

/// Parse a goal count that may be written as an integer (`2`), a quoted
/// integer (`"2"`) or a float (`1.0`, as in the extended-stats dataset).
fn parse_goal(s: &str) -> Option<i32> {
    let t = s.trim();
    if t.is_empty() {
        return None;
    }
    if let Ok(i) = t.parse::<i32>() {
        return Some(i);
    }
    if let Ok(f) = t.parse::<f64>() {
        if f.is_finite() {
            return Some(f as i32);
        }
    }
    None
}

fn parse_int(s: &str) -> Option<i32> {
    let t = s.trim();
    if t.is_empty() {
        return None;
    }
    t.parse::<i32>()
        .ok()
        .or_else(|| t.parse::<f64>().ok().map(|f| f as i32))
}

/// Build a header-name -> column-index map, trimming a leading UTF-8 BOM that
/// `fifa_data.csv` carries on its first column.
fn header_index(rdr: &mut csv::Reader<std::fs::File>) -> Result<HashMap<String, usize>, Box<dyn Error>> {
    let mut map = HashMap::new();
    for (i, name) in rdr.headers()?.iter().enumerate() {
        let clean = name.trim_start_matches('\u{feff}').trim().to_string();
        map.insert(clean, i);
    }
    Ok(map)
}

fn open(path: &Path) -> Result<csv::Reader<std::fs::File>, Box<dyn Error>> {
    Ok(csv::ReaderBuilder::new()
        .has_headers(true)
        .flexible(true)
        .from_path(path)?)
}

/// Fetch a trimmed field by header name; returns `""` when absent.
fn field<'a>(rec: &'a StringRecord, idx: &HashMap<String, usize>, name: &str) -> &'a str {
    idx.get(name)
        .and_then(|&i| rec.get(i))
        .map(str::trim)
        .unwrap_or("")
}

/// Build a `Match` with the *raw* team names still in the `home`/`away`
/// fields and the identity keys left blank. `Database::load` rewrites these in
/// a second pass once it knows which base names are ambiguous (see
/// `normalize::ambiguous_bases`).
fn make_match(
    comp: &str,
    season: i32,
    date: Option<Date>,
    round: Option<String>,
    stage: Option<String>,
    home_raw: &str,
    away_raw: &str,
    home_goal: i32,
    away_goal: i32,
    dataset: &str,
) -> Match {
    Match {
        competition: comp.to_string(),
        season,
        date,
        round,
        stage,
        home: home_raw.to_string(),
        away: away_raw.to_string(),
        home_key: String::new(),
        away_key: String::new(),
        home_goal,
        away_goal,
        dataset: dataset.to_string(),
    }
}

impl Database {
    /// Load every dataset found under `data_dir` (expected to be the
    /// `data/kaggle` directory). Missing optional files are skipped with a
    /// warning on stderr rather than aborting the load.
    pub fn load(data_dir: impl AsRef<Path>) -> Result<Database, Box<dyn Error>> {
        let dir = data_dir.as_ref();
        let mut matches = Vec::new();
        let mut players = Vec::new();

        load_optional(&mut matches, dir, "Brasileirao_Matches.csv", load_brasileirao);
        load_optional(&mut matches, dir, "Brazilian_Cup_Matches.csv", load_cup);
        load_optional(&mut matches, dir, "Libertadores_Matches.csv", load_libertadores);
        load_optional(&mut matches, dir, "BR-Football-Dataset.csv", load_br_football);
        load_optional(&mut matches, dir, "novo_campeonato_brasileiro.csv", load_novo);

        let fifa = dir.join("fifa_data.csv");
        if fifa.exists() {
            match load_fifa(&fifa) {
                Ok(mut p) => players.append(&mut p),
                Err(e) => eprintln!("warning: failed to load fifa_data.csv: {e}"),
            }
        } else {
            eprintln!("warning: fifa_data.csv not found in {}", dir.display());
        }

        if matches.is_empty() && players.is_empty() {
            return Err(format!(
                "no datasets could be loaded from {}",
                dir.display()
            )
            .into());
        }

        // Second pass: now that every team name has been seen, build the
        // ambiguity registry and resolve each match's identity keys and
        // canonical display names.
        let registry = TeamRegistry::build(
            matches
                .iter()
                .flat_map(|m| [m.home.as_str(), m.away.as_str()]),
        );
        for m in &mut matches {
            let raw_home = std::mem::take(&mut m.home);
            let raw_away = std::mem::take(&mut m.away);
            m.home_key = registry.id(&raw_home);
            m.away_key = registry.id(&raw_away);
            m.home = registry.display(&raw_home);
            m.away = registry.display(&raw_away);
        }

        Ok(Database { matches, players })
    }

    /// Return one authoritative match per `(competition, season)` group.
    ///
    /// Several CSVs cover the same league seasons. For each group this keeps
    /// only the source file with the most rows (ties broken by a fixed source
    /// priority), so head-to-head records, standings and aggregate statistics
    /// are computed from a de-duplicated set.
    pub fn canonical_matches(&self) -> Vec<&Match> {
        // (competition, season) -> dataset -> row count
        let mut groups: HashMap<(&str, i32), HashMap<&str, usize>> = HashMap::new();
        for m in &self.matches {
            *groups
                .entry((m.competition.as_str(), m.season))
                .or_default()
                .entry(m.dataset.as_str())
                .or_default() += 1;
        }

        let mut chosen: HashMap<(&str, i32), &str> = HashMap::new();
        for (key, counts) in &groups {
            let best = counts
                .iter()
                .max_by_key(|(ds, count)| (**count, source_priority(ds)))
                .map(|(ds, _)| *ds)
                .unwrap();
            chosen.insert(*key, best);
        }

        self.matches
            .iter()
            .filter(|m| {
                chosen
                    .get(&(m.competition.as_str(), m.season))
                    .map(|ds| *ds == m.dataset.as_str())
                    .unwrap_or(false)
            })
            .collect()
    }
}

/// Priority used to break ties when two source files have equal row counts
/// for the same competition+season. Dedicated single-competition files rank
/// above the broad multi-competition aggregates.
fn source_priority(dataset: &str) -> i32 {
    match dataset {
        "Brasileirao_Matches.csv" => 4,
        "Brazilian_Cup_Matches.csv" => 4,
        "Libertadores_Matches.csv" => 4,
        "novo_campeonato_brasileiro.csv" => 3,
        "BR-Football-Dataset.csv" => 2,
        _ => 1,
    }
}

fn load_optional(
    out: &mut Vec<Match>,
    dir: &Path,
    file: &str,
    loader: fn(&Path) -> Result<Vec<Match>, Box<dyn Error>>,
) {
    let path: PathBuf = dir.join(file);
    if !path.exists() {
        eprintln!("warning: {file} not found in {}", dir.display());
        return;
    }
    match loader(&path) {
        Ok(mut rows) => out.append(&mut rows),
        Err(e) => eprintln!("warning: failed to load {file}: {e}"),
    }
}

/// `Brasileirao_Matches.csv` — Brasileirão Série A, team names carry a state
/// suffix ("Palmeiras-SP").
fn load_brasileirao(path: &Path) -> Result<Vec<Match>, Box<dyn Error>> {
    let mut rdr = open(path)?;
    let idx = header_index(&mut rdr)?;
    let mut out = Vec::new();
    for rec in rdr.records() {
        let rec = rec?;
        let (Some(hg), Some(ag)) = (
            parse_goal(field(&rec, &idx, "home_goal")),
            parse_goal(field(&rec, &idx, "away_goal")),
        ) else {
            continue;
        };
        let season = parse_int(field(&rec, &idx, "season")).unwrap_or(0);
        let round = field(&rec, &idx, "round");
        out.push(make_match(
            competition::SERIE_A,
            season,
            parse_date(field(&rec, &idx, "datetime")),
            (!round.is_empty()).then(|| round.to_string()),
            None,
            field(&rec, &idx, "home_team"),
            field(&rec, &idx, "away_team"),
            hg,
            ag,
            "Brasileirao_Matches.csv",
        ));
    }
    Ok(out)
}

/// `Brazilian_Cup_Matches.csv` — Copa do Brasil.
fn load_cup(path: &Path) -> Result<Vec<Match>, Box<dyn Error>> {
    let mut rdr = open(path)?;
    let idx = header_index(&mut rdr)?;
    let mut out = Vec::new();
    for rec in rdr.records() {
        let rec = rec?;
        let (Some(hg), Some(ag)) = (
            parse_goal(field(&rec, &idx, "home_goal")),
            parse_goal(field(&rec, &idx, "away_goal")),
        ) else {
            continue;
        };
        let season = parse_int(field(&rec, &idx, "season")).unwrap_or(0);
        let round = field(&rec, &idx, "round");
        out.push(make_match(
            competition::COPA_DO_BRASIL,
            season,
            parse_date(field(&rec, &idx, "datetime")),
            (!round.is_empty()).then(|| round.to_string()),
            None,
            field(&rec, &idx, "home_team"),
            field(&rec, &idx, "away_team"),
            hg,
            ag,
            "Brazilian_Cup_Matches.csv",
        ));
    }
    Ok(out)
}

/// `Libertadores_Matches.csv` — Copa Libertadores, goals are quoted strings,
/// rows carry a tournament `stage` instead of a round number.
fn load_libertadores(path: &Path) -> Result<Vec<Match>, Box<dyn Error>> {
    let mut rdr = open(path)?;
    let idx = header_index(&mut rdr)?;
    let mut out = Vec::new();
    for rec in rdr.records() {
        let rec = rec?;
        let (Some(hg), Some(ag)) = (
            parse_goal(field(&rec, &idx, "home_goal")),
            parse_goal(field(&rec, &idx, "away_goal")),
        ) else {
            continue;
        };
        let season = parse_int(field(&rec, &idx, "season")).unwrap_or(0);
        let stage = field(&rec, &idx, "stage");
        out.push(make_match(
            competition::LIBERTADORES,
            season,
            parse_date(field(&rec, &idx, "datetime")),
            None,
            (!stage.is_empty()).then(|| stage.to_string()),
            field(&rec, &idx, "home_team"),
            field(&rec, &idx, "away_team"),
            hg,
            ag,
            "Libertadores_Matches.csv",
        ));
    }
    Ok(out)
}

/// `BR-Football-Dataset.csv` — extended stats; competition is in `tournament`,
/// goals are floats, and the season is derived from the `date` column.
fn load_br_football(path: &Path) -> Result<Vec<Match>, Box<dyn Error>> {
    let mut rdr = open(path)?;
    let idx = header_index(&mut rdr)?;
    let mut out = Vec::new();
    for rec in rdr.records() {
        let rec = rec?;
        let (Some(hg), Some(ag)) = (
            parse_goal(field(&rec, &idx, "home_goal")),
            parse_goal(field(&rec, &idx, "away_goal")),
        ) else {
            continue;
        };
        let date = parse_date(field(&rec, &idx, "date"));
        let Some(season) = date.map(|d| d.year) else {
            continue;
        };
        out.push(make_match(
            &canon_competition(field(&rec, &idx, "tournament")),
            season,
            date,
            None,
            None,
            field(&rec, &idx, "home"),
            field(&rec, &idx, "away"),
            hg,
            ag,
            "BR-Football-Dataset.csv",
        ));
    }
    Ok(out)
}

/// `novo_campeonato_brasileiro.csv` — historical Brasileirão 2003-2019,
/// Portuguese column names and `DD/MM/YYYY` dates.
///
/// This file writes most team names without a state suffix but carries the
/// state in separate `*_UF` columns; the suffix is re-attached here so these
/// clubs resolve to the same identity as the suffixed names in the other files.
fn load_novo(path: &Path) -> Result<Vec<Match>, Box<dyn Error>> {
    let mut rdr = open(path)?;
    let idx = header_index(&mut rdr)?;
    let mut out = Vec::new();
    for rec in rdr.records() {
        let rec = rec?;
        let (Some(hg), Some(ag)) = (
            parse_goal(field(&rec, &idx, "Gols_mandante")),
            parse_goal(field(&rec, &idx, "Gols_visitante")),
        ) else {
            continue;
        };
        let season = parse_int(field(&rec, &idx, "Ano")).unwrap_or(0);
        let round = field(&rec, &idx, "Rodada");
        let home = with_state(
            field(&rec, &idx, "Equipe_mandante"),
            field(&rec, &idx, "Mandante_UF"),
        );
        let away = with_state(
            field(&rec, &idx, "Equipe_visitante"),
            field(&rec, &idx, "Visitante_UF"),
        );
        out.push(make_match(
            competition::SERIE_A,
            season,
            parse_date(field(&rec, &idx, "Data")),
            (!round.is_empty()).then(|| round.to_string()),
            None,
            &home,
            &away,
            hg,
            ag,
            "novo_campeonato_brasileiro.csv",
        ));
    }
    Ok(out)
}

/// Append a `-UF` state suffix to a team name when the name does not already
/// carry one and `uf` is a valid two-letter code.
fn with_state(name: &str, uf: &str) -> String {
    let uf = uf.trim();
    let valid_code = uf.chars().count() == 2 && uf.chars().all(|c| c.is_ascii_uppercase());
    if valid_code && crate::normalize::split_suffix(name).1.is_empty() {
        format!("{}-{}", name.trim(), uf)
    } else {
        name.trim().to_string()
    }
}

/// Map a raw `tournament` value from the extended-stats dataset to the
/// canonical competition name used everywhere else.
fn canon_competition(raw: &str) -> String {
    match raw.trim() {
        "Serie A" => competition::SERIE_A,
        "Serie B" => competition::SERIE_B,
        "Serie C" => competition::SERIE_C,
        "Copa do Brasil" => competition::COPA_DO_BRASIL,
        other => other,
    }
    .to_string()
}

/// `fifa_data.csv` — FIFA player database (~90 columns; a subset is kept).
fn load_fifa(path: &Path) -> Result<Vec<Player>, Box<dyn Error>> {
    let mut rdr = open(path)?;
    let idx = header_index(&mut rdr)?;
    let mut out = Vec::new();
    for rec in rdr.records() {
        let rec = rec?;
        let name = field(&rec, &idx, "Name");
        if name.is_empty() {
            continue;
        }
        out.push(Player {
            id: parse_int(field(&rec, &idx, "ID")).unwrap_or(0) as i64,
            name: name.to_string(),
            name_key: crate::normalize::fold(name),
            age: parse_int(field(&rec, &idx, "Age")).unwrap_or(0),
            nationality: field(&rec, &idx, "Nationality").to_string(),
            overall: parse_int(field(&rec, &idx, "Overall")).unwrap_or(0),
            potential: parse_int(field(&rec, &idx, "Potential")).unwrap_or(0),
            club: field(&rec, &idx, "Club").to_string(),
            position: field(&rec, &idx, "Position").to_string(),
            jersey: parse_int(field(&rec, &idx, "Jersey Number")),
            height: field(&rec, &idx, "Height").to_string(),
            weight: field(&rec, &idx, "Weight").to_string(),
            value: field(&rec, &idx, "Value").to_string(),
        });
    }
    Ok(out)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn date_formats() {
        assert_eq!(
            parse_date("2012-05-19 18:30:00"),
            Some(Date { year: 2012, month: 5, day: 19 })
        );
        assert_eq!(
            parse_date("29/03/2003"),
            Some(Date { year: 2003, month: 3, day: 29 })
        );
        assert_eq!(
            parse_date("2023-09-24"),
            Some(Date { year: 2023, month: 9, day: 24 })
        );
        assert_eq!(parse_date(""), None);
    }

    #[test]
    fn goal_formats() {
        assert_eq!(parse_goal("2"), Some(2));
        assert_eq!(parse_goal("1.0"), Some(1));
        assert_eq!(parse_goal(""), None);
    }
}
