//! CSV loaders: one raw row struct per source file, converted into the
//! unified [`crate::model::MatchRecord`] / [`crate::model::PlayerRecord`]
//! shapes.

use std::path::Path;

use anyhow::{Context, Result};
use serde::Deserialize;

use crate::dates::parse_flexible_date;
use crate::model::{Competition, MatchRecord, PlayerRecord};
use crate::normalize::{display_team_name, normalize_team_name};
use crate::store::KnowledgeBase;

/// Load all six provided datasets from `data_dir` (expected to contain the
/// files as shipped under `data/kaggle/`) into a single queryable
/// [`KnowledgeBase`].
pub fn load_from_dir(data_dir: &Path) -> Result<KnowledgeBase> {
    let mut matches = Vec::new();
    matches.extend(load_brasileirao(&data_dir.join("Brasileirao_Matches.csv"))?);
    matches.extend(load_copa_do_brasil(
        &data_dir.join("Brazilian_Cup_Matches.csv"),
    )?);
    matches.extend(load_libertadores(
        &data_dir.join("Libertadores_Matches.csv"),
    )?);
    matches.extend(load_extended_stats(
        &data_dir.join("BR-Football-Dataset.csv"),
    )?);
    matches.extend(load_historical_brasileirao(
        &data_dir.join("novo_campeonato_brasileiro.csv"),
    )?);
    let players = load_players(&data_dir.join("fifa_data.csv"))?;
    Ok(KnowledgeBase::new(matches, players))
}

fn matches_from(home_raw: &str, away_raw: &str) -> (String, String, String, String) {
    (
        display_team_name(home_raw),
        display_team_name(away_raw),
        normalize_team_name(home_raw),
        normalize_team_name(away_raw),
    )
}

/// A handful of rows (e.g. the Brasileirão 2016 Chapecoense fixture, never
/// played after the team's air disaster) record goals as the literal string
/// "NA" rather than a number. Such rows carry no result, so callers should
/// skip them rather than fabricating a score.
fn parse_goal(raw: &str) -> Option<u32> {
    raw.trim().parse::<u32>().ok()
}

// ---------------------------------------------------------------------
// Brasileirao_Matches.csv
// ---------------------------------------------------------------------

#[derive(Debug, Deserialize)]
struct BrasileiraoRow {
    datetime: String,
    home_team: String,
    #[serde(rename = "home_team_state")]
    _home_team_state: String,
    away_team: String,
    #[serde(rename = "away_team_state")]
    _away_team_state: String,
    home_goal: String,
    away_goal: String,
    season: i32,
    round: i32,
}

pub fn load_brasileirao(path: &Path) -> Result<Vec<MatchRecord>> {
    let mut reader =
        csv::Reader::from_path(path).with_context(|| format!("opening {}", path.display()))?;
    let mut out = Vec::new();
    for row in reader.deserialize::<BrasileiraoRow>() {
        let row = row.with_context(|| format!("parsing row in {}", path.display()))?;
        let (Some(home_goal), Some(away_goal)) =
            (parse_goal(&row.home_goal), parse_goal(&row.away_goal))
        else {
            continue; // match never played / no recorded result
        };
        let (home_team, away_team, home_team_key, away_team_key) =
            matches_from(&row.home_team, &row.away_team);
        out.push(MatchRecord {
            competition: Competition::Brasileirao,
            tournament: None,
            date: parse_flexible_date(&row.datetime),
            season: row.season,
            round: Some(row.round.to_string()),
            stage: None,
            home_team,
            away_team,
            home_team_key,
            away_team_key,
            home_goal,
            away_goal,
            venue: None,
            home_corners: None,
            away_corners: None,
            home_shots: None,
            away_shots: None,
        });
    }
    Ok(out)
}

// ---------------------------------------------------------------------
// Brazilian_Cup_Matches.csv
// ---------------------------------------------------------------------

#[derive(Debug, Deserialize)]
struct CupRow {
    round: String,
    datetime: String,
    home_team: String,
    away_team: String,
    home_goal: String,
    away_goal: String,
    season: i32,
}

