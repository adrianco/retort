// =============================================================================
// CONTEXT: Brazilian Soccer MCP Server — data layer
//
// Responsibilities:
//   * Load all six Kaggle CSV files into unified `Match` and `Player` records.
//   * Normalize team names so that "Palmeiras-SP", "Palmeiras" and
//     "Sao Paulo" / "São Paulo" all resolve to comparable keys. State suffixes
//     are stripped EXCEPT for clubs whose base name is ambiguous without one
//     (Atlético-MG vs Atlético-GO vs Atlético-PR, América-MG vs América-RN,
//     Botafogo-RJ vs Botafogo-SP/PB, Nacional ...).
//   * Parse the three date formats present in the data:
//     "2012-05-19 18:30:00", "2023-09-24" and "29/03/2003".
//   * Handle UTF-8 / accented Portuguese text via ASCII accent folding.
//
// Records keep a `Source` tag so the query layer can de-duplicate matches that
// appear in more than one dataset (e.g. a 2015 Serie A game is present in
// Brasileirao_Matches.csv, novo_campeonato_brasileiro.csv and
// BR-Football-Dataset.csv).
// =============================================================================

use anyhow::{Context, Result};
use chrono::NaiveDate;
use std::collections::HashMap;
use std::path::Path;

/// Which CSV file a match came from. Order doubles as de-duplication priority
/// (lower = preferred when the same fixture appears in several files).
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum Source {
    /// Brasileirao_Matches.csv (Serie A 2012-2022)
    Brasileirao,
    /// novo_campeonato_brasileiro.csv (Serie A 2003-2019)
    Historical,
    /// Brazilian_Cup_Matches.csv (Copa do Brasil 2012-2021)
    Cup,
    /// Libertadores_Matches.csv (2013-2022)
    Libertadores,
    /// BR-Football-Dataset.csv (Serie A/B/C + Copa do Brasil 2014-2023)
    Extended,
}

impl Source {
    pub fn label(&self) -> &'static str {
        match self {
            Source::Brasileirao => "Brasileirao_Matches.csv",
            Source::Historical => "novo_campeonato_brasileiro.csv",
            Source::Cup => "Brazilian_Cup_Matches.csv",
            Source::Libertadores => "Libertadores_Matches.csv",
            Source::Extended => "BR-Football-Dataset.csv",
        }
    }
}

#[derive(Debug, Clone)]
pub struct Match {
    pub date: Option<NaiveDate>,
    pub home_team: String,
    pub away_team: String,
    pub home_key: String,
    pub away_key: String,
    pub home_goals: Option<i32>,
    pub away_goals: Option<i32>,
    pub competition: String,
    pub season: Option<i32>,
    pub round: Option<i32>,
    pub stage: Option<String>,
    pub stadium: Option<String>,
    pub home_shots: Option<i32>,
    pub away_shots: Option<i32>,
    pub home_corners: Option<i32>,
    pub away_corners: Option<i32>,
    pub source: Source,
}

impl Match {
    /// True when both scores are known (match was played and recorded).
    pub fn has_score(&self) -> bool {
        self.home_goals.is_some() && self.away_goals.is_some()
    }

    /// De-duplication key identifying a fixture regardless of which CSV it
    /// came from. For Brazilian league/cup competitions a team pair meets at
    /// a given venue at most once per season, so (competition, season, home,
    /// away) is used — robust against sources recording kick-off dates one
    /// day apart. Elsewhere the exact date disambiguates.
    pub fn dedup_key(&self) -> Option<String> {
        const UNIQUE_PER_SEASON: &[&str] = &[
            "Brasileirão Série A",
            "Brasileirão Série B",
            "Brasileirão Série C",
            "Copa do Brasil",
        ];
        if let Some(season) = self.season {
            if UNIQUE_PER_SEASON.contains(&self.competition.as_str()) {
                return Some(format!(
                    "{}|{}|{}|{}",
                    self.competition, season, self.home_key, self.away_key
                ));
            }
        }
        self.date
            .map(|d| format!("{}|{}|{}", d, self.home_key, self.away_key))
    }
}

