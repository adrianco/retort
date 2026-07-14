// =============================================================================
// Context
// -----------------------------------------------------------------------------
// Module:  data
// Purpose: In-memory model + CSV loaders for the six provided datasets. Every
//          source CSV has a slightly different schema, so each file gets its
//          own loader that maps its columns onto the unified `Match` model (or
//          the `Player` model for the FIFA data). Loaders are tolerant: rows
//          with unparseable scores are skipped rather than aborting the load.
//
//          Team names are run through `normalize` so the rest of the program
//          only ever deals with clean display names + comparable keys.
//
// Datasets:
//   Brasileirao_Matches.csv          -> "Brasileirão Série A"
//   Brazilian_Cup_Matches.csv        -> "Copa do Brasil"
//   Libertadores_Matches.csv         -> "Copa Libertadores"
//   BR-Football-Dataset.csv          -> per-row `tournament` column
//   novo_campeonato_brasileiro.csv   -> "Brasileirão Série A" (historical)
//   fifa_data.csv                    -> FIFA player attributes
//
// Used by: queries.rs (everything reads from the loaded `Dataset`).
// =============================================================================

use crate::normalize::{display_team, normalize_date, year_from_date, Canonicalizer};
use std::collections::HashMap;
use std::error::Error;
use std::path::Path;

/// A single match, unified across all match datasets.
#[derive(Debug, Clone)]
pub struct Match {
    pub competition: String,
    pub date: String, // ISO YYYY-MM-DD (may be empty if source had none)
    pub season: i32,
    pub round: Option<String>,
    pub stage: Option<String>,
    pub home_team: String, // cleaned display name
    pub away_team: String, // cleaned display name
    pub home_raw: String,  // original name (retains state suffix for canonicalization)
    pub away_raw: String,
    pub home_goal: i32,
    pub away_goal: i32,
    pub source: &'static str,
}

impl Match {
    pub fn total_goals(&self) -> i32 {
        self.home_goal + self.away_goal
    }

    /// "Home", "Away" or "Draw" from the home team's perspective.
    pub fn result(&self) -> &'static str {
        match self.home_goal.cmp(&self.away_goal) {
            std::cmp::Ordering::Greater => "Home",
            std::cmp::Ordering::Less => "Away",
            std::cmp::Ordering::Equal => "Draw",
        }
    }
}

/// A single FIFA player record (only the fields we expose are retained).
#[derive(Debug, Clone)]
pub struct Player {
    pub id: String,
    pub name: String,
    pub age: Option<i32>,
    pub nationality: String,
    pub overall: i32,
    pub potential: i32,
    pub club: String,
    pub position: String,
    pub jersey: String,
    pub height: String,
    pub weight: String,
}

/// The full loaded dataset.
#[derive(Debug, Default)]
pub struct Dataset {
    pub matches: Vec<Match>,
    pub players: Vec<Player>,
    /// Data-derived team-identity resolver, used for de-duplication and for
    /// grouping matches in standings / aggregate statistics.
    pub canon: Canonicalizer,
}

/// Map a CSV header row to a name -> column-index lookup. The FIFA file has a
/// leading BOM on its first (blank) header which we strip here.
fn header_index(headers: &csv::StringRecord) -> HashMap<String, usize> {
    headers
        .iter()
        .enumerate()
        .map(|(i, h)| (h.trim_start_matches('\u{feff}').trim().to_string(), i))
        .collect()
}

/// Fetch a field by header name, returning an empty string if absent.
fn field<'a>(rec: &'a csv::StringRecord, idx: &HashMap<String, usize>, name: &str) -> &'a str {
    idx.get(name).and_then(|&i| rec.get(i)).unwrap_or("").trim()
}

/// Parse a goal value that may be an integer ("3") or a float ("3.0").
fn parse_goal(s: &str) -> Option<i32> {
    let s = s.trim();
    if s.is_empty() {
        return None;
    }
    if let Ok(i) = s.parse::<i32>() {
        return Some(i);
    }
    s.parse::<f64>().ok().map(|f| f.round() as i32)
}

