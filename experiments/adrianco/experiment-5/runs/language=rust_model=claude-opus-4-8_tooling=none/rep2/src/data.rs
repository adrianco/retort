//! ============================================================================
//! Context
//! ----------------------------------------------------------------------------
//! Module:   data
//! Purpose:  Load the six Kaggle CSV files into the in-memory `Database`.
//!           Each file has a different schema, so each gets its own loader that
//!           maps columns (by header name) onto the unified `Match`/`Player`
//!           domain models in `models`.
//!
//! Robustness:
//!   * Columns are looked up by header name via a per-file index map, so column
//!     order changes do not break parsing.
//!   * A UTF-8 BOM on the first header (present in `fifa_data.csv`) is stripped.
//!   * Missing/blank/garbage cells degrade to `None` rather than failing the
//!     whole load.
//!   * The data directory is configurable (constructor arg or `SOCCER_DATA_DIR`
//!     env var) which keeps the loader testable.
//!
//! ============================================================================

use std::collections::HashMap;
use std::path::{Path, PathBuf};

use crate::models::{Match, Player};
use crate::normalize::{parse_date, parse_goal};

/// The full in-memory knowledge graph: every match and every player.
#[derive(Debug, Default)]
pub struct Database {
    pub matches: Vec<Match>,
    pub players: Vec<Player>,
}

/// The six expected source files, relative to the data directory.
pub const MATCH_FILES: &[&str] = &[
    "Brasileirao_Matches.csv",
    "Brazilian_Cup_Matches.csv",
    "Libertadores_Matches.csv",
    "BR-Football-Dataset.csv",
    "novo_campeonato_brasileiro.csv",
];
pub const PLAYER_FILE: &str = "fifa_data.csv";

impl Database {
    /// Resolve the data directory: explicit `dir` if given, else the
    /// `SOCCER_DATA_DIR` env var, else the bundled `data/kaggle`.
    pub fn data_dir(dir: Option<&Path>) -> PathBuf {
        if let Some(d) = dir {
            return d.to_path_buf();
        }
        if let Ok(env) = std::env::var("SOCCER_DATA_DIR") {
            return PathBuf::from(env);
        }
        PathBuf::from("data/kaggle")
    }

    /// Load all datasets from the resolved data directory.
    pub fn load(dir: Option<&Path>) -> Result<Database, String> {
        let base = Self::data_dir(dir);
        let mut db = Database::default();

        db.load_brasileirao(&base.join("Brasileirao_Matches.csv"))?;
        db.load_cup(&base.join("Brazilian_Cup_Matches.csv"))?;
        db.load_libertadores(&base.join("Libertadores_Matches.csv"))?;
        db.load_br_football(&base.join("BR-Football-Dataset.csv"))?;
        db.load_historical(&base.join("novo_campeonato_brasileiro.csv"))?;
        db.load_players(&base.join(PLAYER_FILE))?;

        db.resolve_overlaps();
        Ok(db)
    }