#[derive(Debug, Clone)]
pub struct Player {
    pub name: String,
    pub name_key: String,
    pub age: Option<i32>,
    pub nationality: String,
    pub overall: Option<i32>,
    pub potential: Option<i32>,
    pub club: String,
    pub club_key: String,
    pub position: String,
    pub jersey: Option<i32>,
    pub height: String,
    pub weight: String,
    pub value: String,
    pub wage: String,
    pub preferred_foot: String,
    /// Named skill ratings (Crossing, Finishing, Dribbling, ...).
    pub attributes: Vec<(String, i32)>,
}

pub struct Data {
    pub matches: Vec<Match>,
    pub players: Vec<Player>,
    /// Per-source loaded row counts, for the data-summary tool.
    pub source_counts: HashMap<&'static str, usize>,
}

// ---------------------------------------------------------------------------
// Text normalization
// ---------------------------------------------------------------------------

/// Fold accented Latin characters to ASCII (São Paulo -> Sao Paulo).
fn fold_char(c: char) -> char {
    match c {
        'á' | 'à' | 'â' | 'ã' | 'ä' | 'Á' | 'À' | 'Â' | 'Ã' | 'Ä' => 'a',
        'é' | 'è' | 'ê' | 'ë' | 'É' | 'È' | 'Ê' | 'Ë' => 'e',
        'í' | 'ì' | 'î' | 'ï' | 'Í' | 'Ì' | 'Î' | 'Ï' => 'i',
        'ó' | 'ò' | 'ô' | 'õ' | 'ö' | 'Ó' | 'Ò' | 'Ô' | 'Õ' | 'Ö' => 'o',
        'ú' | 'ù' | 'û' | 'ü' | 'Ú' | 'Ù' | 'Û' | 'Ü' => 'u',
        'ç' | 'Ç' => 'c',
        'ñ' | 'Ñ' => 'n',
        other => other,
    }
}

/// Lowercase, fold accents, turn punctuation into spaces, collapse whitespace.
pub fn fold(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    for c in s.chars() {
        let c = fold_char(c);
        for lc in c.to_lowercase() {
            if lc.is_alphanumeric() {
                out.push(lc);
            } else {
                out.push(' ');
            }
        }
    }
    out.split_whitespace().collect::<Vec<_>>().join(" ")
}

/// Brazilian state abbreviations (used as team-name suffixes).
const STATES: &[&str] = &[
    "ac", "al", "ap", "am", "ba", "ce", "df", "es", "go", "ma", "mt", "ms",
    "mg", "pa", "pb", "pr", "pe", "pi", "rj", "rn", "rs", "ro", "rr", "sc",
    "sp", "se", "to",
];

/// Base names that are ambiguous without a state suffix — the suffix is kept
/// as part of the key for these clubs.
const AMBIGUOUS_BASES: &[&str] = &["america", "atletico", "botafogo", "nacional"];

/// Remove parenthesized chunks: "Boavista (antigo EC Barreira) - RJ" ->
/// "Boavista  - RJ"; "Nacional (URU)" -> "Nacional".
fn strip_parens(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    let mut depth = 0usize;
    for c in s.chars() {
        match c {
            '(' => depth += 1,
            ')' => depth = depth.saturating_sub(1),
            _ if depth == 0 => out.push(c),
            _ => {}
        }
    }
    out
}

/// Normalize a raw team name into a comparable key.
///
/// "Palmeiras-SP"  -> "palmeiras"
/// "São Paulo"     -> "sao paulo"      (== "Sao Paulo")
/// "Athletico-PR"  -> "atletico pr"    (== "Atlético-PR"; suffix kept,
///                                      base "atletico" is ambiguous)
/// "América - MG"  -> "america mg"
pub fn team_key(raw: &str) -> String {
    let folded = fold(&strip_parens(raw));
    // Old/new spelling of the same club.
    let folded = folded.replace("athletico", "atletico");
    let tokens: Vec<&str> = folded.split(' ').filter(|t| !t.is_empty()).collect();
    if tokens.len() > 1 {
        let last = tokens[tokens.len() - 1];
        if STATES.contains(&last) {
            let base = tokens[..tokens.len() - 1].join(" ");
            if AMBIGUOUS_BASES.iter().any(|b| base == *b) {
                return format!("{} {}", base, last);
            }
            return base;
        }
    }
    tokens.join(" ")
}