fn parse_int(s: &str) -> Option<i32> {
    s.trim().parse::<i32>().ok().or_else(|| {
        s.trim().parse::<f64>().ok().map(|f| f.round() as i32)
    })
}

fn open(path: &Path) -> Result<csv::Reader<std::fs::File>, Box<dyn Error>> {
    csv::ReaderBuilder::new()
        .flexible(true)
        .from_path(path)
        .map_err(|e| format!("failed to open {}: {e}", path.display()).into())
}

impl Dataset {
    /// Load every CSV found under `dir` (typically "data/kaggle"). Missing
    /// individual files are tolerated so the server can still start with a
    /// partial dataset, but at least one file must load.
    pub fn load_from_dir(dir: &Path) -> Result<Dataset, Box<dyn Error>> {
        let mut ds = Dataset::default();
        let mut loaded_any = false;

        let mut try_load = |res: Result<(), Box<dyn Error>>| {
            if let Err(e) = res {
                eprintln!("[warn] {e}");
            } else {
                loaded_any = true;
            }
        };

        try_load(ds.load_brasileirao(&dir.join("Brasileirao_Matches.csv")));
        try_load(ds.load_cup(&dir.join("Brazilian_Cup_Matches.csv")));
        try_load(ds.load_libertadores(&dir.join("Libertadores_Matches.csv")));
        try_load(ds.load_br_football(&dir.join("BR-Football-Dataset.csv")));
        try_load(ds.load_novo(&dir.join("novo_campeonato_brasileiro.csv")));
        try_load(ds.load_fifa(&dir.join("fifa_data.csv")));

        if !loaded_any {
            return Err(format!("no datasets could be loaded from {}", dir.display()).into());
        }

        // Resolve team identities from the full set of observed raw names, then
        // de-duplicate fixtures that overlap between sources.
        ds.canon = Canonicalizer::build(
            ds.matches
                .iter()
                .flat_map(|m| [m.home_raw.as_str(), m.away_raw.as_str()]),
        );
        ds.deduplicate_matches();
        Ok(ds)
    }

    /// Several files overlap (e.g. the 2012-2019 Brasileirão appears in
    /// `Brasileirao_Matches.csv`, `novo_campeonato_brasileiro.csv` and the
    /// "Serie A" rows of `BR-Football-Dataset.csv`). Without de-duplication
    /// every aggregate (standings, win counts, averages) would be inflated.
    ///
    /// Two records are considered the same fixture when they share a date and
    /// the same accent/case/suffix-folded home and away team keys. The first
    /// occurrence wins, which - given load order - prefers the dedicated
    /// competition files and their richer competition labels. Records without
    /// a usable date are always kept.
    fn deduplicate_matches(&mut self) {
        use std::collections::HashSet;
        let mut seen: HashSet<(String, String, String)> = HashSet::new();
        let mut kept = Vec::with_capacity(self.matches.len());
        for m in std::mem::take(&mut self.matches) {
            if m.date.is_empty() {
                kept.push(m);
                continue;
            }
            let key = (
                m.date.clone(),
                self.canon.key(&m.home_raw),
                self.canon.key(&m.away_raw),
            );
            if seen.insert(key) {
                kept.push(m);
            }
        }
        self.matches = kept;
    }

