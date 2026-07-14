// ============================================================================
// CONTEXT: Brazilian Soccer MCP Server - data loading layer
//
// Purpose:  Loads the six Kaggle CSV files from data/kaggle/ into two unified
//           in-memory models:
//             Match  - one row per match, from 5 match datasets
//             Player - one row per player, from the FIFA player database
//
// Sources (and their quirks handled here):
//   Brasileirao_Matches.csv        Serie A 2012-2022, names like "Palmeiras-SP"
//   Brazilian_Cup_Matches.csv      Copa do Brasil, names like "América - MG"
//   Libertadores_Matches.csv       goals quoted as strings, "(URU)" suffixes
//   BR-Football-Dataset.csv        floats for goals, no season column (derived
//                                  from date), extra stats (corners/shots)
//   novo_campeonato_brasileiro.csv Serie A 2003-2019, DD/MM/YYYY dates, arena
//   fifa_data.csv                  UTF-8 BOM, 80+ columns, accessed by header
//
// Overlap:  Serie A 2012-2019 appears in three files; queries.rs deduplicates
//           by (date, home, away) using the Source priority defined here.
// ============================================================================

use crate::normalize::{canonical_team, parse_date, COPA_DO_BRASIL, LIBERTADORES, SERIE_A, SERIE_B, SERIE_C};
use std::collections::HashMap;
use std::path::Path;

/// Which CSV a match came from. Order doubles as deduplication priority
/// (lower = preferred when the same fixture appears in several files).
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum Source {
    Brasileirao,
    NovoCampeonato,
    BrazilianCup,
    Libertadores,
    BrFootball,
}

impl Source {
    pub fn label(&self) -> &'static str {
        match self {
            Source::Brasileirao => "Brasileirao_Matches.csv",
            Source::NovoCampeonato => "novo_campeonato_brasileiro.csv",
            Source::BrazilianCup => "Brazilian_Cup_Matches.csv",
            Source::Libertadores => "Libertadores_Matches.csv",
            Source::BrFootball => "BR-Football-Dataset.csv",
        }
    }
}

#[derive(Debug, Clone, Default)]
pub struct MatchExtra {
    pub home_corners: Option<i32>,
    pub away_corners: Option<i32>,
    pub home_shots: Option<i32>,
    pub away_shots: Option<i32>,
    pub home_attacks: Option<i32>,
    pub away_attacks: Option<i32>,
    pub stadium: Option<String>,
}

#[derive(Debug, Clone)]
pub struct Match {
    pub source: Source,
    pub competition: String,
    /// ISO date "YYYY-MM-DD" (empty string when the row had no parseable date)
    pub date: String,
    pub season: i32,
    /// Round number or tournament stage, as text
    pub round: String,
    pub home_raw: String,
    pub away_raw: String,
    /// canonical team keys (see normalize::canonical_team)
    pub home: String,
    pub away: String,
    pub home_goals: i32,
    pub away_goals: i32,
    pub extra: MatchExtra,
}

impl Match {
    pub fn involves(&self, canonical_query: &str) -> bool {
        crate::normalize::team_matches(&self.home, canonical_query)
            || crate::normalize::team_matches(&self.away, canonical_query)
    }
    /// Key identifying the same real-world fixture across source files.
    /// League formats are a double round-robin, so an ordered home/away pair
    /// occurs exactly once per season - keying on the season absorbs the
    /// small date disagreements between datasets. Cup fixtures can repeat
    /// (two-legged ties), so there the date stays in the key.
    pub fn dedup_key(&self) -> (String, String, String) {
        let scope = if self.competition.starts_with("Brasileir") {
            format!("{}|{}", self.competition, self.season)
        } else {
            format!("{}|{}", self.competition, self.date)
        };
        (scope, self.home.clone(), self.away.clone())
    }
}

