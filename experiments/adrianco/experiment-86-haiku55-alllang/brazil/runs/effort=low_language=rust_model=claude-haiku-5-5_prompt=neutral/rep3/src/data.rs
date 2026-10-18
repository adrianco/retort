//! Context: in-memory dataset built from the Kaggle CSV files in `data/kaggle/`.
//!
//! Five match sources are merged into one list of [`Match`]es and the FIFA
//! export is loaded into [`Player`]s. Sources overlap (for example the 2012+
//! Brasileirão appears in two files), so later sources skip any fixture that
//! is already present (same date and same pair of teams).
//!
//! Loaders take `impl Read`, so tests can feed inline CSV text.

use std::collections::{HashMap, HashSet};
use std::fs::File;
use std::io::Read;
use std::path::Path;

use crate::normalize::{Team, canonical_competition, parse_date, parse_goals};

#[derive(Debug, Clone, PartialEq)]
pub struct Match {
    pub competition: String,
    pub season: i32,
    /// ISO `YYYY-MM-DD`; lexicographic order equals chronological order.
    pub date: String,
    pub round: Option<String>,
    pub home: Team,
    pub away: Team,
    pub home_goals: u32,
    pub away_goals: u32,
}

impl Match {
    /// Result from the perspective of `team`: `Some('W' | 'D' | 'L')`,
    /// or `None` when the team is not in this match.
    pub fn result_for(&self, team: &Team) -> Option<char> {
        let (mine, theirs) = if self.home.matches(team) {
            (self.home_goals, self.away_goals)
        } else if self.away.matches(team) {
            (self.away_goals, self.home_goals)
        } else {
            return None;
        };
        Some(match mine.cmp(&theirs) {
            std::cmp::Ordering::Greater => 'W',
            std::cmp::Ordering::Equal => 'D',
            std::cmp::Ordering::Less => 'L',
        })
    }

    /// Goals `(scored, conceded)` from `team`'s perspective, if it played.
    pub fn goals_for(&self, team: &Team) -> Option<(u32, u32)> {
        if self.home.matches(team) {
            Some((self.home_goals, self.away_goals))
        } else if self.away.matches(team) {
            Some((self.away_goals, self.home_goals))
        } else {
            None
        }
    }

    fn dedupe_key(&self) -> (String, String, String) {
        let mut pair = [self.home.key.clone(), self.away.key.clone()];
        pair.sort();
        (self.date.clone(), pair[0].clone(), pair[1].clone())
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct Player {
    pub name: String,
    pub age: u32,
    pub nationality: String,
    pub overall: u32,
    pub potential: u32,
    pub club: Option<String>,
    pub position: Option<String>,
    pub jersey_number: Option<u32>,
}

#[derive(Debug, Default)]
pub struct Dataset {
    pub matches: Vec<Match>,
    pub players: Vec<Player>,
    seen: HashSet<(String, String, String)>,
}

#[derive(Debug)]
pub enum LoadError {
    Io(std::io::Error),
    Csv(csv::Error),
    MissingColumn(String),
}

impl std::fmt::Display for LoadError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            LoadError::Io(e) => write!(f, "I/O error: {e}"),
            LoadError::Csv(e) => write!(f, "CSV error: {e}"),
            LoadError::MissingColumn(c) => write!(f, "missing column `{c}`"),
        }
    }
}

impl std::error::Error for LoadError {}

impl From<std::io::Error> for LoadError {
    fn from(e: std::io::Error) -> Self {
        LoadError::Io(e)
    }
}

impl From<csv::Error> for LoadError {
    fn from(e: csv::Error) -> Self {
        LoadError::Csv(e)
    }
}

/// Column lookup by header name; tolerates a UTF-8 BOM and surrounding spaces.
struct Columns {
    index: HashMap<String, usize>,
}

impl Columns {
    fn new(headers: &csv::StringRecord) -> Self {
        let index = headers
            .iter()
            .enumerate()
            .map(|(i, h)| (h.trim_start_matches('\u{feff}').trim().to_string(), i))
            .collect();
        Columns { index }
    }

    fn require(&self, name: &str) -> Result<usize, LoadError> {
        self.index
            .get(name)
            .copied()
            .ok_or_else(|| LoadError::MissingColumn(name.to_string()))
    }
}

