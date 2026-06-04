// =============================================================================
// data — record models and CSV loaders
// -----------------------------------------------------------------------------
// Context:
//   Six heterogeneous CSV files (see TASK.md) are unified into two in-memory
//   record types: `Match` and `Player`. Each loader knows the column layout of
//   one file and maps it onto the shared model, applying the normalization from
//   the `normalize` module (team keys, dates, integer-from-float parsing).
//
//   Because several files overlap (e.g. the historical Brasileirão file and the
//   extended-statistics file both contain Série A games), `load_matches` builds
//   a de-duplication set keyed by (competition, season, home_key, away_key,
//   date) so the unified dataset does not double-count the same fixture.
// =============================================================================

use crate::normalize::{display_team, parse_date, parse_int, team_key};
use std::collections::{HashMap, HashSet};
use std::path::Path;

/// A single match/fixture, unified across all source files.
#[derive(Debug, Clone)]
pub struct Match {
    pub competition: String,
    pub season: i64,
    pub date_iso: String,
    pub date_key: i64,
    pub home_raw: String,
    pub away_raw: String,
    pub home: String, // display name
    pub away: String, // display name
    pub home_key: String,
    pub away_key: String,
    pub home_goal: Option<i64>,
    pub away_goal: Option<i64>,
    pub stage: Option<String>, // round number or tournament stage
    pub source: String,        // originating file name
}

impl Match {
    /// True when both scores are present.
    pub fn has_score(&self) -> bool {
        self.home_goal.is_some() && self.away_goal.is_some()
    }

    /// 1 if `key` (home or away) won this match, -1 if it lost, 0 for a draw or
    /// when the team did not play / score is missing.
    pub fn result_for(&self, key: &str) -> i64 {
        let (hg, ag) = match (self.home_goal, self.away_goal) {
            (Some(h), Some(a)) => (h, a),
            _ => return 0,
        };
        if self.home_key == key {
            (hg - ag).signum()
        } else if self.away_key == key {
            (ag - hg).signum()
        } else {
            0
        }
    }

    /// `"Home 2-1 Away"` style scoreline.
    pub fn scoreline(&self) -> String {
        match (self.home_goal, self.away_goal) {
            (Some(h), Some(a)) => format!("{} {}-{} {}", self.home, h, a, self.away),
            _ => format!("{} vs {} (score n/a)", self.home, self.away),
        }
    }
}

/// A FIFA-database player.
#[derive(Debug, Clone)]
pub struct Player {
    pub name: String,
    pub age: Option<i64>,
    pub nationality: String,
    pub overall: Option<i64>,
    pub potential: Option<i64>,
    pub club: String,
    pub club_key: String,
    pub position: String,
    pub jersey: String,
    pub height: String,
    pub weight: String,
    pub value: String,
    pub wage: String,
    pub preferred_foot: String,
}

// ----------------------------------------------------------------------------
// CSV helpers
// ----------------------------------------------------------------------------

/// Build a header-name -> column-index map, stripping a leading UTF-8 BOM and
/// surrounding whitespace from each header.
fn header_map(headers: &csv::StringRecord) -> HashMap<String, usize> {
    let mut m = HashMap::new();
    for (i, h) in headers.iter().enumerate() {
        let key = h.trim_start_matches('\u{feff}').trim().to_string();
        m.entry(key).or_insert(i);
    }
    m
}

/// Fetch a column value by header name, returning "" when absent.
fn field<'a>(rec: &'a csv::StringRecord, map: &HashMap<String, usize>, name: &str) -> &'a str {
    map.get(name).and_then(|&i| rec.get(i)).unwrap_or("").trim()
}

fn reader(path: &Path) -> csv::Result<csv::Reader<std::fs::File>> {
    csv::ReaderBuilder::new()
        .flexible(true)
        .has_headers(true)
        .from_path(path)
}

fn make_match(
    competition: &str,
    season: i64,
    date_raw: &str,
    home_raw: &str,
    away_raw: &str,
    home_goal: Option<i64>,
    away_goal: Option<i64>,
    stage: Option<String>,
    source: &str,
) -> Match {
    let (date_iso, mut date_key) = parse_date(date_raw);
    // Fall back to season ordering when a date is missing so sorts stay stable.
    if date_key == 0 && season > 0 {
        date_key = season * 10000;
    }
    Match {
        competition: competition.to_string(),
        season,
        date_iso,
        date_key,
        home: display_team(home_raw),
        away: display_team(away_raw),
        home_key: team_key(home_raw),
        away_key: team_key(away_raw),
        home_raw: home_raw.to_string(),
        away_raw: away_raw.to_string(),
        home_goal,
        away_goal,
        stage,
        source: source.to_string(),
    }
}

// ----------------------------------------------------------------------------
// Per-file loaders. Each pushes onto `out`; the caller de-duplicates.
// ----------------------------------------------------------------------------

