use csv::ReaderBuilder;
use std::path::Path;

#[derive(Debug, Clone)]
pub struct Match {
    pub datetime: String,
    pub home_team: String,
    pub away_team: String,
    pub home_goal: i32,
    pub away_goal: i32,
    pub season: i32,
    pub round: String,
    pub competition: String, // "brasileirao", "copa_brasil", "libertadores"
    pub stage: Option<String>,
}

#[derive(Debug, Clone)]
pub struct Player {
    pub name: String,
    pub age: u32,
    pub nationality: String,
    pub overall: u32,
    pub potential: u32,
    pub club: String,
    pub value: String,
    pub position: String,
}

pub struct AppData {
    pub matches: Vec<Match>,
    pub players: Vec<Player>,
}

impl AppData {
    pub fn load(data_dir: &str) -> Self {
        let mut matches = Vec::new();
        let mut players = Vec::new();

        // Load Brasileirao_Matches.csv
        let path = Path::new(data_dir).join("Brasileirao_Matches.csv");
        if path.exists() {
            match load_brasileirao_matches(&path.to_string_lossy()) {
                Ok(mut m) => {
                    eprintln!("Loaded {} Brasileirao matches", m.len());
                    matches.append(&mut m);
                }
                Err(e) => eprintln!("Error loading Brasileirao_Matches.csv: {}", e),
            }
        } else {
            eprintln!("Brasileirao_Matches.csv not found at {:?}", path);
        }

        // Load Brazilian_Cup_Matches.csv
        let path = Path::new(data_dir).join("Brazilian_Cup_Matches.csv");
        if path.exists() {
            match load_cup_matches(&path.to_string_lossy()) {
                Ok(mut m) => {
                    eprintln!("Loaded {} Copa Brasil matches", m.len());
                    matches.append(&mut m);
                }
                Err(e) => eprintln!("Error loading Brazilian_Cup_Matches.csv: {}", e),
            }
        }

        // Load Libertadores_Matches.csv
        let path = Path::new(data_dir).join("Libertadores_Matches.csv");
        if path.exists() {
            match load_libertadores_matches(&path.to_string_lossy()) {
                Ok(mut m) => {
                    eprintln!("Loaded {} Libertadores matches", m.len());
                    matches.append(&mut m);
                }
                Err(e) => eprintln!("Error loading Libertadores_Matches.csv: {}", e),
            }
        }

        // Load BR-Football-Dataset.csv (Serie A, Copa do Brasil - newer data)
        let path = Path::new(data_dir).join("BR-Football-Dataset.csv");
        if path.exists() {
            match load_br_football_dataset(&path.to_string_lossy()) {
                Ok(mut m) => {
                    eprintln!("Loaded {} BR-Football-Dataset matches", m.len());
                    matches.append(&mut m);
                }
                Err(e) => eprintln!("Error loading BR-Football-Dataset.csv: {}", e),
            }
        }

        // Load novo_campeonato_brasileiro.csv (2003-2019)
        let path = Path::new(data_dir).join("novo_campeonato_brasileiro.csv");
        if path.exists() {
            match load_novo_campeonato(&path.to_string_lossy()) {
                Ok(mut m) => {
                    eprintln!("Loaded {} novo campeonato matches", m.len());
                    matches.append(&mut m);
                }
                Err(e) => eprintln!("Error loading novo_campeonato_brasileiro.csv: {}", e),
            }
        }

        // Load fifa_data.csv
        let path = Path::new(data_dir).join("fifa_data.csv");
        if path.exists() {
            match load_fifa_players(&path.to_string_lossy()) {
                Ok(mut p) => {
                    eprintln!("Loaded {} FIFA players", p.len());
                    players.append(&mut p);
                }
                Err(e) => eprintln!("Error loading fifa_data.csv: {}", e),
            }
        }

        AppData { matches, players }
    }
}

fn parse_goals(s: &str) -> i32 {
    let s = s.trim().trim_matches('"');
    // Handle float strings like "2.0"
    if let Ok(f) = s.parse::<f64>() {
        return f as i32;
    }
    s.parse::<i32>().unwrap_or(0)
}

fn parse_season(s: &str) -> i32 {
    let s = s.trim().trim_matches('"');
    s.parse::<i32>().unwrap_or(0)
}

