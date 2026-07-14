use anyhow::Result;
use std::collections::HashMap;
use std::path::Path;

#[derive(Debug, Clone)]
pub struct Match {
    pub date: String,
    pub home_team: String,
    pub away_team: String,
    pub home_goals: i32,
    pub away_goals: i32,
    pub competition: String,
    pub season: i32,
    pub round: Option<String>,
    pub stage: Option<String>,
}

#[allow(dead_code)]
#[derive(Debug, Clone)]
pub struct Player {
    pub id: String,
    pub name: String,
    pub age: Option<i32>,
    pub nationality: String,
    pub overall: i32,
    pub potential: i32,
    pub club: String,
    pub position: String,
    pub value: String,
    pub wage: String,
}

pub struct DataStore {
    pub matches: Vec<Match>,
    pub players: Vec<Player>,
}

/// Normalizes a team name: remove parentheticals, remove state suffixes, lowercase, trim.
pub fn normalize_team(name: &str) -> String {
    let mut s = name.to_string();

    // Remove (...) parenthetical parts
    while let Some(start) = s.find('(') {
        if let Some(end) = s.find(')') {
            if end > start {
                s = format!("{}{}", &s[..start], &s[end + 1..]);
            } else {
                break;
            }
        } else {
            break;
        }
    }

    // Remove " - XX" state suffixes (space-dash-space-2uppercase)
    let re_space = regex_remove_state_space(&s);
    s = re_space;

    // Remove "-XX" state suffixes
    let re_dash = regex_remove_state_dash(&s);
    s = re_dash;

    s.to_lowercase().trim().to_string()
}

fn regex_remove_state_space(s: &str) -> String {
    // Remove " - XX" where XX is 2 uppercase letters at end or followed by whitespace
    let bytes = s.as_bytes();
    let len = bytes.len();
    let mut result = s.to_string();

    // Find " - XX" pattern
    let mut i = 0;
    while i + 4 < len {
        if bytes[i] == b' ' && bytes[i + 1] == b'-' && bytes[i + 2] == b' '
            && bytes[i + 3].is_ascii_uppercase()
            && bytes[i + 4].is_ascii_uppercase()
        {
            // Check it's end of string or followed by whitespace/end
            let end = i + 5;
            if end == len || bytes[end].is_ascii_whitespace() {
                result = format!("{}{}", &s[..i], &s[end..]);
                break;
            }
        }
        i += 1;
    }
    result
}

fn regex_remove_state_dash(s: &str) -> String {
    // Remove "-XX" where XX is 2 uppercase letters at end
    let bytes = s.as_bytes();
    let len = bytes.len();

    if len >= 3 {
        let i = len - 3;
        if bytes[i] == b'-'
            && bytes[i + 1].is_ascii_uppercase()
            && bytes[i + 2].is_ascii_uppercase()
        {
            return s[..i].to_string();
        }
    }
    s.to_string()
}

/// Returns true if normalized team name contains or is contained by normalized query.
pub fn team_matches_query(team_name: &str, query: &str) -> bool {
    let norm_team = normalize_team(team_name);
    let norm_query = normalize_team(query);
    norm_team.contains(&norm_query) || norm_query.contains(&norm_team)
}

/// Parse date: convert "DD/MM/YYYY" to "YYYY-MM-DD", extract date from "YYYY-MM-DD HH:MM:SS"
pub fn normalize_date(s: &str) -> String {
    let s = s.trim();
    // DD/MM/YYYY
    if s.len() == 10 && s.chars().nth(2) == Some('/') && s.chars().nth(5) == Some('/') {
        let parts: Vec<&str> = s.split('/').collect();
        if parts.len() == 3 {
            return format!("{}-{}-{}", parts[2], parts[1], parts[0]);
        }
    }
    // YYYY-MM-DD HH:MM:SS
    if s.len() >= 10 && s.chars().nth(4) == Some('-') {
        return s[..10].to_string();
    }
    s.to_string()
}

fn parse_goals(s: &str) -> Option<i32> {
    let s = s.trim();
    if let Ok(f) = s.parse::<f64>() {
        return Some(f as i32);
    }
    if let Ok(i) = s.parse::<i32>() {
        return Some(i);
    }
    None
}

fn parse_season(s: &str) -> Option<i32> {
    let s = s.trim();
    s.parse::<i32>().ok()
}

