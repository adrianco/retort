//! Dataset loading and the in-memory `Database`.
//!
//! Context: this module reads the six Kaggle CSV files described in `TASK.md`
//! and normalizes every row into the unified [`Match`] / [`Player`] model.
//! Because several files overlap (e.g. historical Brasileirão appears both in
//! `novo_campeonato_brasileiro.csv` and `Brasileirao_Matches.csv`), matches are
//! de-duplicated on competition/season/date/teams/score after loading; when a
//! duplicate carries extra detail (extended stats, round, stadium) that detail
//! is merged into the surviving record.

use std::collections::HashMap;
use std::path::Path;

use crate::csvparse;
use crate::model::{Match, MatchStats, Player};
use crate::normalize;

/// The six dataset file names, in load order. Order matters for de-duplication:
/// richer historical files are loaded first so their round/stadium metadata is
/// preferred, and `BR-Football-Dataset.csv` is loaded last so its extended
/// statistics merge into already-known matches.
pub const DATASET_FILES: &[&str] = &[
    "novo_campeonato_brasileiro.csv",
    "Brasileirao_Matches.csv",
    "Libertadores_Matches.csv",
    "Brazilian_Cup_Matches.csv",
    "BR-Football-Dataset.csv",
    "fifa_data.csv",
];

/// In-memory knowledge graph over all loaded datasets.
pub struct Database {
    pub matches: Vec<Match>,
    pub players: Vec<Player>,
    /// `match_key -> best human-readable club name`.
    pub team_names: HashMap<String, String>,
}

/// Read a field by (case-insensitive) column name, empty string when absent.
fn field<'a>(row: &'a [String], idx: &HashMap<String, usize>, name: &str) -> &'a str {
    idx.get(name)
        .and_then(|&i| row.get(i))
        .map(|s| s.trim())
        .unwrap_or("")
}

/// Parse an integer, tolerating float-formatted values such as `"2.0"`.
fn parse_i32(s: &str) -> Option<i32> {
    let s = s.trim();
    if s.is_empty() {
        return None;
    }
    if let Ok(v) = s.parse::<i32>() {
        return Some(v);
    }
    s.parse::<f64>().ok().map(|f| f.round() as i32)
}

/// Parse a goal count, defaulting to 0 for blank/garbage cells.
fn parse_goal(s: &str) -> i32 {
    parse_i32(s).unwrap_or(0)
}

/// Normalize a date cell to ISO `YYYY-MM-DD`.
///
/// Handles ISO datetimes (`2012-05-19 18:30:00`), bare ISO dates and the
/// Brazilian `DD/MM/YYYY` format used by `novo_campeonato_brasileiro.csv`.
pub fn parse_date(s: &str) -> String {
    let s = s.trim();
    if s.is_empty() {
        return String::new();
    }
    if s.contains('/') {
        let parts: Vec<&str> = s.split('/').collect();
        if parts.len() == 3 {
            let (d, m, y) = (parts[0].trim(), parts[1].trim(), parts[2].trim());
            if !y.is_empty() && !m.is_empty() && !d.is_empty() {
                return format!("{:0>4}-{:0>2}-{:0>2}", y, m, d);
            }
        }
    }
    // ISO form: keep the leading YYYY-MM-DD.
    s.chars().take(10).collect()
}

/// Extract the four-digit year from an ISO date string.
fn year_of(date: &str) -> Option<i32> {
    if date.len() >= 4 {
        date[..4].parse::<i32>().ok()
    } else {
        None
    }
}

/// Map a `BR-Football-Dataset.csv` tournament label to a canonical competition.
fn br_football_competition(t: &str) -> String {
    match t.trim() {
        "Serie A" => "Brasileirão Série A",
        "Serie B" => "Brasileirão Série B",
        "Serie C" => "Brasileirão Série C",
        "Copa do Brasil" => "Copa do Brasil",
        other => other,
    }
    .to_string()
}

