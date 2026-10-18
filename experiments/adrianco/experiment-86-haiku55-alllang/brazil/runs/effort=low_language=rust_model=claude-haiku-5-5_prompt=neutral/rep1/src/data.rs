//! Loads the Kaggle CSV files into an in-memory [`Dataset`].
//!
//! Match sources are loaded in priority order. The Brasileirão files overlap
//! each other, and some sources record a match one day off, so a row is a
//! duplicate when the same competition has the same unordered team pair within
//! one day. Unparseable rows are counted in [`SourceSummary`] instead of
//! failing the load.

use std::collections::HashMap;
use std::error::Error;
use std::path::Path;

use crate::normalize::{display_name, team_key};

/// Competitions covered by the datasets.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum Competition {
    Brasileirao,
    CopaDoBrasil,
    Libertadores,
    SerieB,
    SerieC,
}

impl Competition {
    pub const ALL: [Competition; 5] = [
        Competition::Brasileirao,
        Competition::CopaDoBrasil,
        Competition::Libertadores,
        Competition::SerieB,
        Competition::SerieC,
    ];

    pub fn label(self) -> &'static str {
        match self {
            Competition::Brasileirao => "Brasileirão",
            Competition::CopaDoBrasil => "Copa do Brasil",
            Competition::Libertadores => "Copa Libertadores",
            Competition::SerieB => "Série B",
            Competition::SerieC => "Série C",
        }
    }

    /// Stable identifier used in tool arguments and output.
    pub fn slug(self) -> &'static str {
        match self {
            Competition::Brasileirao => "brasileirao",
            Competition::CopaDoBrasil => "copa_do_brasil",
            Competition::Libertadores => "libertadores",
            Competition::SerieB => "serie_b",
            Competition::SerieC => "serie_c",
        }
    }

    /// Accepts slugs, labels and common spellings, case- and accent-insensitively.
    pub fn parse(input: &str) -> Option<Self> {
        let text = crate::normalize::fold(input).replace('_', " ");
        match text.as_str() {
            "brasileirao" | "brasileiro" | "serie a" | "brasileirao serie a" | "brasileirao a" => {
                Some(Competition::Brasileirao)
            }
            "copa do brasil" | "copa brasil" => Some(Competition::CopaDoBrasil),
            "libertadores" | "copa libertadores" => Some(Competition::Libertadores),
            "serie b" | "brasileirao serie b" => Some(Competition::SerieB),
            "serie c" | "brasileirao serie c" => Some(Competition::SerieC),
            _ => None,
        }
    }
}

/// A team with its matching key and display name.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Team {
    pub key: String,
    pub name: String,
}

impl Team {
    fn from_raw(raw: &str) -> Self {
        Team { key: team_key(raw), name: display_name(raw) }
    }
}

/// One played match. `date` is ISO `YYYY-MM-DD`, so lexical order is date order.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Match {
    pub date: String,
    pub season: i32,
    pub competition: Competition,
    /// Display label such as `Round 22` or `group stage`, when the source has one.
    pub round: Option<String>,
    pub home: Team,
    pub away: Team,
    pub home_goals: u32,
    pub away_goals: u32,
}

/// A player from the FIFA ratings file.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Player {
    pub name: String,
    pub age: u32,
    pub nationality: String,
    pub overall: u32,
    pub potential: u32,
    pub club: String,
    pub position: String,
    pub jersey_number: Option<u32>,
    pub height: String,
    pub weight: String,
}

/// Row counts for one source file.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SourceSummary {
    pub file: String,
    pub rows_loaded: usize,
    /// Same match already loaded from an earlier source.
    pub rows_duplicate: usize,
    /// Row could not be parsed (bad date, missing goals or team).
    pub rows_invalid: usize,
    /// Row is outside the datasets' scope (e.g. an unmapped tournament).
    pub rows_out_of_scope: usize,
}

/// Outcome of trying to add one row.
#[derive(Debug, PartialEq, Eq)]
enum Insert {
    Added,
    Duplicate,
    Invalid,
}

/// Matches already loaded, keyed by competition and sorted team pair.
/// Each entry holds the ordinal day numbers of those matches.
type SeenMatches = HashMap<(Competition, String, String), Vec<i64>>;

