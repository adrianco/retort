use crate::csv::{CsvRow, CsvTable};
use std::{
    collections::BTreeMap,
    error::Error,
    fmt,
    path::{Path, PathBuf},
};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Match {
    pub id: String,
    pub date: String,
    pub season: i32,
    pub competition: String,
    pub home_team: String,
    pub home_key: String,
    pub away_team: String,
    pub away_key: String,
    pub home_goals: i32,
    pub away_goals: i32,
    pub round_or_stage: Option<String>,
    pub stadium: Option<String>,
    pub source: String,
    pub extended: ExtendedStats,
}

#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct ExtendedStats {
    pub home_corners: Option<i32>,
    pub away_corners: Option<i32>,
    pub home_attacks: Option<i32>,
    pub away_attacks: Option<i32>,
    pub home_shots: Option<i32>,
    pub away_shots: Option<i32>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Player {
    pub id: String,
    pub name: String,
    pub name_key: String,
    pub age: Option<i32>,
    pub nationality: String,
    pub nationality_key: String,
    pub overall: Option<i32>,
    pub potential: Option<i32>,
    pub club: String,
    pub club_key: String,
    pub position: String,
    pub jersey_number: Option<i32>,
    pub height: Option<String>,
    pub weight: Option<String>,
    pub attributes: BTreeMap<String, i32>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DatasetReport {
    pub file: String,
    pub rows: usize,
    pub loaded: usize,
    pub skipped: usize,
}

#[derive(Debug, Clone)]
pub struct DataStore {
    pub matches: Vec<Match>,
    pub players: Vec<Player>,
    pub teams: BTreeMap<String, String>,
    pub reports: Vec<DatasetReport>,
    pub data_dir: PathBuf,
}

#[derive(Debug)]
pub struct DataError(pub String);

impl fmt::Display for DataError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.0)
    }
}
impl Error for DataError {}

impl DataStore {
    pub fn load(data_dir: impl AsRef<Path>) -> Result<Self, DataError> {
        let data_dir = data_dir.as_ref().to_path_buf();
        let mut store = Self {
            matches: Vec::new(),
            players: Vec::new(),
            teams: BTreeMap::new(),
            reports: Vec::new(),
            data_dir,
        };
        store.load_brasileirao()?;
        store.load_brazilian_cup()?;
        store.load_libertadores()?;
        store.load_extended()?;
        store.load_historical()?;
        store.load_players()?;
        if store.matches.is_empty() || store.players.is_empty() {
            return Err(DataError(
                "datasets loaded but produced no matches or players".into(),
            ));
        }
        Ok(store)
    }

    pub fn total_source_rows(&self) -> usize {
        self.reports.iter().map(|report| report.rows).sum()
    }

    fn table(&self, file: &str) -> Result<CsvTable, DataError> {
        let path = self.data_dir.join(file);
        CsvTable::from_path(&path)
            .map_err(|error| DataError(format!("failed to load {}: {error}", path.display())))
    }

    fn add_match(&mut self, mut item: Match) {
        item.home_key = normalize_team(&item.home_team);
        item.away_key = normalize_team(&item.away_team);
        self.teams
            .entry(item.home_key.clone())
            .or_insert_with(|| clean_team_display(&item.home_team, &item.home_key));
        self.teams
            .entry(item.away_key.clone())
            .or_insert_with(|| clean_team_display(&item.away_team, &item.away_key));
        self.matches.push(item);
    }

    fn load_brasileirao(&mut self) -> Result<(), DataError> {
        const FILE: &str = "Brasileirao_Matches.csv";
        let table = self.table(FILE)?;
        let total = table.len();
        let before = self.matches.len();
        for (index, row) in table.rows().enumerate() {
            let Some(item) = base_match(
                row,
                FILE,
                index,
                "Brasileirão Série A",
                MatchColumns {
                    date: "datetime",
                    season: "season",
                    home: "home_team",
                    away: "away_team",
                    home_goals: "home_goal",
                    away_goals: "away_goal",
                },
                row.get("round").map(|value| format!("Round {value}")),
                None,
            ) else {
                continue;
            };
            self.add_match(item);
        }
        self.report(FILE, total, self.matches.len() - before);
        Ok(())
    }