impl Database {
    /// Load every dataset found in `dir`. Missing files are skipped with a
    /// warning on stderr rather than aborting, so the server still starts.
    pub fn load(dir: &str) -> Database {
        let mut raw_matches: Vec<Match> = Vec::new();
        let mut players: Vec<Player> = Vec::new();

        for fname in DATASET_FILES {
            let path = Path::new(dir).join(fname);
            let bytes = match std::fs::read(&path) {
                Ok(b) => b,
                Err(e) => {
                    eprintln!("[data] warning: could not read {}: {e}", path.display());
                    continue;
                }
            };
            let content = String::from_utf8_lossy(&bytes);
            let rows = csvparse::parse(&content);
            if rows.is_empty() {
                continue;
            }
            let header = csvparse::header_index(&rows[0]);
            let body = &rows[1..];

            match *fname {
                "novo_campeonato_brasileiro.csv" => {
                    load_novo(body, &header, &mut raw_matches, fname)
                }
                "Brasileirao_Matches.csv" => {
                    load_brasileirao(body, &header, &mut raw_matches, fname)
                }
                "Libertadores_Matches.csv" => {
                    load_libertadores(body, &header, &mut raw_matches, fname)
                }
                "Brazilian_Cup_Matches.csv" => {
                    load_cup(body, &header, &mut raw_matches, fname)
                }
                "BR-Football-Dataset.csv" => {
                    load_br_football(body, &header, &mut raw_matches, fname)
                }
                "fifa_data.csv" => load_fifa(body, &header, &mut players),
                _ => {}
            }
        }

        let matches = dedup_matches(raw_matches);

        // Build the canonical club-name lookup.
        let mut team_names: HashMap<String, String> = HashMap::new();
        for m in &matches {
            team_names
                .entry(m.home_key.clone())
                .or_insert_with(|| m.home_team.clone());
            team_names
                .entry(m.away_key.clone())
                .or_insert_with(|| m.away_team.clone());
        }

        Database {
            matches,
            players,
            team_names,
        }
    }

    /// Sorted list of distinct competitions present in the data.
    pub fn competitions(&self) -> Vec<String> {
        let mut set: Vec<String> = Vec::new();
        for m in &self.matches {
            if !set.contains(&m.competition) {
                set.push(m.competition.clone());
            }
        }
        set.sort();
        set
    }

    /// Sorted list of distinct seasons for a competition (or all competitions
    /// when `competition` is `None`).
    pub fn seasons(&self, competition: Option<&str>) -> Vec<i32> {
        let mut set: Vec<i32> = Vec::new();
        for m in &self.matches {
            if let Some(c) = competition {
                if !m.competition.eq_ignore_ascii_case(c) {
                    continue;
                }
            }
            if !set.contains(&m.season) {
                set.push(m.season);
            }
        }
        set.sort();
        set
    }

    /// Best human-readable name for a club match-key.
    pub fn display_name(&self, key: &str) -> String {
        self.team_names
            .get(key)
            .cloned()
            .unwrap_or_else(|| key.to_string())
    }

    /// Resolve a free-text club query to its `(canonical_key, display_name)`.
    ///
    /// Prefers an exact canonical-key match, then the most specific (shortest)
    /// key whose club plausibly matches the query.
    pub fn resolve_team(&self, query: &str) -> Option<(String, String)> {
        let qk = normalize::team_key(query);
        if !qk.is_empty() {
            if let Some(name) = self.team_names.get(&qk) {
                return Some((qk, name.clone()));
            }
        }
        let mut candidates: Vec<&String> = self
            .team_names
            .keys()
            .filter(|k| normalize::key_matches(k, query))
            .collect();
        candidates.sort_by_key(|k| k.len());
        candidates
            .first()
            .map(|k| ((*k).clone(), self.team_names[*k].clone()))
    }
}

/// Resolve a raw club name to `(display_name, canonical_key)`.
fn club(raw: &str) -> (String, String) {
    let (key, display) = normalize::resolve(raw);
    (display, key)
}

