use serde::{Deserialize, Serialize};
use std::path::Path;

use crate::normalize::{display_team, normalize_team};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum Competition {
    Brasileirao,
    CopaDoBrasil,
    Libertadores,
    Other,
}

impl Competition {
    pub fn as_str(&self) -> &'static str {
        match self {
            Competition::Brasileirao => "Brasileirão",
            Competition::CopaDoBrasil => "Copa do Brasil",
            Competition::Libertadores => "Copa Libertadores",
            Competition::Other => "Other",
        }
    }

    pub fn from_tournament(s: &str) -> Competition {
        let l = s.to_lowercase();
        if l.contains("libertadores") { Competition::Libertadores }
        else if l.contains("copa do brasil") || l.contains("brazilian cup") { Competition::CopaDoBrasil }
        else if l.contains("brasileir") || l.contains("serie a") || l.contains("campeonato brasileiro") {
            Competition::Brasileirao
        } else {
            Competition::Other
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Match {
    pub competition: Competition,
    pub season: i32,
    pub round: Option<String>,
    pub stage: Option<String>,
    pub date: String, // ISO YYYY-MM-DD
    pub home_team: String,
    pub away_team: String,
    pub home_team_key: String,
    pub away_team_key: String,
    pub home_goal: i32,
    pub away_goal: i32,
    pub home_state: Option<String>,
    pub away_state: Option<String>,
    pub arena: Option<String>,
}

impl Match {
    pub fn winner(&self) -> Winner {
        if self.home_goal > self.away_goal { Winner::Home }
        else if self.home_goal < self.away_goal { Winner::Away }
        else { Winner::Draw }
    }
    pub fn total_goals(&self) -> i32 { self.home_goal + self.away_goal }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Winner { Home, Away, Draw }

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Player {
    pub id: i64,
    pub name: String,
    pub age: Option<i32>,
    pub nationality: String,
    pub overall: Option<i32>,
    pub potential: Option<i32>,
    pub club: String,
    pub position: String,
    pub jersey_number: Option<i32>,
    pub height: String,
    pub weight: String,
}

#[derive(Debug, Default)]
pub struct Dataset {
    pub matches: Vec<Match>,
    pub players: Vec<Player>,
}

impl Dataset {
    pub fn load_default<P: AsRef<Path>>(dir: P) -> std::io::Result<Dataset> {
        let dir = dir.as_ref();
        let mut ds = Dataset::default();
        ds.matches.extend(load_brasileirao(&dir.join("Brasileirao_Matches.csv"))?);
        ds.matches.extend(load_copa_brasil(&dir.join("Brazilian_Cup_Matches.csv"))?);
        ds.matches.extend(load_libertadores(&dir.join("Libertadores_Matches.csv"))?);
        ds.matches.extend(load_br_football(&dir.join("BR-Football-Dataset.csv"))?);
        ds.matches.extend(load_novo_brasileirao(&dir.join("novo_campeonato_brasileiro.csv"))?);
        ds.players.extend(load_fifa(&dir.join("fifa_data.csv"))?);
        Ok(ds)
    }
}

fn parse_int(s: &str) -> Option<i32> {
    s.trim().trim_matches('"').parse::<f64>().ok().map(|f| f as i32)
}
fn parse_i64(s: &str) -> Option<i64> {
    s.trim().trim_matches('"').parse::<f64>().ok().map(|f| f as i64)
}

fn iso_date(s: &str) -> String {
    let s = s.trim();
    // "2023-09-24" or "2023-09-24 20:00:00" -> "2023-09-24"
    if s.len() >= 10 && &s[4..5] == "-" && &s[7..8] == "-" {
        return s[..10].to_string();
    }
    // Brazilian: "29/03/2003"
    if s.len() == 10 && &s[2..3] == "/" && &s[5..6] == "/" {
        return format!("{}-{}-{}", &s[6..10], &s[3..5], &s[0..2]);
    }
    s.to_string()
}

fn reader<P: AsRef<Path>>(path: P) -> std::io::Result<csv::Reader<std::fs::File>> {
    csv::ReaderBuilder::new()
        .flexible(true)
        .from_path(path)
        .map_err(|e| std::io::Error::new(std::io::ErrorKind::Other, e))
}

fn load_brasileirao(path: &Path) -> std::io::Result<Vec<Match>> {
    let mut rdr = reader(path)?;
    let headers = rdr.headers().map_err(io_err)?.clone();
    let idx = |n: &str| headers.iter().position(|h| h.eq_ignore_ascii_case(n));
    let i_dt = idx("datetime").unwrap();
    let i_home = idx("home_team").unwrap();
    let i_away = idx("away_team").unwrap();
    let i_hs = idx("home_team_state");
    let i_as = idx("away_team_state");
    let i_hg = idx("home_goal").unwrap();
    let i_ag = idx("away_goal").unwrap();
    let i_season = idx("season").unwrap();
    let i_round = idx("round");
    let mut out = Vec::new();
    for r in rdr.records() {
        let r = match r { Ok(r) => r, Err(_) => continue };
        let home = r.get(i_home).unwrap_or("").to_string();
        let away = r.get(i_away).unwrap_or("").to_string();
        if home.is_empty() || away.is_empty() { continue; }
        let hg = parse_int(r.get(i_hg).unwrap_or("")).unwrap_or(0);
        let ag = parse_int(r.get(i_ag).unwrap_or("")).unwrap_or(0);
        let season = parse_int(r.get(i_season).unwrap_or("")).unwrap_or(0);
        out.push(Match {
            competition: Competition::Brasileirao,
            season,
            round: i_round.and_then(|i| r.get(i)).map(|s| s.to_string()),
            stage: None,
            date: iso_date(r.get(i_dt).unwrap_or("")),
            home_team: display_team(&home),
            away_team: display_team(&away),
            home_team_key: normalize_team(&home),
            away_team_key: normalize_team(&away),
            home_goal: hg,
            away_goal: ag,
            home_state: i_hs.and_then(|i| r.get(i)).map(|s| s.to_string()),
            away_state: i_as.and_then(|i| r.get(i)).map(|s| s.to_string()),
            arena: None,
        });
    }
    Ok(out)
}

fn load_copa_brasil(path: &Path) -> std::io::Result<Vec<Match>> {
    let mut rdr = reader(path)?;
    let headers = rdr.headers().map_err(io_err)?.clone();
    let idx = |n: &str| headers.iter().position(|h| h.eq_ignore_ascii_case(n));
    let i_dt = idx("datetime").unwrap();
    let i_home = idx("home_team").unwrap();
    let i_away = idx("away_team").unwrap();
    let i_hg = idx("home_goal").unwrap();
    let i_ag = idx("away_goal").unwrap();
    let i_season = idx("season").unwrap();
    let i_round = idx("round");
    let mut out = Vec::new();
    for r in rdr.records() {
        let r = match r { Ok(r) => r, Err(_) => continue };
        let home = r.get(i_home).unwrap_or("").to_string();
        let away = r.get(i_away).unwrap_or("").to_string();
        if home.is_empty() || away.is_empty() { continue; }
        let hg = parse_int(r.get(i_hg).unwrap_or("")).unwrap_or(0);
        let ag = parse_int(r.get(i_ag).unwrap_or("")).unwrap_or(0);
        let season = parse_int(r.get(i_season).unwrap_or("")).unwrap_or(0);
        out.push(Match {
            competition: Competition::CopaDoBrasil,
            season,
            round: i_round.and_then(|i| r.get(i)).map(|s| s.to_string()),
            stage: None,
            date: iso_date(r.get(i_dt).unwrap_or("")),
            home_team: display_team(&home),
            away_team: display_team(&away),
            home_team_key: normalize_team(&home),
            away_team_key: normalize_team(&away),
            home_goal: hg,
            away_goal: ag,
            home_state: None,
            away_state: None,
            arena: None,
        });
    }
    Ok(out)
}

fn load_libertadores(path: &Path) -> std::io::Result<Vec<Match>> {
    let mut rdr = reader(path)?;
    let headers = rdr.headers().map_err(io_err)?.clone();
    let idx = |n: &str| headers.iter().position(|h| h.eq_ignore_ascii_case(n));
    let i_dt = idx("datetime").unwrap();
    let i_home = idx("home_team").unwrap();
    let i_away = idx("away_team").unwrap();
    let i_hg = idx("home_goal").unwrap();
    let i_ag = idx("away_goal").unwrap();
    let i_season = idx("season").unwrap();
    let i_stage = idx("stage");
    let mut out = Vec::new();
    for r in rdr.records() {
        let r = match r { Ok(r) => r, Err(_) => continue };
        let home = r.get(i_home).unwrap_or("").to_string();
        let away = r.get(i_away).unwrap_or("").to_string();
        if home.is_empty() || away.is_empty() { continue; }
        let hg = parse_int(r.get(i_hg).unwrap_or("")).unwrap_or(0);
        let ag = parse_int(r.get(i_ag).unwrap_or("")).unwrap_or(0);
        let season = parse_int(r.get(i_season).unwrap_or("")).unwrap_or(0);
        out.push(Match {
            competition: Competition::Libertadores,
            season,
            round: None,
            stage: i_stage.and_then(|i| r.get(i)).map(|s| s.to_string()),
            date: iso_date(r.get(i_dt).unwrap_or("")),
            home_team: display_team(&home),
            away_team: display_team(&away),
            home_team_key: normalize_team(&home),
            away_team_key: normalize_team(&away),
            home_goal: hg,
            away_goal: ag,
            home_state: None,
            away_state: None,
            arena: None,
        });
    }
    Ok(out)
}

fn load_br_football(path: &Path) -> std::io::Result<Vec<Match>> {
    let mut rdr = reader(path)?;
    let headers = rdr.headers().map_err(io_err)?.clone();
    let idx = |n: &str| headers.iter().position(|h| h.eq_ignore_ascii_case(n));
    let i_tournament = idx("tournament").unwrap();
    let i_home = idx("home").unwrap();
    let i_away = idx("away").unwrap();
    let i_hg = idx("home_goal").unwrap();
    let i_ag = idx("away_goal").unwrap();
    let i_date = idx("date").unwrap();
    let mut out = Vec::new();
    for r in rdr.records() {
        let r = match r { Ok(r) => r, Err(_) => continue };
        let home = r.get(i_home).unwrap_or("").to_string();
        let away = r.get(i_away).unwrap_or("").to_string();
        if home.is_empty() || away.is_empty() { continue; }
        let hg = parse_int(r.get(i_hg).unwrap_or("")).unwrap_or(0);
        let ag = parse_int(r.get(i_ag).unwrap_or("")).unwrap_or(0);
        let date = iso_date(r.get(i_date).unwrap_or(""));
        let season: i32 = date.get(0..4).and_then(|s| s.parse().ok()).unwrap_or(0);
        let comp = Competition::from_tournament(r.get(i_tournament).unwrap_or(""));
        out.push(Match {
            competition: comp,
            season,
            round: None,
            stage: None,
            date,
            home_team: display_team(&home),
            away_team: display_team(&away),
            home_team_key: normalize_team(&home),
            away_team_key: normalize_team(&away),
            home_goal: hg,
            away_goal: ag,
            home_state: None,
            away_state: None,
            arena: None,
        });
    }
    Ok(out)
}

fn load_novo_brasileirao(path: &Path) -> std::io::Result<Vec<Match>> {
    let mut rdr = reader(path)?;
    let headers = rdr.headers().map_err(io_err)?.clone();
    let idx = |n: &str| headers.iter().position(|h| h.eq_ignore_ascii_case(n));
    let i_data = idx("Data").unwrap();
    let i_ano = idx("Ano").unwrap();
    let i_rod = idx("Rodada");
    let i_home = idx("Equipe_mandante").unwrap();
    let i_away = idx("Equipe_visitante").unwrap();
    let i_hg = idx("Gols_mandante").unwrap();
    let i_ag = idx("Gols_visitante").unwrap();
    let i_hs = idx("Mandante_UF");
    let i_as = idx("Visitante_UF");
    let i_arena = idx("Arena");
    let mut out = Vec::new();
    for r in rdr.records() {
        let r = match r { Ok(r) => r, Err(_) => continue };
        let home = r.get(i_home).unwrap_or("").to_string();
        let away = r.get(i_away).unwrap_or("").to_string();
        if home.is_empty() || away.is_empty() { continue; }
        let hg = parse_int(r.get(i_hg).unwrap_or("")).unwrap_or(0);
        let ag = parse_int(r.get(i_ag).unwrap_or("")).unwrap_or(0);
        let season = parse_int(r.get(i_ano).unwrap_or("")).unwrap_or(0);
        out.push(Match {
            competition: Competition::Brasileirao,
            season,
            round: i_rod.and_then(|i| r.get(i)).map(|s| s.to_string()),
            stage: None,
            date: iso_date(r.get(i_data).unwrap_or("")),
            home_team: display_team(&home),
            away_team: display_team(&away),
            home_team_key: normalize_team(&home),
            away_team_key: normalize_team(&away),
            home_goal: hg,
            away_goal: ag,
            home_state: i_hs.and_then(|i| r.get(i)).map(|s| s.to_string()),
            away_state: i_as.and_then(|i| r.get(i)).map(|s| s.to_string()),
            arena: i_arena.and_then(|i| r.get(i)).map(|s| s.to_string()).filter(|s| !s.is_empty()),
        });
    }
    Ok(out)
}

fn load_fifa(path: &Path) -> std::io::Result<Vec<Player>> {
    let mut rdr = reader(path)?;
    let headers = rdr.headers().map_err(io_err)?.clone();
    let idx = |n: &str| headers.iter().position(|h| h.eq_ignore_ascii_case(n));
    let i_id = idx("ID").unwrap();
    let i_name = idx("Name").unwrap();
    let i_age = idx("Age");
    let i_nat = idx("Nationality").unwrap();
    let i_ovr = idx("Overall");
    let i_pot = idx("Potential");
    let i_club = idx("Club").unwrap();
    let i_pos = idx("Position");
    let i_jer = idx("Jersey Number");
    let i_h = idx("Height");
    let i_w = idx("Weight");
    let mut out = Vec::new();
    for r in rdr.records() {
        let r = match r { Ok(r) => r, Err(_) => continue };
        let id = parse_i64(r.get(i_id).unwrap_or("")).unwrap_or(0);
        let name = r.get(i_name).unwrap_or("").to_string();
        if name.is_empty() { continue; }
        out.push(Player {
            id,
            name,
            age: i_age.and_then(|i| r.get(i)).and_then(parse_int),
            nationality: r.get(i_nat).unwrap_or("").to_string(),
            overall: i_ovr.and_then(|i| r.get(i)).and_then(parse_int),
            potential: i_pot.and_then(|i| r.get(i)).and_then(parse_int),
            club: r.get(i_club).unwrap_or("").to_string(),
            position: i_pos.and_then(|i| r.get(i)).unwrap_or("").to_string(),
            jersey_number: i_jer.and_then(|i| r.get(i)).and_then(parse_int),
            height: i_h.and_then(|i| r.get(i)).unwrap_or("").to_string(),
            weight: i_w.and_then(|i| r.get(i)).unwrap_or("").to_string(),
        });
    }
    Ok(out)
}

fn io_err<E: std::fmt::Display>(e: E) -> std::io::Error {
    std::io::Error::new(std::io::ErrorKind::Other, e.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn iso_date_formats() {
        assert_eq!(iso_date("2023-09-24"), "2023-09-24");
        assert_eq!(iso_date("2012-05-19 18:30:00"), "2012-05-19");
        assert_eq!(iso_date("29/03/2003"), "2003-03-29");
    }

    #[test]
    fn load_all_csvs() {
        let ds = Dataset::load_default("data/kaggle").expect("load");
        assert!(ds.matches.len() > 20_000, "matches: {}", ds.matches.len());
        assert!(ds.players.len() > 18_000, "players: {}", ds.players.len());
    }
}