/// Everything the server queries, loaded once at startup.
#[derive(Debug, Default)]
pub struct Dataset {
    pub matches: Vec<Match>,
    pub players: Vec<Player>,
    pub sources: Vec<SourceSummary>,
}

impl Dataset {
    /// Loads every CSV file from `dir`. Missing files are an error.
    pub fn load(dir: &Path) -> Result<Dataset, Box<dyn Error>> {
        let mut ds = Dataset::default();
        let mut seen = SeenMatches::new();

        // Priority order: earlier sources win when the same match appears twice.
        let brasileirao = CsvFile::open(&dir.join("Brasileirao_Matches.csv"))?;
        ds.load_matches("Brasileirao_Matches.csv", &brasileirao, &mut seen, |f, r| {
            Some(RawMatch {
                date: f.get(r, "datetime"),
                season: parse_i32(f.get(r, "season")),
                competition: Competition::Brasileirao,
                round: non_empty(f.get(r, "round")).map(|round| format!("Round {round}")),
                home: f.get(r, "home_team"),
                away: f.get(r, "away_team"),
                home_goals: f.get(r, "home_goal"),
                away_goals: f.get(r, "away_goal"),
            })
        });

        let historical = CsvFile::open(&dir.join("novo_campeonato_brasileiro.csv"))?;
        ds.load_matches("novo_campeonato_brasileiro.csv", &historical, &mut seen, |f, r| {
            Some(RawMatch {
                date: f.get(r, "Data"),
                season: parse_i32(f.get(r, "Ano")),
                competition: Competition::Brasileirao,
                round: non_empty(f.get(r, "Rodada")).map(|round| format!("Round {round}")),
                home: f.get(r, "Equipe_mandante"),
                away: f.get(r, "Equipe_visitante"),
                home_goals: f.get(r, "Gols_mandante"),
                away_goals: f.get(r, "Gols_visitante"),
            })
        });

        let cup = CsvFile::open(&dir.join("Brazilian_Cup_Matches.csv"))?;
        ds.load_matches("Brazilian_Cup_Matches.csv", &cup, &mut seen, |f, r| {
            Some(RawMatch {
                date: f.get(r, "datetime"),
                season: parse_i32(f.get(r, "season")),
                competition: Competition::CopaDoBrasil,
                round: non_empty(f.get(r, "round")).map(|round| format!("Round {round}")),
                home: f.get(r, "home_team"),
                away: f.get(r, "away_team"),
                home_goals: f.get(r, "home_goal"),
                away_goals: f.get(r, "away_goal"),
            })
        });

        let libertadores = CsvFile::open(&dir.join("Libertadores_Matches.csv"))?;
        ds.load_matches("Libertadores_Matches.csv", &libertadores, &mut seen, |f, r| {
            Some(RawMatch {
                date: f.get(r, "datetime"),
                season: parse_i32(f.get(r, "season")),
                competition: Competition::Libertadores,
                round: non_empty(f.get(r, "stage")).map(str::to_string),
                home: f.get(r, "home_team"),
                away: f.get(r, "away_team"),
                home_goals: f.get(r, "home_goal"),
                away_goals: f.get(r, "away_goal"),
            })
        });

        let extended = CsvFile::open(&dir.join("BR-Football-Dataset.csv"))?;
        ds.load_matches("BR-Football-Dataset.csv", &extended, &mut seen, |f, r| {
            let competition = match f.get(r, "tournament") {
                "Serie A" => Competition::Brasileirao,
                "Serie B" => Competition::SerieB,
                "Serie C" => Competition::SerieC,
                "Copa do Brasil" => Competition::CopaDoBrasil,
                _ => return None,
            };
            Some(RawMatch {
                date: f.get(r, "date"),
                season: 0, // taken from the date below
                competition,
                round: None,
                home: f.get(r, "home"),
                away: f.get(r, "away"),
                home_goals: f.get(r, "home_goal"),
                away_goals: f.get(r, "away_goal"),
            })
        });

        let players = CsvFile::open(&dir.join("fifa_data.csv"))?;
        let mut loaded = 0;
        let mut skipped = 0;
        for record in &players.records {
            match parse_player(&players, record) {
                Some(player) => {
                    ds.players.push(player);
                    loaded += 1;
                }
                None => skipped += 1,
            }
        }
        ds.sources.push(SourceSummary {
            file: "fifa_data.csv".into(),
            rows_loaded: loaded,
            rows_duplicate: 0,
            rows_invalid: skipped,
            rows_out_of_scope: 0,
        });

        Ok(ds)
    }