fn load_novo(
    body: &[Vec<String>],
    h: &HashMap<String, usize>,
    out: &mut Vec<Match>,
    src: &str,
) {
    for row in body {
        let home_raw = field(row, h, "equipe_mandante");
        let away_raw = field(row, h, "equipe_visitante");
        if home_raw.is_empty() || away_raw.is_empty() {
            continue;
        }
        let (home_team, home_key) = club(home_raw);
        let (away_team, away_key) = club(away_raw);
        let season = parse_i32(field(row, h, "ano")).unwrap_or(0);
        let stadium = field(row, h, "arena");
        out.push(Match {
            competition: "Brasileirão Série A".to_string(),
            season,
            round: Some(field(row, h, "rodada").to_string()),
            stage: None,
            date: parse_date(field(row, h, "data")),
            home_team,
            away_team,
            home_key,
            away_key,
            home_goal: parse_goal(field(row, h, "gols_mandante")),
            away_goal: parse_goal(field(row, h, "gols_visitante")),
            stadium: if stadium.is_empty() {
                None
            } else {
                Some(stadium.to_string())
            },
            source: src.to_string(),
            stats: None,
        });
    }
}

fn load_brasileirao(
    body: &[Vec<String>],
    h: &HashMap<String, usize>,
    out: &mut Vec<Match>,
    src: &str,
) {
    for row in body {
        let home_raw = field(row, h, "home_team");
        let away_raw = field(row, h, "away_team");
        if home_raw.is_empty() || away_raw.is_empty() {
            continue;
        }
        let (home_team, home_key) = club(home_raw);
        let (away_team, away_key) = club(away_raw);
        let date = parse_date(field(row, h, "datetime"));
        let season = parse_i32(field(row, h, "season"))
            .or_else(|| year_of(&date))
            .unwrap_or(0);
        out.push(Match {
            competition: "Brasileirão Série A".to_string(),
            season,
            round: Some(field(row, h, "round").to_string()),
            stage: None,
            date,
            home_team,
            away_team,
            home_key,
            away_key,
            home_goal: parse_goal(field(row, h, "home_goal")),
            away_goal: parse_goal(field(row, h, "away_goal")),
            stadium: None,
            source: src.to_string(),
            stats: None,
        });
    }
}

fn load_libertadores(
    body: &[Vec<String>],
    h: &HashMap<String, usize>,
    out: &mut Vec<Match>,
    src: &str,
) {
    for row in body {
        let home_raw = field(row, h, "home_team");
        let away_raw = field(row, h, "away_team");
        if home_raw.is_empty() || away_raw.is_empty() {
            continue;
        }
        let (home_team, home_key) = club(home_raw);
        let (away_team, away_key) = club(away_raw);
        let date = parse_date(field(row, h, "datetime"));
        let season = parse_i32(field(row, h, "season"))
            .or_else(|| year_of(&date))
            .unwrap_or(0);
        let stage = field(row, h, "stage");
        out.push(Match {
            competition: "Copa Libertadores".to_string(),
            season,
            round: None,
            stage: if stage.is_empty() {
                None
            } else {
                Some(stage.to_string())
            },
            date,
            home_team,
            away_team,
            home_key,
            away_key,
            home_goal: parse_goal(field(row, h, "home_goal")),
            away_goal: parse_goal(field(row, h, "away_goal")),
            stadium: None,
            source: src.to_string(),
            stats: None,
        });
    }
}

fn load_cup(
    body: &[Vec<String>],
    h: &HashMap<String, usize>,
    out: &mut Vec<Match>,
    src: &str,
) {
    for row in body {
        let home_raw = field(row, h, "home_team");
        let away_raw = field(row, h, "away_team");
        if home_raw.is_empty() || away_raw.is_empty() {
            continue;
        }
        let (home_team, home_key) = club(home_raw);
        let (away_team, away_key) = club(away_raw);
        let date = parse_date(field(row, h, "datetime"));
        let season = parse_i32(field(row, h, "season"))
            .or_else(|| year_of(&date))
            .unwrap_or(0);
        out.push(Match {
            competition: "Copa do Brasil".to_string(),
            season,
            round: Some(field(row, h, "round").to_string()),
            stage: None,
            date,
            home_team,
            away_team,
            home_key,
            away_key,
            home_goal: parse_goal(field(row, h, "home_goal")),
            away_goal: parse_goal(field(row, h, "away_goal")),
            stadium: None,
            source: src.to_string(),
            stats: None,
        });
    }
}

