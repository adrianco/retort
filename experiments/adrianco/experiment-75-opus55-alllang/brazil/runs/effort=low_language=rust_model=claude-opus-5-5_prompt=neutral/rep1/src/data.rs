//! Data loading and normalization for the Brazilian soccer datasets.

use std::collections::{HashMap, HashSet};
use std::path::Path;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum Competition {
    Brasileirao,
    SerieB,
    SerieC,
    CopaDoBrasil,
    Libertadores,
}

impl Competition {
    pub fn name(self) -> &'static str {
        match self {
            Competition::Brasileirao => "Brasileirão",
            Competition::SerieB => "Série B",
            Competition::SerieC => "Série C",
            Competition::CopaDoBrasil => "Copa do Brasil",
            Competition::Libertadores => "Libertadores",
        }
    }

    /// Parse a user-supplied competition name.
    pub fn parse(s: &str) -> Option<Competition> {
        let f = fold(s);
        if f.contains("liberta") {
            Some(Competition::Libertadores)
        } else if f.contains("copa") || f.contains("cup") {
            Some(Competition::CopaDoBrasil)
        } else if f.contains("serie b") {
            Some(Competition::SerieB)
        } else if f.contains("serie c") {
            Some(Competition::SerieC)
        } else if f.contains("brasileir") || f.contains("serie a") || f.contains("league") {
            Some(Competition::Brasileirao)
        } else {
            None
        }
    }
}

#[derive(Debug, Clone)]
pub struct Match {
    /// ISO date YYYY-MM-DD
    pub date: String,
    pub season: i32,
    pub competition: Competition,
    /// Round / stage description
    pub round: String,
    pub home: String,
    pub away: String,
    pub home_key: String,
    pub away_key: String,
    pub home_goals: u32,
    pub away_goals: u32,
    pub arena: Option<String>,
    pub source: &'static str,
    /// Extended stats (corners, shots, attacks) home/away when available.
    pub extra: Option<[f64; 6]>,
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
    pub value: String,
    pub skills: Vec<(String, u32)>,
}