    fn load_brazilian_cup(&mut self) -> Result<(), DataError> {
        const FILE: &str = "Brazilian_Cup_Matches.csv";
        let table = self.table(FILE)?;
        let total = table.len();
        let before = self.matches.len();
        let mut final_round_by_season: BTreeMap<i32, i32> = BTreeMap::new();
        for row in table.rows() {
            if let (Some(season), Some(round)) = (int(row.get("season")), int(row.get("round"))) {
                final_round_by_season
                    .entry(season)
                    .and_modify(|value| *value = (*value).max(round))
                    .or_insert(round);
            }
        }
        for (index, row) in table.rows().enumerate() {
            let season = int(row.get("season"));
            let round_number = int(row.get("round"));
            let round = row.get("round").map(|value| {
                if round_number.is_some_and(|round| {
                    season
                        .and_then(|year| final_round_by_season.get(&year))
                        .is_some_and(|final_round| round == *final_round)
                }) {
                    format!("Final (Round {value})")
                } else if value.chars().all(|c| c.is_ascii_digit()) {
                    format!("Round {value}")
                } else {
                    value.to_string()
                }
            });
            let Some(item) = base_match(
                row,
                FILE,
                index,
                "Copa do Brasil",
                MatchColumns {
                    date: "datetime",
                    season: "season",
                    home: "home_team",
                    away: "away_team",
                    home_goals: "home_goal",
                    away_goals: "away_goal",
                },
                round,
                None,
            ) else {
                continue;
            };
            self.add_match(item);
        }
        self.report(FILE, total, self.matches.len() - before);
        Ok(())
    }

    fn load_libertadores(&mut self) -> Result<(), DataError> {
        const FILE: &str = "Libertadores_Matches.csv";
        let table = self.table(FILE)?;
        let total = table.len();
        let before = self.matches.len();
        for (index, row) in table.rows().enumerate() {
            let Some(item) = base_match(
                row,
                FILE,
                index,
                "Copa Libertadores",
                MatchColumns {
                    date: "datetime",
                    season: "season",
                    home: "home_team",
                    away: "away_team",
                    home_goals: "home_goal",
                    away_goals: "away_goal",
                },
                row.get("stage").map(title_case),
                None,
            ) else {
                continue;
            };
            self.add_match(item);
        }
        self.report(FILE, total, self.matches.len() - before);
        Ok(())
    }

    fn load_extended(&mut self) -> Result<(), DataError> {
        const FILE: &str = "BR-Football-Dataset.csv";
        let table = self.table(FILE)?;
        let total = table.len();
        let before = self.matches.len();
        for (index, row) in table.rows().enumerate() {
            let date = row.get("date").and_then(normalize_date);
            let season = date
                .as_deref()
                .and_then(|value| value.get(..4))
                .and_then(|year| year.parse().ok());
            let (
                Some(date),
                Some(season),
                Some(home),
                Some(away),
                Some(home_goals),
                Some(away_goals),
            ) = (
                date,
                season,
                row.get("home"),
                row.get("away"),
                int(row.get("home_goal")),
                int(row.get("away_goal")),
            )
            else {
                continue;
            };
            let competition = normalize_competition(row.get("tournament").unwrap_or("Other"));
            self.add_match(Match {
                id: format!("extended:{index}"),
                date,
                season,
                competition,
                home_team: home.trim().into(),
                home_key: String::new(),
                away_team: away.trim().into(),
                away_key: String::new(),
                home_goals,
                away_goals,
                round_or_stage: None,
                stadium: None,
                source: FILE.into(),
                extended: ExtendedStats {
                    home_corners: int(row.get("home_corner")),
                    away_corners: int(row.get("away_corner")),
                    home_attacks: int(row.get("home_attack")),
                    away_attacks: int(row.get("away_attack")),
                    home_shots: int(row.get("home_shots")),
                    away_shots: int(row.get("away_shots")),
                },
            });
        }
        self.report(FILE, total, self.matches.len() - before);
        Ok(())
    }