/// Display name: original minus parenthetical noise and odd spacing.
pub fn team_display(raw: &str) -> String {
    strip_parens(raw)
        .split_whitespace()
        .collect::<Vec<_>>()
        .join(" ")
        .trim_end_matches(" -")
        .to_string()
}

/// True when `query` (already folded/keyed) refers to team `key`:
/// exact match or contiguous word-subsequence containment in either direction
/// ("corinthians" matches "sport club corinthians paulista").
pub fn team_matches(key: &str, query_key: &str) -> bool {
    if key.is_empty() || query_key.is_empty() {
        return false;
    }
    if key == query_key {
        return true;
    }
    let padded_key = format!(" {} ", key);
    let padded_query = format!(" {} ", query_key);
    padded_key.contains(&padded_query) || padded_query.contains(&padded_key)
}

// ---------------------------------------------------------------------------
// Date parsing
// ---------------------------------------------------------------------------

/// Parse any of the date formats found in the datasets.
pub fn parse_date(raw: &str) -> Option<NaiveDate> {
    let s = raw.trim();
    if s.is_empty() || s == "NA" {
        return None;
    }
    for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y"] {
        if let Ok(dt) = chrono::NaiveDateTime::parse_from_str(s, fmt) {
            return Some(dt.date());
        }
        if let Ok(d) = NaiveDate::parse_from_str(s, fmt) {
            return Some(d);
        }
    }
    None
}

fn parse_goals(raw: &str) -> Option<i32> {
    let s = raw.trim();
    if s.is_empty() || s == "-" || s == "NA" {
        return None;
    }
    // Extended dataset stores goals as floats ("1.0").
    s.parse::<i32>().ok().or_else(|| s.parse::<f64>().ok().map(|f| f as i32))
}

fn parse_int(raw: &str) -> Option<i32> {
    let s = raw.trim();
    if s.is_empty() || s == "NA" {
        return None;
    }
    s.parse::<i32>().ok().or_else(|| s.parse::<f64>().ok().map(|f| f as i32))
}

// ---------------------------------------------------------------------------
// CSV loading
// ---------------------------------------------------------------------------

/// Header-name -> column-index map; strips the UTF-8 BOM csv leaves on the
/// first header of fifa_data.csv.
struct Columns(HashMap<String, usize>);

impl Columns {
    fn new(headers: &csv::StringRecord) -> Self {
        let mut map = HashMap::new();
        for (i, h) in headers.iter().enumerate() {
            map.insert(h.trim_start_matches('\u{feff}').trim().to_string(), i);
        }
        Columns(map)
    }

    fn get<'r>(&self, record: &'r csv::StringRecord, name: &str) -> &'r str {
        self.0
            .get(name)
            .and_then(|&i| record.get(i))
            .unwrap_or("")
    }
}

fn open_reader(path: &Path) -> Result<csv::Reader<std::fs::File>> {
    csv::ReaderBuilder::new()
        .flexible(true)
        .from_path(path)
        .with_context(|| format!("opening {}", path.display()))
}

fn new_match(source: Source, competition: &str) -> Match {
    Match {
        date: None,
        home_team: String::new(),
        away_team: String::new(),
        home_key: String::new(),
        away_key: String::new(),
        home_goals: None,
        away_goals: None,
        competition: competition.to_string(),
        season: None,
        round: None,
        stage: None,
        stadium: None,
        home_shots: None,
        away_shots: None,
        home_corners: None,
        away_corners: None,
        source,
    }
}

fn set_teams(m: &mut Match, home: &str, away: &str) {
    m.home_team = team_display(home);
    m.away_team = team_display(away);
    m.home_key = team_key(home);
    m.away_key = team_key(away);
}

fn load_brasileirao(path: &Path, out: &mut Vec<Match>) -> Result<usize> {
    let mut rdr = open_reader(path)?;
    let cols = Columns::new(rdr.headers()?);
    let mut n = 0;
    for record in rdr.records() {
        let r = record?;
        let mut m = new_match(Source::Brasileirao, "Brasileirão Série A");
        set_teams(&mut m, cols.get(&r, "home_team"), cols.get(&r, "away_team"));
        if m.home_key.is_empty() || m.away_key.is_empty() {
            continue;
        }
        m.date = parse_date(cols.get(&r, "datetime"));
        m.home_goals = parse_goals(cols.get(&r, "home_goal"));
        m.away_goals = parse_goals(cols.get(&r, "away_goal"));
        m.season = parse_int(cols.get(&r, "season"));
        m.round = parse_int(cols.get(&r, "round"));
        out.push(m);
        n += 1;
    }
    Ok(n)
}