pub fn load_copa_do_brasil(path: &Path) -> Result<Vec<MatchRecord>> {
    let mut reader =
        csv::Reader::from_path(path).with_context(|| format!("opening {}", path.display()))?;
    let mut out = Vec::new();
    for row in reader.deserialize::<CupRow>() {
        let row = row.with_context(|| format!("parsing row in {}", path.display()))?;
        let (Some(home_goal), Some(away_goal)) =
            (parse_goal(&row.home_goal), parse_goal(&row.away_goal))
        else {
            continue; // match never played / no recorded result
        };
        let (home_team, away_team, home_team_key, away_team_key) =
            matches_from(&row.home_team, &row.away_team);
        out.push(MatchRecord {
            competition: Competition::CopaDoBrasil,
            tournament: None,
            date: parse_flexible_date(&row.datetime),
            season: row.season,
            round: Some(row.round),
            stage: None,
            home_team,
            away_team,
            home_team_key,
            away_team_key,
            home_goal,
            away_goal,
            venue: None,
            home_corners: None,
            away_corners: None,
            home_shots: None,
            away_shots: None,
        });
    }
    Ok(out)
}

// ---------------------------------------------------------------------
// Libertadores_Matches.csv
// ---------------------------------------------------------------------

#[derive(Debug, Deserialize)]
struct LibertadoresRow {
    datetime: String,
    home_team: String,
    away_team: String,
    home_goal: String,
    away_goal: String,
    season: String,
    stage: String,
}

pub fn load_libertadores(path: &Path) -> Result<Vec<MatchRecord>> {
    let mut reader =
        csv::Reader::from_path(path).with_context(|| format!("opening {}", path.display()))?;
    let mut out = Vec::new();
    for row in reader.deserialize::<LibertadoresRow>() {
        let row = row.with_context(|| format!("parsing row in {}", path.display()))?;
        // A couple of rows have no numeric result: an abandoned fixture
        // (goals recorded as "-") and a placeholder row with season "NA".
        let (Some(home_goal), Some(away_goal), Some(season)) = (
            parse_goal(&row.home_goal),
            parse_goal(&row.away_goal),
            row.season.trim().parse::<i32>().ok(),
        ) else {
            continue;
        };
        let (home_team, away_team, home_team_key, away_team_key) =
            matches_from(&row.home_team, &row.away_team);
        out.push(MatchRecord {
            competition: Competition::Libertadores,
            tournament: None,
            date: parse_flexible_date(&row.datetime),
            season,
            round: None,
            stage: Some(row.stage),
            home_team,
            away_team,
            home_team_key,
            away_team_key,
            home_goal,
            away_goal,
            venue: None,
            home_corners: None,
            away_corners: None,
            home_shots: None,
            away_shots: None,
        });
    }
    Ok(out)
}

// ---------------------------------------------------------------------
// BR-Football-Dataset.csv
// ---------------------------------------------------------------------

#[derive(Debug, Deserialize)]
struct ExtendedStatsRow {
    tournament: String,
    home: String,
    home_goal: f64,
    away_goal: f64,
    away: String,
    home_corner: Option<f64>,
    away_corner: Option<f64>,
    #[serde(rename = "home_attack")]
    _home_attack: Option<f64>,
    #[serde(rename = "away_attack")]
    _away_attack: Option<f64>,
    home_shots: Option<f64>,
    away_shots: Option<f64>,
    #[serde(rename = "time")]
    _time: String,
    date: String,
}

pub fn load_extended_stats(path: &Path) -> Result<Vec<MatchRecord>> {
    let mut reader =
        csv::Reader::from_path(path).with_context(|| format!("opening {}", path.display()))?;
    let mut out = Vec::new();
    for row in reader.deserialize::<ExtendedStatsRow>() {
        let row = row.with_context(|| format!("parsing row in {}", path.display()))?;
        let (home_team, away_team, home_team_key, away_team_key) =
            matches_from(&row.home, &row.away);
        let date = parse_flexible_date(&row.date);
        out.push(MatchRecord {
            competition: Competition::ExtendedStats,
            tournament: Some(row.tournament),
            season: date
                .map(|d| d.format("%Y").to_string().parse().unwrap_or(0))
                .unwrap_or(0),
            date,
            round: None,
            stage: None,
            home_team,
            away_team,
            home_team_key,
            away_team_key,
            home_goal: row.home_goal.round() as u32,
            away_goal: row.away_goal.round() as u32,
            venue: None,
            home_corners: row.home_corner,
            away_corners: row.away_corner,
            home_shots: row.home_shots,
            away_shots: row.away_shots,
        });
    }
    Ok(out)
}