    fn load_historical(&mut self) -> Result<(), DataError> {
        const FILE: &str = "novo_campeonato_brasileiro.csv";
        let table = self.table(FILE)?;
        let total = table.len();
        let before = self.matches.len();
        for (index, row) in table.rows().enumerate() {
            let round = row.get("Rodada").map(|value| format!("Round {value}"));
            let Some(mut item) = base_match(
                row,
                FILE,
                index,
                "Brasileirão Série A",
                MatchColumns {
                    date: "Data",
                    season: "Ano",
                    home: "Equipe_mandante",
                    away: "Equipe_visitante",
                    home_goals: "Gols_mandante",
                    away_goals: "Gols_visitante",
                },
                round,
                row.get("Arena").map(str::to_string),
            ) else {
                continue;
            };
            if let Some(id) = row.get("ID") {
                item.id = format!("historical:{id}");
            }
            self.add_match(item);
        }
        self.report(FILE, total, self.matches.len() - before);
        Ok(())
    }

    fn load_players(&mut self) -> Result<(), DataError> {
        const FILE: &str = "fifa_data.csv";
        let table = self.table(FILE)?;
        let total = table.len();
        let before = self.players.len();
        const SKILLS: &[&str] = &[
            "Crossing",
            "Finishing",
            "HeadingAccuracy",
            "ShortPassing",
            "Volleys",
            "Dribbling",
            "Curve",
            "FKAccuracy",
            "LongPassing",
            "BallControl",
            "Acceleration",
            "SprintSpeed",
            "Agility",
            "Reactions",
            "Balance",
            "ShotPower",
            "Jumping",
            "Stamina",
            "Strength",
            "LongShots",
            "Aggression",
            "Interceptions",
            "Positioning",
            "Vision",
            "Penalties",
            "Composure",
            "Marking",
            "StandingTackle",
            "SlidingTackle",
            "GKDiving",
            "GKHandling",
            "GKKicking",
            "GKPositioning",
            "GKReflexes",
        ];
        for row in table.rows() {
            let (Some(id), Some(name), Some(nationality)) =
                (row.get("ID"), row.get("Name"), row.get("Nationality"))
            else {
                continue;
            };
            let club = row.get("Club").unwrap_or("Free Agent").trim().to_string();
            let attributes = SKILLS
                .iter()
                .filter_map(|skill| int(row.get(skill)).map(|value| ((*skill).to_string(), value)))
                .collect();
            self.players.push(Player {
                id: id.into(),
                name: name.trim().into(),
                name_key: normalize_text(name),
                age: int(row.get("Age")),
                nationality: nationality.trim().into(),
                nationality_key: normalize_text(nationality),
                overall: int(row.get("Overall")),
                potential: int(row.get("Potential")),
                club_key: normalize_team(&club),
                club,
                position: row.get("Position").unwrap_or("Unknown").trim().into(),
                jersey_number: int(row.get("Jersey Number")),
                height: row.get("Height").map(str::to_string),
                weight: row.get("Weight").map(str::to_string),
                attributes,
            });
        }
        self.reports.push(DatasetReport {
            file: FILE.into(),
            rows: total,
            loaded: self.players.len() - before,
            skipped: total - (self.players.len() - before),
        });
        Ok(())
    }

    fn report(&mut self, file: &str, total: usize, loaded: usize) {
        self.reports.push(DatasetReport {
            file: file.into(),
            rows: total,
            loaded,
            skipped: total.saturating_sub(loaded),
        });
    }
}

#[derive(Clone, Copy)]
struct MatchColumns<'a> {
    date: &'a str,
    season: &'a str,
    home: &'a str,
    away: &'a str,
    home_goals: &'a str,
    away_goals: &'a str,
}

fn base_match(
    row: CsvRow<'_>,
    source: &str,
    index: usize,
    competition: &str,
    columns: MatchColumns<'_>,
    round_or_stage: Option<String>,
    stadium: Option<String>,
) -> Option<Match> {
    let date = normalize_date(row.get(columns.date)?)?;
    let season = int(row.get(columns.season)).or_else(|| date.get(..4)?.parse().ok())?;
    Some(Match {
        id: format!("{}:{index}", source.trim_end_matches(".csv")),
        date,
        season,
        competition: competition.into(),
        home_team: row.get(columns.home)?.trim().into(),
        home_key: String::new(),
        away_team: row.get(columns.away)?.trim().into(),
        away_key: String::new(),
        home_goals: int(row.get(columns.home_goals))?,
        away_goals: int(row.get(columns.away_goals))?,
        round_or_stage,
        stadium,
        source: source.into(),
        extended: ExtendedStats::default(),
    })
}

