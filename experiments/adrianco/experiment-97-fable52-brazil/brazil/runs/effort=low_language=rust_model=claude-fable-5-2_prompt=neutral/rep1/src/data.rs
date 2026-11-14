//! Data model and CSV loading for the six Kaggle datasets.
use crate::normalize::{day_number, display_candidate, parse_date, team_key};
use std::collections::{BTreeMap, HashMap};
use std::path::Path;

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

    /// Parse a free-text competition name ("Brasileirão", "serie b", "Brazilian Cup"...).
    pub fn parse(s: &str) -> Option<Competition> {
        let f = crate::normalize::fold(s);
        if f.contains("libertadores") {
            Some(Competition::Libertadores)
        } else if f.contains("copa") || f.contains("cup") {
            Some(Competition::CopaDoBrasil)
        } else if f.contains("serie b") {
            Some(Competition::SerieB)
        } else if f.contains("serie c") {
            Some(Competition::SerieC)
        } else if f.contains("brasileir") || f.contains("serie a") || f.contains("league") {
            Some(Competition::SerieA)
        } else {
            None
        }
    }
}

/// Source file of a match, in order of preference when the same match appears twice.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum Source {
    BrasileiraoMatches,
    NovoCampeonato,
    CupMatches,
    LibertadoresMatches,
    BrFootball,
}

impl Source {
    pub fn file(self) -> &'static str {
        match self {
            Source::BrasileiraoMatches => "Brasileirao_Matches.csv",
            Source::NovoCampeonato => "novo_campeonato_brasileiro.csv",
            Source::CupMatches => "Brazilian_Cup_Matches.csv",
            Source::LibertadoresMatches => "Libertadores_Matches.csv",
            Source::BrFootball => "BR-Football-Dataset.csv",
        }
    }
}

/// Extended statistics (only in BR-Football-Dataset.csv): (home, away) pairs.
#[derive(Debug, Clone, Default)]
pub struct Extended {
    pub corners: Option<(u32, u32)>,
    pub attacks: Option<(u32, u32)>,
    pub shots: Option<(u32, u32)>,
}

#[derive(Debug, Clone)]
pub struct Match {
    /// ISO date (YYYY-MM-DD).
    pub date: String,
    pub season: i32,
    pub competition: Competition,
    /// Round or stage label ("Round 12", "Final", "group stage"); may be empty.
    pub stage: String,
    pub home_key: String,
    pub away_key: String,
    pub home_goals: u32,
    pub away_goals: u32,
    pub arena: Option<String>,
    pub extended: Option<Extended>,
    pub source: Source,
    /// True when the same match was already loaded from a preferred source.
    pub duplicate: bool,
}

#[derive(Debug, Clone)]
pub struct Player {
    pub id: u64,
    pub name: String,
    pub age: u32,
    pub nationality: String,
    pub overall: u32,
    pub potential: u32,
    pub club: String,
    pub club_key: String,
    pub position: String,
    pub jersey: String,
    pub height: String,
    pub weight: String,
    pub foot: String,
    pub value: String,
    pub wage: String,
    /// Skill ratings (Crossing, Finishing, ...), in file order.
    pub skills: Vec<(String, u32)>,
}

pub struct Db {
    pub matches: Vec<Match>,
    pub players: Vec<Player>,
    /// Canonical team key -> display name.
    pub display: HashMap<String, String>,
    /// Rows loaded per source file (matches) plus "fifa_data.csv".
    pub loaded: BTreeMap<&'static str, usize>,
}

struct Table {
    idx: HashMap<String, usize>,
    rows: Vec<csv::StringRecord>,
}

impl Table {
    fn read(path: &Path) -> Result<Table, String> {
        let mut rdr = csv::ReaderBuilder::new()
            .flexible(true)
            .from_path(path)
            .map_err(|e| format!("cannot open {}: {e}", path.display()))?;
        let idx = rdr
            .headers()
            .map_err(|e| format!("{}: {e}", path.display()))?
            .iter()
            .enumerate()
            .map(|(i, h)| (h.trim_start_matches('\u{feff}').trim().to_string(), i))
            .collect();
        let mut rows = Vec::new();
        for r in rdr.records() {
            rows.push(r.map_err(|e| format!("{}: {e}", path.display()))?);
        }
        Ok(Table { idx, rows })
    }

