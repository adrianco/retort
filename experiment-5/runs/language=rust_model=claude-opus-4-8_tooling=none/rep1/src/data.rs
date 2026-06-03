//! CSV loading and the in-memory `Dataset`.

use std::collections::{HashMap, HashSet};
use std::path::{Path, PathBuf};

use crate::model::{Match, Player};

/// Default directory containing the Kaggle CSV files.
pub const DEFAULT_DATA_DIR: &str = "data/kaggle";

#[derive(Default)]
pub struct Dataset {
    pub matches: Vec<Match>,
    pub players: Vec<Player>,
    /// Per-source match counts, for reporting.
    pub source_counts: Vec<(String, usize)>,
}

/// Build a header-name -> column-index map from a CSV header record.
fn header_index(headers: &csv::StringRecord) -> HashMap<String, usize> {
    headers
        .iter()
        .enumerate()
        .map(|(i, h)| (h.trim().trim_start_matches('\u{feff}').to_string(), i))
        .collect()
}

fn get<'a>(rec: &'a csv::StringRecord, idx: &HashMap<String, usize>, name: &str) -> &'a str {
    idx.get(name).and_then(|&i| rec.get(i)).unwrap_or("").trim()
}

fn parse_goal(s: &str) -> Option<i32> {
    let t = s.trim().trim_matches('"');
    if t.is_empty() || t.eq_ignore_ascii_case("na") || t == "-" {
        return None;
    }
    t.parse::<f64>().ok().map(|f| f.round() as i32)
}

fn parse_f64(s: &str) -> Option<f64> {
    let t = s.trim();
    if t.is_empty() || t.eq_ignore_ascii_case("na") {
        return None;
    }
    t.parse::<f64>().ok()
}

fn parse_season(s: &str) -> Option<i32> {
    let t = s.trim();
    if t.is_empty() || t.eq_ignore_ascii_case("na") {
        return None;
    }
    // Some season fields look like "2003.01" — keep the leading year.
    t.split(['.', '-']).next()?.parse::<i32>().ok()
}

/// Normalize the various date encodings to ISO `YYYY-MM-DD`.
fn iso_date(raw: &str) -> String {
    let t = raw.trim();
    if t.is_empty() {
        return String::new();
    }
    // "2012-05-19 18:30:00" or "2023-09-24" -> take the date part.
    if t.len() >= 10 && t.as_bytes()[4] == b'-' {
        return t[..10].to_string();
    }
    // Brazilian "DD/MM/YYYY".
    if let Some((d, rest)) = t.split_once('/') {
        if let Some((m, y)) = rest.split_once('/') {
            let y = y.split_whitespace().next().unwrap_or(y);
            if d.len() <= 2 && m.len() <= 2 && y.len() == 4 {
                return format!("{:04}-{:0>2}-{:0>2}", y.parse::<i32>().unwrap_or(0), m, d);
            }
        }
    }
    t.to_string()
}

fn open_reader(path: &Path) -> Result<csv::Reader<std::fs::File>, String> {
    csv::ReaderBuilder::new()
        .flexible(true)
        .from_path(path)
        .map_err(|e| format!("failed to open {}: {e}", path.display()))
}

impl Dataset {
    /// Load from `SOCCER_DATA_DIR` if set, otherwise [`DEFAULT_DATA_DIR`].
    pub fn load_default() -> Result<Dataset, String> {
        let dir = std::env::var("SOCCER_DATA_DIR").unwrap_or_else(|_| DEFAULT_DATA_DIR.to_string());
        Dataset::load(&dir)
    }

    pub fn load(dir: impl AsRef<Path>) -> Result<Dataset, String> {
        let dir = dir.as_ref();
        let mut ds = Dataset::default();
        let mut raw: Vec<Match> = Vec::new();

        let add = |raw: &mut Vec<Match>, counts: &mut Vec<(String, usize)>, label: &str, v: Vec<Match>| {
            counts.push((label.to_string(), v.len()));
            raw.extend(v);
        };

        add(&mut raw, &mut ds.source_counts, "Brasileirão (Brasileirao_Matches.csv)",
            load_brasileirao(&dir.join("Brasileirao_Matches.csv"))?);
        add(&mut raw, &mut ds.source_counts, "Copa do Brasil (Brazilian_Cup_Matches.csv)",
            load_cup(&dir.join("Brazilian_Cup_Matches.csv"))?);
        add(&mut raw, &mut ds.source_counts, "Copa Libertadores (Libertadores_Matches.csv)",
            load_libertadores(&dir.join("Libertadores_Matches.csv"))?);
        add(&mut raw, &mut ds.source_counts, "Brasileirão 2003-2019 (novo_campeonato_brasileiro.csv)",
            load_novo(&dir.join("novo_campeonato_brasileiro.csv"))?);
        add(&mut raw, &mut ds.source_counts, "Extended stats (BR-Football-Dataset.csv)",
            load_br_football(&dir.join("BR-Football-Dataset.csv"))?);

        // Deduplicate the same real match appearing in several files.
        let mut seen: HashSet<String> = HashSet::new();
        for m in raw {
            if seen.insert(m.dedup_key()) {
                ds.matches.push(m);
            }
        }

        ds.players = load_players(&dir.join("fifa_data.csv"))?;
        ds.source_counts
            .push(("FIFA players (fifa_data.csv)".to_string(), ds.players.len()));

        Ok(ds)
    }