    fn load_matches<'a>(
        &mut self,
        file: &str,
        csv: &'a CsvFile,
        seen: &mut SeenMatches,
        map_row: impl Fn(&CsvFile, &'a csv::StringRecord) -> Option<RawMatch<'a>>,
    ) {
        let mut summary = SourceSummary {
            file: file.into(),
            rows_loaded: 0,
            rows_duplicate: 0,
            rows_invalid: 0,
            rows_out_of_scope: 0,
        };
        for record in &csv.records {
            let Some(raw) = map_row(csv, record) else {
                summary.rows_out_of_scope += 1;
                continue;
            };
            match self.push_match(raw, seen) {
                Insert::Added => summary.rows_loaded += 1,
                Insert::Duplicate => summary.rows_duplicate += 1,
                Insert::Invalid => summary.rows_invalid += 1,
            }
        }
        self.sources.push(summary);
    }

    fn push_match(&mut self, raw: RawMatch<'_>, seen: &mut SeenMatches) -> Insert {
        let Some(date) = parse_date(raw.date) else { return Insert::Invalid };
        let (Some(home_goals), Some(away_goals)) = (parse_goals(raw.home_goals), parse_goals(raw.away_goals))
        else {
            return Insert::Invalid;
        };
        let season = match raw.season {
            0 => match date[..4].parse() {
                Ok(year) => year,
                Err(_) => return Insert::Invalid,
            },
            season => season,
        };
        let home = Team::from_raw(raw.home);
        let away = Team::from_raw(raw.away);
        if home.key.is_empty() || away.key.is_empty() {
            return Insert::Invalid;
        }
        let (first, second) = if home.key <= away.key {
            (home.key.clone(), away.key.clone())
        } else {
            (away.key.clone(), home.key.clone())
        };
        let day = day_number(&date);
        let days = seen.entry((raw.competition, first, second)).or_default();
        if days.iter().any(|known| (known - day).abs() <= 1) {
            return Insert::Duplicate;
        }
        days.push(day);
        self.matches.push(Match {
            date,
            season,
            competition: raw.competition,
            round: raw.round,
            home,
            away,
            home_goals,
            away_goals,
        });
        Insert::Added
    }
}

/// Fields of one match row, already mapped from a file's column names.
struct RawMatch<'a> {
    date: &'a str,
    /// Zero means "derive from the date".
    season: i32,
    competition: Competition,
    round: Option<String>,
    home: &'a str,
    away: &'a str,
    home_goals: &'a str,
    away_goals: &'a str,
}

/// A CSV file read fully into memory, with its header names indexed.
struct CsvFile {
    headers: HashMap<String, usize>,
    records: Vec<csv::StringRecord>,
}

impl CsvFile {
    fn open(path: &Path) -> Result<CsvFile, Box<dyn Error>> {
        let mut reader = csv::ReaderBuilder::new().flexible(true).from_path(path)?;
        let headers = reader
            .headers()?
            .iter()
            .enumerate()
            .map(|(index, name)| (name.trim_start_matches('\u{feff}').trim().to_string(), index))
            .collect();
        let records = reader.records().collect::<Result<Vec<_>, _>>()?;
        Ok(CsvFile { headers, records })
    }

    /// Returns the trimmed field, or an empty string when the column is absent.
    fn get<'a>(&self, record: &'a csv::StringRecord, column: &str) -> &'a str {
        self.headers.get(column).and_then(|&index| record.get(index)).unwrap_or("").trim()
    }
}

fn parse_player(file: &CsvFile, record: &csv::StringRecord) -> Option<Player> {
    let name = file.get(record, "Name");
    if name.is_empty() {
        return None;
    }
    Some(Player {
        name: name.to_string(),
        age: file.get(record, "Age").parse().ok()?,
        nationality: file.get(record, "Nationality").to_string(),
        overall: file.get(record, "Overall").parse().ok()?,
        potential: file.get(record, "Potential").parse().ok()?,
        club: file.get(record, "Club").to_string(),
        position: file.get(record, "Position").to_string(),
        jersey_number: file.get(record, "Jersey Number").parse().ok(),
        height: file.get(record, "Height").to_string(),
        weight: file.get(record, "Weight").to_string(),
    })
}