    fn get<'a>(&self, row: &'a csv::StringRecord, col: &str) -> &'a str {
        self.idx
            .get(col)
            .and_then(|i| row.get(*i))
            .map(str::trim)
            .unwrap_or("")
    }
}

fn num(s: &str) -> Option<u32> {
    let v = s.trim().parse::<f64>().ok()?;
    (v >= 0.0 && v.is_finite()).then_some(v as u32)
}

fn pair(a: &str, b: &str) -> Option<(u32, u32)> {
    Some((num(a)?, num(b)?))
}

struct Builder {
    matches: Vec<Match>,
    names: HashMap<String, HashMap<String, usize>>,
    seen: HashMap<(Competition, String, String), Vec<(i64, Source, i32, usize)>>,
}

impl Builder {
    fn team(&mut self, raw: &str, state: Option<&str>) -> String {
        let key = team_key(raw, state);
        *self
            .names
            .entry(key.clone())
            .or_default()
            .entry(display_candidate(raw, &key))
            .or_default() += 1;
        key
    }

    /// Add a match, flagging it as a duplicate when a preferred source already has the
    /// same fixture within three days (or, for leagues, in the same season) (kick-off dates differ by time zone between files).
    /// A duplicate inherits the season of the original, which is authoritative.
    fn push(&mut self, mut m: Match) {
        let day = day_number(&m.date);
        let k = (m.competition, m.home_key.clone(), m.away_key.clone());
        let e = self.seen.entry(k).or_default();
        // In a league each home/away pairing happens once per season, so a season match is enough.
        let league = !matches!(m.competition, Competition::CopaDoBrasil | Competition::Libertadores);
        if let Some((_, _, season, idx)) = e
            .iter()
            .find(|(d, s, y, _)| *s != m.source && ((d - day).abs() <= 3 || (league && *y == m.season)))
        {
            m.duplicate = true;
            m.season = *season;
            // Keep the extended statistics queryable on the surviving record.
            let original = &mut self.matches[*idx];
            if original.extended.is_none() && original.home_goals == m.home_goals && original.away_goals == m.away_goals {
                original.extended = m.extended.clone();
            }
        } else {
            e.push((day, m.source, m.season, self.matches.len()));
        }
        self.matches.push(m);
    }
}

