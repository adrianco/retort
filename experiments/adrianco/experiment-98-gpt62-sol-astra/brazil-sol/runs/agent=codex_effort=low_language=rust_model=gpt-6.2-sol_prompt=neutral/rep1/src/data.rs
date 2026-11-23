use serde::Serialize;
use std::{
    collections::{BTreeMap, HashMap},
    error::Error,
    path::Path,
};

pub const SOURCES: [&str; 6] = [
    "novo_campeonato_brasileiro.csv",
    "Brasileirao_Matches.csv",
    "Brazilian_Cup_Matches.csv",
    "Libertadores_Matches.csv",
    "BR-Football-Dataset.csv",
    "fifa_data.csv",
];

pub fn fold(input: &str) -> String {
    input
        .to_lowercase()
        .chars()
        .map(|c| match c {
            'á' | 'à' | 'ã' | 'â' | 'ä' => 'a',
            'é' | 'è' | 'ê' | 'ë' => 'e',
            'í' | 'ì' | 'î' | 'ï' => 'i',
            'ó' | 'ò' | 'õ' | 'ô' | 'ö' => 'o',
            'ú' | 'ù' | 'û' | 'ü' => 'u',
            'ç' => 'c',
            'ñ' => 'n',
            c if c.is_alphanumeric() => c,
            _ => ' ',
        })
        .collect::<String>()
        .split_whitespace()
        .collect::<Vec<_>>()
        .join(" ")
}

pub fn team_key(name: &str, state: &str) -> String {
    let name = fold(name);
    let (base, uf) = name
        .rsplit_once(' ')
        .filter(|(_, suffix)| {
            [
                "ac", "al", "ap", "am", "ba", "ce", "df", "es", "go", "ma", "mt", "ms", "mg", "pa",
                "pb", "pr", "pe", "pi", "rj", "rn", "rs", "ro", "rr", "sc", "sp", "se", "to",
            ]
            .contains(suffix)
        })
        .unwrap_or((&name, state));
    let uf = uf.to_ascii_lowercase();
    match (base, uf.as_str()) {
        ("atletico", "pr")
        | ("athletico", _)
        | ("athletico paranaense", _)
        | ("atletico paranaense", _)
        | ("club athletico paranaense", _) => "athletico paranaense".into(),
        ("atletico", "go") | ("atletico goianiense", _) => "atletico goianiense".into(),
        ("atletico", "mg" | "") | ("atletico mineiro", _) => "atletico mineiro".into(),
        ("america", "rn") | ("america fc natal", _) => "america rn".into(),
        ("america", "mg" | "") | ("america fc minas gerais", _) => "america mg".into(),
        ("botafogo", "rj" | "") | ("botafogo de futebol e regatas", _) => "botafogo rj".into(),
        ("flamengo", "rj" | "") | ("clube de regatas do flamengo", _) => "flamengo".into(),
        ("vasco" | "vasco da gama" | "club de regatas vasco da gama", _) => "vasco da gama".into(),
        ("corinthians", "sp" | "") | ("sport club corinthians paulista", _) => "corinthians".into(),
        ("sao paulo" | "sao paulo fc" | "sao paulo futebol clube", _) => "sao paulo".into(),
        ("palmeiras" | "sociedade esportiva palmeiras", _) => "palmeiras".into(),
        ("santos" | "santos fc" | "santos futebol clube", _) => "santos".into(),
        ("fluminense" | "fluminense football club", _) => "fluminense".into(),
        ("fortaleza" | "fortaleza fc" | "fortaleza esporte clube", _) => "fortaleza".into(),
        ("sport" | "sport recife" | "sport club do recife", _) => "sport".into(),
        ("bragantino" | "red bull bragantino" | "rb bragantino", _) => "bragantino".into(),
        ("bahia" | "ec bahia" | "esporte clube bahia", _) => "bahia".into(),
        ("juventude" | "ec juventude", _) => "juventude".into(),
        ("santa cruz" | "santa cruz fc", _) => "santa cruz".into(),
        ("goias" | "goias esporte clube", _) => "goias".into(),
        ("ceara" | "ceara sc" | "ceara sporting club", _) => "ceara".into(),
        ("gremio" | "gremio fbpa", _) => "gremio".into(),
        ("boavista sport club antigo esporte clube barreira" | "boavista", _) => "boavista".into(),
        ("atletico" | "america" | "botafogo" | "flamengo" | "corinthians" | "sao raimundo", _)
            if !uf.is_empty() =>
        {
            format!("{base} {uf}")
        }
        _ => base.into(),
    }
}