fn load_br_football(
    body: &[Vec<String>],
    h: &HashMap<String, usize>,
    out: &mut Vec<Match>,
    src: &str,
) {
    for row in body {
        let home_raw = field(row, h, "home");
        let away_raw = field(row, h, "away");
        if home_raw.is_empty() || away_raw.is_empty() {
            continue;
        }
        let (home_team, home_key) = club(home_raw);
        let (away_team, away_key) = club(away_raw);
        let date = parse_date(field(row, h, "date"));
        let season = year_of(&date).unwrap_or(0);
        let stats = MatchStats {
            home_corner: parse_goal(field(row, h, "home_corner")),
            away_corner: parse_goal(field(row, h, "away_corner")),
            home_shots: parse_goal(field(row, h, "home_shots")),
            away_shots: parse_goal(field(row, h, "away_shots")),
            home_attack: parse_goal(field(row, h, "home_attack")),
            away_attack: parse_goal(field(row, h, "away_attack")),
        };
        out.push(Match {
            competition: br_football_competition(field(row, h, "tournament")),
            season,
            round: None,
            stage: None,
            date,
            home_team,
            away_team,
            home_key,
            away_key,
            home_goal: parse_goal(field(row, h, "home_goal")),
            away_goal: parse_goal(field(row, h, "away_goal")),
            stadium: None,
            source: src.to_string(),
            stats: Some(stats),
        });
    }
}

fn load_fifa(body: &[Vec<String>], h: &HashMap<String, usize>, out: &mut Vec<Player>) {
    for row in body {
        let name = field(row, h, "name");
        if name.is_empty() {
            continue;
        }
        out.push(Player {
            id: field(row, h, "id").to_string(),
            name: name.to_string(),
            age: parse_i32(field(row, h, "age")),
            nationality: field(row, h, "nationality").to_string(),
            overall: parse_i32(field(row, h, "overall")),
            potential: parse_i32(field(row, h, "potential")),
            club: field(row, h, "club").to_string(),
            position: field(row, h, "position").to_string(),
            jersey: field(row, h, "jersey number").to_string(),
            height: field(row, h, "height").to_string(),
            weight: field(row, h, "weight").to_string(),
        });
    }
}

/// Collapse matches that appear in more than one dataset into single records,
/// merging round/stage/stadium/extended-stats detail from the duplicates.
///
/// The de-duplication key is `competition | season | home | away` and
/// deliberately excludes the date and score. In a round-robin league each
/// ordered pair of clubs meets exactly once per season, and a two-legged cup
/// tie swaps the home side — so the ordered pair is unique within a
/// competition+season. Excluding the date is essential because
/// `BR-Football-Dataset.csv` records kick-off in UTC, shifting late games to
/// the following calendar day relative to the other (local-time) datasets.
fn dedup_matches(raw: Vec<Match>) -> Vec<Match> {
    let mut deduped: Vec<Match> = Vec::with_capacity(raw.len());
    let mut seen: HashMap<String, usize> = HashMap::new();
    for m in raw {
        let key = format!(
            "{}|{}|{}|{}",
            m.competition, m.season, m.home_key, m.away_key
        );
        if let Some(&idx) = seen.get(&key) {
            let entry = &mut deduped[idx];
            if entry.date.is_empty() {
                entry.date = m.date;
            }
            if entry.round.as_deref().unwrap_or("").is_empty() {
                entry.round = m.round;
            }
            if entry.stage.is_none() {
                entry.stage = m.stage;
            }
            if entry.stadium.is_none() {
                entry.stadium = m.stadium;
            }
            if entry.stats.is_none() {
                entry.stats = m.stats;
            }
        } else {
            seen.insert(key, deduped.len());
            deduped.push(m);
        }
    }
    deduped
}