/// Reads all rows, handing each record to `f` with the column index.
fn for_each_row<R: Read>(
    reader: R,
    mut f: impl FnMut(&Columns, &csv::StringRecord) -> Result<(), LoadError>,
) -> Result<(), LoadError> {
    let mut rdr = csv::ReaderBuilder::new()
        .flexible(true)
        .trim(csv::Trim::All)
        .from_reader(reader);
    let columns = Columns::new(rdr.headers()?);
    for record in rdr.records() {
        f(&columns, &record?)?;
    }
    Ok(())
}

fn field(rec: &csv::StringRecord, idx: usize) -> &str {
    rec.get(idx).unwrap_or("")
}

impl Dataset {
    pub fn new() -> Self {
        Self::default()
    }

    /// Loads every file from the standard layout under `dir`.
    /// Missing optional files are an error: the spec requires all six.
    pub fn load_dir(dir: &Path) -> Result<Self, LoadError> {
        let mut ds = Dataset::new();
        ds.add_brasileirao(File::open(dir.join("Brasileirao_Matches.csv"))?)?;
        ds.add_historical_brasileirao(File::open(dir.join("novo_campeonato_brasileiro.csv"))?)?;
        ds.add_cup(File::open(dir.join("Brazilian_Cup_Matches.csv"))?)?;
        ds.add_libertadores(File::open(dir.join("Libertadores_Matches.csv"))?)?;
        ds.add_extended(File::open(dir.join("BR-Football-Dataset.csv"))?)?;
        ds.add_fifa(File::open(dir.join("fifa_data.csv"))?)?;
        Ok(ds)
    }

    /// `Brasileirao_Matches.csv`: datetime, home_team, away_team, goals, season, round.
    pub fn add_brasileirao<R: Read>(&mut self, reader: R) -> Result<usize, LoadError> {
        self.load_matches(
            reader,
            &MatchSpec {
                date: "datetime",
                home: "home_team",
                away: "away_team",
                home_goals: "home_goal",
                away_goals: "away_goal",
                season: Some("season"),
                round: Some("round"),
                stage: None,
                competition: "Brasileirão Série A",
            },
        )
    }

    /// `novo_campeonato_brasileiro.csv` (2003–2019). Rows overlapping the
    /// Brasileirao_Matches range are skipped as duplicates.
    pub fn add_historical_brasileirao<R: Read>(&mut self, reader: R) -> Result<usize, LoadError> {
        self.load_matches(
            reader,
            &MatchSpec {
                date: "Data",
                home: "Equipe_mandante",
                away: "Equipe_visitante",
                home_goals: "Gols_mandante",
                away_goals: "Gols_visitante",
                season: Some("Ano"),
                round: Some("Rodada"),
                stage: None,
                competition: "Brasileirão Série A",
            },
        )
    }

    /// `Brazilian_Cup_Matches.csv`.
    pub fn add_cup<R: Read>(&mut self, reader: R) -> Result<usize, LoadError> {
        self.load_matches(
            reader,
            &MatchSpec {
                date: "datetime",
                home: "home_team",
                away: "away_team",
                home_goals: "home_goal",
                away_goals: "away_goal",
                season: Some("season"),
                round: Some("round"),
                stage: None,
                competition: "Copa do Brasil",
            },
        )
    }

    /// `Libertadores_Matches.csv`, which carries a `stage` column instead of a round.
    pub fn add_libertadores<R: Read>(&mut self, reader: R) -> Result<usize, LoadError> {
        self.load_matches(
            reader,
            &MatchSpec {
                date: "datetime",
                home: "home_team",
                away: "away_team",
                home_goals: "home_goal",
                away_goals: "away_goal",
                season: Some("season"),
                round: None,
                stage: Some("stage"),
                competition: "Copa Libertadores",
            },
        )
    }