    fn load_brasileirao(&mut self, path: &Path) -> Result<(), Box<dyn Error>> {
        let mut rdr = open(path)?;
        let idx = header_index(rdr.headers()?);
        for rec in rdr.records() {
            let rec = rec?;
            let (Some(hg), Some(ag)) = (
                parse_goal(field(&rec, &idx, "home_goal")),
                parse_goal(field(&rec, &idx, "away_goal")),
            ) else {
                continue;
            };
            let date = normalize_date(field(&rec, &idx, "datetime"));
            let season = parse_int(field(&rec, &idx, "season"))
                .or_else(|| year_from_date(&date))
                .unwrap_or(0);
            self.matches.push(Match {
                competition: "Brasileirão Série A".to_string(),
                date,
                season,
                round: Some(field(&rec, &idx, "round").to_string()),
                stage: None,
                home_team: display_team(field(&rec, &idx, "home_team")),
                away_team: display_team(field(&rec, &idx, "away_team")),
                home_raw: field(&rec, &idx, "home_team").to_string(),
                away_raw: field(&rec, &idx, "away_team").to_string(),
                home_goal: hg,
                away_goal: ag,
                source: "Brasileirao_Matches.csv",
            });
        }
        Ok(())
    }

    fn load_cup(&mut self, path: &Path) -> Result<(), Box<dyn Error>> {
        let mut rdr = open(path)?;
        let idx = header_index(rdr.headers()?);
        for rec in rdr.records() {
            let rec = rec?;
            let (Some(hg), Some(ag)) = (
                parse_goal(field(&rec, &idx, "home_goal")),
                parse_goal(field(&rec, &idx, "away_goal")),
            ) else {
                continue;
            };
            let date = normalize_date(field(&rec, &idx, "datetime"));
            let season = parse_int(field(&rec, &idx, "season"))
                .or_else(|| year_from_date(&date))
                .unwrap_or(0);
            self.matches.push(Match {
                competition: "Copa do Brasil".to_string(),
                date,
                season,
                round: Some(field(&rec, &idx, "round").to_string()),
                stage: None,
                home_team: display_team(field(&rec, &idx, "home_team")),
                away_team: display_team(field(&rec, &idx, "away_team")),
                home_raw: field(&rec, &idx, "home_team").to_string(),
                away_raw: field(&rec, &idx, "away_team").to_string(),
                home_goal: hg,
                away_goal: ag,
                source: "Brazilian_Cup_Matches.csv",
            });
        }
        Ok(())
    }

    fn load_libertadores(&mut self, path: &Path) -> Result<(), Box<dyn Error>> {
        let mut rdr = open(path)?;
        let idx = header_index(rdr.headers()?);
        for rec in rdr.records() {
            let rec = rec?;
            let (Some(hg), Some(ag)) = (
                parse_goal(field(&rec, &idx, "home_goal")),
                parse_goal(field(&rec, &idx, "away_goal")),
            ) else {
                continue;
            };
            let date = normalize_date(field(&rec, &idx, "datetime"));
            let season = parse_int(field(&rec, &idx, "season"))
                .or_else(|| year_from_date(&date))
                .unwrap_or(0);
            self.matches.push(Match {
                competition: "Copa Libertadores".to_string(),
                date,
                season,
                round: None,
                stage: Some(field(&rec, &idx, "stage").to_string()),
                home_team: display_team(field(&rec, &idx, "home_team")),
                away_team: display_team(field(&rec, &idx, "away_team")),
                home_raw: field(&rec, &idx, "home_team").to_string(),
                away_raw: field(&rec, &idx, "away_team").to_string(),
                home_goal: hg,
                away_goal: ag,
                source: "Libertadores_Matches.csv",
            });
        }
        Ok(())
    }

    fn load_br_football(&mut self, path: &Path) -> Result<(), Box<dyn Error>> {
        let mut rdr = open(path)?;
        let idx = header_index(rdr.headers()?);
        for rec in rdr.records() {
            let rec = rec?;
            let (Some(hg), Some(ag)) = (
                parse_goal(field(&rec, &idx, "home_goal")),
                parse_goal(field(&rec, &idx, "away_goal")),
            ) else {
                continue;
            };
            let date = normalize_date(field(&rec, &idx, "date"));
            let season = year_from_date(&date).unwrap_or(0);
            let tournament = field(&rec, &idx, "tournament");
            let competition = if tournament.is_empty() {
                "Brazilian Football".to_string()
            } else {
                tournament.to_string()
            };
            self.matches.push(Match {
                competition,
                date,
                season,
                round: None,
                stage: None,
                home_team: display_team(field(&rec, &idx, "home")),
                away_team: display_team(field(&rec, &idx, "away")),
                home_raw: field(&rec, &idx, "home").to_string(),
                away_raw: field(&rec, &idx, "away").to_string(),
                home_goal: hg,
                away_goal: ag,
                source: "BR-Football-Dataset.csv",
            });
        }
        Ok(())
    }