fn load_brasileirao_matches(path: &str) -> Result<Vec<Match>, Box<dyn std::error::Error>> {
    let mut rdr = ReaderBuilder::new().flexible(true).from_path(path)?;
    let mut matches = Vec::new();

    for result in rdr.records() {
        let record = result?;
        // datetime, home_team, home_team_state, away_team, away_team_state, home_goal, away_goal, season, round
        if record.len() < 9 {
            continue;
        }
        let home_goal = parse_goals(record.get(5).unwrap_or("0"));
        let away_goal = parse_goals(record.get(6).unwrap_or("0"));
        let season = parse_season(record.get(7).unwrap_or("0"));
        if season == 0 {
            continue;
        }
        matches.push(Match {
            datetime: record.get(0).unwrap_or("").trim_matches('"').to_string(),
            home_team: record.get(1).unwrap_or("").trim_matches('"').to_string(),
            away_team: record.get(3).unwrap_or("").trim_matches('"').to_string(),
            home_goal,
            away_goal,
            season,
            round: record.get(8).unwrap_or("").trim_matches('"').to_string(),
            competition: "brasileirao".to_string(),
            stage: None,
        });
    }

    Ok(matches)
}

fn load_cup_matches(path: &str) -> Result<Vec<Match>, Box<dyn std::error::Error>> {
    let mut rdr = ReaderBuilder::new().flexible(true).from_path(path)?;
    let mut matches = Vec::new();

    for result in rdr.records() {
        let record = result?;
        // round, datetime, home_team, away_team, home_goal, away_goal, season
        if record.len() < 7 {
            continue;
        }
        let home_goal = parse_goals(record.get(4).unwrap_or("0"));
        let away_goal = parse_goals(record.get(5).unwrap_or("0"));
        let season = parse_season(record.get(6).unwrap_or("0"));
        if season == 0 {
            continue;
        }
        let round_val = record.get(0).unwrap_or("").trim_matches('"').to_string();
        matches.push(Match {
            datetime: record.get(1).unwrap_or("").trim_matches('"').to_string(),
            home_team: record.get(2).unwrap_or("").trim_matches('"').to_string(),
            away_team: record.get(3).unwrap_or("").trim_matches('"').to_string(),
            home_goal,
            away_goal,
            season,
            round: round_val.clone(),
            competition: "copa_brasil".to_string(),
            stage: Some(round_val),
        });
    }

    Ok(matches)
}

fn load_libertadores_matches(path: &str) -> Result<Vec<Match>, Box<dyn std::error::Error>> {
    let mut rdr = ReaderBuilder::new().flexible(true).from_path(path)?;
    let mut matches = Vec::new();

    for result in rdr.records() {
        let record = result?;
        // datetime, home_team, away_team, home_goal, away_goal, season, stage
        if record.len() < 6 {
            continue;
        }
        let home_goal = parse_goals(record.get(3).unwrap_or("0"));
        let away_goal = parse_goals(record.get(4).unwrap_or("0"));
        let season = parse_season(record.get(5).unwrap_or("0"));
        if season == 0 {
            continue;
        }
        let stage = record.get(6).map(|s| s.trim_matches('"').to_string());
        matches.push(Match {
            datetime: record.get(0).unwrap_or("").trim_matches('"').to_string(),
            home_team: record.get(1).unwrap_or("").trim_matches('"').to_string(),
            away_team: record.get(2).unwrap_or("").trim_matches('"').to_string(),
            home_goal,
            away_goal,
            season,
            round: stage.clone().unwrap_or_default(),
            competition: "libertadores".to_string(),
            stage,
        });
    }

    Ok(matches)
}

fn load_br_football_dataset(path: &str) -> Result<Vec<Match>, Box<dyn std::error::Error>> {
    let mut rdr = ReaderBuilder::new().flexible(true).from_path(path)?;
    let mut matches = Vec::new();

    // tournament, home, home_goal, away_goal, away, home_corner, away_corner, home_attack,
    // away_attack, home_shots, away_shots, time, date, ht_diff, at_diff, ht_result, at_result, total_corners
    for result in rdr.records() {
        let record = result?;
        if record.len() < 13 {
            continue;
        }
        let tournament = record.get(0).unwrap_or("").trim();
        let competition = match tournament {
            "Serie A" => "brasileirao",
            "Serie B" => "serie_b",
            "Serie C" => "serie_c",
            "Copa do Brasil" => "copa_brasil",
            _ => "other",
        };

        let home_goal = parse_goals(record.get(2).unwrap_or("0"));
        let away_goal = parse_goals(record.get(3).unwrap_or("0"));

        // date field at index 12: "2023-09-24"
        let date_str = record.get(12).unwrap_or("").trim();
        let season = if date_str.len() >= 4 {
            date_str[..4].parse::<i32>().unwrap_or(0)
        } else {
            0
        };
        if season == 0 {
            continue;
        }

        matches.push(Match {
            datetime: format!("{} {}", date_str, record.get(11).unwrap_or("00:00:00").trim()),
            home_team: record.get(1).unwrap_or("").trim().to_string(),
            away_team: record.get(4).unwrap_or("").trim().to_string(),
            home_goal,
            away_goal,
            season,
            round: String::new(),
            competition: competition.to_string(),
            stage: None,
        });
    }

    Ok(matches)
}

