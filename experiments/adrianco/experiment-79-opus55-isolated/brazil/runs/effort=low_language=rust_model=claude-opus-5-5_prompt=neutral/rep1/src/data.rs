//! In-memory database built from the six Kaggle CSV files.

use crate::normalize::{canonical, fold, parse_date};
use std::collections::{BTreeMap, HashMap, HashSet};
use std::path::{Path, PathBuf};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum Competition {
    SerieA,
    SerieB,
    SerieC,
    CopaDoBrasil,
    Libertadores,
}

impl Competition {
    pub const ALL: [Competition; 5] = [
        Competition::SerieA,
        Competition::SerieB,
        Competition::SerieC,
        Competition::CopaDoBrasil,
        Competition::Libertadores,
    ];

    pub fn name(self) -> &'static str {
        match self {
            Competition::SerieA => "Brasileirão Série A",
            Competition::SerieB => "Brasileirão Série B",
            Competition::SerieC => "Brasileirão Série C",
            Competition::CopaDoBrasil => "Copa do Brasil",
            Competition::Libertadores => "Copa Libertadores",
        }
    }

    pub fn is_league(self) -> bool {
        matches!(self, Competition::SerieA | Competition::SerieB | Competition::SerieC)
    }

    /// Parse a user supplied competition name ("Brasileirão", "serie a", "cup", ...).
    pub fn parse(s: &str) -> Result<Competition, String> {
        let f = fold(s);
        if f.contains("libertadores") {
            Ok(Competition::Libertadores)
        } else if f.contains("copa") || f.contains("cup") {
            Ok(Competition::CopaDoBrasil)
        } else if f.contains("serie b") {
            Ok(Competition::SerieB)
        } else if f.contains("serie c") {
            Ok(Competition::SerieC)
        } else if f.contains("serie a") || f.contains("brasileir") || f.contains("campeonato") {
            Ok(Competition::SerieA)
        } else {
            Err(format!(
                "Unknown competition '{s}'. Use one of: Brasileirão (Serie A), Serie B, Serie C, Copa do Brasil, Libertadores."
            ))
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum Source {
    Brasileirao,
    Cup,
    Libertadores,
    BrFootball,
    Novo,
}

impl Source {
    pub const ALL: [Source; 5] =
        [Source::Brasileirao, Source::Cup, Source::Libertadores, Source::BrFootball, Source::Novo];

    pub fn file(self) -> &'static str {
        match self {
            Source::Brasileirao => "Brasileirao_Matches.csv",
            Source::Cup => "Brazilian_Cup_Matches.csv",
            Source::Libertadores => "Libertadores_Matches.csv",
            Source::BrFootball => "BR-Football-Dataset.csv",
            Source::Novo => "novo_campeonato_brasileiro.csv",
        }
    }

    pub fn parse(s: &str) -> Result<Source, String> {
        let f = fold(s).replace(' ', "");
        Source::ALL
            .into_iter()
            .find(|src| {
                let file = fold(src.file()).replace(' ', "");
                file == f || file.trim_end_matches("csv") == f
            })
            .or_else(|| match f.as_str() {
                "brasileirao" => Some(Source::Brasileirao),
                "cup" | "copadobrasil" => Some(Source::Cup),
                "libertadores" => Some(Source::Libertadores),
                "brfootball" | "extended" => Some(Source::BrFootball),
                "novo" | "historical" => Some(Source::Novo),
                _ => None,
            })
            .ok_or_else(|| {
                format!("Unknown source '{s}'. Use: brasileirao, cup, libertadores, br-football, novo (or the CSV file name).")
            })
    }
}

/// Extended statistics, only present in BR-Football-Dataset.csv.
#[derive(Debug, Clone, Default)]
pub struct Extra {
    pub home_corner: Option<u32>,
    pub away_corner: Option<u32>,
    pub home_shots: Option<u32>,
    pub away_shots: Option<u32>,
    pub home_attack: Option<u32>,
    pub away_attack: Option<u32>,
}

#[derive(Debug, Clone)]
pub struct Match {
    /// ISO date, when known.
    pub date: Option<String>,
    pub season: u16,
    pub competition: Competition,
    pub source: Source,
    pub round: Option<String>,
    pub stage: Option<String>,
    pub home: String,
    pub away: String,
    pub home_key: String,
    pub away_key: String,
    /// `None` for fixtures without a recorded score.
    pub home_goal: Option<u32>,
    pub away_goal: Option<u32>,
    pub arena: Option<String>,
    pub extra: Option<Extra>,
    /// Several files cover the same competition/season. Exactly one source per
    /// (competition, season) is primary so statistics never double count.
    pub primary: bool,
}

impl Match {
    pub fn score(&self) -> Option<(u32, u32)> {
        Some((self.home_goal?, self.away_goal?))
    }
}

#[derive(Debug, Clone)]
pub struct Player {
    pub id: String,
    pub name: String,
    pub age: Option<u32>,
    pub nationality: String,
    pub overall: u32,
    pub potential: u32,
    pub club: String,
    pub club_key: String,
    pub position: String,
    pub jersey: String,
    pub height: String,
    pub weight: String,
    pub value: String,
    pub wage: String,
    pub foot: String,
    pub skills: Vec<(&'static str, u32)>,
}

const SKILLS: &[&str] = &[
    "Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Dribbling", "BallControl",
    "Acceleration", "SprintSpeed", "Stamina", "Strength", "ShotPower", "LongShots", "Vision",
    "Interceptions", "StandingTackle",
];

pub struct Database {
    pub matches: Vec<Match>,
    pub players: Vec<Player>,
    /// team key -> display name, for every team appearing in match data.
    pub teams: BTreeMap<String, String>,
    /// stateless spelling -> key of the single state-qualified team it refers to.
    pub remap: HashMap<String, String>,
    /// rows loaded per CSV file.
    pub file_rows: Vec<(&'static str, usize)>,
}

struct Table {
    cols: HashMap<String, usize>,
    rows: Vec<csv::StringRecord>,
}

impl Table {
    fn read(dir: &Path, file: &str) -> Result<Table, String> {
        let path = dir.join(file);
        let mut rdr = csv::ReaderBuilder::new()
            .flexible(true)
            .from_path(&path)
            .map_err(|e| format!("cannot open {}: {e}", path.display()))?;
        let cols = rdr
            .headers()
            .map_err(|e| format!("{file}: {e}"))?
            .iter()
            .enumerate()
            .map(|(i, h)| (h.trim_start_matches('\u{feff}').trim().to_string(), i))
            .collect();
        let rows = rdr.records().collect::<Result<Vec<_>, _>>().map_err(|e| format!("{file}: {e}"))?;
        Ok(Table { cols, rows })
    }

    fn get<'a>(&self, row: &'a csv::StringRecord, col: &str) -> &'a str {
        self.cols.get(col).and_then(|i| row.get(*i)).map(str::trim).unwrap_or("")
    }
}

fn num(s: &str) -> Option<u32> {
    s.trim().parse::<f64>().ok().filter(|v| *v >= 0.0).map(|v| v as u32)
}

fn opt(s: &str) -> Option<String> {
    (!s.is_empty() && s != "NA").then(|| s.to_string())
}

/// Locate the data directory: explicit argument, `BR_SOCCER_DATA_DIR`,
/// `./data/kaggle`, then the crate's own `data/kaggle`.
pub fn find_data_dir(explicit: Option<&str>) -> Result<PathBuf, String> {
    let mut candidates: Vec<PathBuf> = Vec::new();
    if let Some(p) = explicit {
        candidates.push(p.into());
    } else {
        if let Ok(p) = std::env::var("BR_SOCCER_DATA_DIR") {
            candidates.push(p.into());
        }
        candidates.push("data/kaggle".into());
        candidates.push(Path::new(env!("CARGO_MANIFEST_DIR")).join("data/kaggle"));
    }
    candidates
        .iter()
        .find(|p| p.join("fifa_data.csv").is_file())
        .cloned()
        .ok_or_else(|| format!("data directory not found (tried {candidates:?})"))
}

impl Database {
    pub fn load(dir: &Path) -> Result<Database, String> {
        let mut matches: Vec<Match> = Vec::new();
        let mut file_rows = Vec::new();
        let mut stateless: HashSet<String> = HashSet::new();

        let mut push = |matches: &mut Vec<Match>,
                        source: Source,
                        competition: Competition,
                        date: Option<String>,
                        season: Option<u16>,
                        home: &str,
                        away: &str,
                        hg: &str,
                        ag: &str|
         -> bool {
            let season = match season.or_else(|| date.as_ref().and_then(|d| d[..4].parse().ok())) {
                Some(s) => s,
                None => return false,
            };
            if home.is_empty() || away.is_empty() {
                return false;
            }
            let (h, a) = (canonical(home), canonical(away));
            for t in [&h, &a] {
                if t.stateless {
                    stateless.insert(t.key.clone());
                }
            }
            let (home_goal, away_goal) = match (num(hg), num(ag)) {
                (Some(x), Some(y)) => (Some(x), Some(y)),
                _ => (None, None),
            };
            matches.push(Match {
                date,
                season,
                competition,
                source,
                round: None,
                stage: None,
                home: h.display,
                away: a.display,
                home_key: h.key,
                away_key: a.key,
                home_goal,
                away_goal,
                arena: None,
                extra: None,
                primary: false,
            });
            true
        };

        let t = Table::read(dir, Source::Brasileirao.file())?;
        file_rows.push((Source::Brasileirao.file(), t.rows.len()));
        for r in &t.rows {
            let g = |c| t.get(r, c);
            if push(&mut matches, Source::Brasileirao, Competition::SerieA, parse_date(g("datetime")),
                g("season").parse().ok(), g("home_team"), g("away_team"), g("home_goal"), g("away_goal"))
            {
                matches.last_mut().unwrap().round = opt(g("round"));
            }
        }

        let t = Table::read(dir, Source::Cup.file())?;
        file_rows.push((Source::Cup.file(), t.rows.len()));
        for r in &t.rows {
            let g = |c| t.get(r, c);
            if push(&mut matches, Source::Cup, Competition::CopaDoBrasil, parse_date(g("datetime")),
                g("season").parse().ok(), g("home_team"), g("away_team"), g("home_goal"), g("away_goal"))
            {
                matches.last_mut().unwrap().round = opt(g("round"));
            }
        }

        let t = Table::read(dir, Source::Libertadores.file())?;
        file_rows.push((Source::Libertadores.file(), t.rows.len()));
        for r in &t.rows {
            let g = |c| t.get(r, c);
            if push(&mut matches, Source::Libertadores, Competition::Libertadores, parse_date(g("datetime")),
                g("season").parse().ok(), g("home_team"), g("away_team"), g("home_goal"), g("away_goal"))
            {
                matches.last_mut().unwrap().stage = opt(g("stage"));
            }
        }

        let t = Table::read(dir, Source::BrFootball.file())?;
        file_rows.push((Source::BrFootball.file(), t.rows.len()));
        for r in &t.rows {
            let g = |c| t.get(r, c);
            let Ok(comp) = Competition::parse(g("tournament")) else { continue };
            // This file has no season column; the calendar year of the match is used.
            if push(&mut matches, Source::BrFootball, comp, parse_date(g("date")), None,
                g("home"), g("away"), g("home_goal"), g("away_goal"))
            {
                matches.last_mut().unwrap().extra = Some(Extra {
                    home_corner: num(g("home_corner")),
                    away_corner: num(g("away_corner")),
                    home_shots: num(g("home_shots")),
                    away_shots: num(g("away_shots")),
                    home_attack: num(g("home_attack")),
                    away_attack: num(g("away_attack")),
                });
            }
        }

        let t = Table::read(dir, Source::Novo.file())?;
        file_rows.push((Source::Novo.file(), t.rows.len()));
        for r in &t.rows {
            let g = |c| t.get(r, c);
            if push(&mut matches, Source::Novo, Competition::SerieA, parse_date(g("Data")),
                g("Ano").parse().ok(), g("Equipe_mandante"), g("Equipe_visitante"),
                g("Gols_mandante"), g("Gols_visitante"))
            {
                let m = matches.last_mut().unwrap();
                m.round = opt(g("Rodada"));
                m.arena = opt(g("Arena"));
            }
        }

        // Merge "Tupi" with "Tupi MG" when only one state-qualified team shares the base name.
        let all_keys: HashSet<String> =
            matches.iter().flat_map(|m| [m.home_key.clone(), m.away_key.clone()]).collect();
        let mut remap: HashMap<String, String> = HashMap::new();
        for base in &stateless {
            let prefix = format!("{base} ");
            let mut cands = all_keys.iter().filter(|k| {
                k.strip_prefix(&prefix).map_or(false, |rest| rest.len() <= 3 && !rest.contains(' '))
            });
            if let (Some(only), None) = (cands.next(), cands.next()) {
                remap.insert(base.clone(), only.clone());
            }
        }
        let mut teams: BTreeMap<String, String> = BTreeMap::new();
        for m in &matches {
            for (k, d) in [(&m.home_key, &m.home), (&m.away_key, &m.away)] {
                if !remap.contains_key(k) {
                    teams.entry(k.clone()).or_insert_with(|| d.clone());
                }
            }
        }
        for m in &mut matches {
            if let Some(k) = remap.get(&m.home_key) {
                m.home = teams[k].clone();
                m.home_key = k.clone();
            }
            if let Some(k) = remap.get(&m.away_key) {
                m.away = teams[k].clone();
                m.away_key = k.clone();
            }
        }

        // Pick one primary source per (competition, season): for leagues the
        // preferred file holding a complete double round-robin, otherwise the
        // file with the most scored matches (ties go to the preferred file).
        let priority = |s: Source| match s {
            Source::Novo | Source::Cup | Source::Libertadores => 0,
            Source::Brasileirao => 1,
            Source::BrFootball => 2,
        };
        let mut played: HashMap<(Competition, u16, Source), HashMap<&str, u32>> = HashMap::new();
        for m in &matches {
            let per_team = played.entry((m.competition, m.season, m.source)).or_default();
            if m.score().is_some() {
                *per_team.entry(&m.home_key).or_default() += 1;
                *per_team.entry(&m.away_key).or_default() += 1;
            }
        }
        let mut best: HashMap<(Competition, u16), (Source, (bool, u32, i32))> = HashMap::new();
        for ((comp, season, source), per_team) in &played {
            let n = per_team.len() as u32;
            let complete = comp.is_league() && n > 1 && per_team.values().all(|p| *p == 2 * (n - 1));
            let scored = per_team.values().sum::<u32>() / 2;
            let rank = if complete { (true, 0, -priority(*source)) } else { (false, scored, -priority(*source)) };
            let e = best.entry((*comp, *season)).or_insert((*source, rank));
            if rank > e.1 {
                *e = (*source, rank);
            }
        }
        let best: HashMap<(Competition, u16), Source> = best.into_iter().map(|(k, v)| (k, v.0)).collect();
        for m in &mut matches {
            m.primary = best[&(m.competition, m.season)] == m.source;
        }

        // Copa do Brasil: the last round of a season with at most two legs is the final.
        let mut last_round: HashMap<u16, (u32, usize)> = HashMap::new();
        for m in matches.iter().filter(|m| m.source == Source::Cup) {
            if let Some(r) = m.round.as_deref().and_then(|r| r.parse::<u32>().ok()) {
                let e = last_round.entry(m.season).or_insert((r, 0));
                if r > e.0 {
                    *e = (r, 1);
                } else if r == e.0 {
                    e.1 += 1;
                }
            }
        }
        for m in matches.iter_mut().filter(|m| m.source == Source::Cup) {
            let r = m.round.as_deref().and_then(|r| r.parse::<u32>().ok());
            if let (Some(r), Some((max, n))) = (r, last_round.get(&m.season)) {
                if r == *max && *n <= 2 {
                    m.stage = Some("final".to_string());
                }
            }
        }

        let t = Table::read(dir, "fifa_data.csv")?;
        file_rows.push(("fifa_data.csv", t.rows.len()));
        let players = t
            .rows
            .iter()
            .filter(|r| !t.get(r, "Name").is_empty())
            .map(|r| {
                let g = |c| t.get(r, c);
                let club = g("Club").to_string();
                Player {
                    id: g("ID").to_string(),
                    name: g("Name").to_string(),
                    age: num(g("Age")),
                    nationality: g("Nationality").to_string(),
                    overall: num(g("Overall")).unwrap_or(0),
                    potential: num(g("Potential")).unwrap_or(0),
                    club_key: if club.is_empty() { String::new() } else { canonical(&club).key },
                    club,
                    position: g("Position").to_string(),
                    jersey: g("Jersey Number").to_string(),
                    height: g("Height").to_string(),
                    weight: g("Weight").to_string(),
                    value: g("Value").to_string(),
                    wage: g("Wage").to_string(),
                    foot: g("Preferred Foot").to_string(),
                    skills: SKILLS.iter().filter_map(|s| Some((*s, num(g(s))?))).collect(),
                }
            })
            .collect();

        Ok(Database { matches, players, teams, remap, file_rows })
    }
}