fn load_cup(path: &Path, out: &mut Vec<Match>) -> Result<usize> {
    let mut rdr = open_reader(path)?;
    let cols = Columns::new(rdr.headers()?);
    let mut n = 0;
    for record in rdr.records() {
        let r = record?;
        let mut m = new_match(Source::Cup, "Copa do Brasil");
        set_teams(&mut m, cols.get(&r, "home_team"), cols.get(&r, "away_team"));
        if m.home_key.is_empty() || m.away_key.is_empty() {
            continue;
        }
        m.date = parse_date(cols.get(&r, "datetime"));
        m.home_goals = parse_goals(cols.get(&r, "home_goal"));
        m.away_goals = parse_goals(cols.get(&r, "away_goal"));
        m.season = parse_int(cols.get(&r, "season"));
        m.round = parse_int(cols.get(&r, "round"));
        out.push(m);
        n += 1;
    }
    Ok(n)
}

fn load_libertadores(path: &Path, out: &mut Vec<Match>) -> Result<usize> {
    let mut rdr = open_reader(path)?;
    let cols = Columns::new(rdr.headers()?);
    let mut n = 0;
    for record in rdr.records() {
        let r = record?;
        let mut m = new_match(Source::Libertadores, "Copa Libertadores");
        set_teams(&mut m, cols.get(&r, "home_team"), cols.get(&r, "away_team"));
        if m.home_key.is_empty() || m.away_key.is_empty() {
            continue;
        }
        m.date = parse_date(cols.get(&r, "datetime"));
        m.home_goals = parse_goals(cols.get(&r, "home_goal"));
        m.away_goals = parse_goals(cols.get(&r, "away_goal"));
        m.season = parse_int(cols.get(&r, "season"));
        let stage = cols.get(&r, "stage").trim();
        if !stage.is_empty() && stage != "NA" {
            m.stage = Some(stage.to_string());
        }
        out.push(m);
        n += 1;
    }
    Ok(n)
}

fn load_extended(path: &Path, out: &mut Vec<Match>) -> Result<usize> {
    let mut rdr = open_reader(path)?;
    let cols = Columns::new(rdr.headers()?);
    let mut n = 0;
    for record in rdr.records() {
        let r = record?;
        let competition = match cols.get(&r, "tournament").trim() {
            "Serie A" => "Brasileirão Série A",
            "Serie B" => "Brasileirão Série B",
            "Serie C" => "Brasileirão Série C",
            "Copa do Brasil" => "Copa do Brasil",
            other => {
                if other.is_empty() {
                    continue;
                }
                other
            }
        };
        let mut m = new_match(Source::Extended, competition);
        set_teams(&mut m, cols.get(&r, "home"), cols.get(&r, "away"));
        if m.home_key.is_empty() || m.away_key.is_empty() {
            continue;
        }
        m.date = parse_date(cols.get(&r, "date"));
        // Season = calendar year, except league rounds spilling into Jan/Feb
        // (the pandemic-delayed 2020 Serie A/B ended in February 2021), which
        // belong to the previous season. Regular seasons run April-December.
        m.season = m.date.map(|d| {
            use chrono::Datelike;
            if competition.starts_with("Brasileirão") && d.month() <= 2 {
                d.year() - 1
            } else {
                d.year()
            }
        });
        m.home_goals = parse_goals(cols.get(&r, "home_goal"));
        m.away_goals = parse_goals(cols.get(&r, "away_goal"));
        m.home_corners = parse_int(cols.get(&r, "home_corner"));
        m.away_corners = parse_int(cols.get(&r, "away_corner"));
        m.home_shots = parse_int(cols.get(&r, "home_shots"));
        m.away_shots = parse_int(cols.get(&r, "away_shots"));
        out.push(m);
        n += 1;
    }
    Ok(n)
}