pub struct Dataset {
    pub matches: Vec<Match>,
    pub players: Vec<Player>,
    pub display: HashMap<String, String>,
    /// Number of rows loaded from each file.
    pub file_counts: Vec<(&'static str, usize)>,
}

/// Lowercase, strip accents, turn punctuation into spaces, collapse whitespace.
pub fn fold(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    for c in s.chars() {
        let m = match c {
            'á' | 'à' | 'â' | 'ã' | 'ä' | 'Á' | 'À' | 'Â' | 'Ã' | 'Ä' => 'a',
            'é' | 'è' | 'ê' | 'ë' | 'É' | 'È' | 'Ê' | 'Ë' => 'e',
            'í' | 'ì' | 'î' | 'ï' | 'Í' | 'Ì' | 'Î' | 'Ï' => 'i',
            'ó' | 'ò' | 'ô' | 'õ' | 'ö' | 'Ó' | 'Ò' | 'Ô' | 'Õ' | 'Ö' => 'o',
            'ú' | 'ù' | 'û' | 'ü' | 'Ú' | 'Ù' | 'Û' | 'Ü' => 'u',
            'ç' | 'Ç' => 'c',
            'ñ' | 'Ñ' => 'n',
            c if c.is_alphanumeric() => c.to_ascii_lowercase(),
            _ => ' ',
        };
        out.push(m);
    }
    out.split_whitespace().collect::<Vec<_>>().join(" ")
}

const UFS: &[&str] = &[
    "ac", "al", "ap", "am", "ba", "ce", "df", "es", "go", "ma", "mt", "ms", "mg", "pa", "pb",
    "pr", "pe", "pi", "rj", "rn", "rs", "ro", "rr", "sc", "sp", "se", "to",
];

/// Canonical key for a team name, so that "Palmeiras-SP", "Palmeiras" and
/// "Sociedade Esportiva Palmeiras" all map to the same key.
pub fn team_key(name: &str) -> String {
    let f = fold(name);
    let mut toks: Vec<&str> = f.split(' ').filter(|t| !t.is_empty()).collect();
    let mut uf = None;
    if toks.len() > 1 && UFS.contains(toks.last().unwrap()) {
        uf = toks.pop();
    }
    let base = toks.join(" ");
    let with_uf = |b: &str| match uf {
        Some(u) => format!("{b} {u}"),
        None => b.to_string(),
    };
    let key: String = match (base.as_str(), uf) {
        ("atletico", Some("mg")) | ("atletico mineiro", _) | ("clube atletico mineiro", _) => {
            "atletico mineiro".into()
        }
        ("atletico", Some("go")) | ("atletico goianiense", _) => "atletico goianiense".into(),
        ("atletico", Some("pr")) | ("athletico", _) | ("atletico paranaense", _)
        | ("athletico paranaense", _) | ("club athletico paranaense", _) => {
            "athletico paranaense".into()
        }
        ("america", Some("mg")) | ("america mineiro", _) | ("america fc minas gerais", _) => {
            "america mineiro".into()
        }
        ("america", Some("rn")) | ("america fc natal", _) => "america rn".into(),
        ("vasco", _) | ("vasco da gama", _) | ("cr vasco da gama", _) => "vasco".into(),
        ("red bull bragantino", _) | ("bragantino", _) | ("rb bragantino", _) => {
            "bragantino".into()
        }
        ("botafogo", None) | ("botafogo", Some("rj")) => "botafogo".into(),
        ("botafogo", _) => with_uf("botafogo"),
        ("flamengo", None) | ("flamengo", Some("rj")) | ("cr flamengo", _) => "flamengo".into(),
        ("flamengo", _) => with_uf("flamengo"),
        ("sport club do recife", _) | ("sport recife", _) => "sport".into(),
        ("ceara sporting club", _) => "ceara".into(),
        ("sport club corinthians paulista", _) => "corinthians".into(),
        ("sociedade esportiva palmeiras", _) => "palmeiras".into(),
        ("sao paulo fc", _) | ("sao paulo futebol clube", _) => "sao paulo".into(),
        ("gremio fbpa", _) | ("gremio foot ball porto alegrense", _) => "gremio".into(),
        ("santos fc", _) => "santos".into(),
        ("ec vitoria", _) => "vitoria".into(),
        _ => {
            // Drop generic club prefixes/suffixes such as "EC Bahia" or "Fortaleza FC".
            let mut t: Vec<&str> = base.split(' ').collect();
            while t.len() > 1 && ["ec", "fc", "sc", "se", "cr", "ac"].contains(&t[0]) {
                t.remove(0);
            }
            while t.len() > 1 && ["fc", "ec", "sc"].contains(t.last().unwrap()) {
                t.pop();
            }
            let b = t.join(" ");
            if b != base { return team_key(&with_uf(&b)); }
            base
        }
    };
    key
}

/// Preferred display names for keys that are produced by aliasing.
const DISPLAY_OVERRIDES: &[(&str, &str)] = &[
    ("atletico mineiro", "Atlético Mineiro"),
    ("athletico paranaense", "Athletico Paranaense"),
    ("atletico goianiense", "Atlético Goianiense"),
    ("america mineiro", "América Mineiro"),
    ("america rn", "América-RN"),
    ("botafogo", "Botafogo"),
    ("flamengo", "Flamengo"),
    ("vasco", "Vasco da Gama"),
    ("bragantino", "Red Bull Bragantino"),
    ("sport", "Sport Recife"),
];

fn strip_suffix(name: &str) -> String {
    let t = name.trim();
    for sep in [" - ", "-", " "] {
        if let Some(i) = t.rfind(sep) {
            let suf = &t[i + sep.len()..];
            if suf.len() == 2 && UFS.contains(&suf.to_ascii_lowercase().as_str()) {
                return t[..i].trim().to_string();
            }
        }
    }
    t.to_string()
}

/// Normalize a date to ISO YYYY-MM-DD from ISO, ISO+time, or DD/MM/YYYY.
pub fn normalize_date(s: &str) -> String {
    let s = s.trim();
    let d = s.split(' ').next().unwrap_or("");
    if d.contains('/') {
        let p: Vec<&str> = d.split('/').collect();
        if p.len() == 3 {
            return format!("{}-{:0>2}-{:0>2}", p[2], p[1], p[0]);
        }
    }
    d.to_string()
}

fn num(s: &str) -> Option<f64> {
    s.trim().trim_matches('"').parse::<f64>().ok()
}

fn reader(path: &Path) -> Result<csv::Reader<std::fs::File>, String> {
    csv::ReaderBuilder::new()
        .flexible(true)
        .from_path(path)
        .map_err(|e| format!("{}: {e}", path.display()))
}

fn col(headers: &csv::StringRecord, name: &str) -> Result<usize, String> {
    headers
        .iter()
        .position(|h| h.trim_start_matches('\u{feff}') == name)
        .ok_or_else(|| format!("missing column {name}"))
}

impl Dataset {
    pub fn load(dir: impl AsRef<Path>) -> Result<Dataset, String> {
        let dir = dir.as_ref();
        let mut matches = Vec::new();
        let mut counts = Vec::new();
        let mut display_votes: HashMap<String, HashMap<String, usize>> = HashMap::new();

        let mut push = |m: Match, votes: &mut HashMap<String, HashMap<String, usize>>| {
            for (k, n) in [(&m.home_key, &m.home), (&m.away_key, &m.away)] {
                let short = strip_suffix(n);
                let label = if team_key(&short) == *k { short } else { n.clone() };
                *votes.entry(k.clone()).or_default().entry(label).or_default() += 1;
            }
            matches.push(m);
        };
        let mk = |date: String, season: i32, comp, round: String, home: &str, away: &str,
                  hg: f64, ag: f64, source| Match {
            date,
            season,
            competition: comp,
            round,
            home: home.trim().to_string(),
            away: away.trim().to_string(),
            home_key: team_key(home),
            away_key: team_key(away),
            home_goals: hg as u32,
            away_goals: ag as u32,
            arena: None,
            source,
            extra: None,
        };

        // 1. Brasileirao_Matches.csv
        let src = "Brasileirao_Matches.csv";
        let mut r = reader(&dir.join(src))?;
        let h = r.headers().map_err(|e| e.to_string())?.clone();
        let (dt, ht, at, hg, ag, se, ro) = (col(&h, "datetime")?, col(&h, "home_team")?,
            col(&h, "away_team")?, col(&h, "home_goal")?, col(&h, "away_goal")?,
            col(&h, "season")?, col(&h, "round")?);
        let mut n = 0;
        for rec in r.records().flatten() {
            let (Some(g1), Some(g2), Some(s)) = (num(&rec[hg]), num(&rec[ag]), num(&rec[se])) else { continue };
            push(mk(normalize_date(&rec[dt]), s as i32, Competition::Brasileirao,
                format!("Round {}", &rec[ro]), &rec[ht], &rec[at], g1, g2, src), &mut display_votes);
            n += 1;
        }
        counts.push((src, n));

        // 2. Brazilian_Cup_Matches.csv
        let src = "Brazilian_Cup_Matches.csv";
        let mut r = reader(&dir.join(src))?;
        let h = r.headers().map_err(|e| e.to_string())?.clone();
        let (ro, dt, ht, at, hg, ag, se) = (col(&h, "round")?, col(&h, "datetime")?,
            col(&h, "home_team")?, col(&h, "away_team")?, col(&h, "home_goal")?,
            col(&h, "away_goal")?, col(&h, "season")?);
        let mut n = 0;
        let mut cup: Vec<Match> = Vec::new();
        for rec in r.records().flatten() {
            let (Some(g1), Some(g2), Some(s)) = (num(&rec[hg]), num(&rec[ag]), num(&rec[se])) else { continue };
            cup.push(mk(normalize_date(&rec[dt]), s as i32, Competition::CopaDoBrasil,
                format!("Round {}", &rec[ro]), &rec[ht], &rec[at], g1, g2, src));
            n += 1;
        }
        // The highest round number in each season is the final.
        let mut max_round: HashMap<i32, u32> = HashMap::new();
        for m in &cup {
            let rn: u32 = m.round.trim_start_matches("Round ").parse().unwrap_or(0);
            let e = max_round.entry(m.season).or_default();
            *e = (*e).max(rn);
        }
        let mut round_count: HashMap<(i32, u32), usize> = HashMap::new();
        for m in &cup {
            let rn: u32 = m.round.trim_start_matches("Round ").parse().unwrap_or(0);
            *round_count.entry((m.season, rn)).or_default() += 1;
        }
        for mut m in cup {
            let rn: u32 = m.round.trim_start_matches("Round ").parse().unwrap_or(0);
            if rn == max_round[&m.season] && round_count[&(m.season, rn)] <= 2 {
                m.round = "Final".into();
            }
            push(m, &mut display_votes);
        }
        counts.push((src, n));

        // 3. Libertadores_Matches.csv
        let src = "Libertadores_Matches.csv";
        let mut r = reader(&dir.join(src))?;
        let h = r.headers().map_err(|e| e.to_string())?.clone();
        let (dt, ht, at, hg, ag, se, st) = (col(&h, "datetime")?, col(&h, "home_team")?,
            col(&h, "away_team")?, col(&h, "home_goal")?, col(&h, "away_goal")?,
            col(&h, "season")?, col(&h, "stage")?);
        let mut n = 0;
        for rec in r.records().flatten() {
            let (Some(g1), Some(g2), Some(s)) = (num(&rec[hg]), num(&rec[ag]), num(&rec[se])) else { continue };
            push(mk(normalize_date(&rec[dt]), s as i32, Competition::Libertadores,
                rec[st].to_string(), &rec[ht], &rec[at], g1, g2, src), &mut display_votes);
            n += 1;
        }
        counts.push((src, n));

        // 4. BR-Football-Dataset.csv
        let src = "BR-Football-Dataset.csv";
        let mut r = reader(&dir.join(src))?;
        let h = r.headers().map_err(|e| e.to_string())?.clone();
        let (tn, ht, at, hg, ag, da) = (col(&h, "tournament")?, col(&h, "home")?, col(&h, "away")?,
            col(&h, "home_goal")?, col(&h, "away_goal")?, col(&h, "date")?);
        let extra_cols = [col(&h, "home_corner")?, col(&h, "away_corner")?, col(&h, "home_attack")?,
            col(&h, "away_attack")?, col(&h, "home_shots")?, col(&h, "away_shots")?];
        let mut n = 0;
        for rec in r.records().flatten() {
            let (Some(g1), Some(g2)) = (num(&rec[hg]), num(&rec[ag])) else { continue };
            let Some(comp) = Competition::parse(&rec[tn]) else { continue };
            let date = normalize_date(&rec[da]);
            let season = date.get(..4).and_then(|y| y.parse().ok()).unwrap_or(0);
            let mut m = mk(date, season, comp, String::new(), &rec[ht], &rec[at], g1, g2, src);
            let mut ex = [0.0; 6];
            for (i, c) in extra_cols.iter().enumerate() {
                ex[i] = num(&rec[*c]).unwrap_or(0.0);
            }
            m.extra = Some(ex);
            push(m, &mut display_votes);
            n += 1;
        }
        counts.push((src, n));

        // 5. novo_campeonato_brasileiro.csv
        let src = "novo_campeonato_brasileiro.csv";
        let mut r = reader(&dir.join(src))?;
        let h = r.headers().map_err(|e| e.to_string())?.clone();
        let (da, an, ro, ht, at, hg, ag, ar) = (col(&h, "Data")?, col(&h, "Ano")?, col(&h, "Rodada")?,
            col(&h, "Equipe_mandante")?, col(&h, "Equipe_visitante")?, col(&h, "Gols_mandante")?,
            col(&h, "Gols_visitante")?, col(&h, "Arena")?);
        let mut n = 0;
        for rec in r.records().flatten() {
            let (Some(g1), Some(g2), Some(s)) = (num(&rec[hg]), num(&rec[ag]), num(&rec[an])) else { continue };
            let mut m = mk(normalize_date(&rec[da]), s as i32, Competition::Brasileirao,
                format!("Round {}", &rec[ro]), &rec[ht], &rec[at], g1, g2, src);
            if !rec[ar].trim().is_empty() {
                m.arena = Some(rec[ar].trim().to_string());
            }
            push(m, &mut display_votes);
            n += 1;
        }
        counts.push((src, n));

        // Prefer accented display names (e.g. "São Paulo" over "Sao Paulo").
        let mut display: HashMap<String, String> = display_votes
            .into_iter()
            .map(|(k, v)| {
                let best = v
                    .into_iter()
                    .max_by_key(|(name, c)| (!name.is_ascii() as usize, !name.contains('(') as usize, *c, name.clone()))
                    .map(|(n, _)| n)
                    .unwrap_or_else(|| k.clone());
                (k, best)
            })
            .collect();
        for (k, v) in DISPLAY_OVERRIDES {
            if display.contains_key(*k) {
                display.insert(k.to_string(), v.to_string());
            }
        }

        // 6. fifa_data.csv
        let src = "fifa_data.csv";
        let mut r = reader(&dir.join(src))?;
        let h = r.headers().map_err(|e| e.to_string())?.clone();
        let c = |n: &str| col(&h, n);
        let (id, nm, age, nat, ov, po, cl, pos, jn, hgt, wgt, val) = (c("ID")?, c("Name")?, c("Age")?,
            c("Nationality")?, c("Overall")?, c("Potential")?, c("Club")?, c("Position")?,
            c("Jersey Number")?, c("Height")?, c("Weight")?, c("Value")?);
        let skill_names = ["Crossing", "Finishing", "ShortPassing", "Dribbling", "BallControl",
            "Acceleration", "SprintSpeed", "Stamina", "Strength", "StandingTackle"];
        let skill_cols: Vec<(String, usize)> = skill_names
            .iter()
            .filter_map(|s| c(s).ok().map(|i| (s.to_string(), i)))
            .collect();
        let mut players = Vec::new();
        for rec in r.records().flatten() {
            let g = |i: usize| rec.get(i).unwrap_or("").trim().to_string();
            players.push(Player {
                id: num(&g(id)).unwrap_or(0.0) as u64,
                name: g(nm),
                age: num(&g(age)).unwrap_or(0.0) as u32,
                nationality: g(nat),
                overall: num(&g(ov)).unwrap_or(0.0) as u32,
                potential: num(&g(po)).unwrap_or(0.0) as u32,
                club_key: team_key(&g(cl)),
                club: g(cl),
                position: g(pos),
                jersey: g(jn),
                height: g(hgt),
                weight: g(wgt),
                value: g(val),
                skills: skill_cols
                    .iter()
                    .filter_map(|(n, i)| num(&g(*i)).map(|v| (n.clone(), v as u32)))
                    .collect(),
            });
        }
        counts.push((src, players.len()));

        Ok(Dataset { matches, players, display, file_counts: counts })
    }

    pub fn display_name(&self, key: &str) -> String {
        self.display.get(key).cloned().unwrap_or_else(|| key.to_string())
    }

    /// Set of all team keys appearing in Brazilian domestic competitions.
    pub fn brazilian_team_keys(&self) -> HashSet<&str> {
        self.matches
            .iter()
            .filter(|m| m.competition != Competition::Libertadores)
            .flat_map(|m| [m.home_key.as_str(), m.away_key.as_str()])
            .collect()
    }

    /// Resolve a user team query to a canonical key known in the data.
    pub fn resolve_team(&self, q: &str) -> Option<String> {
        let k = team_key(q);
        if self.display.contains_key(&k) {
            return Some(k);
        }
        // Fallback: unique-ish prefix/contains match, preferring the most frequent team.
        let mut freq: HashMap<&str, usize> = HashMap::new();
        for m in &self.matches {
            for key in [&m.home_key, &m.away_key] {
                if key.starts_with(&k) || key.contains(&k) {
                    *freq.entry(key.as_str()).or_default() += 1;
                }
            }
        }
        freq.into_iter().max_by_key(|(k, c)| (*c, k.to_string())).map(|(k, _)| k.to_string())
    }
}
