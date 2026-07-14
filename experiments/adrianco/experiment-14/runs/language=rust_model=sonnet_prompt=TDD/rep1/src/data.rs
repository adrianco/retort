use anyhow::{Context, Result};
use csv::ReaderBuilder;
use std::path::Path;

use crate::models::{Competition, Match, Player};

fn parse_goals(s: &str) -> u32 {
    // Handle values like "2", "2.0", or empty
    let s = s.trim().trim_matches('"');
    if s.is_empty() {
        return 0;
    }
    s.parse::<f64>().map(|f| f as u32).unwrap_or(0)
}

fn parse_season(s: &str) -> u32 {
    s.trim().trim_matches('"').parse().unwrap_or(0)
}

pub fn load_brasileirao(path: &Path) -> Result<Vec<Match>> {
    let mut reader = ReaderBuilder::new()
        .flexible(true)
        .from_path(path)
        .with_context(|| format!("Failed to open {}", path.display()))?;

    let mut matches = Vec::new();
    for result in reader.records() {
        let record = result?;
        let datetime = record.get(0).unwrap_or("").trim_matches('"').to_string();
        let home_team = record.get(1).unwrap_or("").trim_matches('"').to_string();
        let away_team = record.get(3).unwrap_or("").trim_matches('"').to_string();
        let home_goal = parse_goals(record.get(5).unwrap_or("0"));
        let away_goal = parse_goals(record.get(6).unwrap_or("0"));
        let season = parse_season(record.get(7).unwrap_or("0"));
        let round = record.get(8).map(|s| s.trim_matches('"').to_string());

        if home_team.is_empty() {
            continue;
        }

        matches.push(Match {
            competition: Competition::Brasileirao,
            datetime,
            home_team,
            away_team,
            home_goal,
            away_goal,
            season,
            round,
            stage: None,
            arena: None,
        });
    }
    Ok(matches)
}

pub fn load_copa_do_brasil(path: &Path) -> Result<Vec<Match>> {
    let mut reader = ReaderBuilder::new()
        .flexible(true)
        .from_path(path)
        .with_context(|| format!("Failed to open {}", path.display()))?;

    let mut matches = Vec::new();
    for result in reader.records() {
        let record = result?;
        let round = record.get(0).map(|s| s.trim_matches('"').to_string());
        let datetime = record.get(1).unwrap_or("").trim_matches('"').to_string();
        let home_team = record.get(2).unwrap_or("").trim_matches('"').to_string();
        let away_team = record.get(3).unwrap_or("").trim_matches('"').to_string();
        let home_goal = parse_goals(record.get(4).unwrap_or("0"));
        let away_goal = parse_goals(record.get(5).unwrap_or("0"));
        let season = parse_season(record.get(6).unwrap_or("0"));

        if home_team.is_empty() {
            continue;
        }

        matches.push(Match {
            competition: Competition::CopaDoBrasil,
            datetime,
            home_team,
            away_team,
            home_goal,
            away_goal,
            season,
            round,
            stage: None,
            arena: None,
        });
    }
    Ok(matches)
}

pub fn load_libertadores(path: &Path) -> Result<Vec<Match>> {
    let mut reader = ReaderBuilder::new()
        .flexible(true)
        .from_path(path)
        .with_context(|| format!("Failed to open {}", path.display()))?;

    let mut matches = Vec::new();
    for result in reader.records() {
        let record = result?;
        let datetime = record.get(0).unwrap_or("").trim_matches('"').to_string();
        let home_team = record.get(1).unwrap_or("").trim_matches('"').to_string();
        let away_team = record.get(2).unwrap_or("").trim_matches('"').to_string();
        let home_goal = parse_goals(record.get(3).unwrap_or("0"));
        let away_goal = parse_goals(record.get(4).unwrap_or("0"));
        let season = parse_season(record.get(5).unwrap_or("0"));
        let stage = record.get(6).map(|s| s.trim_matches('"').to_string());

        if home_team.is_empty() {
            continue;
        }

        matches.push(Match {
            competition: Competition::Libertadores,
            datetime,
            home_team,
            away_team,
            home_goal,
            away_goal,
            season,
            round: None,
            stage,
            arena: None,
        });
    }
    Ok(matches)
}