    fn load_novo(&mut self, path: &Path) -> Result<(), Box<dyn Error>> {
        let mut rdr = open(path)?;
        let idx = header_index(rdr.headers()?);
        for rec in rdr.records() {
            let rec = rec?;
            let (Some(hg), Some(ag)) = (
                parse_goal(field(&rec, &idx, "Gols_mandante")),
                parse_goal(field(&rec, &idx, "Gols_visitante")),
            ) else {
                continue;
            };
            let date = normalize_date(field(&rec, &idx, "Data"));
            let season = parse_int(field(&rec, &idx, "Ano"))
                .or_else(|| year_from_date(&date))
                .unwrap_or(0);
            self.matches.push(Match {
                competition: "Brasileirão Série A".to_string(),
                date,
                season,
                round: Some(field(&rec, &idx, "Rodada").to_string()),
                stage: None,
                home_team: display_team(field(&rec, &idx, "Equipe_mandante")),
                away_team: display_team(field(&rec, &idx, "Equipe_visitante")),
                home_raw: field(&rec, &idx, "Equipe_mandante").to_string(),
                away_raw: field(&rec, &idx, "Equipe_visitante").to_string(),
                home_goal: hg,
                away_goal: ag,
                source: "novo_campeonato_brasileiro.csv",
            });
        }
        Ok(())
    }

    fn load_fifa(&mut self, path: &Path) -> Result<(), Box<dyn Error>> {
        let mut rdr = open(path)?;
        let idx = header_index(rdr.headers()?);
        for rec in rdr.records() {
            let rec = rec?;
            let name = field(&rec, &idx, "Name");
            if name.is_empty() {
                continue;
            }
            let overall = parse_int(field(&rec, &idx, "Overall")).unwrap_or(0);
            let potential = parse_int(field(&rec, &idx, "Potential")).unwrap_or(0);
            self.players.push(Player {
                id: field(&rec, &idx, "ID").to_string(),
                name: name.to_string(),
                age: parse_int(field(&rec, &idx, "Age")),
                nationality: field(&rec, &idx, "Nationality").to_string(),
                overall,
                potential,
                club: field(&rec, &idx, "Club").to_string(),
                position: field(&rec, &idx, "Position").to_string(),
                jersey: field(&rec, &idx, "Jersey Number").to_string(),
                height: field(&rec, &idx, "Height").to_string(),
                weight: field(&rec, &idx, "Weight").to_string(),
            });
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_float_and_int_goals() {
        assert_eq!(parse_goal("3"), Some(3));
        assert_eq!(parse_goal("3.0"), Some(3));
        assert_eq!(parse_goal(""), None);
        assert_eq!(parse_goal("x"), None);
    }

    #[test]
    fn match_result_logic() {
        let mut m = Match {
            competition: "X".into(),
            date: "2020-01-01".into(),
            season: 2020,
            round: None,
            stage: None,
            home_team: "A".into(),
            away_team: "B".into(),
            home_raw: "A".into(),
            away_raw: "B".into(),
            home_goal: 2,
            away_goal: 1,
            source: "test",
        };
        assert_eq!(m.result(), "Home");
        m.away_goal = 3;
        assert_eq!(m.result(), "Away");
        m.home_goal = 3;
        assert_eq!(m.result(), "Draw");
        assert_eq!(m.total_goals(), 6);
    }
}
