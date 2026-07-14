use std::io::Read;
use std::path::Path;

use crate::dates::parse_flexible_date;
use crate::models::{Competition, Match};
use crate::normalize::normalize_team_name;
use serde::Deserialize;

/// Some matches (e.g. Chapecoense's 2016 games after the Sep 2016 air disaster) are
/// recorded with "NA" goal counts since the fixture was never played out; treat those as 0.
fn deserialize_goal_count<'de, D>(deserializer: D) -> Result<u32, D::Error>
where
    D: serde::Deserializer<'de>,
{
    let s = String::deserialize(deserializer)?;
    Ok(s.trim().parse().unwrap_or(0))
}

#[derive(Debug, serde::Deserialize)]
struct BrasileiraoRecord {
    datetime: String,
    home_team: String,
    away_team: String,
    #[serde(deserialize_with = "deserialize_goal_count")]
    home_goal: u32,
    #[serde(deserialize_with = "deserialize_goal_count")]
    away_goal: u32,
    season: i32,
    round: String,
}

pub fn load_brasileirao_matches_from_reader<R: Read>(reader: R) -> anyhow::Result<Vec<Match>> {
    let mut rdr = csv::Reader::from_reader(reader);
    let mut matches = Vec::new();
    for result in rdr.deserialize() {
        let record: BrasileiraoRecord = result?;
        matches.push(Match {
            date: parse_flexible_date(&record.datetime),
            competition: Competition::BrasileiraoSerieA,
            season: record.season,
            round: Some(record.round),
            stage: None,
            home_team: normalize_team_name(&record.home_team),
            away_team: normalize_team_name(&record.away_team),
            home_goal: record.home_goal,
            away_goal: record.away_goal,
            venue: None,
            source: "Brasileirao_Matches.csv",
        });
    }
    Ok(matches)
}

#[derive(Debug, serde::Deserialize)]
struct BrazilianCupRecord {
    round: String,
    datetime: String,
    home_team: String,
    away_team: String,
    #[serde(deserialize_with = "deserialize_goal_count")]
    home_goal: u32,
    #[serde(deserialize_with = "deserialize_goal_count")]
    away_goal: u32,
    season: i32,
}

pub fn load_brazilian_cup_matches_from_reader<R: Read>(reader: R) -> anyhow::Result<Vec<Match>> {
    let mut rdr = csv::Reader::from_reader(reader);
    let mut matches = Vec::new();
    for result in rdr.deserialize() {
        let record: BrazilianCupRecord = result?;
        matches.push(Match {
            date: parse_flexible_date(&record.datetime),
            competition: Competition::CopaDoBrasil,
            season: record.season,
            round: Some(record.round),
            stage: None,
            home_team: normalize_team_name(&record.home_team),
            away_team: normalize_team_name(&record.away_team),
            home_goal: record.home_goal,
            away_goal: record.away_goal,
            venue: None,
            source: "Brazilian_Cup_Matches.csv",
        });
    }
    Ok(matches)
}

/// Handles a stray unplayed-fixture placeholder row in the Libertadores dataset
/// (`season` is literally "NA" with "-" for goals); such rows carry no usable data.
fn deserialize_optional_season<'de, D>(deserializer: D) -> Result<Option<i32>, D::Error>
where
    D: serde::Deserializer<'de>,
{
    let s = String::deserialize(deserializer)?;
    Ok(s.trim().parse().ok())
}

#[derive(Debug, serde::Deserialize)]
struct LibertadoresRecord {
    datetime: String,
    home_team: String,
    away_team: String,
    #[serde(deserialize_with = "deserialize_goal_count")]
    home_goal: u32,
    #[serde(deserialize_with = "deserialize_goal_count")]
    away_goal: u32,
    #[serde(deserialize_with = "deserialize_optional_season")]
    season: Option<i32>,
    stage: String,
}