fn int(value: Option<&str>) -> Option<i32> {
    let value = value?.trim();
    value
        .parse()
        .ok()
        .or_else(|| value.parse::<f64>().ok().map(|number| number as i32))
}

pub fn normalize_date(input: &str) -> Option<String> {
    let raw = input.split_whitespace().next()?;
    if raw.len() >= 10 && raw.as_bytes().get(4) == Some(&b'-') {
        let (year, month, day) = (&raw[0..4], &raw[5..7], &raw[8..10]);
        valid_date(year, month, day).then(|| format!("{year}-{month}-{day}"))
    } else {
        let parts: Vec<_> = raw.split('/').collect();
        if parts.len() != 3 {
            return None;
        }
        let (day, month, year) = (parts[0], parts[1], parts[2]);
        valid_date(year, month, day).then(|| format!("{year}-{month:0>2}-{day:0>2}"))
    }
}

fn valid_date(year: &str, month: &str, day: &str) -> bool {
    let (Ok(year), Ok(month), Ok(day)) = (
        year.parse::<i32>(),
        month.parse::<u32>(),
        day.parse::<u32>(),
    ) else {
        return false;
    };
    let max_day = match month {
        1 | 3 | 5 | 7 | 8 | 10 | 12 => 31,
        4 | 6 | 9 | 11 => 30,
        2 if year % 400 == 0 || (year % 4 == 0 && year % 100 != 0) => 29,
        2 => 28,
        _ => return false,
    };
    (1800..=2200).contains(&year) && (1..=max_day).contains(&day)
}

pub fn normalize_text(input: &str) -> String {
    let mut output = String::new();
    let mut spaced = true;
    for ch in input.chars().flat_map(|ch| ch.to_lowercase()) {
        let replacement = match ch {
            'á' | 'à' | 'â' | 'ã' | 'ä' => 'a',
            'é' | 'è' | 'ê' | 'ë' => 'e',
            'í' | 'ì' | 'î' | 'ï' => 'i',
            'ó' | 'ò' | 'ô' | 'õ' | 'ö' => 'o',
            'ú' | 'ù' | 'û' | 'ü' => 'u',
            'ç' => 'c',
            'ñ' => 'n',
            ch if ch.is_alphanumeric() => ch,
            _ => ' ',
        };
        if replacement == ' ' {
            if !spaced {
                output.push(' ');
                spaced = true;
            }
        } else {
            output.push(replacement);
            spaced = false;
        }
    }
    output.trim().to_string()
}

pub fn normalize_team(input: &str) -> String {
    let had_suffix = input.rsplit_once('-').is_some() || input.rsplit_once(" - ").is_some();
    let mut normalized = normalize_text(input);
    if had_suffix {
        const STATES: &[&str] = &[
            "ac", "al", "ap", "am", "ba", "ce", "df", "es", "go", "ma", "mt", "ms", "mg", "pa",
            "pb", "pr", "pe", "pi", "rj", "rn", "rs", "ro", "rr", "sc", "sp", "se", "to",
        ];
        if let Some(last) = normalized.split_whitespace().last()
            && STATES.contains(&last)
        {
            let base = normalized[..normalized.len() - last.len()].trim();
            normalized = match (base, last) {
                ("atletico", "mg") => "atletico mineiro".into(),
                ("atletico", "pr") | ("athletico", "pr") => "athletico paranaense".into(),
                ("atletico", "go") => "atletico goianiense".into(),
                ("america", "mg") => "america mineiro".into(),
                ("america", "rn") => "america natal".into(),
                ("botafogo", "rj") => "botafogo".into(),
                ("botafogo", state) | ("operario", state) | ("nacional", state) => {
                    format!("{base} {state}")
                }
                _ => base.into(),
            };
        }
    }
    let compact: String = normalized
        .split_whitespace()
        .filter(|word| {
            !matches!(
                *word,
                "de" | "da"
                    | "do"
                    | "futebol"
                    | "football"
                    | "foot"
                    | "ball"
                    | "clube"
                    | "club"
                    | "esporte"
                    | "sport"
                    | "sociedade"
                    | "associacao"
                    | "paulista"
            )
        })
        .collect::<Vec<_>>()
        .join(" ");
    match compact.as_str() {
        "regatas flamengo" => "flamengo".into(),
        "fluminense" => "fluminense".into(),
        "corinthians" => "corinthians".into(),
        "palmeiras" => "palmeiras".into(),
        "sao paulo" | "sao paulo fc" => "sao paulo".into(),
        "santos" => "santos".into(),
        "gremio porto alegrense" => "gremio".into(),
        "regatas vasco gama" | "vasco gama" | "vasco gama rj" => "vasco".into(),
        "botafogo rj" => "botafogo".into(),
        "ec bahia" => "bahia".into(),
        "fortaleza fc" => "fortaleza".into(),
        "atletico mineiro" => "atletico mineiro".into(),
        "athletico paranaense" | "atletico paranaense" | "atletico pr" => {
            "athletico paranaense".into()
        }
        _ if compact.is_empty() => normalized,
        _ => compact,
    }
}