fn col_index(headers: &csv::StringRecord, name: &str) -> Option<usize> {
    let lower = name.to_lowercase();
    for (i, h) in headers.iter().enumerate() {
        // Strip BOM if present
        let h = h.trim_start_matches('\u{FEFF}').trim_start_matches('﻿').trim();
        if h.to_lowercase() == lower {
            return Some(i);
        }
    }
    None
}

fn get_field(record: &csv::StringRecord, idx: Option<usize>) -> &str {
    match idx {
        Some(i) => record.get(i).unwrap_or("").trim(),
        None => "",
    }
}

impl DataStore {
    pub fn load(data_dir: &Path) -> Result<Self> {
        let mut matches = Vec::new();
        let mut players = Vec::new();

        // 1. Brasileirao_Matches.csv
        // headers: datetime, home_team, home_team_state, away_team, away_team_state, home_goal, away_goal, season, round
        {
            let path = data_dir.join("Brasileirao_Matches.csv");
            let mut rdr = csv::ReaderBuilder::new()
                .flexible(true)
                .trim(csv::Trim::All)
                .from_path(&path)?;
            let headers = rdr.headers()?.clone();
            let c_datetime = col_index(&headers, "datetime");
            let c_home = col_index(&headers, "home_team");
            let c_away = col_index(&headers, "away_team");
            let c_hg = col_index(&headers, "home_goal");
            let c_ag = col_index(&headers, "away_goal");
            let c_season = col_index(&headers, "season");
            let c_round = col_index(&headers, "round");

            let mut count = 0;
            for result in rdr.records() {
                let record = match result {
                    Ok(r) => r,
                    Err(_) => continue,
                };
                let date = normalize_date(get_field(&record, c_datetime));
                let home = get_field(&record, c_home).to_string();
                let away = get_field(&record, c_away).to_string();
                let hg = match parse_goals(get_field(&record, c_hg)) { Some(v) => v, None => continue };
                let ag = match parse_goals(get_field(&record, c_ag)) { Some(v) => v, None => continue };
                let season = match parse_season(get_field(&record, c_season)) { Some(v) => v, None => continue };
                let round = {
                    let r = get_field(&record, c_round).to_string();
                    if r.is_empty() { None } else { Some(r) }
                };
                matches.push(Match {
                    date,
                    home_team: home,
                    away_team: away,
                    home_goals: hg,
                    away_goals: ag,
                    competition: "Brasileirão".to_string(),
                    season,
                    round,
                    stage: None,
                });
                count += 1;
            }
            eprintln!("Loaded {} Brasileirao matches", count);
        }

        // 2. Brazilian_Cup_Matches.csv
        // headers: round, datetime, home_team, away_team, home_goal, away_goal, season
        {
            let path = data_dir.join("Brazilian_Cup_Matches.csv");
            let mut rdr = csv::ReaderBuilder::new()
                .flexible(true)
                .trim(csv::Trim::All)
                .from_path(&path)?;
            let headers = rdr.headers()?.clone();
            let c_datetime = col_index(&headers, "datetime");
            let c_home = col_index(&headers, "home_team");
            let c_away = col_index(&headers, "away_team");
            let c_hg = col_index(&headers, "home_goal");
            let c_ag = col_index(&headers, "away_goal");
            let c_season = col_index(&headers, "season");
            let c_round = col_index(&headers, "round");

            let mut count = 0;
            for result in rdr.records() {
                let record = match result {
                    Ok(r) => r,
                    Err(_) => continue,
                };
                let date = normalize_date(get_field(&record, c_datetime));
                let home = get_field(&record, c_home).to_string();
                let away = get_field(&record, c_away).to_string();
                let hg = match parse_goals(get_field(&record, c_hg)) { Some(v) => v, None => continue };
                let ag = match parse_goals(get_field(&record, c_ag)) { Some(v) => v, None => continue };
                let season = match parse_season(get_field(&record, c_season)) { Some(v) => v, None => continue };
                let round = {
                    let r = get_field(&record, c_round).to_string();
                    if r.is_empty() { None } else { Some(r) }
                };
                matches.push(Match {
                    date,
                    home_team: home,
                    away_team: away,
                    home_goals: hg,
                    away_goals: ag,
                    competition: "Copa do Brasil".to_string(),
                    season,
                    round,
                    stage: None,
                });
                count += 1;
            }
            eprintln!("Loaded {} Brazilian Cup matches", count);
        }

        // 3. Libertadores_Matches.csv
        // headers: datetime, home_team, away_team, home_goal, away_goal, season, stage
        {
            let path = data_dir.join("Libertadores_Matches.csv");
            let mut rdr = csv::ReaderBuilder::new()
                .flexible(true)
                .trim(csv::Trim::All)
                .from_path(&path)?;
            let headers = rdr.headers()?.clone();
            let c_datetime = col_index(&headers, "datetime");
            let c_home = col_index(&headers, "home_team");
            let c_away = col_index(&headers, "away_team");
            let c_hg = col_index(&headers, "home_goal");
            let c_ag = col_index(&headers, "away_goal");
            let c_season = col_index(&headers, "season");
            let c_stage = col_index(&headers, "stage");

            let mut count = 0;
            for result in rdr.records() {
                let record = match result {
                    Ok(r) => r,
                    Err(_) => continue,
                };
                let date = normalize_date(get_field(&record, c_datetime));
                let home = get_field(&record, c_home).to_string();
                let away = get_field(&record, c_away).to_string();
                let hg = match parse_goals(get_field(&record, c_hg)) { Some(v) => v, None => continue };
                let ag = match parse_goals(get_field(&record, c_ag)) { Some(v) => v, None => continue };
                let season = match parse_season(get_field(&record, c_season)) { Some(v) => v, None => continue };
                let stage = {
                    let r = get_field(&record, c_stage).to_string();
                    if r.is_empty() { None } else { Some(r) }
                };
                matches.push(Match {
                    date,
                    home_team: home,
                    away_team: away,
                    home_goals: hg,
                    away_goals: ag,
                    competition: "Copa Libertadores".to_string(),
                    season,
                    round: None,
                    stage,
                });
                count += 1;
            }
            eprintln!("Loaded {} Libertadores matches", count);
        }

        // 4. BR-Football-Dataset.csv
        // headers: tournament, home, home_goal, away_goal, away, ..., date
        {
            let path = data_dir.join("BR-Football-Dataset.csv");
            let mut rdr = csv::ReaderBuilder::new()
                .flexible(true)
                .trim(csv::Trim::All)
                .from_path(&path)?;
            let headers = rdr.headers()?.clone();
            let c_tournament = col_index(&headers, "tournament");
            let c_home = col_index(&headers, "home");
            let c_away = col_index(&headers, "away");
            let c_hg = col_index(&headers, "home_goal");
            let c_ag = col_index(&headers, "away_goal");
            let c_date = col_index(&headers, "date");

            let mut count = 0;
            for result in rdr.records() {
                let record = match result {
                    Ok(r) => r,
                    Err(_) => continue,
                };
                let date = normalize_date(get_field(&record, c_date));
                let home = get_field(&record, c_home).to_string();
                let away = get_field(&record, c_away).to_string();
                let hg = match parse_goals(get_field(&record, c_hg)) { Some(v) => v, None => continue };
                let ag = match parse_goals(get_field(&record, c_ag)) { Some(v) => v, None => continue };
                let competition = get_field(&record, c_tournament).to_string();
                // Extract year from date for season
                let season = if date.len() >= 4 {
                    date[..4].parse::<i32>().unwrap_or(0)
                } else {
                    0
                };
                if home.is_empty() || away.is_empty() {
                    continue;
                }
                matches.push(Match {
                    date,
                    home_team: home,
                    away_team: away,
                    home_goals: hg,
                    away_goals: ag,
                    competition,
                    season,
                    round: None,
                    stage: None,
                });
                count += 1;
            }
            eprintln!("Loaded {} BR-Football matches", count);
        }

        // 5. novo_campeonato_brasileiro.csv
        // headers: ID, Data, Ano, Rodada, Equipe_mandante, Equipe_visitante, Gols_mandante, Gols_visitante, ...
        {
            let path = data_dir.join("novo_campeonato_brasileiro.csv");
            let mut rdr = csv::ReaderBuilder::new()
                .flexible(true)
                .trim(csv::Trim::All)
                .from_path(&path)?;
            let headers = rdr.headers()?.clone();
            let c_data = col_index(&headers, "Data");
            let c_ano = col_index(&headers, "Ano");
            let c_rodada = col_index(&headers, "Rodada");
            let c_home = col_index(&headers, "Equipe_mandante");
            let c_away = col_index(&headers, "Equipe_visitante");
            let c_hg = col_index(&headers, "Gols_mandante");
            let c_ag = col_index(&headers, "Gols_visitante");

            let mut count = 0;
            for result in rdr.records() {
                let record = match result {
                    Ok(r) => r,
                    Err(_) => continue,
                };
                let date = normalize_date(get_field(&record, c_data));
                let home = get_field(&record, c_home).to_string();
                let away = get_field(&record, c_away).to_string();
                let hg = match parse_goals(get_field(&record, c_hg)) { Some(v) => v, None => continue };
                let ag = match parse_goals(get_field(&record, c_ag)) { Some(v) => v, None => continue };
                let season = match parse_season(get_field(&record, c_ano)) { Some(v) => v, None => continue };
                let round = {
                    let r = get_field(&record, c_rodada).to_string();
                    if r.is_empty() { None } else { Some(r) }
                };
                if home.is_empty() || away.is_empty() {
                    continue;
                }
                matches.push(Match {
                    date,
                    home_team: home,
                    away_team: away,
                    home_goals: hg,
                    away_goals: ag,
                    competition: "Brasileirão".to_string(),
                    season,
                    round,
                    stage: None,
                });
                count += 1;
            }
            eprintln!("Loaded {} novo_campeonato_brasileiro matches", count);
        }

        // 6. fifa_data.csv
        // Has BOM, empty first column. Headers include: ID, Name, Age, Nationality, Overall, Potential, Club, Position, Value, Wage
        {
            let path = data_dir.join("fifa_data.csv");
            // Read raw bytes to strip BOM
            let content = std::fs::read(&path)?;
            let content = if content.starts_with(&[0xEF, 0xBB, 0xBF]) {
                content[3..].to_vec()
            } else {
                content
            };

            let mut rdr = csv::ReaderBuilder::new()
                .flexible(true)
                .trim(csv::Trim::All)
                .from_reader(content.as_slice());

            let headers = rdr.headers()?.clone();

            // Build a map of header name -> index, stripping BOM from first header
            let mut header_map: HashMap<String, usize> = HashMap::new();
            for (i, h) in headers.iter().enumerate() {
                let h_clean = h.trim_start_matches('\u{FEFF}').trim_start_matches('﻿').trim().to_lowercase();
                header_map.insert(h_clean, i);
            }

            let c_id = header_map.get("id").copied();
            let c_name = header_map.get("name").copied();
            let c_age = header_map.get("age").copied();
            let c_nationality = header_map.get("nationality").copied();
            let c_overall = header_map.get("overall").copied();
            let c_potential = header_map.get("potential").copied();
            let c_club = header_map.get("club").copied();
            let c_position = header_map.get("position").copied();
            let c_value = header_map.get("value").copied();
            let c_wage = header_map.get("wage").copied();

            let mut count = 0;
            for result in rdr.records() {
                let record = match result {
                    Ok(r) => r,
                    Err(_) => continue,
                };
                let id = get_field(&record, c_id).to_string();
                let name = get_field(&record, c_name).to_string();
                if name.is_empty() {
                    continue;
                }
                let age = get_field(&record, c_age).parse::<i32>().ok();
                let nationality = get_field(&record, c_nationality).to_string();
                let overall = match get_field(&record, c_overall).parse::<i32>().ok() {
                    Some(v) => v,
                    None => continue,
                };
                let potential = get_field(&record, c_potential).parse::<i32>().unwrap_or(0);
                let club = get_field(&record, c_club).to_string();
                let position = get_field(&record, c_position).to_string();
                let value = get_field(&record, c_value).to_string();
                let wage = get_field(&record, c_wage).to_string();

                players.push(Player {
                    id,
                    name,
                    age,
                    nationality,
                    overall,
                    potential,
                    club,
                    position,
                    value,
                    wage,
                });
                count += 1;
            }
            eprintln!("Loaded {} FIFA players", count);
        }

        eprintln!("Total matches: {}, Total players: {}", matches.len(), players.len());
        Ok(DataStore { matches, players })
    }
}