pub fn competition(name: &str) -> String {
    match fold(name).as_str() {
        "serie a"
        | "brasileirao"
        | "brasileirao serie a"
        | "campeonato brasileiro"
        | "campeonato brasileiro serie a" => "Brasileirão".into(),
        "serie b" | "brasileirao serie b" => "Série B".into(),
        "serie c" | "brasileirao serie c" => "Série C".into(),
        "copa do brasil" | "brazilian cup" => "Copa do Brasil".into(),
        "libertadores" | "copa libertadores" | "copa libertadores da america" => {
            "Copa Libertadores".into()
        }
        _ => name.trim().into(),
    }
}

pub fn date(input: &str) -> Option<String> {
    let input = input.split([' ', 'T']).next()?;
    let parts: Vec<_> = input.split(['-', '/']).collect();
    let [a, b, c] = *parts.as_slice() else {
        return None;
    };
    let (y, m, d) = if input.contains('/') {
        (c, b, a)
    } else {
        (a, b, c)
    };
    let (y, m, d) = (
        y.parse::<u32>().ok()?,
        m.parse::<u32>().ok()?,
        d.parse::<u32>().ok()?,
    );
    let days = match m {
        1 | 3 | 5 | 7 | 8 | 10 | 12 => 31,
        4 | 6 | 9 | 11 => 30,
        2 if y % 4 == 0 && (y % 100 != 0 || y % 400 == 0) => 29,
        2 => 28,
        _ => return None,
    };
    (y > 0 && y <= 9999 && d > 0 && d <= days).then(|| format!("{y:04}-{m:02}-{d:02}"))
}

fn next_day(day: &str) -> String {
    let year: u32 = day[..4].parse().unwrap();
    let month: u32 = day[5..7].parse().unwrap();
    let d: u32 = day[8..].parse().unwrap();
    date(&format!("{year:04}-{month:02}-{:02}", d + 1))
        .or_else(|| date(&format!("{year:04}-{:02}-01", month + 1)))
        .unwrap_or_else(|| format!("{:04}-01-01", year + 1))
}

fn number(input: &str) -> Option<u32> {
    input.strip_suffix(".0").unwrap_or(input).parse().ok()
}

#[derive(Clone, Serialize)]
pub struct Match {
    pub date: Option<String>,
    pub time: Option<String>,
    pub competition: String,
    pub season: Option<u32>,
    pub round: Option<String>,
    pub stage: Option<String>,
    pub home_team: String,
    pub away_team: String,
    #[serde(skip)]
    pub home: String,
    #[serde(skip)]
    pub away: String,
    pub home_state: Option<String>,
    pub away_state: Option<String>,
    pub home_goal: Option<u32>,
    pub away_goal: Option<u32>,
    pub stadium: Option<String>,
    pub source_id: Option<String>,
    pub sources: Vec<&'static str>,
    #[serde(skip_serializing_if = "BTreeMap::is_empty")]
    pub extra: BTreeMap<String, String>,
}

impl Match {
    pub fn score(&self) -> Option<(u32, u32)> {
        Some((self.home_goal?, self.away_goal?))
    }

    fn merge(&mut self, other: &Self) {
        // Keep the preferred source's score as a pair.
        if self.score().is_none() && other.score().is_some() {
            self.home_goal = other.home_goal;
            self.away_goal = other.away_goal;
            if self.date != other.date && other.date.is_some() {
                self.date = other.date.clone();
                self.time = other.time.clone();
            }
        }
        if self.date == other.date {
            self.time = self.time.take().or_else(|| other.time.clone());
        }
        self.round = self.round.take().or_else(|| other.round.clone());
        self.stage = self.stage.take().or_else(|| other.stage.clone());
        self.stadium = self.stadium.take().or_else(|| other.stadium.clone());
        self.source_id = self.source_id.take().or_else(|| other.source_id.clone());
        self.home_state = self.home_state.take().or_else(|| other.home_state.clone());
        self.away_state = self.away_state.take().or_else(|| other.away_state.clone());
        self.extra.extend(other.extra.clone());
        if !self.sources.contains(&other.sources[0]) {
            self.sources.push(other.sources[0]);
        }
    }
}

