use serde::{Deserialize, Serialize};
use std::path::Path;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum Competition {
    Brasileirao,
    CopaDoBrasil,
    Libertadores,
    ExtendedStats,
    HistoricalBrasileirao,
}

impl Competition {
    pub fn name(&self) -> &'static str {
        match self {
            Competition::Brasileirao => "Brasileirão",
            Competition::CopaDoBrasil => "Copa do Brasil",
            Competition::Libertadores => "Copa Libertadores",
            Competition::ExtendedStats => "Extended Stats",
            Competition::HistoricalBrasileirao => "Historical Brasileirão",
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Match {
    pub competition: Competition,
    pub date: String,
    pub season: i32,
    pub round: Option<String>,
    pub stage: Option<String>,
    pub home_team: String,
    pub away_team: String,
    pub home_team_norm: String,
    pub away_team_norm: String,
    pub home_goal: i32,
    pub away_goal: i32,
    pub home_state: Option<String>,
    pub away_state: Option<String>,
    pub arena: Option<String>,
    pub tournament: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Player {
    pub id: i64,
    pub name: String,
    pub age: i32,
    pub nationality: String,
    pub overall: i32,
    pub potential: i32,
    pub club: String,
    pub position: String,
    pub jersey_number: Option<i32>,
    pub height: String,
    pub weight: String,
}

#[derive(Default, Debug, Clone)]
pub struct Dataset {
    pub matches: Vec<Match>,
    pub players: Vec<Player>,
}

/// Normalize team names by stripping state suffixes (-SP, -RJ, etc.), country
/// codes like (URU), trimming whitespace, and lowercasing. Also strips common
/// phrases so "Palmeiras-SP", "Palmeiras", "S.E. Palmeiras" match.
pub fn normalize_team(name: &str) -> String {
    let mut s = name.trim().to_string();
    // Strip country codes like "(URU)"
    if let Some(idx) = s.find('(') {
        if let Some(end) = s[idx..].find(')') {
            let _tag = &s[idx..idx + end + 1];
            s = format!("{}{}", &s[..idx].trim(), &s[idx + end + 1..]);
            s = s.trim().to_string();
        }
    }
    // Strip trailing " - UF" or "-UF"
    let mut parts: Vec<&str> = s.rsplitn(2, '-').collect();
    if parts.len() == 2 {
        let tail = parts[0].trim();
        if tail.len() <= 3 && tail.chars().all(|c| c.is_ascii_alphabetic()) {
            s = parts.remove(1).trim().to_string();
        }
    }
    // Remove common prefixes / words
    let lower = s.to_lowercase();
    let lower = lower
        .replace("sport club", "")
        .replace("esporte clube", "")
        .replace("futebol clube", "")
        .replace(" fc", "")
        .replace("clube de regatas", "")
        .replace("clube atlético", "")
        .replace("clube atletico", "");
    let lower = lower.trim().to_string();
    // Strip accents (basic)
    strip_accents(&lower)
}

fn strip_accents(s: &str) -> String {
    s.chars()
        .map(|c| match c {
            'á' | 'à' | 'â' | 'ã' | 'ä' => 'a',
            'é' | 'è' | 'ê' | 'ë' => 'e',
            'í' | 'ì' | 'î' | 'ï' => 'i',
            'ó' | 'ò' | 'ô' | 'õ' | 'ö' => 'o',
            'ú' | 'ù' | 'û' | 'ü' => 'u',
            'ç' => 'c',
            'ñ' => 'n',
            _ => c,
        })
        .collect()
}

impl Dataset {
    pub fn load_from_dir<P: AsRef<Path>>(dir: P) -> Result<Self, Box<dyn std::error::Error>> {
        let dir = dir.as_ref();
        let mut ds = Dataset::default();
        ds.load_brasileirao(&dir.join("Brasileirao_Matches.csv"))?;
        ds.load_cup(&dir.join("Brazilian_Cup_Matches.csv"))?;
        ds.load_libertadores(&dir.join("Libertadores_Matches.csv"))?;
        ds.load_extended(&dir.join("BR-Football-Dataset.csv"))?;
        ds.load_historical(&dir.join("novo_campeonato_brasileiro.csv"))?;
        ds.load_fifa(&dir.join("fifa_data.csv"))?;
        Ok(ds)
    }

    fn load_brasileirao(&mut self, path: &Path) -> Result<(), Box<dyn std::error::Error>> {
        let mut rdr = csv::Reader::from_path(path)?;
        for rec in rdr.records() {
            let r = rec?;
            let home = r.get(1).unwrap_or("").to_string();
            let away = r.get(3).unwrap_or("").to_string();
            let home_goal: i32 = r.get(5).unwrap_or("0").parse().unwrap_or(0);
            let away_goal: i32 = r.get(6).unwrap_or("0").parse().unwrap_or(0);
            let season: i32 = r.get(7).unwrap_or("0").parse().unwrap_or(0);
            self.matches.push(Match {
                competition: Competition::Brasileirao,
                date: r.get(0).unwrap_or("").to_string(),
                season,
                round: r.get(8).map(String::from),
                stage: None,
                home_team_norm: normalize_team(&home),
                away_team_norm: normalize_team(&away),
                home_team: home,
                away_team: away,
                home_goal,
                away_goal,
                home_state: r.get(2).map(String::from),
                away_state: r.get(4).map(String::from),
                arena: None,
                tournament: None,
            });
        }
        Ok(())
    }

    fn load_cup(&mut self, path: &Path) -> Result<(), Box<dyn std::error::Error>> {
        let mut rdr = csv::Reader::from_path(path)?;
        for rec in rdr.records() {
            let r = rec?;
            let home = r.get(2).unwrap_or("").to_string();
            let away = r.get(3).unwrap_or("").to_string();
            let home_goal: i32 = r.get(4).unwrap_or("0").parse().unwrap_or(0);
            let away_goal: i32 = r.get(5).unwrap_or("0").parse().unwrap_or(0);
            let season: i32 = r.get(6).unwrap_or("0").parse().unwrap_or(0);
            self.matches.push(Match {
                competition: Competition::CopaDoBrasil,
                date: r.get(1).unwrap_or("").to_string(),
                season,
                round: r.get(0).map(String::from),
                stage: None,
                home_team_norm: normalize_team(&home),
                away_team_norm: normalize_team(&away),
                home_team: home,
                away_team: away,
                home_goal,
                away_goal,
                home_state: None,
                away_state: None,
                arena: None,
                tournament: None,
            });
        }
        Ok(())
    }

    fn load_libertadores(&mut self, path: &Path) -> Result<(), Box<dyn std::error::Error>> {
        let mut rdr = csv::Reader::from_path(path)?;
        for rec in rdr.records() {
            let r = rec?;
            let home = r.get(1).unwrap_or("").to_string();
            let away = r.get(2).unwrap_or("").to_string();
            let home_goal: i32 = r.get(3).unwrap_or("0").parse().unwrap_or(0);
            let away_goal: i32 = r.get(4).unwrap_or("0").parse().unwrap_or(0);
            let season: i32 = r.get(5).unwrap_or("0").parse().unwrap_or(0);
            self.matches.push(Match {
                competition: Competition::Libertadores,
                date: r.get(0).unwrap_or("").to_string(),
                season,
                round: None,
                stage: r.get(6).map(String::from),
                home_team_norm: normalize_team(&home),
                away_team_norm: normalize_team(&away),
                home_team: home,
                away_team: away,
                home_goal,
                away_goal,
                home_state: None,
                away_state: None,
                arena: None,
                tournament: None,
            });
        }
        Ok(())
    }

    fn load_extended(&mut self, path: &Path) -> Result<(), Box<dyn std::error::Error>> {
        let mut rdr = csv::Reader::from_path(path)?;
        for rec in rdr.records() {
            let r = rec?;
            let tournament = r.get(0).unwrap_or("").to_string();
            let home = r.get(1).unwrap_or("").to_string();
            let home_goal: i32 = r.get(2).unwrap_or("0").parse::<f32>().unwrap_or(0.0) as i32;
            let away_goal: i32 = r.get(3).unwrap_or("0").parse::<f32>().unwrap_or(0.0) as i32;
            let away = r.get(4).unwrap_or("").to_string();
            let date = r.get(12).unwrap_or("").to_string();
            let season: i32 = date.get(..4).and_then(|s| s.parse().ok()).unwrap_or(0);
            self.matches.push(Match {
                competition: Competition::ExtendedStats,
                date,
                season,
                round: None,
                stage: None,
                home_team_norm: normalize_team(&home),
                away_team_norm: normalize_team(&away),
                home_team: home,
                away_team: away,
                home_goal,
                away_goal,
                home_state: None,
                away_state: None,
                arena: None,
                tournament: Some(tournament),
            });
        }
        Ok(())
    }

    fn load_historical(&mut self, path: &Path) -> Result<(), Box<dyn std::error::Error>> {
        let mut rdr = csv::Reader::from_path(path)?;
        for rec in rdr.records() {
            let r = rec?;
            let home = r.get(4).unwrap_or("").to_string();
            let away = r.get(5).unwrap_or("").to_string();
            let home_goal: i32 = r.get(6).unwrap_or("0").parse().unwrap_or(0);
            let away_goal: i32 = r.get(7).unwrap_or("0").parse().unwrap_or(0);
            let season: i32 = r.get(2).unwrap_or("0").parse().unwrap_or(0);
            self.matches.push(Match {
                competition: Competition::HistoricalBrasileirao,
                date: r.get(1).unwrap_or("").to_string(),
                season,
                round: r.get(3).map(String::from),
                stage: None,
                home_team_norm: normalize_team(&home),
                away_team_norm: normalize_team(&away),
                home_team: home,
                away_team: away,
                home_goal,
                away_goal,
                home_state: r.get(8).map(String::from),
                away_state: r.get(9).map(String::from),
                arena: r.get(11).map(String::from),
                tournament: None,
            });
        }
        Ok(())
    }

    fn load_fifa(&mut self, path: &Path) -> Result<(), Box<dyn std::error::Error>> {
        let mut rdr = csv::ReaderBuilder::new().flexible(true).from_path(path)?;
        let headers = rdr.headers()?.clone();
        let find = |name: &str| headers.iter().position(|h| h.trim_start_matches('\u{FEFF}') == name);
        let idx_id = find("ID");
        let idx_name = find("Name");
        let idx_age = find("Age");
        let idx_nat = find("Nationality");
        let idx_overall = find("Overall");
        let idx_pot = find("Potential");
        let idx_club = find("Club");
        let idx_pos = find("Position");
        let idx_jersey = find("Jersey Number");
        let idx_h = find("Height");
        let idx_w = find("Weight");

        for rec in rdr.records() {
            let r = rec?;
            let get = |i: Option<usize>| i.and_then(|ix| r.get(ix)).unwrap_or("");
            self.players.push(Player {
                id: get(idx_id).parse().unwrap_or(0),
                name: get(idx_name).to_string(),
                age: get(idx_age).parse().unwrap_or(0),
                nationality: get(idx_nat).to_string(),
                overall: get(idx_overall).parse().unwrap_or(0),
                potential: get(idx_pot).parse().unwrap_or(0),
                club: get(idx_club).to_string(),
                position: get(idx_pos).to_string(),
                jersey_number: get(idx_jersey).parse().ok(),
                height: get(idx_h).to_string(),
                weight: get(idx_w).to_string(),
            });
        }
        Ok(())
    }
}