fn load_historical(path: &Path, out: &mut Vec<Match>) -> Result<usize> {
    let mut rdr = open_reader(path)?;
    let cols = Columns::new(rdr.headers()?);
    let mut n = 0;
    for record in rdr.records() {
        let r = record?;
        let mut m = new_match(Source::Historical, "Brasileirão Série A");
        set_teams(
            &mut m,
            cols.get(&r, "Equipe_mandante"),
            cols.get(&r, "Equipe_visitante"),
        );
        if m.home_key.is_empty() || m.away_key.is_empty() {
            continue;
        }
        m.date = parse_date(cols.get(&r, "Data"));
        m.season = parse_int(cols.get(&r, "Ano"));
        m.round = parse_int(cols.get(&r, "Rodada"));
        m.home_goals = parse_goals(cols.get(&r, "Gols_mandante"));
        m.away_goals = parse_goals(cols.get(&r, "Gols_visitante"));
        let arena = cols.get(&r, "Arena").trim();
        if !arena.is_empty() {
            m.stadium = Some(arena.to_string());
        }
        out.push(m);
        n += 1;
    }
    Ok(n)
}

/// Skill-rating columns kept from fifa_data.csv.
const PLAYER_ATTRS: &[&str] = &[
    "Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys",
    "Dribbling", "Curve", "FKAccuracy", "LongPassing", "BallControl",
    "Acceleration", "SprintSpeed", "Agility", "Reactions", "Balance",
    "ShotPower", "Jumping", "Stamina", "Strength", "LongShots", "Aggression",
    "Interceptions", "Positioning", "Vision", "Penalties", "Composure",
    "Marking", "StandingTackle", "SlidingTackle", "GKDiving", "GKHandling",
    "GKKicking", "GKPositioning", "GKReflexes",
];

fn load_players(path: &Path, out: &mut Vec<Player>) -> Result<usize> {
    let mut rdr = open_reader(path)?;
    let cols = Columns::new(rdr.headers()?);
    let mut n = 0;
    for record in rdr.records() {
        let r = record?;
        let name = cols.get(&r, "Name").trim().to_string();
        if name.is_empty() {
            continue;
        }
        let club = cols.get(&r, "Club").trim().to_string();
        let mut attributes = Vec::new();
        for attr in PLAYER_ATTRS {
            if let Some(v) = parse_int(cols.get(&r, attr)) {
                attributes.push((attr.to_string(), v));
            }
        }
        out.push(Player {
            name_key: fold(&name),
            age: parse_int(cols.get(&r, "Age")),
            nationality: cols.get(&r, "Nationality").trim().to_string(),
            overall: parse_int(cols.get(&r, "Overall")),
            potential: parse_int(cols.get(&r, "Potential")),
            club_key: team_key(&club),
            club,
            position: cols.get(&r, "Position").trim().to_string(),
            jersey: parse_int(cols.get(&r, "Jersey Number")),
            height: cols.get(&r, "Height").trim().to_string(),
            weight: cols.get(&r, "Weight").trim().to_string(),
            value: cols.get(&r, "Value").trim().to_string(),
            wage: cols.get(&r, "Wage").trim().to_string(),
            preferred_foot: cols.get(&r, "Preferred Foot").trim().to_string(),
            name,
            attributes,
        });
        n += 1;
    }
    Ok(n)
}

impl Data {
    /// Load all six CSV files from `dir` (the data/kaggle directory).
    pub fn load(dir: &Path) -> Result<Data> {
        let mut matches = Vec::new();
        let mut players = Vec::new();
        let mut source_counts = HashMap::new();

        let n = load_brasileirao(&dir.join("Brasileirao_Matches.csv"), &mut matches)?;
        source_counts.insert(Source::Brasileirao.label(), n);

        let n = load_cup(&dir.join("Brazilian_Cup_Matches.csv"), &mut matches)?;
        source_counts.insert(Source::Cup.label(), n);

        let n = load_libertadores(&dir.join("Libertadores_Matches.csv"), &mut matches)?;
        source_counts.insert(Source::Libertadores.label(), n);

        let n = load_extended(&dir.join("BR-Football-Dataset.csv"), &mut matches)?;
        source_counts.insert(Source::Extended.label(), n);

        let n = load_historical(&dir.join("novo_campeonato_brasileiro.csv"), &mut matches)?;
        source_counts.insert(Source::Historical.label(), n);

        let n = load_players(&dir.join("fifa_data.csv"), &mut players)?;
        source_counts.insert("fifa_data.csv", n);

        Ok(Data {
            matches,
            players,
            source_counts,
        })
    }
}