#[derive(Serialize)]
pub struct Player {
    pub id: u32,
    pub name: String,
    pub nationality: String,
    pub club: Option<String>,
    pub position: Option<String>,
    pub age: Option<u32>,
    pub overall: Option<u32>,
    pub potential: Option<u32>,
    pub jersey_number: Option<u32>,
    pub height: Option<String>,
    pub weight: Option<String>,
    pub attributes: BTreeMap<String, String>,
    #[serde(skip)]
    pub name_key: String,
    #[serde(skip)]
    pub club_key: String,
    #[serde(skip)]
    pub nationality_key: String,
}

pub struct Graph {
    pub fixtures: Vec<Match>,
    pub raw: Vec<Match>,
    pub players: Vec<Player>,
    pub teams: BTreeMap<String, String>,
    pub counts: BTreeMap<&'static str, usize>,
}

impl Graph {
    pub fn load(dir: &Path) -> Result<Self, Box<dyn Error>> {
        let mut graph = Self {
            fixtures: Vec::new(),
            raw: Vec::new(),
            players: Vec::new(),
            teams: BTreeMap::new(),
            counts: BTreeMap::new(),
        };
        for (source, file) in SOURCES.iter().enumerate() {
            let path = dir.join(file);
            let mut reader =
                csv::Reader::from_path(&path).map_err(|e| format!("{}: {e}", path.display()))?;
            let headers = reader.headers()?.clone();
            let columns: HashMap<_, _> = headers.iter().enumerate().map(|(i, s)| (s, i)).collect();
            let mut count = 0;
            for row in reader.records() {
                let row = row.map_err(|e| format!("{}: {e}", path.display()))?;
                count += 1;
                let get = |key: &str| {
                    columns
                        .get(key)
                        .and_then(|&i| row.get(i))
                        .unwrap_or("")
                        .trim()
                };
                let optional = |key| match get(key) {
                    "" | "NA" | "-" => None,
                    value => Some(value.to_string()),
                };
                if source == 5 {
                    let name = get("Name");
                    let club = optional("Club");
                    let nationality = get("Nationality");
                    graph.players.push(Player {
                        id: number(get("ID")).ok_or_else(|| {
                            format!("{file}: invalid player ID on row {}", count + 1)
                        })?,
                        name: name.into(),
                        nationality: nationality.into(),
                        name_key: fold(name),
                        club_key: team_key(get("Club"), ""),
                        nationality_key: fold(nationality),
                        club,
                        position: optional("Position"),
                        age: number(get("Age")),
                        overall: number(get("Overall")),
                        potential: number(get("Potential")),
                        jersey_number: number(get("Jersey Number")),
                        height: optional("Height"),
                        weight: optional("Weight"),
                        attributes: headers
                            .iter()
                            .skip_while(|&h| h != "Preferred Foot")
                            .filter_map(|h| optional(h).map(|v| (h.to_string(), v)))
                            .collect(),
                    });
                    continue;
                }
                let (home, away, hg, ag, day) = match source {
                    0 => (
                        "Equipe_mandante",
                        "Equipe_visitante",
                        "Gols_mandante",
                        "Gols_visitante",
                        "Data",
                    ),
                    4 => ("home", "away", "home_goal", "away_goal", "date"),
                    _ => (
                        "home_team",
                        "away_team",
                        "home_goal",
                        "away_goal",
                        "datetime",
                    ),
                };
                let date = date(get(day));
                let season = match source {
                    0 => number(get("Ano")),
                    4 => date.as_ref().and_then(|d| number(&d[..4])),
                    _ => number(get("season")),
                };
                let comp = match source {
                    0 | 1 => "Brasileirão".into(),
                    2 => "Copa do Brasil".into(),
                    3 => "Copa Libertadores".into(),
                    _ => competition(get("tournament")),
                };
                let home_state = optional(if source == 0 {
                    "Mandante_UF"
                } else {
                    "home_team_state"
                });
                let away_state = optional(if source == 0 {
                    "Visitante_UF"
                } else {
                    "away_team_state"
                });
                graph.raw.push(Match {
                    date,
                    time: optional("time")
                        .or_else(|| get(day).split_once(' ').map(|(_, t)| t.into())),
                    competition: comp,
                    season,
                    round: optional("round").or_else(|| optional("Rodada")),
                    stage: optional("stage"),
                    home_team: get(home).into(),
                    away_team: get(away).into(),
                    home: team_key(get(home), home_state.as_deref().unwrap_or("")),
                    away: team_key(get(away), away_state.as_deref().unwrap_or("")),
                    home_state,
                    away_state,
                    home_goal: number(get(hg)),
                    away_goal: number(get(ag)),
                    stadium: optional("Arena"),
                    source_id: optional("ID"),
                    sources: vec![file],
                    extra: [
                        "home_corner",
                        "away_corner",
                        "home_attack",
                        "away_attack",
                        "home_shots",
                        "away_shots",
                        "ht_diff",
                        "at_diff",
                        "ht_result",
                        "at_result",
                        "total_corners",
                        "Vencedor",
                        "OBS",
                    ]
                    .into_iter()
                    .filter_map(|k| optional(k).map(|v| (k.into(), v)))
                    .collect(),
                });
            }
            graph.counts.insert(file, count);
        }

        graph.build_fixtures();
        graph
            .players
            .sort_by_key(|p| (std::cmp::Reverse(p.overall), p.id));
        Ok(graph)
    }