    /// The curated files overlap: the Brasileirão seasons 2012-2019 appear in
    /// BOTH `Brasileirao_Matches.csv` and `novo_campeonato_brasileiro.csv`.
    /// The two sources disagree on team spellings ("Vasco" vs "Vasco da Gama",
    /// "Athletico" vs "Atletico") and on some kickoff dates, so they cannot be
    /// merged row-by-row without splitting clubs or double-counting.
    ///
    /// We resolve this by treating each (competition, season) as owned by a
    /// single source — the one with the most rows for that combo, preferring
    /// the curated file over the historical one on ties. Rows from the other
    /// source for that exact combo are dropped. This leaves every Brasileirão
    /// season sourced consistently from one file while still drawing the
    /// historical-only seasons (2003-2011) from `novo_campeonato`.
    ///
    /// The extended `BR-Football-Dataset.csv` is left untouched here: it is
    /// excluded from aggregates elsewhere and remains opt-in for search.
    fn resolve_overlaps(&mut self) {
        use std::collections::HashMap;

        // Count rows per (competition, season) per source (non-extended only).
        let mut counts: HashMap<(String, i32), HashMap<String, usize>> = HashMap::new();
        for m in &self.matches {
            if m.is_extended() {
                continue;
            }
            if let Some(season) = m.season {
                *counts
                    .entry((m.competition.clone(), season))
                    .or_default()
                    .entry(m.source.clone())
                    .or_insert(0) += 1;
            }
        }

        let rank = |s: &str| -> u8 {
            match s {
                "Brasileirao_Matches.csv"
                | "Brazilian_Cup_Matches.csv"
                | "Libertadores_Matches.csv" => 0,
                "novo_campeonato_brasileiro.csv" => 1,
                _ => 2,
            }
        };

        // Decide the owning source for each contested (competition, season).
        let mut owner: HashMap<(String, i32), String> = HashMap::new();
        for (key, by_source) in counts {
            let chosen = by_source
                .into_iter()
                .max_by(|a, b| a.1.cmp(&b.1).then_with(|| rank(&b.0).cmp(&rank(&a.0))))
                .map(|(s, _)| s);
            if let Some(s) = chosen {
                owner.insert(key, s);
            }
        }

        self.matches.retain(|m| {
            if m.is_extended() {
                return true;
            }
            match m.season {
                Some(season) => {
                    match owner.get(&(m.competition.clone(), season)) {
                        Some(src) => m.source == *src,
                        None => true,
                    }
                }
                None => true,
            }
        });
    }

    fn load_brasileirao(&mut self, path: &Path) -> Result<(), String> {
        for_each_record(path, |g| {
            self.matches.push(Match::new(
                "Brasileirão",
                "Brasileirao_Matches.csv",
                parse_date(g.get("datetime")),
                g.get("season").trim().parse().ok(),
                non_empty(g.get("round")),
                None,
                g.get("home_team"),
                g.get("away_team"),
                parse_goal(g.get("home_goal")),
                parse_goal(g.get("away_goal")),
            ));
        })
    }

    fn load_cup(&mut self, path: &Path) -> Result<(), String> {
        for_each_record(path, |g| {
            self.matches.push(Match::new(
                "Copa do Brasil",
                "Brazilian_Cup_Matches.csv",
                parse_date(g.get("datetime")),
                g.get("season").trim().parse().ok(),
                non_empty(g.get("round")),
                None,
                g.get("home_team"),
                g.get("away_team"),
                parse_goal(g.get("home_goal")),
                parse_goal(g.get("away_goal")),
            ));
        })
    }

    fn load_libertadores(&mut self, path: &Path) -> Result<(), String> {
        for_each_record(path, |g| {
            self.matches.push(Match::new(
                "Copa Libertadores",
                "Libertadores_Matches.csv",
                parse_date(g.get("datetime")),
                g.get("season").trim().parse().ok(),
                None,
                non_empty(g.get("stage")),
                g.get("home_team"),
                g.get("away_team"),
                parse_goal(g.get("home_goal")),
                parse_goal(g.get("away_goal")),
            ));
        })
    }

    fn load_br_football(&mut self, path: &Path) -> Result<(), String> {
        for_each_record(path, |g| {
            // This file uses canonical competition labels in the `tournament`
            // column ("Serie A", "Copa do Brasil", ...). Resolve to our buckets.
            let comp = crate::normalize::canonical_competition(g.get("tournament"));
            let date = parse_date(g.get("date"));
            // No season column; derive it from the match year.
            let season = date.map(|d| d.year);
            self.matches.push(Match::new(
                comp,
                "BR-Football-Dataset.csv",
                date,
                season,
                None,
                None,
                g.get("home"),
                g.get("away"),
                parse_goal(g.get("home_goal")),
                parse_goal(g.get("away_goal")),
            ));
        })
    }