// ---------------------------------------------------------------------
// novo_campeonato_brasileiro.csv
// ---------------------------------------------------------------------

#[derive(Debug, Deserialize)]
struct HistoricalRow {
    #[serde(rename = "ID")]
    _id: String,
    #[serde(rename = "Data")]
    data: String,
    #[serde(rename = "Ano")]
    ano: i32,
    #[serde(rename = "Rodada")]
    rodada: i32,
    #[serde(rename = "Equipe_mandante")]
    equipe_mandante: String,
    #[serde(rename = "Equipe_visitante")]
    equipe_visitante: String,
    #[serde(rename = "Gols_mandante")]
    gols_mandante: u32,
    #[serde(rename = "Gols_visitante")]
    gols_visitante: u32,
    #[serde(rename = "Arena")]
    arena: Option<String>,
}

pub fn load_historical_brasileirao(path: &Path) -> Result<Vec<MatchRecord>> {
    let mut reader =
        csv::Reader::from_path(path).with_context(|| format!("opening {}", path.display()))?;
    let mut out = Vec::new();
    for row in reader.deserialize::<HistoricalRow>() {
        let row = row.with_context(|| format!("parsing row in {}", path.display()))?;
        let (home_team, away_team, home_team_key, away_team_key) =
            matches_from(&row.equipe_mandante, &row.equipe_visitante);
        out.push(MatchRecord {
            competition: Competition::HistoricalBrasileirao,
            tournament: None,
            date: parse_flexible_date(&row.data),
            season: row.ano,
            round: Some(row.rodada.to_string()),
            stage: None,
            home_team,
            away_team,
            home_team_key,
            away_team_key,
            home_goal: row.gols_mandante,
            away_goal: row.gols_visitante,
            venue: row.arena,
            home_corners: None,
            away_corners: None,
            home_shots: None,
            away_shots: None,
        });
    }
    Ok(out)
}

// ---------------------------------------------------------------------
// fifa_data.csv
// ---------------------------------------------------------------------

#[derive(Debug, Deserialize)]
struct FifaRow {
    #[serde(rename = "ID")]
    id: u64,
    #[serde(rename = "Name")]
    name: String,
    #[serde(rename = "Age")]
    age: Option<u32>,
    #[serde(rename = "Nationality")]
    nationality: String,
    #[serde(rename = "Overall")]
    overall: Option<u32>,
    #[serde(rename = "Potential")]
    potential: Option<u32>,
    #[serde(rename = "Club")]
    club: Option<String>,
    #[serde(rename = "Position")]
    position: Option<String>,
    #[serde(rename = "Jersey Number")]
    jersey_number: Option<u32>,
    #[serde(rename = "Height")]
    height: Option<String>,
    #[serde(rename = "Weight")]
    weight: Option<String>,
}