    pub fn data_dir() -> PathBuf {
        PathBuf::from(
            std::env::var("SOCCER_DATA_DIR").unwrap_or_else(|_| DEFAULT_DATA_DIR.to_string()),
        )
    }
}

fn load_brasileirao(path: &Path) -> Result<Vec<Match>, String> {
    let mut rdr = open_reader(path)?;
    let idx = header_index(rdr.headers().map_err(|e| e.to_string())?);
    let mut out = Vec::new();
    for rec in rdr.records() {
        let rec = rec.map_err(|e| e.to_string())?;
        let (hg, ag) = match (parse_goal(get(&rec, &idx, "home_goal")), parse_goal(get(&rec, &idx, "away_goal"))) {
            (Some(h), Some(a)) => (h, a),
            _ => continue,
        };
        let mut m = Match::new(
            "Brasileirão Série A",
            iso_date(get(&rec, &idx, "datetime")),
            parse_season(get(&rec, &idx, "season")),
            get(&rec, &idx, "home_team"),
            get(&rec, &idx, "away_team"),
            hg,
            ag,
            "Brasileirao_Matches.csv",
        );
        let r = get(&rec, &idx, "round");
        if !r.is_empty() {
            m.round = Some(r.to_string());
        }
        out.push(m);
    }
    Ok(out)
}

fn load_cup(path: &Path) -> Result<Vec<Match>, String> {
    let mut rdr = open_reader(path)?;
    let idx = header_index(rdr.headers().map_err(|e| e.to_string())?);
    let mut out = Vec::new();
    for rec in rdr.records() {
        let rec = rec.map_err(|e| e.to_string())?;
        let (hg, ag) = match (parse_goal(get(&rec, &idx, "home_goal")), parse_goal(get(&rec, &idx, "away_goal"))) {
            (Some(h), Some(a)) => (h, a),
            _ => continue,
        };
        let mut m = Match::new(
            "Copa do Brasil",
            iso_date(get(&rec, &idx, "datetime")),
            parse_season(get(&rec, &idx, "season")),
            get(&rec, &idx, "home_team"),
            get(&rec, &idx, "away_team"),
            hg,
            ag,
            "Brazilian_Cup_Matches.csv",
        );
        let r = get(&rec, &idx, "round");
        if !r.is_empty() {
            m.round = Some(r.to_string());
        }
        out.push(m);
    }
    Ok(out)
}

fn load_libertadores(path: &Path) -> Result<Vec<Match>, String> {
    let mut rdr = open_reader(path)?;
    let idx = header_index(rdr.headers().map_err(|e| e.to_string())?);
    let mut out = Vec::new();
    for rec in rdr.records() {
        let rec = rec.map_err(|e| e.to_string())?;
        let (hg, ag) = match (parse_goal(get(&rec, &idx, "home_goal")), parse_goal(get(&rec, &idx, "away_goal"))) {
            (Some(h), Some(a)) => (h, a),
            _ => continue,
        };
        let mut m = Match::new(
            "Copa Libertadores",
            iso_date(get(&rec, &idx, "datetime")),
            parse_season(get(&rec, &idx, "season")),
            get(&rec, &idx, "home_team"),
            get(&rec, &idx, "away_team"),
            hg,
            ag,
            "Libertadores_Matches.csv",
        );
        let stage = get(&rec, &idx, "stage");
        if !stage.is_empty() {
            m.stage = Some(stage.to_string());
        }
        out.push(m);
    }
    Ok(out)
}