fn non_empty(text: &str) -> Option<&str> {
    (!text.is_empty()).then_some(text)
}

fn parse_i32(text: &str) -> i32 {
    text.parse().unwrap_or(0)
}

/// Goals appear as `2`, `2.0` or `2.0` in different files; only whole non-negative values are valid.
fn parse_goals(text: &str) -> Option<u32> {
    let value: f64 = text.trim().parse().ok()?;
    (value.is_finite() && value >= 0.0 && value.fract() == 0.0).then_some(value as u32)
}

/// Accepts ISO (`2023-09-24`, `2012-05-19 18:30:00`) and Brazilian (`29/03/2003`) dates.
/// Returns the normalized ISO date `YYYY-MM-DD`.
pub fn parse_date(text: &str) -> Option<String> {
    let text = text.trim();
    let head = text.split([' ', 'T']).next()?;
    if let Some((day, rest)) = head.split_once('/') {
        let (month, year) = rest.split_once('/')?;
        return iso_date(year, month, day);
    }
    let mut parts = head.splitn(3, '-');
    let (year, month, day) = (parts.next()?, parts.next()?, parts.next()?);
    iso_date(year, month, day)
}

/// Days since 1970-01-01 for an ISO date, so nearby dates differ by small numbers.
/// Uses the standard civil-calendar algorithm (proleptic Gregorian).
fn day_number(iso: &str) -> i64 {
    let year: i64 = iso[0..4].parse().unwrap_or(0);
    let month: i64 = iso[5..7].parse().unwrap_or(1);
    let day: i64 = iso[8..10].parse().unwrap_or(1);
    let y = if month <= 2 { year - 1 } else { year };
    let era = y.div_euclid(400);
    let year_of_era = y - era * 400;
    let shifted_month = if month > 2 { month - 3 } else { month + 9 };
    let day_of_year = (153 * shifted_month + 2) / 5 + day - 1;
    let day_of_era = year_of_era * 365 + year_of_era / 4 - year_of_era / 100 + day_of_year;
    era * 146_097 + day_of_era - 719_468
}

fn iso_date(year: &str, month: &str, day: &str) -> Option<String> {
    let year: u32 = year.parse().ok()?;
    let month: u32 = month.parse().ok()?;
    let day: u32 = day.parse().ok()?;
    let plausible = (1900..=2100).contains(&year) && (1..=12).contains(&month) && (1..=31).contains(&day);
    plausible.then(|| format!("{year:04}-{month:02}-{day:02}"))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_all_date_formats_in_the_data() {
        assert_eq!(parse_date("2023-09-24").as_deref(), Some("2023-09-24"));
        assert_eq!(parse_date("2012-05-19 18:30:00").as_deref(), Some("2012-05-19"));
        assert_eq!(parse_date("29/03/2003").as_deref(), Some("2003-03-29"));
        assert_eq!(parse_date("13/13/2020"), None);
        assert_eq!(parse_date("not a date"), None);
    }

    #[test]
    fn day_numbers_differ_by_calendar_days() {
        assert_eq!(day_number("1970-01-02") - day_number("1970-01-01"), 1);
        assert_eq!(day_number("2019-12-31") - day_number("2019-11-27"), 34);
        assert_eq!(day_number("2020-03-01") - day_number("2020-02-28"), 2);
    }

    #[test]
    fn goals_accept_integer_and_float_text() {
        assert_eq!(parse_goals("2"), Some(2));
        assert_eq!(parse_goals("2.0"), Some(2));
        assert_eq!(parse_goals(""), None);
        assert_eq!(parse_goals("1.5"), None);
    }

    #[test]
    fn competition_parses_common_spellings() {
        assert_eq!(Competition::parse("Brasileirão"), Some(Competition::Brasileirao));
        assert_eq!(Competition::parse("copa do brasil"), Some(Competition::CopaDoBrasil));
        assert_eq!(Competition::parse("copa_libertadores"), Some(Competition::Libertadores));
        assert_eq!(Competition::parse("premier league"), None);
    }
}