pub fn load_extended(path: &Path) -> Result<Vec<Match>> {
    let mut reader = ReaderBuilder::new()
        .flexible(true)
        .from_path(path)
        .with_context(|| format!("Failed to open {}", path.display()))?;

    let mut matches = Vec::new();
    let headers = reader.headers()?.clone();

    let col = |name: &str| headers.iter().position(|h| h == name);
    let idx_tournament = col("tournament").unwrap_or(0);
    let idx_home = col("home").unwrap_or(1);
    let idx_home_goal = col("home_goal").unwrap_or(2);
    let idx_away_goal = col("away_goal").unwrap_or(3);
    let idx_away = col("away").unwrap_or(4);
    let idx_date = col("date").unwrap_or(12);

    for result in reader.records() {
        let record = result?;
        let home_team = record.get(idx_home).unwrap_or("").trim().to_string();
        let away_team = record.get(idx_away).unwrap_or("").trim().to_string();
        let home_goal = parse_goals(record.get(idx_home_goal).unwrap_or("0"));
        let away_goal = parse_goals(record.get(idx_away_goal).unwrap_or("0"));
        let datetime = record.get(idx_date).unwrap_or("").trim().to_string();
        let tournament = record.get(idx_tournament).unwrap_or("").trim().to_string();

        if home_team.is_empty() {
            continue;
        }

        // Extract season from date (first 4 chars)
        let season = datetime.get(..4).and_then(|s| s.parse().ok()).unwrap_or(0);

        matches.push(Match {
            competition: Competition::Extended,
            datetime,
            home_team,
            away_team,
            home_goal,
            away_goal,
            season,
            round: None,
            stage: Some(tournament),
            arena: None,
        });
    }
    Ok(matches)
}

pub fn load_historical(path: &Path) -> Result<Vec<Match>> {
    let mut reader = ReaderBuilder::new()
        .flexible(true)
        .from_path(path)
        .with_context(|| format!("Failed to open {}", path.display()))?;

    let mut matches = Vec::new();
    let headers = reader.headers()?.clone();

    let col = |name: &str| headers.iter().position(|h| h == name);
    let idx_data = col("Data").unwrap_or(1);
    let idx_ano = col("Ano").unwrap_or(2);
    let idx_rodada = col("Rodada").unwrap_or(3);
    let idx_home = col("Equipe_mandante").unwrap_or(4);
    let idx_away = col("Equipe_visitante").unwrap_or(5);
    let idx_home_g = col("Gols_mandante").unwrap_or(6);
    let idx_away_g = col("Gols_visitante").unwrap_or(7);
    let idx_arena = col("Arena").unwrap_or(11);

    for result in reader.records() {
        let record = result?;
        let home_team = record.get(idx_home).unwrap_or("").trim().to_string();
        let away_team = record.get(idx_away).unwrap_or("").trim().to_string();
        let home_goal = parse_goals(record.get(idx_home_g).unwrap_or("0"));
        let away_goal = parse_goals(record.get(idx_away_g).unwrap_or("0"));
        let datetime = record.get(idx_data).unwrap_or("").trim().to_string();
        let season = parse_season(record.get(idx_ano).unwrap_or("0"));
        let round = record.get(idx_rodada).map(|s| s.trim().to_string());
        let arena = record.get(idx_arena).map(|s| s.trim().to_string());

        if home_team.is_empty() {
            continue;
        }

        matches.push(Match {
            competition: Competition::Historical,
            datetime,
            home_team,
            away_team,
            home_goal,
            away_goal,
            season,
            round,
            stage: None,
            arena,
        });
    }
    Ok(matches)
}

pub fn load_players(path: &Path) -> Result<Vec<Player>> {
    let mut reader = ReaderBuilder::new()
        .flexible(true)
        .from_path(path)
        .with_context(|| format!("Failed to open {}", path.display()))?;

    let mut players = Vec::new();
    let headers = reader.headers()?.clone();

    let col = |name: &str| {
        headers
            .iter()
            .position(|h| h.trim().trim_start_matches('\u{feff}') == name)
    };

    // The first column is unnamed (index), ID is second
    let idx_id = col("ID").unwrap_or(1);
    let idx_name = col("Name").unwrap_or(2);
    let idx_age = col("Age").unwrap_or(3);
    let idx_nationality = col("Nationality").unwrap_or(5);
    let idx_overall = col("Overall").unwrap_or(7);
    let idx_potential = col("Potential").unwrap_or(8);
    let idx_club = col("Club").unwrap_or(9);
    let idx_position = col("Position").unwrap_or(21);
    let idx_jersey = col("Jersey Number").unwrap_or(22);
    let idx_height = col("Height").unwrap_or(26);
    let idx_weight = col("Weight").unwrap_or(27);

    for result in reader.records() {
        let record = result?;
        let name = record.get(idx_name).unwrap_or("").trim().to_string();
        if name.is_empty() {
            continue;
        }

        let id: u64 = record
            .get(idx_id)
            .unwrap_or("0")
            .trim()
            .parse()
            .unwrap_or(0);
        let age: u32 = record
            .get(idx_age)
            .unwrap_or("0")
            .trim()
            .parse()
            .unwrap_or(0);
        let nationality = record.get(idx_nationality).unwrap_or("").trim().to_string();
        let overall: u32 = record
            .get(idx_overall)
            .unwrap_or("0")
            .trim()
            .parse()
            .unwrap_or(0);
        let potential: u32 = record
            .get(idx_potential)
            .unwrap_or("0")
            .trim()
            .parse()
            .unwrap_or(0);
        let club = record.get(idx_club).unwrap_or("").trim().to_string();
        let position = record.get(idx_position).unwrap_or("").trim().to_string();
        let jersey_number = record
            .get(idx_jersey)
            .and_then(|s| s.trim().parse().ok());
        let height = record.get(idx_height).unwrap_or("").trim().to_string();
        let weight = record.get(idx_weight).unwrap_or("").trim().to_string();

        players.push(Player {
            id,
            name,
            age,
            nationality,
            overall,
            potential,
            club,
            position,
            jersey_number,
            height,
            weight,
        });
    }
    Ok(players)
}

