use anyhow::{Context, Result};
use serde::Deserialize;
use std::path::Path;

/// A normalized match record, unified across all CSV sources.
#[derive(Debug, Clone)]
pub struct Match {
    pub date: String,        // ISO-ish or original string
    pub home_team: String,   // raw (may include state suffix)
    pub away_team: String,
    pub home_goal: i32,
    pub away_goal: i32,
    pub competition: Competition,
    pub season: i32,
    pub round: String,
    pub extra: String, // stage / arena / tournament label
}

#[derive(Debug, Clone, PartialEq)]
pub enum Competition {
    Brasileirao,
    CopaBrasil,
    Libertadores,
    BrFootball,
    Historico,
}

impl Competition {
    pub fn label(&self) -> &'static str {
        match self {
            Competition::Brasileirao => "Brasileirao",
            Competition::CopaBrasil => "Copa do Brasil",
            Competition::Libertadores => "Libertadores",
            Competition::BrFootball => "BR Football",
            Competition::Historico => "Historico",
        }
    }

    pub fn from_str(s: &str) -> Option<Self> {
        match s.to_lowercase().as_str() {
            "brasileirao" => Some(Competition::Brasileirao),
            "copa_brasil" | "copa do brasil" | "copa_do_brasil" => Some(Competition::CopaBrasil),
            "libertadores" => Some(Competition::Libertadores),
            "br_football" => Some(Competition::BrFootball),
            "historico" => Some(Competition::Historico),
            _ => None,
        }
    }
}

/// FIFA player record.
#[derive(Debug, Clone)]
pub struct Player {
    #[allow(dead_code)]
    pub id: String,
    pub name: String,
    pub age: i32,
    pub nationality: String,
    pub overall: i32,
    pub potential: i32,
    pub club: String,
    pub position: String,
    #[allow(dead_code)]
    pub value: String,
    #[allow(dead_code)]
    pub wage: String,
}

pub struct DataStore {
    pub matches: Vec<Match>,
    pub players: Vec<Player>,
}

// ---------------------------------------------------------------------------
// CSV row structs
// ---------------------------------------------------------------------------

#[derive(Debug, Deserialize)]
struct BrasileiraoRow {
    datetime: String,
    home_team: String,
    #[allow(dead_code)]
    home_team_state: String,
    away_team: String,
    #[allow(dead_code)]
    away_team_state: String,
    home_goal: String,
    away_goal: String,
    season: String,
    round: String,
}

#[derive(Debug, Deserialize)]
struct CupRow {
    round: String,
    datetime: String,
    home_team: String,
    away_team: String,
    home_goal: String,
    away_goal: String,
    season: String,
}

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

#[derive(Debug, Deserialize)]
struct BrFootballRow {
    tournament: String,
    home: String,
    home_goal: String,
    away_goal: String,
    away: String,
    #[allow(dead_code)]
    home_corner: String,
    #[allow(dead_code)]
    away_corner: String,
    #[allow(dead_code)]
    home_attack: String,
    #[allow(dead_code)]
    away_attack: String,
    #[allow(dead_code)]
    home_shots: String,
    #[allow(dead_code)]
    away_shots: String,
    #[allow(dead_code)]
    time: String,
    date: String,
    #[allow(dead_code)]
    ht_diff: String,
    #[allow(dead_code)]
    at_diff: String,
    #[allow(dead_code)]
    ht_result: String,
    #[allow(dead_code)]
    at_result: String,
    #[allow(dead_code)]
    total_corners: String,
}

#[derive(Debug, Deserialize)]
struct HistoricoRow {
    #[serde(rename = "ID")]
    _id: String,
    #[serde(rename = "Data")]
    data: String,
    #[serde(rename = "Ano")]
    ano: String,
    #[serde(rename = "Rodada")]
    rodada: String,
    #[serde(rename = "Equipe_mandante")]
    equipe_mandante: String,
    #[serde(rename = "Equipe_visitante")]
    equipe_visitante: String,
    #[serde(rename = "Gols_mandante")]
    gols_mandante: String,
    #[serde(rename = "Gols_visitante")]
    gols_visitante: String,
    #[serde(rename = "Mandante_UF")]
    _mandante_uf: String,
    #[serde(rename = "Visitante_UF")]
    _visitante_uf: String,
    #[serde(rename = "Vencedor")]
    _vencedor: String,
    #[serde(rename = "Arena")]
    arena: String,
    #[serde(rename = "OBS")]
    _obs: String,
}