fn load_novo(path: &Path) -> Result<Vec<Match>, String> {
    let mut rdr = open_reader(path)?;
    let idx = header_index(rdr.headers().map_err(|e| e.to_string())?);
    let mut out = Vec::new();
    for rec in rdr.records() {
        let rec = rec.map_err(|e| e.to_string())?;
        let (hg, ag) = match (parse_goal(get(&rec, &idx, "Gols_mandante")), parse_goal(get(&rec, &idx, "Gols_visitante"))) {
            (Some(h), Some(a)) => (h, a),
            _ => continue,
        };
        let home = format!("{}-{}", get(&rec, &idx, "Equipe_mandante"), get(&rec, &idx, "Mandante_UF"));
        let away = format!("{}-{}", get(&rec, &idx, "Equipe_visitante"), get(&rec, &idx, "Visitante_UF"));
        let mut m = Match::new(
            "Brasileirão Série A",
            iso_date(get(&rec, &idx, "Data")),
            parse_season(get(&rec, &idx, "Ano")),
            home,
            away,
            hg,
            ag,
            "novo_campeonato_brasileiro.csv",
        );
        let r = get(&rec, &idx, "Rodada");
        if !r.is_empty() {
            m.round = Some(r.to_string());
        }
        out.push(m);
    }
    Ok(out)
}

fn load_br_football(path: &Path) -> Result<Vec<Match>, String> {
    let mut rdr = open_reader(path)?;
    let idx = header_index(rdr.headers().map_err(|e| e.to_string())?);
    let mut out = Vec::new();
    for rec in rdr.records() {
        let rec = rec.map_err(|e| e.to_string())?;
        let (hg, ag) = match (parse_goal(get(&rec, &idx, "home_goal")), parse_goal(get(&rec, &idx, "away_goal"))) {
            (Some(h), Some(a)) => (h, a),
            _ => continue,
        };
        let tournament = get(&rec, &idx, "tournament");
        let competition = match tournament {
            "Serie A" => "Brasileirão Série A",
            "Serie B" => "Brasileirão Série B",
            "Serie C" => "Brasileirão Série C",
            other => other,
        };
        let date = iso_date(get(&rec, &idx, "date"));
        let season = date.get(0..4).and_then(|y| y.parse::<i32>().ok());
        let mut m = Match::new(
            competition,
            date,
            season,
            get(&rec, &idx, "home"),
            get(&rec, &idx, "away"),
            hg,
            ag,
            "BR-Football-Dataset.csv",
        );
        m.home_shots = parse_f64(get(&rec, &idx, "home_shots"));
        m.away_shots = parse_f64(get(&rec, &idx, "away_shots"));
        m.home_corner = parse_f64(get(&rec, &idx, "home_corner"));
        m.away_corner = parse_f64(get(&rec, &idx, "away_corner"));
        out.push(m);
    }
    Ok(out)
}

fn parse_int(s: &str) -> Option<i32> {
    let t = s.trim();
    if t.is_empty() {
        return None;
    }
    t.parse::<f64>().ok().map(|f| f.round() as i32)
}

fn load_players(path: &Path) -> Result<Vec<Player>, String> {
    let mut rdr = open_reader(path)?;
    let idx = header_index(rdr.headers().map_err(|e| e.to_string())?);
    let mut out = Vec::new();
    for rec in rdr.records() {
        let rec = rec.map_err(|e| e.to_string())?;
        let name = get(&rec, &idx, "Name");
        if name.is_empty() {
            continue;
        }
        let jersey = get(&rec, &idx, "Jersey Number");
        let player = Player {
            id: get(&rec, &idx, "ID").to_string(),
            name: name.to_string(),
            age: parse_int(get(&rec, &idx, "Age")),
            nationality: get(&rec, &idx, "Nationality").to_string(),
            overall: parse_int(get(&rec, &idx, "Overall")),
            potential: parse_int(get(&rec, &idx, "Potential")),
            club: get(&rec, &idx, "Club").to_string(),
            club_norm: String::new(),
            position: get(&rec, &idx, "Position").to_string(),
            jersey: if jersey.is_empty() { None } else { Some(jersey.to_string()) },
            height: get(&rec, &idx, "Height").to_string(),
            weight: get(&rec, &idx, "Weight").to_string(),
        }
        .with_norms();
        out.push(player);
    }
    Ok(out)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn iso_date_formats() {
        assert_eq!(iso_date("2012-05-19 18:30:00"), "2012-05-19");
        assert_eq!(iso_date("2023-09-24"), "2023-09-24");
        assert_eq!(iso_date("29/03/2003"), "2003-03-29");
        assert_eq!(iso_date("9/3/2003"), "2003-03-09");
    }

    #[test]
    fn goal_parsing() {
        assert_eq!(parse_goal("1.0"), Some(1));
        assert_eq!(parse_goal("2"), Some(2));
        assert_eq!(parse_goal("NA"), None);
        assert_eq!(parse_goal(""), None);
        assert_eq!(parse_goal("-"), None);
    }
}