    fn load_historical(&mut self, path: &Path) -> Result<(), String> {
        for_each_record(path, |g| {
            // This file stores the team name and its state in separate columns
            // ("Guarani" + "SP"). The curated Brasileirão file uses the joined
            // "Guarani-SP" form, so reconstruct the suffix here to make the two
            // sources dedupe cleanly.
            let home = join_state(g.get("Equipe_mandante"), g.get("Mandante_UF"));
            let away = join_state(g.get("Equipe_visitante"), g.get("Visitante_UF"));
            self.matches.push(Match::new(
                "Brasileirão",
                "novo_campeonato_brasileiro.csv",
                parse_date(g.get("Data")),
                g.get("Ano").trim().parse().ok(),
                non_empty(g.get("Rodada")),
                None,
                home,
                away,
                parse_goal(g.get("Gols_mandante")),
                parse_goal(g.get("Gols_visitante")),
            ));
        })
    }

    fn load_players(&mut self, path: &Path) -> Result<(), String> {
        for_each_record(path, |g| {
            self.players.push(Player {
                id: g.get("ID").trim().to_string(),
                name: g.get("Name").trim().to_string(),
                age: g.get("Age").trim().parse().ok(),
                nationality: g.get("Nationality").trim().to_string(),
                overall: g.get("Overall").trim().parse().ok(),
                potential: g.get("Potential").trim().parse().ok(),
                club: g.get("Club").trim().to_string(),
                position: g.get("Position").trim().to_string(),
                jersey_number: non_empty(g.get("Jersey Number")),
                height: g.get("Height").trim().to_string(),
                weight: g.get("Weight").trim().to_string(),
            });
        })
    }
}

/// Join a bare team name with its state code, matching the "Name-UF" form used
/// by the curated files. Returns the name unchanged when there is no state code
/// or when the name already carries a suffix (some historical rows do), which
/// avoids producing doubled suffixes like "Athletico-PR-PR".
fn join_state(name: &str, uf: &str) -> String {
    let name = name.trim();
    let uf = uf.trim();
    if uf.is_empty() || name.contains('-') {
        name.to_string()
    } else {
        format!("{}-{}", name, uf)
    }
}

fn non_empty(s: &str) -> Option<String> {
    let t = s.trim();
    if t.is_empty() {
        None
    } else {
        Some(t.to_string())
    }
}

/// A single CSV row plus its header index, offering cell access by column name.
pub struct Row<'a> {
    record: &'a csv::StringRecord,
    index: &'a HashMap<String, usize>,
}

impl<'a> Row<'a> {
    /// Raw cell for `name`, or "" if the column is absent / cell is missing.
    pub fn get(&self, name: &str) -> &'a str {
        match self.index.get(name) {
            Some(&i) => self.record.get(i).unwrap_or(""),
            None => "",
        }
    }
}

/// Read a CSV file and invoke `f` once per data row, passing a [`Row`] from
/// which cells are fetched by header name. A leading UTF-8 BOM on the first
/// header is stripped so `fifa_data.csv` loads cleanly.
fn for_each_record<F>(path: &Path, mut f: F) -> Result<(), String>
where
    F: FnMut(&Row),
{
    let mut reader = csv::ReaderBuilder::new()
        .flexible(true)
        .from_path(path)
        .map_err(|e| format!("failed to open {}: {}", path.display(), e))?;

    let headers = reader
        .headers()
        .map_err(|e| format!("failed to read headers from {}: {}", path.display(), e))?
        .clone();
    let mut index: HashMap<String, usize> = HashMap::new();
    for (i, h) in headers.iter().enumerate() {
        let key = h.trim_start_matches('\u{feff}').trim().to_string();
        index.entry(key).or_insert(i);
    }

    let mut record = csv::StringRecord::new();
    loop {
        match reader.read_record(&mut record) {
            Ok(true) => {
                let row = Row {
                    record: &record,
                    index: &index,
                };
                f(&row);
            }
            Ok(false) => break,
            Err(e) => return Err(format!("error reading {}: {}", path.display(), e)),
        }
    }
    Ok(())
}