fn load_novo_campeonato(path: &str) -> Result<Vec<Match>, Box<dyn std::error::Error>> {
    let mut rdr = ReaderBuilder::new().flexible(true).from_path(path)?;
    let mut matches = Vec::new();

    // ID, Data (DD/MM/YYYY), Ano, Rodada, Equipe_mandante, Equipe_visitante,
    // Gols_mandante, Gols_visitante, Mandante_UF, Visitante_UF, Vencedor, Arena, OBS
    for result in rdr.records() {
        let record = result?;
        if record.len() < 8 {
            continue;
        }
        let season = parse_season(record.get(2).unwrap_or("0"));
        if season == 0 {
            continue;
        }

        // Parse DD/MM/YYYY -> YYYY-MM-DD
        let raw_date = record.get(1).unwrap_or("").trim();
        let datetime = if raw_date.len() == 10 && raw_date.chars().nth(2) == Some('/') {
            format!("{}-{}-{}", &raw_date[6..10], &raw_date[3..5], &raw_date[0..2])
        } else {
            raw_date.to_string()
        };

        let home_goal = parse_goals(record.get(6).unwrap_or("0"));
        let away_goal = parse_goals(record.get(7).unwrap_or("0"));
        let round = record.get(3).unwrap_or("").trim().to_string();

        // Skip records where goals are 0 and home_team is empty (likely bad rows)
        let home_team = record.get(4).unwrap_or("").trim().to_string();
        let away_team = record.get(5).unwrap_or("").trim().to_string();
        if home_team.is_empty() || away_team.is_empty() {
            continue;
        }

        matches.push(Match {
            datetime,
            home_team,
            away_team,
            home_goal,
            away_goal,
            season,
            round,
            competition: "brasileirao".to_string(),
            stage: None,
        });
    }

    Ok(matches)
}

fn load_fifa_players(path: &str) -> Result<Vec<Player>, Box<dyn std::error::Error>> {
    // Handle BOM by reading bytes and stripping it
    let content = std::fs::read(path)?;
    let content_str = if content.starts_with(&[0xEF, 0xBB, 0xBF]) {
        String::from_utf8_lossy(&content[3..]).to_string()
    } else {
        String::from_utf8_lossy(&content).to_string()
    };

    let mut rdr = ReaderBuilder::new()
        .flexible(true)
        .from_reader(content_str.as_bytes());

    let headers = rdr.headers()?.clone();

    // Find column indices by name
    let find_col = |name: &str| -> Option<usize> {
        headers.iter().position(|h| h.trim() == name)
    };

    // The BOM-stripped first header might be empty or the row index column
    // Headers: (empty/BOM), ID, Name, Age, Photo, Nationality, Flag, Overall, Potential, Club, ...
    let name_col = find_col("Name").unwrap_or(2);
    let age_col = find_col("Age").unwrap_or(3);
    let nationality_col = find_col("Nationality").unwrap_or(5);
    let overall_col = find_col("Overall").unwrap_or(7);
    let potential_col = find_col("Potential").unwrap_or(8);
    let club_col = find_col("Club").unwrap_or(9);
    let value_col = find_col("Value").unwrap_or(11);
    let position_col = find_col("Position").unwrap_or(21);

    let mut players = Vec::new();

    for result in rdr.records() {
        let record = result?;

        let name = record.get(name_col).unwrap_or("").trim().to_string();
        if name.is_empty() {
            continue;
        }

        let age: u32 = record
            .get(age_col)
            .unwrap_or("0")
            .trim()
            .parse()
            .unwrap_or(0);
        let overall: u32 = record
            .get(overall_col)
            .unwrap_or("0")
            .trim()
            .parse()
            .unwrap_or(0);
        let potential: u32 = record
            .get(potential_col)
            .unwrap_or("0")
            .trim()
            .parse()
            .unwrap_or(0);

        players.push(Player {
            name,
            age,
            nationality: record
                .get(nationality_col)
                .unwrap_or("")
                .trim()
                .to_string(),
            overall,
            potential,
            club: record.get(club_col).unwrap_or("").trim().to_string(),
            value: record.get(value_col).unwrap_or("").trim().to_string(),
            position: record.get(position_col).unwrap_or("").trim().to_string(),
        });
    }

    Ok(players)
}