fn load_brasileirao(path: &Path, out: &mut Vec<Match>) -> csv::Result<()> {
    let mut rdr = reader(path)?;
    let map = header_map(rdr.headers()?);
    for rec in rdr.records() {
        let rec = rec?;
        let season = parse_int(field(&rec, &map, "season")).unwrap_or(0);
        let round = field(&rec, &map, "round");
        out.push(make_match(
            "Brasileirão Série A",
            season,
            field(&rec, &map, "datetime"),
            field(&rec, &map, "home_team"),
            field(&rec, &map, "away_team"),
            parse_int(field(&rec, &map, "home_goal")),
            parse_int(field(&rec, &map, "away_goal")),
            if round.is_empty() {
                None
            } else {
                Some(format!("Round {}", round))
            },
            "Brasileirao_Matches.csv",
        ));
    }
    Ok(())
}

fn load_cup(path: &Path, out: &mut Vec<Match>) -> csv::Result<()> {
    let mut rdr = reader(path)?;
    let map = header_map(rdr.headers()?);
    for rec in rdr.records() {
        let rec = rec?;
        let season = parse_int(field(&rec, &map, "season")).unwrap_or(0);
        let round = field(&rec, &map, "round");
        out.push(make_match(
            "Copa do Brasil",
            season,
            field(&rec, &map, "datetime"),
            field(&rec, &map, "home_team"),
            field(&rec, &map, "away_team"),
            parse_int(field(&rec, &map, "home_goal")),
            parse_int(field(&rec, &map, "away_goal")),
            if round.is_empty() {
                None
            } else {
                Some(format!("Round {}", round))
            },
            "Brazilian_Cup_Matches.csv",
        ));
    }
    Ok(())
}

fn load_libertadores(path: &Path, out: &mut Vec<Match>) -> csv::Result<()> {
    let mut rdr = reader(path)?;
    let map = header_map(rdr.headers()?);
    for rec in rdr.records() {
        let rec = rec?;
        let season = parse_int(field(&rec, &map, "season")).unwrap_or(0);
        let stage = field(&rec, &map, "stage");
        out.push(make_match(
            "Copa Libertadores",
            season,
            field(&rec, &map, "datetime"),
            field(&rec, &map, "home_team"),
            field(&rec, &map, "away_team"),
            parse_int(field(&rec, &map, "home_goal")),
            parse_int(field(&rec, &map, "away_goal")),
            if stage.is_empty() {
                None
            } else {
                Some(stage.to_string())
            },
            "Libertadores_Matches.csv",
        ));
    }
    Ok(())
}

fn load_novo(path: &Path, out: &mut Vec<Match>) -> csv::Result<()> {
    let mut rdr = reader(path)?;
    let map = header_map(rdr.headers()?);
    for rec in rdr.records() {
        let rec = rec?;
        let season = parse_int(field(&rec, &map, "Ano")).unwrap_or(0);
        let rodada = field(&rec, &map, "Rodada");
        out.push(make_match(
            "Brasileirão Série A",
            season,
            field(&rec, &map, "Data"),
            field(&rec, &map, "Equipe_mandante"),
            field(&rec, &map, "Equipe_visitante"),
            parse_int(field(&rec, &map, "Gols_mandante")),
            parse_int(field(&rec, &map, "Gols_visitante")),
            if rodada.is_empty() {
                None
            } else {
                Some(format!("Round {}", rodada))
            },
            "novo_campeonato_brasileiro.csv",
        ));
    }
    Ok(())
}

/// The extended-statistics file. `tournament` maps onto canonical competition
/// names; the season is derived from the match date.
fn load_br_football(path: &Path, out: &mut Vec<Match>) -> csv::Result<()> {
    let mut rdr = reader(path)?;
    let map = header_map(rdr.headers()?);
    for rec in rdr.records() {
        let rec = rec?;
        let tournament = field(&rec, &map, "tournament");
        let competition = match tournament {
            "Serie A" => "Brasileirão Série A",
            "Serie B" => "Brasileirão Série B",
            "Serie C" => "Brasileirão Série C",
            "Copa do Brasil" => "Copa do Brasil",
            other if !other.is_empty() => {
                // Keep unknown tournaments under their own label.
                out.push(make_match(
                    other,
                    {
                        let (iso, _) = parse_date(field(&rec, &map, "date"));
                        iso.split('-').next().and_then(|y| y.parse().ok()).unwrap_or(0)
                    },
                    field(&rec, &map, "date"),
                    field(&rec, &map, "home"),
                    field(&rec, &map, "away"),
                    parse_int(field(&rec, &map, "home_goal")),
                    parse_int(field(&rec, &map, "away_goal")),
                    None,
                    "BR-Football-Dataset.csv",
                ));
                continue;
            }
            _ => continue,
        };
        let date_raw = field(&rec, &map, "date");
        let (iso, _) = parse_date(date_raw);
        let season = iso.split('-').next().and_then(|y| y.parse().ok()).unwrap_or(0);
        out.push(make_match(
            competition,
            season,
            date_raw,
            field(&rec, &map, "home"),
            field(&rec, &map, "away"),
            parse_int(field(&rec, &map, "home_goal")),
            parse_int(field(&rec, &map, "away_goal")),
            None,
            "BR-Football-Dataset.csv",
        ));
    }
    Ok(())
}

