use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::path::Path;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Match {
    pub datetime: Option<String>,
    pub home_team: String,
    pub away_team: String,
    pub home_goal: Option<i32>,
    pub away_goal: Option<i32>,
    pub season: Option<i32>,
    pub competition: String,
    pub round: Option<String>,
    pub stage: Option<String>,
    pub arena: Option<String>,
    pub home_corner: Option<f64>,
    pub away_corner: Option<f64>,
    pub home_shots: Option<f64>,
    pub away_shots: Option<f64>,
    pub home_attacks: Option<f64>,
    pub away_attacks: Option<f64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Player {
    pub id: Option<i64>,
    pub name: String,
    pub age: Option<i32>,
    pub nationality: String,
    pub overall: Option<i32>,
    pub potential: Option<i32>,
    pub club: String,
    pub position: String,
    pub jersey_number: Option<String>,
    pub height: Option<String>,
    pub weight: Option<String>,
    pub value: Option<String>,
    pub wage: Option<String>,
}

#[derive(Debug, Default)]
pub struct Database {
    pub matches: Vec<Match>,
    pub players: Vec<Player>,
}

/// Normalize a team name: strip trailing state suffix like "-SP" or "- SP"
/// and convert to lowercase for comparison.
pub fn normalize_team_name(name: &str) -> String {
    let name = name.trim();
    // Look for trailing "- XX" where XX is a 2-letter state code
    if let Some(pos) = name.rfind('-') {
        let suffix = name[pos + 1..].trim();
        if suffix.len() == 2 && suffix.chars().all(|c| c.is_ascii_uppercase()) {
            return name[..pos].trim().to_lowercase();
        }
    }
    name.to_lowercase()
}

/// Check if search_term matches a team name (case-insensitive, handles state suffixes)
pub fn team_matches(team_name: &str, search_term: &str) -> bool {
    let normalized_team = normalize_team_name(team_name);
    let normalized_search = search_term.trim().to_lowercase();
    normalized_team.contains(&normalized_search) || normalized_search.contains(&normalized_team)
}

fn parse_goals(s: &str) -> Option<i32> {
    let s = s.trim();
    if s.is_empty() || s == "nan" || s == "NaN" || s == "NA" {
        return None;
    }
    // Handle float-like "1.0"
    if let Ok(f) = s.parse::<f64>() {
        return Some(f as i32);
    }
    s.parse::<i32>().ok()
}

fn parse_season(s: &str) -> Option<i32> {
    let s = s.trim();
    if s.is_empty() {
        return None;
    }
    s.parse::<i32>().ok()
}

fn parse_float(s: &str) -> Option<f64> {
    let s = s.trim();
    if s.is_empty() || s == "nan" || s == "NaN" || s == "NA" {
        return None;
    }
    s.parse::<f64>().ok()
}

impl Database {
    pub fn load(data_dir: &Path) -> Result<Self> {
        let mut db = Database::default();

        db.load_brasileirao(data_dir)?;
        db.load_cup(data_dir)?;
        db.load_libertadores(data_dir)?;
        db.load_br_football(data_dir)?;
        db.load_novo_campeonato(data_dir)?;
        db.load_fifa(data_dir)?;

        Ok(db)
    }

    fn load_brasileirao(&mut self, data_dir: &Path) -> Result<()> {
        let path = data_dir.join("Brasileirao_Matches.csv");
        let mut rdr = csv::ReaderBuilder::new()
            .has_headers(true)
            .from_path(&path)
            .with_context(|| format!("Opening {}", path.display()))?;

        for result in rdr.records() {
            let record = result?;
            // datetime,home_team,home_team_state,away_team,away_team_state,home_goal,away_goal,season,round
            let m = Match {
                datetime: Some(record[0].to_string()),
                home_team: record[1].to_string(),
                away_team: record[3].to_string(),
                home_goal: parse_goals(&record[5]),
                away_goal: parse_goals(&record[6]),
                season: parse_season(&record[7]),
                competition: "Brasileirão Serie A".to_string(),
                round: Some(record[8].to_string()),
                stage: None,
                arena: None,
                home_corner: None,
                away_corner: None,
                home_shots: None,
                away_shots: None,
                home_attacks: None,
                away_attacks: None,
            };
            self.matches.push(m);
        }
        Ok(())
    }

    fn load_cup(&mut self, data_dir: &Path) -> Result<()> {
        let path = data_dir.join("Brazilian_Cup_Matches.csv");
        let mut rdr = csv::ReaderBuilder::new()
            .has_headers(true)
            .from_path(&path)
            .with_context(|| format!("Opening {}", path.display()))?;

        for result in rdr.records() {
            let record = result?;
            // round,datetime,home_team,away_team,home_goal,away_goal,season
            let m = Match {
                datetime: Some(record[1].to_string()),
                home_team: record[2].to_string(),
                away_team: record[3].to_string(),
                home_goal: parse_goals(&record[4]),
                away_goal: parse_goals(&record[5]),
                season: parse_season(&record[6]),
                competition: "Copa do Brasil".to_string(),
                round: Some(record[0].to_string()),
                stage: None,
                arena: None,
                home_corner: None,
                away_corner: None,
                home_shots: None,
                away_shots: None,
                home_attacks: None,
                away_attacks: None,
            };
            self.matches.push(m);
        }
        Ok(())
    }

    fn load_libertadores(&mut self, data_dir: &Path) -> Result<()> {
        let path = data_dir.join("Libertadores_Matches.csv");
        let mut rdr = csv::ReaderBuilder::new()
            .has_headers(true)
            .from_path(&path)
            .with_context(|| format!("Opening {}", path.display()))?;

        for result in rdr.records() {
            let record = result?;
            // datetime,home_team,away_team,home_goal,away_goal,season,stage
            let m = Match {
                datetime: Some(record[0].to_string()),
                home_team: record[1].to_string(),
                away_team: record[2].to_string(),
                home_goal: parse_goals(&record[3]),
                away_goal: parse_goals(&record[4]),
                season: parse_season(&record[5]),
                competition: "Copa Libertadores".to_string(),
                round: None,
                stage: Some(record[6].to_string()),
                arena: None,
                home_corner: None,
                away_corner: None,
                home_shots: None,
                away_shots: None,
                home_attacks: None,
                away_attacks: None,
            };
            self.matches.push(m);
        }
        Ok(())
    }

    fn load_br_football(&mut self, data_dir: &Path) -> Result<()> {
        let path = data_dir.join("BR-Football-Dataset.csv");
        let mut rdr = csv::ReaderBuilder::new()
            .has_headers(true)
            .from_path(&path)
            .with_context(|| format!("Opening {}", path.display()))?;

        for result in rdr.records() {
            let record = result?;
            // tournament,home,home_goal,away_goal,away,home_corner,away_corner,
            // home_attack,away_attack,home_shots,away_shots,time,date,...
            if record.len() < 13 {
                continue;
            }
            let datetime = if record[12].is_empty() {
                None
            } else {
                Some(record[12].to_string())
            };
            let m = Match {
                datetime,
                home_team: record[1].to_string(),
                away_team: record[4].to_string(),
                home_goal: parse_goals(&record[2]),
                away_goal: parse_goals(&record[3]),
                season: None, // date field, no explicit season column
                competition: record[0].to_string(),
                round: None,
                stage: None,
                arena: None,
                home_corner: parse_float(&record[5]),
                away_corner: parse_float(&record[6]),
                home_attacks: parse_float(&record[7]),
                away_attacks: parse_float(&record[8]),
                home_shots: parse_float(&record[9]),
                away_shots: parse_float(&record[10]),
            };
            self.matches.push(m);
        }
        Ok(())
    }

    fn load_novo_campeonato(&mut self, data_dir: &Path) -> Result<()> {
        let path = data_dir.join("novo_campeonato_brasileiro.csv");
        let mut rdr = csv::ReaderBuilder::new()
            .has_headers(true)
            .from_path(&path)
            .with_context(|| format!("Opening {}", path.display()))?;

        for result in rdr.records() {
            let record = result?;
            // ID,Data,Ano,Rodada,Equipe_mandante,Equipe_visitante,
            // Gols_mandante,Gols_visitante,Mandante_UF,Visitante_UF,
            // Vencedor,Arena,OBS
            if record.len() < 12 {
                continue;
            }
            // Date is in DD/MM/YYYY format
            let date_str = record[1].to_string();
            let m = Match {
                datetime: Some(date_str),
                home_team: record[4].to_string(),
                away_team: record[5].to_string(),
                home_goal: parse_goals(&record[6]),
                away_goal: parse_goals(&record[7]),
                season: parse_season(&record[2]),
                competition: "Brasileirão (Historical)".to_string(),
                round: Some(record[3].to_string()),
                stage: None,
                arena: Some(record[11].to_string()),
                home_corner: None,
                away_corner: None,
                home_shots: None,
                away_shots: None,
                home_attacks: None,
                away_attacks: None,
            };
            self.matches.push(m);
        }
        Ok(())
    }

    fn load_fifa(&mut self, data_dir: &Path) -> Result<()> {
        let path = data_dir.join("fifa_data.csv");
        let mut rdr = csv::ReaderBuilder::new()
            .has_headers(true)
            .flexible(true)
            .from_path(&path)
            .with_context(|| format!("Opening {}", path.display()))?;

        let headers = rdr.headers()?.clone();

        // Find column indices, handling BOM in first header
        let find_col = |name: &str| -> Option<usize> {
            headers.iter().position(|h| {
                // Strip BOM if present
                let h = h.trim_start_matches('\u{feff}').trim();
                h.eq_ignore_ascii_case(name)
            })
        };

        let idx_id = find_col("ID");
        let idx_name = find_col("Name").unwrap_or(2);
        let idx_age = find_col("Age");
        let idx_nationality = find_col("Nationality").unwrap_or(5);
        let idx_overall = find_col("Overall");
        let idx_potential = find_col("Potential");
        let idx_club = find_col("Club").unwrap_or(9);
        let idx_position = find_col("Position");
        let idx_jersey = find_col("Jersey Number");
        let idx_height = find_col("Height");
        let idx_weight = find_col("Weight");
        let idx_value = find_col("Value");
        let idx_wage = find_col("Wage");

        for result in rdr.records() {
            let record = result?;
            if record.len() <= idx_name {
                continue;
            }
            let name = record[idx_name].trim().to_string();
            if name.is_empty() {
                continue;
            }

            let get = |idx: Option<usize>| -> &str {
                idx.and_then(|i| record.get(i)).unwrap_or("")
            };

            let p = Player {
                id: idx_id.and_then(|i| record.get(i)).and_then(|s| s.trim().parse().ok()),
                name,
                age: get(idx_age).trim().parse().ok(),
                nationality: get(Some(idx_nationality)).trim().to_string(),
                overall: get(idx_overall).trim().parse().ok(),
                potential: get(idx_potential).trim().parse().ok(),
                club: get(Some(idx_club)).trim().to_string(),
                position: get(idx_position).trim().to_string(),
                jersey_number: Some(get(idx_jersey).trim().to_string()),
                height: Some(get(idx_height).trim().to_string()),
                weight: Some(get(idx_weight).trim().to_string()),
                value: Some(get(idx_value).trim().to_string()),
                wage: Some(get(idx_wage).trim().to_string()),
            };
            self.players.push(p);
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_normalize_team_name() {
        assert_eq!(normalize_team_name("Palmeiras-SP"), "palmeiras");
        assert_eq!(normalize_team_name("Flamengo-RJ"), "flamengo");
        assert_eq!(normalize_team_name("Flamengo"), "flamengo");
        assert_eq!(normalize_team_name("São Paulo-SP"), "são paulo");
    }

    #[test]
    fn test_team_matches() {
        assert!(team_matches("Palmeiras-SP", "palmeiras"));
        assert!(team_matches("Palmeiras-SP", "Palmeiras"));
        assert!(team_matches("Flamengo-RJ", "flamengo"));
        assert!(!team_matches("Palmeiras-SP", "Flamengo"));
    }

    #[test]
    fn test_parse_goals() {
        assert_eq!(parse_goals("2"), Some(2));
        assert_eq!(parse_goals("1.0"), Some(1));
        assert_eq!(parse_goals(""), None);
        assert_eq!(parse_goals("nan"), None);
    }
}