#[derive(Debug, Clone)]
pub struct Player {
    pub name: String,
    pub canonical_name: String,
    pub age: Option<i32>,
    pub nationality: String,
    pub overall: i32,
    pub potential: Option<i32>,
    pub club: String,
    pub canonical_club: String,
    pub position: String,
    pub jersey_number: Option<i32>,
    pub height: String,
    pub weight: String,
    pub value: String,
    pub wage: String,
    pub preferred_foot: String,
    /// Selected skill ratings (Crossing, Finishing, Dribbling, ...)
    pub skills: Vec<(String, i32)>,
}

#[derive(Debug, Default)]
pub struct Dataset {
    pub matches: Vec<Match>,
    pub players: Vec<Player>,
    /// per-file row counts actually loaded, for diagnostics
    pub file_counts: HashMap<&'static str, usize>,
}

fn parse_goals(s: &str) -> Option<i32> {
    let t = s.trim().trim_matches('"');
    if t.is_empty() {
        return None;
    }
    t.parse::<f64>().ok().map(|v| v.round() as i32)
}

fn parse_int(s: &str) -> Option<i32> {
    parse_goals(s)
}

/// Build a header-name -> column-index map, stripping the UTF-8 BOM that
/// fifa_data.csv carries on its first header cell.
fn header_index(headers: &csv::StringRecord) -> HashMap<String, usize> {
    headers
        .iter()
        .enumerate()
        .map(|(i, h)| (h.trim_start_matches('\u{feff}').trim().to_string(), i))
        .collect()
}

fn open(path: &Path) -> Result<csv::Reader<std::fs::File>, String> {
    csv::ReaderBuilder::new()
        .flexible(true)
        .from_path(path)
        .map_err(|e| format!("cannot open {}: {}", path.display(), e))
}

impl Dataset {
    /// Load every CSV in `dir`. Fails if any of the six files is missing.
    pub fn load(dir: &Path) -> Result<Dataset, String> {
        let mut ds = Dataset::default();
        ds.load_brasileirao(&dir.join("Brasileirao_Matches.csv"))?;
        ds.load_novo(&dir.join("novo_campeonato_brasileiro.csv"))?;
        ds.load_cup(&dir.join("Brazilian_Cup_Matches.csv"))?;
        ds.load_libertadores(&dir.join("Libertadores_Matches.csv"))?;
        ds.load_br_football(&dir.join("BR-Football-Dataset.csv"))?;
        ds.load_fifa(&dir.join("fifa_data.csv"))?;
        Ok(ds)
    }

    fn push_match(&mut self, m: Match) {
        self.matches.push(m);
    }

    fn load_brasileirao(&mut self, path: &Path) -> Result<(), String> {
        let mut rdr = open(path)?;
        let idx = header_index(rdr.headers().map_err(|e| e.to_string())?);
        let g = |r: &csv::StringRecord, k: &str| idx.get(k).and_then(|&c| r.get(c)).unwrap_or("").to_string();
        let mut count = 0usize;
        for rec in rdr.records().flatten() {
            let home_raw = g(&rec, "home_team");
            let away_raw = g(&rec, "away_team");
            let (Some(hg), Some(ag)) = (parse_goals(&g(&rec, "home_goal")), parse_goals(&g(&rec, "away_goal"))) else {
                continue;
            };
            let date = parse_date(&g(&rec, "datetime")).unwrap_or_default();
            let season = g(&rec, "season").trim().parse().unwrap_or(0);
            self.push_match(Match {
                source: Source::Brasileirao,
                competition: SERIE_A.to_string(),
                date,
                season,
                round: g(&rec, "round"),
                home: canonical_team(&home_raw),
                away: canonical_team(&away_raw),
                home_raw,
                away_raw,
                home_goals: hg,
                away_goals: ag,
                extra: MatchExtra::default(),
            });
            count += 1;
        }
        self.file_counts.insert("Brasileirao_Matches.csv", count);
        Ok(())
    }