    /// `BR-Football-Dataset.csv`: one row per match with a `tournament` column.
    /// Its Serie A and Cup rows overlap the files above and are dropped as
    /// duplicates; Serie B/C and 2023 Serie A rows are new and are kept.
    pub fn add_extended<R: Read>(&mut self, reader: R) -> Result<usize, LoadError> {
        let mut added = 0;
        for_each_row(reader, |c, rec| {
            let tournament = field(rec, c.require("tournament")?);
            let Some(competition) = canonical_competition(tournament) else {
                return Ok(());
            };
            let Some(date) = parse_date(field(rec, c.require("date")?)) else {
                return Ok(());
            };
            let (Some(hg), Some(ag)) = (
                parse_goals(field(rec, c.require("home_goal")?)),
                parse_goals(field(rec, c.require("away_goal")?)),
            ) else {
                return Ok(());
            };
            let m = Match {
                competition: competition.to_string(),
                season: year_of(&date),
                date,
                round: None,
                home: Team::parse(field(rec, c.require("home")?)),
                away: Team::parse(field(rec, c.require("away")?)),
                home_goals: hg,
                away_goals: ag,
            };
            added += usize::from(self.push_unique(m));
            Ok(())
        })?;
        Ok(added)
    }

    /// FIFA player export. Only the columns the queries need are read.
    pub fn add_fifa<R: Read>(&mut self, reader: R) -> Result<usize, LoadError> {
        let mut added = 0;
        for_each_row(reader, |c, rec| {
            let text = |name: &str| -> Result<Option<String>, LoadError> {
                let v = field(rec, c.require(name)?);
                Ok((!v.is_empty()).then(|| v.to_string()))
            };
            let num = |name: &str| -> Result<Option<u32>, LoadError> {
                Ok(field(rec, c.require(name)?).parse::<u32>().ok())
            };
            let Some(name) = text("Name")? else {
                return Ok(());
            };
            self.players.push(Player {
                name,
                age: num("Age")?.unwrap_or(0),
                nationality: text("Nationality")?.unwrap_or_default(),
                overall: num("Overall")?.unwrap_or(0),
                potential: num("Potential")?.unwrap_or(0),
                club: text("Club")?,
                position: text("Position")?,
                jersey_number: num("Jersey Number")?,
            });
            added += 1;
            Ok(())
        })?;
        Ok(added)
    }

    fn load_matches<R: Read>(&mut self, reader: R, spec: &MatchSpec) -> Result<usize, LoadError> {
        let mut added = 0;
        for_each_row(reader, |c, rec| {
            let col = |name: &str| c.require(name);
            let Some(date) = parse_date(field(rec, col(spec.date)?)) else {
                return Ok(());
            };
            let (Some(hg), Some(ag)) = (
                parse_goals(field(rec, col(spec.home_goals)?)),
                parse_goals(field(rec, col(spec.away_goals)?)),
            ) else {
                return Ok(());
            };
            let season = match spec.season {
                Some(name) => field(rec, col(name)?).parse::<i32>().ok(),
                None => None,
            }
            .unwrap_or_else(|| year_of(&date));
            let round = match (spec.round, spec.stage) {
                (Some(name), _) => Some(field(rec, col(name)?)),
                (None, Some(name)) => Some(field(rec, col(name)?)),
                (None, None) => None,
            }
            .filter(|r| !r.is_empty())
            .map(str::to_string);
            let m = Match {
                competition: spec.competition.to_string(),
                season,
                date,
                round,
                home: Team::parse(field(rec, col(spec.home)?)),
                away: Team::parse(field(rec, col(spec.away)?)),
                home_goals: hg,
                away_goals: ag,
            };
            added += usize::from(self.push_unique(m));
            Ok(())
        })?;
        Ok(added)
    }

    /// Adds `m` unless the same fixture (date and team pair) is already present.
    fn push_unique(&mut self, m: Match) -> bool {
        if self.seen.insert(m.dedupe_key()) {
            self.matches.push(m);
            true
        } else {
            false
        }
    }
}

fn year_of(date: &str) -> i32 {
    date[..4].parse().unwrap_or(0)
}

/// Column names and fixed competition label for one match file.
struct MatchSpec {
    date: &'static str,
    home: &'static str,
    away: &'static str,
    home_goals: &'static str,
    away_goals: &'static str,
    season: Option<&'static str>,
    round: Option<&'static str>,
    stage: Option<&'static str>,
    competition: &'static str,
}