/// Load and unify every match file found in `dir`. Missing files are skipped so
/// the server still starts with a partial dataset. Overlapping fixtures across
/// files are de-duplicated.
pub fn load_matches(dir: &Path) -> Vec<Match> {
    let mut all: Vec<Match> = Vec::new();

    let loaders: &[(&str, fn(&Path, &mut Vec<Match>) -> csv::Result<()>)] = &[
        ("Brasileirao_Matches.csv", load_brasileirao),
        ("Brazilian_Cup_Matches.csv", load_cup),
        ("Libertadores_Matches.csv", load_libertadores),
        ("novo_campeonato_brasileiro.csv", load_novo),
        ("BR-Football-Dataset.csv", load_br_football),
    ];

    for (file, loader) in loaders {
        let path = dir.join(file);
        if path.exists() {
            if let Err(e) = loader(&path, &mut all) {
                eprintln!("warning: failed to load {}: {}", file, e);
            }
        } else {
            eprintln!("warning: dataset not found: {}", path.display());
        }
    }

    // Several files overlap (e.g. 2019 Série A appears in three of them) but use
    // different team-naming conventions, so a row-level key cannot reliably
    // identify duplicates. Instead, for each (competition, season) we keep only
    // the single highest-priority source that has data for it. This guarantees
    // no cross-file double-counting and uses the cleanest naming per season.
    let mut best: HashMap<(String, i64), u8> = HashMap::new();
    for m in &all {
        let p = source_priority(&m.competition, &m.source);
        let key = (m.competition.clone(), m.season);
        best.entry(key)
            .and_modify(|b| {
                if p < *b {
                    *b = p;
                }
            })
            .or_insert(p);
    }

    // Keep matches from the winning source, then drop any exact within-source
    // duplicate rows.
    let mut seen: HashSet<(String, i64, String, String, String)> = HashSet::new();
    let mut deduped = Vec::with_capacity(all.len());
    for m in all {
        let p = source_priority(&m.competition, &m.source);
        if best.get(&(m.competition.clone(), m.season)) != Some(&p) {
            continue;
        }
        let key = (
            m.competition.clone(),
            m.season,
            m.home_key.clone(),
            m.away_key.clone(),
            m.date_iso.clone(),
        );
        if seen.insert(key) {
            deduped.push(m);
        }
    }
    deduped
}

/// Lower number = preferred source for a given competition. When more than one
/// file covers the same (competition, season), the lowest-priority source wins.
fn source_priority(competition: &str, source: &str) -> u8 {
    match competition {
        "Brasileirão Série A" => match source {
            "novo_campeonato_brasileiro.csv" => 0, // clean, 2003-2019
            "Brasileirao_Matches.csv" => 1,        // clean, 2012-2022
            "BR-Football-Dataset.csv" => 2,        // 2014-2023, noisier names
            _ => 9,
        },
        "Copa do Brasil" => match source {
            "Brazilian_Cup_Matches.csv" => 0,
            "BR-Football-Dataset.csv" => 1,
            _ => 9,
        },
        // Single-source competitions (Libertadores, Série B/C, misc tournaments).
        _ => 0,
    }
}

/// Load the FIFA player database.
pub fn load_players(dir: &Path) -> Vec<Player> {
    let path = dir.join("fifa_data.csv");
    if !path.exists() {
        eprintln!("warning: dataset not found: {}", path.display());
        return Vec::new();
    }
    let mut rdr = match reader(&path) {
        Ok(r) => r,
        Err(e) => {
            eprintln!("warning: failed to open fifa_data.csv: {}", e);
            return Vec::new();
        }
    };
    let map = match rdr.headers() {
        Ok(h) => header_map(h),
        Err(e) => {
            eprintln!("warning: failed to read fifa headers: {}", e);
            return Vec::new();
        }
    };

    let mut players = Vec::new();
    for rec in rdr.records() {
        let rec = match rec {
            Ok(r) => r,
            Err(_) => continue,
        };
        let name = field(&rec, &map, "Name");
        if name.is_empty() {
            continue;
        }
        let club = field(&rec, &map, "Club");
        players.push(Player {
            name: name.to_string(),
            age: parse_int(field(&rec, &map, "Age")),
            nationality: field(&rec, &map, "Nationality").to_string(),
            overall: parse_int(field(&rec, &map, "Overall")),
            potential: parse_int(field(&rec, &map, "Potential")),
            club_key: team_key(club),
            club: club.to_string(),
            position: field(&rec, &map, "Position").to_string(),
            jersey: field(&rec, &map, "Jersey Number").to_string(),
            height: field(&rec, &map, "Height").to_string(),
            weight: field(&rec, &map, "Weight").to_string(),
            value: field(&rec, &map, "Value").to_string(),
            wage: field(&rec, &map, "Wage").to_string(),
            preferred_foot: field(&rec, &map, "Preferred Foot").to_string(),
        });
    }
    players
}