    fn build_fixtures(&mut self) {
        // In the numbered cup feed, the final round depends on the tournament format.
        for m in &mut self.raw {
            if m.sources[0] == SOURCES[2] {
                let final_round = match m.season {
                    Some(2012) => "6",
                    Some(2016) => "7",
                    _ => "8",
                };
                if m.round.as_deref() == Some(final_round) {
                    m.stage = Some("final".into());
                }
            }
        }
        // The extended feed records the last two fixtures of these cups as reciprocal final legs.
        for year in 2021..=2023 {
            let mut cup: Vec<_> = self
                .raw
                .iter_mut()
                .filter(|m| {
                    m.sources[0] == SOURCES[4]
                        && m.competition == "Copa do Brasil"
                        && m.season == Some(year)
                })
                .collect();
            cup.sort_by_key(|m| std::cmp::Reverse(m.date.clone()));
            if let [last, first, ..] = cup.as_mut_slice()
                && last.home == first.away
                && last.away == first.home
                && last.date != first.date
            {
                last.stage = Some("final".into());
                first.stage = Some("final".into());
            }
        }
        let dedicated_league_seasons: std::collections::HashSet<_> = self
            .raw
            .iter()
            .filter(|m| m.competition == "Brasileirão" && m.sources[0] != SOURCES[4])
            .filter_map(|m| m.season)
            .collect();
        let mut pairs: HashMap<_, Vec<usize>> = HashMap::new();
        for m in &self.raw {
            for (key, name) in [(&m.home, &m.home_team), (&m.away, &m.away_team)] {
                self.teams
                    .entry(key.clone())
                    .or_insert_with(|| name.clone());
            }
            let indices = pairs.entry((&m.competition, &m.home, &m.away)).or_default();
            let from_extended = m.sources[0] == SOURCES[4];
            let league = m.competition == "Brasileirão";
            let candidate = |i: usize| !self.fixtures[i].sources.contains(&m.sources[0]);
            // Try dates first so a match played in the next calendar year retains its season.
            let duplicate = indices
                .iter()
                .copied()
                .filter(|&i| candidate(i))
                .find(|&i| {
                    self.fixtures[i]
                        .date
                        .as_ref()
                        .zip(m.date.as_ref())
                        .is_some_and(|(a, b)| a == b || next_day(a) == *b || next_day(b) == *a)
                })
                .or_else(|| {
                    indices
                        .iter()
                        .copied()
                        .filter(|&i| candidate(i))
                        .find(|&i| {
                            let prior = &self.fixtures[i];
                            league
                                && m.season == prior.season
                                && (from_extended || m.round == prior.round)
                        })
                });
            // The dedicated league files enumerate all scheduled fixtures for these seasons.
            // An unmatched row in the extended feed remains accessible through its source.
            if duplicate.is_none()
                && from_extended
                && league
                && m.season
                    .is_some_and(|year| dedicated_league_seasons.contains(&year))
            {
                continue;
            }
            match duplicate {
                Some(i) => self.fixtures[i].merge(m),
                None => {
                    indices.push(self.fixtures.len());
                    self.fixtures.push(m.clone());
                }
            }
        }
        self.fixtures
            .sort_by(|a, b| b.date.cmp(&a.date).then_with(|| b.time.cmp(&a.time)));
        self.raw
            .sort_by(|a, b| b.date.cmp(&a.date).then_with(|| b.time.cmp(&a.time)));
    }
}