    fn load_novo(&mut self, path: &Path) -> Result<(), String> {
        let mut rdr = open(path)?;
        let idx = header_index(rdr.headers().map_err(|e| e.to_string())?);
        let g = |r: &csv::StringRecord, k: &str| idx.get(k).and_then(|&c| r.get(c)).unwrap_or("").to_string();
        let mut count = 0usize;
        for rec in rdr.records().flatten() {
            let home_raw = g(&rec, "Equipe_mandante");
            let away_raw = g(&rec, "Equipe_visitante");
            let (Some(hg), Some(ag)) = (parse_goals(&g(&rec, "Gols_mandante")), parse_goals(&g(&rec, "Gols_visitante"))) else {
                continue;
            };
            let date = parse_date(&g(&rec, "Data")).unwrap_or_default();
            let season = g(&rec, "Ano").trim().parse().unwrap_or(0);
            let stadium = g(&rec, "Arena");
            self.push_match(Match {
                source: Source::NovoCampeonato,
                competition: SERIE_A.to_string(),
                date,
                season,
                round: g(&rec, "Rodada"),
                home: canonical_team(&home_raw),
                away: canonical_team(&away_raw),
                home_raw,
                away_raw,
                home_goals: hg,
                away_goals: ag,
                extra: MatchExtra {
                    stadium: if stadium.trim().is_empty() { None } else { Some(stadium) },
                    ..MatchExtra::default()
                },
            });
            count += 1;
        }
        self.file_counts.insert("novo_campeonato_brasileiro.csv", count);
        Ok(())
    }

    fn load_cup(&mut self, path: &Path) -> Result<(), String> {
        let mut rdr = open(path)?;
        let idx = header_index(rdr.headers().map_err(|e| e.to_string())?);
        let g = |r: &csv::StringRecord, k: &str| idx.get(k).and_then(|&c| r.get(c)).unwrap_or("").to_string();
        let mut count = 0usize;
        for rec in rdr.records().flatten() {
            let home_raw = g(&rec, "home_team");
            let away_raw = g(&rec, "away_team");
            let (Some(hg), Some(ag)) = (parse_goals(&g(&rec, "home_goal")), parse_goals(&g(&rec, "away_goal"))) else {
                continue;
            };
            self.push_match(Match {
                source: Source::BrazilianCup,
                competition: COPA_DO_BRASIL.to_string(),
                date: parse_date(&g(&rec, "datetime")).unwrap_or_default(),
                season: g(&rec, "season").trim().parse().unwrap_or(0),
                round: g(&rec, "round"),
                home: canonical_team(&home_raw),
                away: canonical_team(&away_raw),
                home_raw,
                away_raw,
                home_goals: hg,
                away_goals: ag,
                extra: MatchExtra::default(),
            });
            count += 1;
        }
        self.file_counts.insert("Brazilian_Cup_Matches.csv", count);
        Ok(())
    }

    fn load_libertadores(&mut self, path: &Path) -> Result<(), String> {
        let mut rdr = open(path)?;
        let idx = header_index(rdr.headers().map_err(|e| e.to_string())?);
        let g = |r: &csv::StringRecord, k: &str| idx.get(k).and_then(|&c| r.get(c)).unwrap_or("").to_string();
        let mut count = 0usize;
        for rec in rdr.records().flatten() {
            let home_raw = g(&rec, "home_team");
            let away_raw = g(&rec, "away_team");
            let (Some(hg), Some(ag)) = (parse_goals(&g(&rec, "home_goal")), parse_goals(&g(&rec, "away_goal"))) else {
                continue;
            };
            self.push_match(Match {
                source: Source::Libertadores,
                competition: LIBERTADORES.to_string(),
                date: parse_date(&g(&rec, "datetime")).unwrap_or_default(),
                season: g(&rec, "season").trim().parse().unwrap_or(0),
                round: g(&rec, "stage"),
                home: canonical_team(&home_raw),
                away: canonical_team(&away_raw),
                home_raw,
                away_raw,
                home_goals: hg,
                away_goals: ag,
                extra: MatchExtra::default(),
            });
            count += 1;
        }
        self.file_counts.insert("Libertadores_Matches.csv", count);
        Ok(())
    }