pub fn load_libertadores_matches_from_reader<R: Read>(reader: R) -> anyhow::Result<Vec<Match>> {
    let mut rdr = csv::Reader::from_reader(reader);
    let mut matches = Vec::new();
    for result in rdr.deserialize() {
        let record: LibertadoresRecord = result?;
        let Some(season) = record.season else {
            continue;
        };
        matches.push(Match {
            date: parse_flexible_date(&record.datetime),
            competition: Competition::Libertadores,
            season,
            round: None,
            stage: Some(record.stage),
            home_team: normalize_team_name(&record.home_team),
            away_team: normalize_team_name(&record.away_team),
            home_goal: record.home_goal,
            away_goal: record.away_goal,
            venue: None,
            source: "Libertadores_Matches.csv",
        });
    }
    Ok(matches)
}

#[derive(Debug, serde::Deserialize)]
struct BrFootballRecord {
    tournament: String,
    home: String,
    home_goal: f64,
    away_goal: f64,
    away: String,
    date: String,
}

fn br_football_competition(tournament: &str) -> Competition {
    match tournament {
        "Serie A" => Competition::BrasileiraoSerieA,
        "Serie B" => Competition::BrasileiraoSerieB,
        "Serie C" => Competition::BrasileiraoSerieC,
        "Copa do Brasil" => Competition::CopaDoBrasil,
        other => Competition::Other(other.to_string()),
    }
}

pub fn load_br_football_dataset_from_reader<R: Read>(reader: R) -> anyhow::Result<Vec<Match>> {
    let mut rdr = csv::Reader::from_reader(reader);
    let mut matches = Vec::new();
    for result in rdr.deserialize() {
        let record: BrFootballRecord = result?;
        let date = parse_flexible_date(&record.date);
        let season = date.map(|d| d.format("%Y").to_string().parse().unwrap_or(0)).unwrap_or(0);
        matches.push(Match {
            date,
            competition: br_football_competition(&record.tournament),
            season,
            round: None,
            stage: None,
            home_team: normalize_team_name(&record.home),
            away_team: normalize_team_name(&record.away),
            home_goal: record.home_goal.round() as u32,
            away_goal: record.away_goal.round() as u32,
            venue: None,
            source: "BR-Football-Dataset.csv",
        });
    }
    Ok(matches)
}

#[derive(Debug, serde::Deserialize)]
struct NovoCampeonatoRecord {
    #[serde(rename = "Data")]
    data: String,
    #[serde(rename = "Ano")]
    ano: i32,
    #[serde(rename = "Rodada")]
    rodada: String,
    #[serde(rename = "Equipe_mandante")]
    equipe_mandante: String,
    #[serde(rename = "Equipe_visitante")]
    equipe_visitante: String,
    #[serde(rename = "Gols_mandante", deserialize_with = "deserialize_goal_count")]
    gols_mandante: u32,
    #[serde(rename = "Gols_visitante", deserialize_with = "deserialize_goal_count")]
    gols_visitante: u32,
    #[serde(rename = "Arena")]
    arena: String,
}

pub fn load_novo_campeonato_from_reader<R: Read>(reader: R) -> anyhow::Result<Vec<Match>> {
    let mut rdr = csv::Reader::from_reader(reader);
    let mut matches = Vec::new();
    for result in rdr.deserialize() {
        let record: NovoCampeonatoRecord = result?;
        matches.push(Match {
            date: parse_flexible_date(&record.data),
            competition: Competition::BrasileiraoSerieA,
            season: record.ano,
            round: Some(record.rodada),
            stage: None,
            home_team: normalize_team_name(&record.equipe_mandante),
            away_team: normalize_team_name(&record.equipe_visitante),
            home_goal: record.gols_mandante,
            away_goal: record.gols_visitante,
            venue: Some(record.arena),
            source: "novo_campeonato_brasileiro.csv",
        });
    }
    Ok(matches)
}

fn open(path: &Path) -> anyhow::Result<std::fs::File> {
    std::fs::File::open(path).map_err(|e| anyhow::anyhow!("failed to open {}: {e}", path.display()))
}

pub fn load_brasileirao_matches(path: &Path) -> anyhow::Result<Vec<Match>> {
    load_brasileirao_matches_from_reader(open(path)?)
}

pub fn load_brazilian_cup_matches(path: &Path) -> anyhow::Result<Vec<Match>> {
    load_brazilian_cup_matches_from_reader(open(path)?)
}