/// Database holding all loaded data.
#[derive(Default)]
pub struct Database {
    pub matches: Vec<Match>,
    pub players: Vec<Player>,
}

impl Database {
    pub fn load_from_dir(data_dir: &Path) -> Result<Self> {
        let kaggle = data_dir.join("kaggle");
        let mut matches = Vec::new();

        let brasileirao = kaggle.join("Brasileirao_Matches.csv");
        if brasileirao.exists() {
            matches.extend(load_brasileirao(&brasileirao)?);
        }

        let copa = kaggle.join("Brazilian_Cup_Matches.csv");
        if copa.exists() {
            matches.extend(load_copa_do_brasil(&copa)?);
        }

        let libertadores = kaggle.join("Libertadores_Matches.csv");
        if libertadores.exists() {
            matches.extend(load_libertadores(&libertadores)?);
        }

        let extended = kaggle.join("BR-Football-Dataset.csv");
        if extended.exists() {
            matches.extend(load_extended(&extended)?);
        }

        let historical = kaggle.join("novo_campeonato_brasileiro.csv");
        if historical.exists() {
            matches.extend(load_historical(&historical)?);
        }

        let fifa = kaggle.join("fifa_data.csv");
        let players = if fifa.exists() {
            load_players(&fifa)?
        } else {
            Vec::new()
        };

        Ok(Database { matches, players })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;
    use tempfile::NamedTempFile;

    fn write_temp(content: &str) -> NamedTempFile {
        let mut f = NamedTempFile::new().unwrap();
        f.write_all(content.as_bytes()).unwrap();
        f
    }

    #[test]
    fn load_brasileirao_parses_records() {
        let csv = "\"datetime\",\"home_team\",\"home_team_state\",\"away_team\",\"away_team_state\",\"home_goal\",\"away_goal\",\"season\",\"round\"\n\
                   2012-05-19 18:30:00,\"Palmeiras-SP\",\"SP\",\"Portuguesa-SP\",\"SP\",1,1,2012,1\n\
                   2012-05-19 18:30:00,\"Sport-PE\",\"PE\",\"Flamengo-RJ\",\"RJ\",1,1,2012,1\n";
        let f = write_temp(csv);
        let matches = load_brasileirao(f.path()).unwrap();
        assert_eq!(matches.len(), 2);
        assert_eq!(matches[0].home_team, "Palmeiras-SP");
        assert_eq!(matches[0].away_team, "Portuguesa-SP");
        assert_eq!(matches[0].home_goal, 1);
        assert_eq!(matches[0].away_goal, 1);
        assert_eq!(matches[0].season, 2012);
        assert_eq!(matches[0].competition, Competition::Brasileirao);
    }

    #[test]
    fn load_brasileirao_skips_empty_teams() {
        let csv = "\"datetime\",\"home_team\",\"home_team_state\",\"away_team\",\"away_team_state\",\"home_goal\",\"away_goal\",\"season\",\"round\"\n\
                   ,,,,,,,,\n\
                   2012-05-19,\"Flamengo-RJ\",\"RJ\",\"Santos-SP\",\"SP\",2,0,2012,1\n";
        let f = write_temp(csv);
        let matches = load_brasileirao(f.path()).unwrap();
        assert_eq!(matches.len(), 1);
        assert_eq!(matches[0].home_team, "Flamengo-RJ");
    }

    #[test]
    fn load_copa_do_brasil_parses_records() {
        let csv = "\"round\",\"datetime\",\"home_team\",\"away_team\",\"home_goal\",\"away_goal\",\"season\"\n\
                   \"1\",2012-03-07 16:00:00,\"Boavista-RJ\",\"América-MG\",0,0,2012\n";
        let f = write_temp(csv);
        let matches = load_copa_do_brasil(f.path()).unwrap();
        assert_eq!(matches.len(), 1);
        assert_eq!(matches[0].competition, Competition::CopaDoBrasil);
        assert_eq!(matches[0].round, Some("1".to_string()));
    }

    #[test]
    fn load_libertadores_parses_records() {
        let csv = "\"datetime\",\"home_team\",\"away_team\",\"home_goal\",\"away_goal\",\"season\",\"stage\"\n\
                   2013-02-12 20:15:00,\"Nacional\",\"Barcelona-EQU\",\"2\",\"2\",2013,\"group stage\"\n";
        let f = write_temp(csv);
        let matches = load_libertadores(f.path()).unwrap();
        assert_eq!(matches.len(), 1);
        assert_eq!(matches[0].competition, Competition::Libertadores);
        assert_eq!(matches[0].stage, Some("group stage".to_string()));
        assert_eq!(matches[0].home_goal, 2);
    }

    #[test]
    fn load_historical_parses_records() {
        let csv = "ID,Data,Ano,Rodada,Equipe_mandante,Equipe_visitante,Gols_mandante,Gols_visitante,Mandante_UF,Visitante_UF,Vencedor,Arena,OBS\n\
                   2003.01.0001,29/03/2003,2003,1,Guarani,Vasco,4,2,SP,RJ,Mandante,Brinco de Ouro,\n";
        let f = write_temp(csv);
        let matches = load_historical(f.path()).unwrap();
        assert_eq!(matches.len(), 1);
        assert_eq!(matches[0].home_team, "Guarani");
        assert_eq!(matches[0].away_team, "Vasco");
        assert_eq!(matches[0].home_goal, 4);
        assert_eq!(matches[0].away_goal, 2);
        assert_eq!(matches[0].season, 2003);
        assert_eq!(matches[0].arena, Some("Brinco de Ouro".to_string()));
    }

    #[test]
    fn load_extended_parses_records() {
        let csv = "tournament,home,home_goal,away_goal,away,home_corner,away_corner,home_attack,away_attack,home_shots,away_shots,time,date,ht_diff,at_diff,ht_result,at_result,total_corners\n\
                   Copa do Brasil,Sao Paulo,1.0,1.0,Flamengo,2.0,4.0,75.0,104.0,8.0,13.0,20:00:00,2023-09-24,0.0,0.0,DRAW,DRAW,6.0\n";
        let f = write_temp(csv);
        let matches = load_extended(f.path()).unwrap();
        assert_eq!(matches.len(), 1);
        assert_eq!(matches[0].home_team, "Sao Paulo");
        assert_eq!(matches[0].away_team, "Flamengo");
        assert_eq!(matches[0].home_goal, 1);
        assert_eq!(matches[0].season, 2023);
    }

    #[test]
    fn load_players_parses_records() {
        let csv = ",ID,Name,Age,Photo,Nationality,Flag,Overall,Potential,Club,Club Logo,Value,Wage,Special,Preferred Foot,International Reputation,Weak Foot,Skill Moves,Work Rate,Body Type,Real Face,Position,Jersey Number,Joined,Loaned From,Contract Valid Until,Height,Weight\n\
                   0,158023,L. Messi,31,photo,Argentina,flag,94,94,FC Barcelona,logo,€110.5M,€565K,2202,Left,5,4,4,Medium/ Medium,Messi,Yes,RF,10,Jul 1 2004,,2021,5'7,159lbs\n";
        let f = write_temp(csv);
        let players = load_players(f.path()).unwrap();
        assert_eq!(players.len(), 1);
        assert_eq!(players[0].name, "L. Messi");
        assert_eq!(players[0].age, 31);
        assert_eq!(players[0].nationality, "Argentina");
        assert_eq!(players[0].overall, 94);
        assert_eq!(players[0].club, "FC Barcelona");
        assert_eq!(players[0].position, "RF");
    }

    #[test]
    fn parse_goals_handles_float_string() {
        assert_eq!(parse_goals("1.0"), 1);
        assert_eq!(parse_goals("2.0"), 2);
        assert_eq!(parse_goals("0.0"), 0);
    }

    #[test]
    fn parse_goals_handles_integer_string() {
        assert_eq!(parse_goals("3"), 3);
        assert_eq!(parse_goals("0"), 0);
    }

    #[test]
    fn parse_goals_handles_empty() {
        assert_eq!(parse_goals(""), 0);
        assert_eq!(parse_goals("  "), 0);
    }
}