    fn load_br_football(&mut self, path: &Path) -> Result<(), String> {
        let mut rdr = open(path)?;
        let idx = header_index(rdr.headers().map_err(|e| e.to_string())?);
        let g = |r: &csv::StringRecord, k: &str| idx.get(k).and_then(|&c| r.get(c)).unwrap_or("").to_string();
        let mut count = 0usize;
        for rec in rdr.records().flatten() {
            let home_raw = g(&rec, "home");
            let away_raw = g(&rec, "away");
            let (Some(hg), Some(ag)) = (parse_goals(&g(&rec, "home_goal")), parse_goals(&g(&rec, "away_goal"))) else {
                continue;
            };
            let date = parse_date(&g(&rec, "date")).unwrap_or_default();
            let mut season: i32 = date.get(..4).and_then(|y| y.parse().ok()).unwrap_or(0);
            let competition = match g(&rec, "tournament").trim() {
                "Serie A" => SERIE_A,
                "Serie B" => SERIE_B,
                "Serie C" => SERIE_C,
                "Copa do Brasil" => COPA_DO_BRASIL,
                _ => SERIE_A,
            };
            // The COVID-delayed 2020 league season finished in February 2021;
            // early-2021 league rounds belong to season 2020.
            if competition != COPA_DO_BRASIL && season == 2021 {
                if let Some(month) = date.get(5..7) {
                    if month < "04" {
                        season = 2020;
                    }
                }
            }
            self.push_match(Match {
                source: Source::BrFootball,
                competition: competition.to_string(),
                date,
                season,
                round: String::new(),
                home: canonical_team(&home_raw),
                away: canonical_team(&away_raw),
                home_raw,
                away_raw,
                home_goals: hg,
                away_goals: ag,
                extra: MatchExtra {
                    home_corners: parse_int(&g(&rec, "home_corner")),
                    away_corners: parse_int(&g(&rec, "away_corner")),
                    home_shots: parse_int(&g(&rec, "home_shots")),
                    away_shots: parse_int(&g(&rec, "away_shots")),
                    home_attacks: parse_int(&g(&rec, "home_attack")),
                    away_attacks: parse_int(&g(&rec, "away_attack")),
                    stadium: None,
                },
            });
            count += 1;
        }
        self.file_counts.insert("BR-Football-Dataset.csv", count);
        Ok(())
    }

    fn load_fifa(&mut self, path: &Path) -> Result<(), String> {
        let mut rdr = open(path)?;
        let idx = header_index(rdr.headers().map_err(|e| e.to_string())?);
        let g = |r: &csv::StringRecord, k: &str| idx.get(k).and_then(|&c| r.get(c)).unwrap_or("").to_string();
        const SKILL_COLS: &[&str] = &[
            "Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Dribbling",
            "BallControl", "Acceleration", "SprintSpeed", "ShotPower", "Stamina",
            "Strength", "Vision", "Penalties", "Composure", "StandingTackle",
            "GKDiving", "GKReflexes",
        ];
        let mut count = 0usize;
        for rec in rdr.records().flatten() {
            let name = g(&rec, "Name");
            if name.trim().is_empty() {
                continue;
            }
            let overall = match parse_int(&g(&rec, "Overall")) {
                Some(v) => v,
                None => continue,
            };
            let club = g(&rec, "Club");
            let skills = SKILL_COLS
                .iter()
                .filter_map(|k| parse_int(&g(&rec, k)).map(|v| (k.to_string(), v)))
                .collect();
            self.players.push(Player {
                canonical_name: crate::normalize::deaccent(&name).to_lowercase(),
                name,
                age: parse_int(&g(&rec, "Age")),
                nationality: g(&rec, "Nationality"),
                overall,
                potential: parse_int(&g(&rec, "Potential")),
                canonical_club: canonical_team(&club),
                club,
                position: g(&rec, "Position"),
                jersey_number: parse_int(&g(&rec, "Jersey Number")),
                height: g(&rec, "Height"),
                weight: g(&rec, "Weight"),
                value: g(&rec, "Value"),
                wage: g(&rec, "Wage"),
                preferred_foot: g(&rec, "Preferred Foot"),
                skills,
            });
            count += 1;
        }
        self.file_counts.insert("fifa_data.csv", count);
        Ok(())
    }
}