pub fn team_matches(query: &str, key: &str) -> bool {
    let query = normalize_team(query);
    query == key
        || (query.len() >= 4
            && key
                .split_whitespace()
                .collect::<Vec<_>>()
                .starts_with(&query.split_whitespace().collect::<Vec<_>>()))
}

pub fn competition_matches(query: &str, competition: &str) -> bool {
    let query = normalize_text(query);
    let value = normalize_text(competition);
    value.contains(&query)
        || query.contains(&value)
        || (query.contains("brasileir") && value.contains("brasileir"))
        || (query.contains("libertadores") && value.contains("libertadores"))
        || (query.contains("copa do brasil") && value.contains("copa do brasil"))
}

fn normalize_competition(value: &str) -> String {
    let key = normalize_text(value);
    if key.contains("libertadores") {
        "Copa Libertadores".into()
    } else if key.contains("copa do brasil") {
        "Copa do Brasil".into()
    } else if key.contains("serie a") || key.contains("brasileir") {
        "Brasileirão Série A".into()
    } else {
        value.trim().into()
    }
}

fn clean_team_display(input: &str, key: &str) -> String {
    match key {
        "atletico mineiro" => return "Atlético Mineiro".into(),
        "athletico paranaense" => return "Athletico Paranaense".into(),
        "atletico goianiense" => return "Atlético Goianiense".into(),
        "america mineiro" => return "América Mineiro".into(),
        "america natal" => return "América de Natal".into(),
        _ => {}
    }
    let trimmed = input.trim();
    if let Some((name, suffix)) = trimmed.rsplit_once('-')
        && suffix.trim().len() == 2
    {
        return name.trim().into();
    }
    if let Some((name, suffix)) = trimmed.rsplit_once(" - ")
        && suffix.trim().len() == 2
    {
        return name.trim().into();
    }
    trimmed.into()
}

fn title_case(input: &str) -> String {
    input
        .split_whitespace()
        .map(|word| {
            let mut chars = word.chars();
            chars
                .next()
                .map(|first| first.to_uppercase().collect::<String>() + chars.as_str())
                .unwrap_or_default()
        })
        .collect::<Vec<_>>()
        .join(" ")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn normalizes_dates_and_team_variations() {
        assert_eq!(normalize_date("29/03/2003"), Some("2003-03-29".into()));
        assert_eq!(
            normalize_date("2023-09-24 18:30:00"),
            Some("2023-09-24".into())
        );
        assert_eq!(normalize_team("São Paulo-SP"), "sao paulo");
        assert_eq!(normalize_team("São Paulo Futebol Clube"), "sao paulo");
        assert_eq!(normalize_team("Clube de Regatas do Flamengo"), "flamengo");
        assert_eq!(normalize_team("Vasco da Gama-RJ"), "vasco");
        assert_eq!(normalize_team("Vasco Da Gama RJ"), "vasco");
        assert_eq!(normalize_team("Botafogo RJ"), "botafogo");
        assert_eq!(normalize_team("EC Bahia"), "bahia");
        assert_eq!(normalize_team("Fortaleza FC"), "fortaleza");
        assert_eq!(normalize_team("Atlético-MG"), "atletico mineiro");
        assert_eq!(normalize_team("Atlético-PR"), "athletico paranaense");
        assert!(team_matches("Flamengo", "flamengo"));
    }

    #[test]
    fn rejects_bad_dates() {
        assert_eq!(normalize_date("2023-02-29"), None);
        assert_eq!(normalize_date("not-a-date"), None);
    }
}