// FIFA has a BOM and a leading unnamed column; we pick only what we need.
// This struct is kept for documentation but actual loading uses flexible StringRecord approach.
#[allow(dead_code)]
#[derive(Debug, Deserialize)]
struct FifaRow {
    // The BOM + empty first column means serde-csv gives us a field named ""
    // (or "\u{feff}") – we skip it with a rename that may or may not match.
    // Instead we use flexible field access by deserializing into a map.
    #[serde(rename = "ID")]
    id: String,
    #[serde(rename = "Name")]
    name: String,
    #[serde(rename = "Age")]
    age: String,
    #[serde(rename = "Nationality")]
    nationality: String,
    #[serde(rename = "Overall")]
    overall: String,
    #[serde(rename = "Potential")]
    potential: String,
    #[serde(rename = "Club")]
    club: String,
    #[serde(rename = "Position")]
    position: String,
    #[serde(rename = "Value")]
    value: String,
    #[serde(rename = "Wage")]
    wage: String,
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

fn parse_int(s: &str) -> i32 {
    let s = s.trim();
    // handle floats like "1.0"
    if let Ok(f) = s.parse::<f64>() {
        return f as i32;
    }
    s.parse::<i32>().unwrap_or(0)
}

/// Convert Brazilian date DD/MM/YYYY to YYYY-MM-DD for consistent sorting.
pub fn normalize_date(s: &str) -> String {
    let s = s.trim();
    // DD/MM/YYYY
    if s.len() == 10 && s.chars().nth(2) == Some('/') {
        let parts: Vec<&str> = s.splitn(3, '/').collect();
        if parts.len() == 3 {
            return format!("{}-{}-{}", parts[2], parts[1], parts[0]);
        }
    }
    // "2012-05-19 18:30:00" -> take only date part
    if s.len() > 10 && s.chars().nth(4) == Some('-') {
        return s[..10].to_string();
    }
    s.to_string()
}

/// Strip trailing state code suffix like "-SP", "-RJ", etc.
pub fn normalize_team_name(name: &str) -> String {
    let name = name.trim();
    // Collect chars to allow safe suffix inspection
    let chars: Vec<char> = name.chars().collect();
    let n = chars.len();

    // Pattern 1: ends with "-XX" where XX = 2 uppercase ASCII letters
    // e.g. "Palmeiras-SP"
    if n >= 4
        && chars[n - 3] == '-'
        && chars[n - 2].is_ascii_uppercase()
        && chars[n - 1].is_ascii_uppercase()
    {
        let prefix: String = chars[..n - 3].iter().collect();
        return prefix.trim().to_string();
    }

    // Pattern 2: ends with " - XX" (with spaces) e.g. "América - MG"
    if n >= 6
        && chars[n - 5] == ' '
        && chars[n - 4] == '-'
        && chars[n - 3] == ' '
        && chars[n - 2].is_ascii_uppercase()
        && chars[n - 1].is_ascii_uppercase()
    {
        let prefix: String = chars[..n - 5].iter().collect();
        return prefix.trim().to_string();
    }

    name.to_string()
}

/// Case-insensitive substring match after normalization.
pub fn team_matches(stored: &str, query: &str) -> bool {
    if query.is_empty() {
        return true;
    }
    let norm_stored = normalize_team_name(stored).to_lowercase();
    let norm_query = normalize_team_name(query).to_lowercase();
    norm_stored.contains(&norm_query) || norm_query.contains(&norm_stored)
}

// ---------------------------------------------------------------------------
// Loading
// ---------------------------------------------------------------------------

impl DataStore {
    pub fn load(data_dir: &str) -> Result<Self> {
        let base = Path::new(data_dir);
        let mut matches: Vec<Match> = Vec::new();
        let mut players: Vec<Player> = Vec::new();

        // 1. Brasileirao
        let path = base.join("Brasileirao_Matches.csv");
        if path.exists() {
            let mut rdr = csv::Reader::from_path(&path)
                .with_context(|| format!("opening {}", path.display()))?;
            for result in rdr.deserialize::<BrasileiraoRow>() {
                match result {
                    Ok(row) => {
                        matches.push(Match {
                            date: normalize_date(&row.datetime),
                            home_team: row.home_team,
                            away_team: row.away_team,
                            home_goal: parse_int(&row.home_goal),
                            away_goal: parse_int(&row.away_goal),
                            competition: Competition::Brasileirao,
                            season: parse_int(&row.season),
                            round: row.round,
                            extra: String::new(),
                        });
                    }
                    Err(e) => {
                        eprintln!("WARN: skipping brasileirao row: {}", e);
                    }
                }
            }
            eprintln!("INFO: loaded {} brasileirao matches", matches.len());
        } else {
            eprintln!("WARN: not found: {}", path.display());
        }

        // 2. Copa do Brasil
        let prev_len = matches.len();
        let path = base.join("Brazilian_Cup_Matches.csv");
        if path.exists() {
            let mut rdr = csv::Reader::from_path(&path)
                .with_context(|| format!("opening {}", path.display()))?;
            for result in rdr.deserialize::<CupRow>() {
                match result {
                    Ok(row) => {
                        matches.push(Match {
                            date: normalize_date(&row.datetime),
                            home_team: row.home_team,
                            away_team: row.away_team,
                            home_goal: parse_int(&row.home_goal),
                            away_goal: parse_int(&row.away_goal),
                            competition: Competition::CopaBrasil,
                            season: parse_int(&row.season),
                            round: row.round,
                            extra: String::new(),
                        });
                    }
                    Err(e) => {
                        eprintln!("WARN: skipping cup row: {}", e);
                    }
                }
            }
            eprintln!("INFO: loaded {} copa brasil matches", matches.len() - prev_len);
        }

        // 3. Libertadores
        let prev_len = matches.len();
        let path = base.join("Libertadores_Matches.csv");
        if path.exists() {
            let mut rdr = csv::Reader::from_path(&path)
                .with_context(|| format!("opening {}", path.display()))?;
            for result in rdr.deserialize::<LibertadoresRow>() {
                match result {
                    Ok(row) => {
                        matches.push(Match {
                            date: normalize_date(&row.datetime),
                            home_team: row.home_team,
                            away_team: row.away_team,
                            home_goal: parse_int(&row.home_goal),
                            away_goal: parse_int(&row.away_goal),
                            competition: Competition::Libertadores,
                            season: parse_int(&row.season),
                            round: String::new(),
                            extra: row.stage,
                        });
                    }
                    Err(e) => {
                        eprintln!("WARN: skipping libertadores row: {}", e);
                    }
                }
            }
            eprintln!("INFO: loaded {} libertadores matches", matches.len() - prev_len);
        }

        // 4. BR-Football-Dataset
        let prev_len = matches.len();
        let path = base.join("BR-Football-Dataset.csv");
        if path.exists() {
            let mut rdr = csv::Reader::from_path(&path)
                .with_context(|| format!("opening {}", path.display()))?;
            for result in rdr.deserialize::<BrFootballRow>() {
                match result {
                    Ok(row) => {
                        // Parse year from date field (format "2023-09-24" or similar)
                        let year = normalize_date(&row.date)
                            .splitn(2, '-')
                            .next()
                            .and_then(|y| y.parse::<i32>().ok())
                            .unwrap_or(0);
                        matches.push(Match {
                            date: normalize_date(&row.date),
                            home_team: row.home,
                            away_team: row.away,
                            home_goal: parse_int(&row.home_goal),
                            away_goal: parse_int(&row.away_goal),
                            competition: Competition::BrFootball,
                            season: year,
                            round: String::new(),
                            extra: row.tournament,
                        });
                    }
                    Err(e) => {
                        eprintln!("WARN: skipping br-football row: {}", e);
                    }
                }
            }
            eprintln!("INFO: loaded {} br-football matches", matches.len() - prev_len);
        }

        // 5. Historico
        let prev_len = matches.len();
        let path = base.join("novo_campeonato_brasileiro.csv");
        if path.exists() {
            let mut rdr = csv::Reader::from_path(&path)
                .with_context(|| format!("opening {}", path.display()))?;
            for result in rdr.deserialize::<HistoricoRow>() {
                match result {
                    Ok(row) => {
                        matches.push(Match {
                            date: normalize_date(&row.data),
                            home_team: row.equipe_mandante,
                            away_team: row.equipe_visitante,
                            home_goal: parse_int(&row.gols_mandante),
                            away_goal: parse_int(&row.gols_visitante),
                            competition: Competition::Historico,
                            season: parse_int(&row.ano),
                            round: row.rodada,
                            extra: row.arena,
                        });
                    }
                    Err(e) => {
                        eprintln!("WARN: skipping historico row: {}", e);
                    }
                }
            }
            eprintln!("INFO: loaded {} historico matches", matches.len() - prev_len);
        }

        eprintln!("INFO: total matches loaded: {}", matches.len());

        // 6. FIFA players
        let path = base.join("fifa_data.csv");
        if path.exists() {
            // The file has a UTF-8 BOM and an extra empty column at the start.
            // Use flexible deserialization via StringRecord to handle this.
            let file = std::fs::File::open(&path)
                .with_context(|| format!("opening {}", path.display()))?;
            // Strip BOM if present
            let reader = bom_strip_reader(file);
            let mut rdr = csv::ReaderBuilder::new()
                .flexible(true)
                .from_reader(reader);
            let headers = rdr.headers()
                .with_context(|| "reading fifa headers")?
                .clone();
            // Find column indices
            let idx_id = col_idx(&headers, &["ID", "id"]);
            let idx_name = col_idx(&headers, &["Name", "name"]);
            let idx_age = col_idx(&headers, &["Age", "age"]);
            let idx_nat = col_idx(&headers, &["Nationality", "nationality"]);
            let idx_overall = col_idx(&headers, &["Overall", "overall"]);
            let idx_potential = col_idx(&headers, &["Potential", "potential"]);
            let idx_club = col_idx(&headers, &["Club", "club"]);
            let idx_position = col_idx(&headers, &["Position", "position"]);
            let idx_value = col_idx(&headers, &["Value", "value"]);
            let idx_wage = col_idx(&headers, &["Wage", "wage"]);

            for result in rdr.records() {
                match result {
                    Ok(rec) => {
                        let get = |idx: Option<usize>| -> String {
                            idx.and_then(|i| rec.get(i))
                                .unwrap_or("")
                                .trim()
                                .to_string()
                        };
                        let name = get(idx_name);
                        if name.is_empty() {
                            continue;
                        }
                        players.push(Player {
                            id: get(idx_id),
                            name,
                            age: parse_int(&get(idx_age)),
                            nationality: get(idx_nat),
                            overall: parse_int(&get(idx_overall)),
                            potential: parse_int(&get(idx_potential)),
                            club: get(idx_club),
                            position: get(idx_position),
                            value: get(idx_value),
                            wage: get(idx_wage),
                        });
                    }
                    Err(e) => {
                        eprintln!("WARN: skipping fifa row: {}", e);
                    }
                }
            }
            eprintln!("INFO: loaded {} fifa players", players.len());
        }

        Ok(DataStore { matches, players })
    }
}

fn col_idx(headers: &csv::StringRecord, names: &[&str]) -> Option<usize> {
    for name in names {
        if let Some(pos) = headers.iter().position(|h| h.trim() == *name) {
            return Some(pos);
        }
    }
    None
}

/// Wrap a file reader and strip leading UTF-8 BOM bytes if present.
fn bom_strip_reader(f: std::fs::File) -> impl std::io::Read {
    use std::io::Read;
    struct BomReader<R: Read> {
        inner: R,
        checked: bool,
        leftover: Vec<u8>,
    }
    impl<R: Read> Read for BomReader<R> {
        fn read(&mut self, buf: &mut [u8]) -> std::io::Result<usize> {
            if !self.checked {
                self.checked = true;
                let mut bom = [0u8; 3];
                let n = self.inner.read(&mut bom)?;
                let start = if n >= 3 && bom[..3] == [0xEF, 0xBB, 0xBF] {
                    3
                } else {
                    0
                };
                self.leftover.extend_from_slice(&bom[start..n]);
            }
            if !self.leftover.is_empty() {
                let to_copy = self.leftover.len().min(buf.len());
                buf[..to_copy].copy_from_slice(&self.leftover[..to_copy]);
                self.leftover.drain(..to_copy);
                return Ok(to_copy);
            }
            self.inner.read(buf)
        }
    }
    BomReader {
        inner: f,
        checked: false,
        leftover: Vec::new(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_normalize_team_name_with_state_suffix() {
        assert_eq!(normalize_team_name("Palmeiras-SP"), "Palmeiras");
        assert_eq!(normalize_team_name("Flamengo-RJ"), "Flamengo");
        assert_eq!(normalize_team_name("Sport-PE"), "Sport");
        assert_eq!(normalize_team_name("Grêmio"), "Grêmio");
        assert_eq!(normalize_team_name("América - MG"), "América");
        assert_eq!(normalize_team_name("Vasco"), "Vasco");
    }

    #[test]
    fn test_normalize_date() {
        assert_eq!(normalize_date("29/03/2003"), "2003-03-29");
        assert_eq!(normalize_date("2012-05-19 18:30:00"), "2012-05-19");
        assert_eq!(normalize_date("2023-09-24"), "2023-09-24");
    }

    #[test]
    fn test_team_matches() {
        assert!(team_matches("Palmeiras-SP", "Palmeiras"));
        assert!(team_matches("Flamengo-RJ", "flamengo"));
        assert!(team_matches("Flamengo", "Fla"));
        assert!(!team_matches("Palmeiras-SP", "Flamengo"));
    }
}