impl Db {
    /// Load all six CSV files from `dir`.
    pub fn load(dir: &Path) -> Result<Db, String> {
        let mut b = Builder {
            matches: Vec::new(),
            names: HashMap::new(),
            seen: HashMap::new(),
        };
        let mut loaded = BTreeMap::new();
        let base = |date: String, season, competition, source| Match {
            date,
            season,
            competition,
            stage: String::new(),
            home_key: String::new(),
            away_key: String::new(),
            home_goals: 0,
            away_goals: 0,
            arena: None,
            extended: None,
            source,
            duplicate: false,
        };

        // 1. Brasileirão Serie A 2012+
        let src = Source::BrasileiraoMatches;
        let t = Table::read(&dir.join(src.file()))?;
        for r in &t.rows {
            let (Some(date), Some((hg, ag)), Some(season)) = (
                parse_date(t.get(r, "datetime")),
                pair(t.get(r, "home_goal"), t.get(r, "away_goal")),
                num(t.get(r, "season")),
            ) else {
                continue;
            };
            let mut m = base(date, season as i32, Competition::SerieA, src);
            m.home_key = b.team(t.get(r, "home_team"), Some(t.get(r, "home_team_state")));
            m.away_key = b.team(t.get(r, "away_team"), Some(t.get(r, "away_team_state")));
            (m.home_goals, m.away_goals) = (hg, ag);
            m.stage = format!("Round {}", t.get(r, "round"));
            b.push(m);
        }
        loaded.insert(src.file(), b.matches.len());

        // 2. Historical Brasileirão 2003-2019
        let before = b.matches.len();
        let src = Source::NovoCampeonato;
        let t = Table::read(&dir.join(src.file()))?;
        for r in &t.rows {
            let (Some(date), Some((hg, ag))) = (
                parse_date(t.get(r, "Data")),
                pair(t.get(r, "Gols_mandante"), t.get(r, "Gols_visitante")),
            ) else {
                continue;
            };
            let season = num(t.get(r, "Ano")).map(|y| y as i32).unwrap_or_else(|| year(&date));
            // The UF columns of this file are unreliable (e.g. Vitória listed as ES), and
            // ambiguous names already carry their state ("América-MG"), so they are not used.
            let mut m = base(date, season, Competition::SerieA, src);
            m.home_key = b.team(t.get(r, "Equipe_mandante"), None);
            m.away_key = b.team(t.get(r, "Equipe_visitante"), None);
            (m.home_goals, m.away_goals) = (hg, ag);
            m.stage = format!("Round {}", t.get(r, "Rodada"));
            let arena = t.get(r, "Arena");
            m.arena = (!arena.is_empty()).then(|| arena.to_string());
            b.push(m);
        }
        loaded.insert(src.file(), b.matches.len() - before);

        // 3. Copa do Brasil
        let before = b.matches.len();
        let src = Source::CupMatches;
        let t = Table::read(&dir.join(src.file()))?;
        let mut cup_rounds: HashMap<(i32, u32), usize> = HashMap::new();
        let mut cup_idx: Vec<(usize, u32)> = Vec::new();
        for r in &t.rows {
            let (Some(date), Some((hg, ag)), Some(season)) = (
                parse_date(t.get(r, "datetime")),
                pair(t.get(r, "home_goal"), t.get(r, "away_goal")),
                num(t.get(r, "season")),
            ) else {
                continue;
            };
            let mut m = base(date, season as i32, Competition::CopaDoBrasil, src);
            m.home_key = b.team(t.get(r, "home_team"), None);
            m.away_key = b.team(t.get(r, "away_team"), None);
            (m.home_goals, m.away_goals) = (hg, ag);
            m.stage = format!("Round {}", t.get(r, "round"));
            if let Some(rn) = num(t.get(r, "round")) {
                *cup_rounds.entry((season as i32, rn)).or_default() += 1;
                cup_idx.push((b.matches.len(), rn));
            }
            b.push(m);
        }
        // Name the closing rounds of each cup season from their size (two-legged ties).
        let mut labels: HashMap<(i32, u32), &str> = HashMap::new();
        let mut by_season: BTreeMap<i32, Vec<(u32, usize)>> = BTreeMap::new();
        for ((s, rn), c) in &cup_rounds {
            by_season.entry(*s).or_default().push((*rn, *c));
        }
        for (s, mut rounds) in by_season {
            rounds.sort_by(|a, b| b.0.cmp(&a.0));
            let stages = [(2, "Final"), (4, "Semifinals"), (8, "Quarterfinals"), (16, "Round of 16")];
            for ((rn, count), (max, label)) in rounds.iter().zip(stages) {
                if *count > max {
                    break;
                }
                labels.insert((s, *rn), label);
            }
        }
        for (i, rn) in cup_idx {
            if let Some(l) = labels.get(&(b.matches[i].season, rn)) {
                b.matches[i].stage = l.to_string();
            }
        }
        loaded.insert(src.file(), b.matches.len() - before);

        // 4. Copa Libertadores
        let before = b.matches.len();
        let src = Source::LibertadoresMatches;
        let t = Table::read(&dir.join(src.file()))?;
        for r in &t.rows {
            let (Some(date), Some((hg, ag)), Some(season)) = (
                parse_date(t.get(r, "datetime")),
                pair(t.get(r, "home_goal"), t.get(r, "away_goal")),
                num(t.get(r, "season")),
            ) else {
                continue;
            };
            let mut m = base(date, season as i32, Competition::Libertadores, src);
            m.home_key = b.team(t.get(r, "home_team"), None);
            m.away_key = b.team(t.get(r, "away_team"), None);
            (m.home_goals, m.away_goals) = (hg, ag);
            m.stage = t.get(r, "stage").to_string();
            b.push(m);
        }
        loaded.insert(src.file(), b.matches.len() - before);

        // 5. Extended statistics (Serie A/B/C + Copa do Brasil)
        let before = b.matches.len();
        let src = Source::BrFootball;
        let t = Table::read(&dir.join(src.file()))?;
        for r in &t.rows {
            let (Some(date), Some((hg, ag)), Some(comp)) = (
                parse_date(t.get(r, "date")),
                pair(t.get(r, "home_goal"), t.get(r, "away_goal")),
                Competition::parse(t.get(r, "tournament")),
            ) else {
                continue;
            };
            // No season column: use the year, except that league matches played in
            // January/February close the previous season (the 2020 season ended in 2021).
            let league = comp != Competition::CopaDoBrasil;
            let season = year(&date) - (league && &date[5..7] <= "02") as i32;
            let mut m = base(date, season, comp, src);
            m.home_key = b.team(t.get(r, "home"), None);
            m.away_key = b.team(t.get(r, "away"), None);
            (m.home_goals, m.away_goals) = (hg, ag);
            m.extended = Some(Extended {
                corners: pair(t.get(r, "home_corner"), t.get(r, "away_corner")),
                attacks: pair(t.get(r, "home_attack"), t.get(r, "away_attack")),
                shots: pair(t.get(r, "home_shots"), t.get(r, "away_shots")),
            });
            b.push(m);
        }
        loaded.insert(src.file(), b.matches.len() - before);

        // 6. FIFA players
        let t = Table::read(&dir.join("fifa_data.csv"))?;
        let skill_start = t.idx.get("Crossing").copied();
        let skill_end = t.idx.get("GKReflexes").copied();
        let mut skill_cols: Vec<(&String, usize)> = match (skill_start, skill_end) {
            (Some(a), Some(z)) => t.idx.iter().filter(|(_, i)| **i >= a && **i <= z).map(|(n, i)| (n, *i)).collect(),
            _ => Vec::new(),
        };
        skill_cols.sort_by_key(|(_, i)| *i);
        let mut players = Vec::new();
        for r in &t.rows {
            let name = t.get(r, "Name");
            let Some(id) = t.get(r, "ID").parse::<u64>().ok() else { continue };
            if name.is_empty() {
                continue;
            }
            let club = t.get(r, "Club").to_string();
            players.push(Player {
                id,
                name: name.to_string(),
                age: num(t.get(r, "Age")).unwrap_or(0),
                nationality: t.get(r, "Nationality").to_string(),
                overall: num(t.get(r, "Overall")).unwrap_or(0),
                potential: num(t.get(r, "Potential")).unwrap_or(0),
                club_key: if club.is_empty() { String::new() } else { team_key(&club, None) },
                club,
                position: t.get(r, "Position").to_string(),
                jersey: t.get(r, "Jersey Number").to_string(),
                height: t.get(r, "Height").to_string(),
                weight: t.get(r, "Weight").to_string(),
                foot: t.get(r, "Preferred Foot").to_string(),
                value: t.get(r, "Value").to_string(),
                wage: t.get(r, "Wage").to_string(),
                skills: skill_cols
                    .iter()
                    .filter_map(|(n, i)| Some(((*n).clone(), num(r.get(*i)?)?)))
                    .collect(),
            });
        }
        loaded.insert("fifa_data.csv", players.len());

        let display = b
            .names
            .into_iter()
            .map(|(k, cands)| {
                // Most frequent spelling, but prefer an accented spelling when it is
                // also common (files differ on "Gremio" vs "Grêmio").
                let top = cands.values().copied().max().unwrap_or(0);
                let best = cands
                    .into_iter()
                    .filter(|(_, n)| *n * 5 >= top)
                    .max_by(|a, b| (!a.0.is_ascii(), a.1, &b.0).cmp(&(!b.0.is_ascii(), b.1, &a.0)))
                    .map(|c| c.0)
                    .unwrap_or_else(|| k.clone());
                (k, best)
            })
            .collect();
        Ok(Db { matches: b.matches, players, display, loaded })
    }

    pub fn name<'a>(&'a self, key: &'a str) -> &'a str {
        self.display.get(key).map(String::as_str).unwrap_or(key)
    }
}

fn year(iso: &str) -> i32 {
    iso[..4].parse().unwrap_or(0)
}