pub fn load_libertadores_matches(path: &Path) -> anyhow::Result<Vec<Match>> {
    load_libertadores_matches_from_reader(open(path)?)
}

pub fn load_br_football_dataset(path: &Path) -> anyhow::Result<Vec<Match>> {
    load_br_football_dataset_from_reader(open(path)?)
}

pub fn load_novo_campeonato(path: &Path) -> anyhow::Result<Vec<Match>> {
    load_novo_campeonato_from_reader(open(path)?)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::models::Competition;

    const BRASILEIRAO_FIXTURE: &str = "\"datetime\",\"home_team\",\"home_team_state\",\"away_team\",\"away_team_state\",\"home_goal\",\"away_goal\",\"season\",\"round\"
2012-05-19 18:30:00,\"Palmeiras-SP\",\"SP\",\"Portuguesa-SP\",\"SP\",1,1,2012,1
2012-05-19 18:30:00,\"Sport-PE\",\"PE\",\"Flamengo-RJ\",\"RJ\",1,1,2012,1
";

    #[test]
    fn loads_brasileirao_matches_with_normalized_team_names() {
        let matches = load_brasileirao_matches_from_reader(BRASILEIRAO_FIXTURE.as_bytes()).unwrap();
        assert_eq!(matches.len(), 2);
        let m = &matches[0];
        assert_eq!(m.home_team, "Palmeiras");
        assert_eq!(m.away_team, "Portuguesa");
        assert_eq!(m.home_goal, 1);
        assert_eq!(m.away_goal, 1);
        assert_eq!(m.season, 2012);
        assert_eq!(m.round, Some("1".to_string()));
        assert_eq!(m.competition, Competition::BrasileiraoSerieA);
        assert_eq!(
            m.date,
            Some(chrono::NaiveDate::from_ymd_opt(2012, 5, 19).unwrap())
        );
    }

    const BRASILEIRAO_NA_GOALS_FIXTURE: &str = "\"datetime\",\"home_team\",\"home_team_state\",\"away_team\",\"away_team_state\",\"home_goal\",\"away_goal\",\"season\",\"round\"
2016-12-11 17:00:00,\"Chapecoense-SC\",\"SC\",\"Atletico-MG\",\"MG\",NA,NA,2016,38
";

    #[test]
    fn treats_na_goal_values_as_zero() {
        let matches =
            load_brasileirao_matches_from_reader(BRASILEIRAO_NA_GOALS_FIXTURE.as_bytes()).unwrap();
        assert_eq!(matches.len(), 1);
        assert_eq!(matches[0].home_goal, 0);
        assert_eq!(matches[0].away_goal, 0);
    }

    const CUP_FIXTURE: &str = "\"round\",\"datetime\",\"home_team\",\"away_team\",\"home_goal\",\"away_goal\",\"season\"
\"1\",2012-03-07 16:00:00,\"Boavista Sport Club - RJ\",\"América - MG\",0,0,2012
";

    #[test]
    fn loads_brazilian_cup_matches() {
        let matches = load_brazilian_cup_matches_from_reader(CUP_FIXTURE.as_bytes()).unwrap();
        assert_eq!(matches.len(), 1);
        let m = &matches[0];
        assert_eq!(m.home_team, "Boavista Sport Club");
        assert_eq!(m.away_team, "América");
        assert_eq!(m.competition, Competition::CopaDoBrasil);
        assert_eq!(m.round, Some("1".to_string()));
        assert_eq!(m.season, 2012);
    }

    const LIBERTADORES_FIXTURE: &str = "\"datetime\",\"home_team\",\"away_team\",\"home_goal\",\"away_goal\",\"season\",\"stage\"
2013-02-12 20:15:00,\"Nacional (URU)\",\"Barcelona-EQU\",\"2\",\"2\",2013,\"group stage\"
";

    const LIBERTADORES_PLACEHOLDER_FIXTURE: &str = "\"datetime\",\"home_team\",\"away_team\",\"home_goal\",\"away_goal\",\"season\",\"stage\"
2013-02-12 20:15:00,\"Nacional (URU)\",\"Barcelona-EQU\",\"2\",\"2\",2013,\"group stage\"
NA,\"Flamengo\",\"Athletico\",\"-\",\"-\",NA,\"final\"
";

    #[test]
    fn skips_placeholder_rows_with_no_season() {
        let matches =
            load_libertadores_matches_from_reader(LIBERTADORES_PLACEHOLDER_FIXTURE.as_bytes())
                .unwrap();
        assert_eq!(matches.len(), 1);
        assert_eq!(matches[0].home_team, "Nacional (URU)");
    }

    #[test]
    fn loads_libertadores_matches() {
        let matches = load_libertadores_matches_from_reader(LIBERTADORES_FIXTURE.as_bytes()).unwrap();
        assert_eq!(matches.len(), 1);
        let m = &matches[0];
        assert_eq!(m.home_team, "Nacional (URU)");
        assert_eq!(m.away_team, "Barcelona-EQU");
        assert_eq!(m.competition, Competition::Libertadores);
        assert_eq!(m.stage, Some("group stage".to_string()));
        assert_eq!(m.home_goal, 2);
        assert_eq!(m.away_goal, 2);
    }

    const BR_FOOTBALL_FIXTURE: &str = "tournament,home,home_goal,away_goal,away,home_corner,away_corner,home_attack,away_attack,home_shots,away_shots,time,date,ht_diff,at_diff,ht_result,at_result,total_corners
Copa do Brasil,Sao Paulo,1.0,1.0,Flamengo,2.0,4.0,75.0,104.0,8.0,13.0,20:00:00,2023-09-24,0.0,0.0,DRAW,DRAW,6.0
Serie A,Palmeiras-SP,3.0,0.0,Santos-SP,5.0,2.0,90.0,60.0,10.0,4.0,16:00:00,2023-10-01,1.0,-1.0,WON,LOST,7.0
";

    #[test]
    fn loads_br_football_dataset_matches() {
        let matches = load_br_football_dataset_from_reader(BR_FOOTBALL_FIXTURE.as_bytes()).unwrap();
        assert_eq!(matches.len(), 2);
        assert_eq!(matches[0].home_team, "Sao Paulo");
        assert_eq!(matches[0].away_team, "Flamengo");
        assert_eq!(matches[0].competition, Competition::CopaDoBrasil);
        assert_eq!(matches[0].home_goal, 1);
        assert_eq!(matches[0].away_goal, 1);
        assert_eq!(
            matches[0].date,
            Some(chrono::NaiveDate::from_ymd_opt(2023, 9, 24).unwrap())
        );
        assert_eq!(matches[0].season, 2023);

        assert_eq!(matches[1].competition, Competition::BrasileiraoSerieA);
        assert_eq!(matches[1].home_team, "Palmeiras");
        assert_eq!(matches[1].away_team, "Santos");
    }

    const NOVO_CAMPEONATO_FIXTURE: &str = "ID,Data,Ano,Rodada,Equipe_mandante,Equipe_visitante,Gols_mandante,Gols_visitante,Mandante_UF,Visitante_UF,Vencedor,Arena,OBS
2003.01.0001,29/03/2003,2003,1,Guarani,Vasco,4,2,SP,RJ,Mandante,Brinco de Ouro,
";

    #[test]
    fn loads_novo_campeonato_matches() {
        let matches = load_novo_campeonato_from_reader(NOVO_CAMPEONATO_FIXTURE.as_bytes()).unwrap();
        assert_eq!(matches.len(), 1);
        let m = &matches[0];
        assert_eq!(m.home_team, "Guarani");
        assert_eq!(m.away_team, "Vasco");
        assert_eq!(m.home_goal, 4);
        assert_eq!(m.away_goal, 2);
        assert_eq!(m.season, 2003);
        assert_eq!(m.round, Some("1".to_string()));
        assert_eq!(m.venue, Some("Brinco de Ouro".to_string()));
        assert_eq!(m.competition, Competition::BrasileiraoSerieA);
        assert_eq!(
            m.date,
            Some(chrono::NaiveDate::from_ymd_opt(2003, 3, 29).unwrap())
        );
    }
}