pub fn load_players(path: &Path) -> Result<Vec<PlayerRecord>> {
    let mut reader =
        csv::Reader::from_path(path).with_context(|| format!("opening {}", path.display()))?;
    let mut out = Vec::new();
    for row in reader.deserialize::<FifaRow>() {
        let row = row.with_context(|| format!("parsing row in {}", path.display()))?;
        let nationality_key = normalize_team_name(&row.nationality);
        let club_key = row
            .club
            .as_deref()
            .map(normalize_team_name)
            .unwrap_or_default();
        let name_key = normalize_team_name(&row.name);
        out.push(PlayerRecord {
            id: row.id,
            name: row.name,
            age: row.age,
            nationality: row.nationality,
            overall: row.overall,
            potential: row.potential,
            club: row.club,
            position: row.position,
            jersey_number: row.jersey_number,
            height: row.height,
            weight: row.weight,
            nationality_key,
            club_key,
            name_key,
        });
    }
    Ok(out)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn write_temp_csv(contents: &str) -> tempfile_like::TempCsv {
        tempfile_like::TempCsv::new(contents)
    }

    /// Minimal drop-in replacement for a temp-file crate: writes the given
    /// contents to a uniquely named file under the OS temp dir and removes
    /// it on drop.
    mod tempfile_like {
        use std::io::Write;
        use std::path::PathBuf;
        use std::sync::atomic::{AtomicU64, Ordering};

        static COUNTER: AtomicU64 = AtomicU64::new(0);

        pub struct TempCsv {
            pub path: PathBuf,
        }

        impl TempCsv {
            pub fn new(contents: &str) -> Self {
                let mut path = std::env::temp_dir();
                let unique = format!(
                    "brazilian_soccer_mcp_test_{}.csv",
                    COUNTER.fetch_add(1, Ordering::Relaxed)
                );
                path.push(unique);
                let mut file = std::fs::File::create(&path).unwrap();
                file.write_all(contents.as_bytes()).unwrap();
                Self { path }
            }
        }

        impl Drop for TempCsv {
            fn drop(&mut self) {
                let _ = std::fs::remove_file(&self.path);
            }
        }
    }

    // Given a Brasileirao CSV row with a state-suffixed team name
    // When it is loaded
    // Then the team names are normalized and the goals/season are parsed
    #[test]
    fn test_given_brasileirao_row_when_loading_then_fields_are_parsed_and_normalized() {
        let csv = "datetime,home_team,home_team_state,away_team,away_team_state,home_goal,away_goal,season,round\n\
                   2012-05-19 18:30:00,Palmeiras-SP,SP,Portuguesa-SP,SP,1,1,2012,1\n";
        let file = write_temp_csv(csv);
        let matches = load_brasileirao(&file.path).unwrap();
        assert_eq!(matches.len(), 1);
        let m = &matches[0];
        assert_eq!(m.home_team, "Palmeiras-SP");
        assert_eq!(m.away_team, "Portuguesa-SP");
        assert_eq!(m.home_team_key, "palmeiras sp");
        assert_eq!(m.season, 2012);
        assert_eq!(m.round.as_deref(), Some("1"));
        assert_eq!(m.date, chrono::NaiveDate::from_ymd_opt(2012, 5, 19));
    }

    // Given a Brasileirao row whose goals are recorded as "NA" (a match
    // that was never played)
    // When it is loaded
    // Then the row is skipped rather than failing the whole file
    #[test]
    fn test_given_row_with_na_goals_when_loading_then_row_is_skipped() {
        let csv = "datetime,home_team,home_team_state,away_team,away_team_state,home_goal,away_goal,season,round\n\
                   2016-12-11 17:00:00,Chapecoense-SC,SC,Atletico-MG,MG,NA,NA,2016,38\n\
                   2012-05-19 18:30:00,Palmeiras-SP,SP,Portuguesa-SP,SP,1,1,2012,1\n";
        let file = write_temp_csv(csv);
        let matches = load_brasileirao(&file.path).unwrap();
        assert_eq!(matches.len(), 1);
        assert_eq!(matches[0].home_team, "Palmeiras-SP");
    }

    // Given a Copa do Brasil CSV row with a long parenthetical team name
    // When it is loaded
    // Then the decorative parenthetical is stripped but the disambiguating
    // state suffix is kept
    #[test]
    fn test_given_cup_row_with_parenthetical_name_when_loading_then_name_is_cleaned() {
        let csv = "round,datetime,home_team,away_team,home_goal,away_goal,season\n\
                   \"1\",2012-03-07 16:00:00,\"Boavista Sport Club (antigo Esporte Clube Barreira) - RJ\",\"América - MG\",0,0,2012\n";
        let file = write_temp_csv(csv);
        let matches = load_copa_do_brasil(&file.path).unwrap();
        assert_eq!(matches[0].home_team, "Boavista Sport Club-RJ");
        assert_eq!(matches[0].away_team, "América-MG");
    }

    // Given a Libertadores CSV row with a country-coded away team
    // When it is loaded
    // Then the stage is captured and the country/region codes are kept as
    // disambiguating suffixes
    #[test]
    fn test_given_libertadores_row_when_loading_then_stage_is_captured() {
        let csv = "datetime,home_team,away_team,home_goal,away_goal,season,stage\n\
                   2013-02-12 20:15:00,\"Nacional (URU)\",\"Barcelona-EQU\",2,2,2013,\"group stage\"\n";
        let file = write_temp_csv(csv);
        let matches = load_libertadores(&file.path).unwrap();
        assert_eq!(matches[0].home_team, "Nacional-URU");
        assert_eq!(matches[0].away_team, "Barcelona-EQU");
        assert_eq!(matches[0].stage.as_deref(), Some("group stage"));
    }

    // Given an extended-stats CSV row with fractional goal counts
    // When it is loaded
    // Then goals are rounded to whole numbers and the tournament is kept
    #[test]
    fn test_given_extended_stats_row_when_loading_then_goals_are_rounded() {
        let csv = "tournament,home,home_goal,away_goal,away,home_corner,away_corner,home_attack,away_attack,home_shots,away_shots,time,date,ht_diff,at_diff,ht_result,at_result,total_corners\n\
                   Copa do Brasil,Sao Paulo,1.0,1.0,Flamengo,2.0,4.0,75.0,104.0,8.0,13.0,20:00:00,2023-09-24,0.0,0.0,DRAW,DRAW,6.0\n";
        let file = write_temp_csv(csv);
        let matches = load_extended_stats(&file.path).unwrap();
        let m = &matches[0];
        assert_eq!(m.home_goal, 1);
        assert_eq!(m.away_goal, 1);
        assert_eq!(m.tournament.as_deref(), Some("Copa do Brasil"));
        assert_eq!(m.season, 2023);
    }

    // Given a historical Brasileirao CSV row with a Brazilian date format
    // When it is loaded
    // Then the date, arena, and winner-derivable goals are parsed
    #[test]
    fn test_given_historical_row_when_loading_then_brazilian_date_is_parsed() {
        let csv = "ID,Data,Ano,Rodada,Equipe_mandante,Equipe_visitante,Gols_mandante,Gols_visitante,Mandante_UF,Visitante_UF,Vencedor,Arena,OBS\n\
                   2003.01.0001,29/03/2003,2003,1,Guarani,Vasco,4,2,SP,RJ,Mandante,Brinco de Ouro,\n";
        let file = write_temp_csv(csv);
        let matches = load_historical_brasileirao(&file.path).unwrap();
        let m = &matches[0];
        assert_eq!(m.date, chrono::NaiveDate::from_ymd_opt(2003, 3, 29));
        assert_eq!(m.venue.as_deref(), Some("Brinco de Ouro"));
        assert_eq!(m.home_goal, 4);
        assert_eq!(m.away_goal, 2);
    }

    // Given a FIFA player CSV row
    // When it is loaded
    // Then the searchable name/nationality/club keys are normalized
    #[test]
    fn test_given_fifa_player_row_when_loading_then_search_keys_are_normalized() {
        let csv = "\u{feff},ID,Name,Age,Photo,Nationality,Flag,Overall,Potential,Club,Club Logo,Value,Wage,Special,Preferred Foot,International Reputation,Weak Foot,Skill Moves,Work Rate,Body Type,Real Face,Position,Jersey Number,Joined,Loaned From,Contract Valid Until,Height,Weight,Release Clause\n\
                   0,158023,L. Messi,31,,Argentina,,94,94,FC Barcelona,,€110.5M,€565K,2202,Left,5,4,4,Medium/ Medium,Messi,Yes,RF,10,\"Jul 1, 2004\",,2021,5'7,159lbs,€226.5M\n";
        let file = write_temp_csv(csv);
        let players = load_players(&file.path).unwrap();
        assert_eq!(players.len(), 1);
        let p = &players[0];
        assert_eq!(p.name, "L. Messi");
        assert_eq!(p.nationality_key, "argentina");
        assert_eq!(p.club_key, "fc barcelona");
        assert_eq!(p.overall, Some(94));
        assert_eq!(p.jersey_number, Some(10));
    }

    // Given a FIFA player row with blank optional fields
    // When it is loaded
    // Then the blanks decode to None rather than failing the row
    #[test]
    fn test_given_fifa_player_row_with_blank_club_when_loading_then_club_is_none() {
        let csv = "ID,Name,Age,Nationality,Overall,Potential,Club,Position,Jersey Number,Height,Weight\n\
                   1,Free Agent,,Brazil,,,,,,,\n";
        let file = write_temp_csv(csv);
        let players = load_players(&file.path).unwrap();
        assert_eq!(players[0].club, None);
        assert_eq!(players[0].age, None);
        assert_eq!(players[0].club_key, "");
    }
}
