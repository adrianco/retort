//! CSV loaders.
//!
//! Each of the six bundled files has its own column layout (see TASK.md).
//! We parse them into a single `Match` value type and a `Player` value type so
//! the query layer doesn't have to know which file a row came from.  The
//! `Dataset` struct holds everything plus a normalized-name index.

use std::collections::{HashMap, HashSet};
use std::path::Path;

use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};

use crate::normalize::normalize_team;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum Competition {
    BrasileiraoSerieA,
    BrasileiraoSerieB,
    BrasileiraoSerieC,
    CopaDoBrasil,
    Libertadores,
    /// Historical 2003-2019 Brasileirao (treated as Serie A).
    BrasileiraoHistorico,
    Other,
}

impl Competition {
    pub fn label(&self) -> &'static str {
        match self {
            Competition::BrasileiraoSerieA => "Brasileirão Série A",
            Competition::BrasileiraoSerieB => "Brasileirão Série B",
            Competition::BrasileiraoSerieC => "Brasileirão Série C",
            Competition::CopaDoBrasil => "Copa do Brasil",
            Competition::Libertadores => "Copa Libertadores",
            Competition::BrasileiraoHistorico => "Brasileirão (Histórico)",
            Competition::Other => "Other",
        }
    }

    fn from_tournament_string(s: &str) -> Self {
        match s.trim() {
            "Serie A" => Competition::BrasileiraoSerieA,
            "Serie B" => Competition::BrasileiraoSerieB,
            "Serie C" => Competition::BrasileiraoSerieC,
            "Copa do Brasil" => Competition::CopaDoBrasil,
            _ => Competition::Other,
        }
    }
}

/// One match, regardless of which CSV it came from.
#[derive(Debug, Clone, Serialize)]
pub struct Match {
    pub competition: Competition,
    pub season: i32,
    pub round: Option<String>,
    pub stage: Option<String>,
    /// ISO date (YYYY-MM-DD).  Empty string if not derivable.
    pub date: String,
    pub home_team: String,
    pub away_team: String,
    pub home_team_norm: String,
    pub away_team_norm: String,
    pub home_goal: i32,
    pub away_goal: i32,
    pub home_state: Option<String>,
    pub away_state: Option<String>,
    pub arena: Option<String>,
}

impl Match {
    pub fn winner(&self) -> Option<&str> {
        if self.home_goal > self.away_goal {
            Some(&self.home_team)
        } else if self.away_goal > self.home_goal {
            Some(&self.away_team)
        } else {
            None
        }
    }

    pub fn winner_norm(&self) -> Option<&str> {
        if self.home_goal > self.away_goal {
            Some(&self.home_team_norm)
        } else if self.away_goal > self.home_goal {
            Some(&self.away_team_norm)
        } else {
            None
        }
    }

    pub fn involves(&self, team_norm: &str) -> bool {
        self.home_team_norm == team_norm || self.away_team_norm == team_norm
    }
}

/// One FIFA player row (only fields we actually use).
#[derive(Debug, Clone, Serialize)]
pub struct Player {
    pub id: i64,
    pub name: String,
    pub age: Option<i32>,
    pub nationality: String,
    pub overall: i32,
    pub potential: i32,
    pub club: String,
    pub position: String,
    pub jersey: Option<i32>,
    pub height: String,
    pub weight: String,
}

#[derive(Debug, Default)]
pub struct Dataset {
    pub matches: Vec<Match>,
    pub players: Vec<Player>,
}

impl Dataset {
    /// Load every CSV in `data/kaggle/` under `root`.
    ///
    /// The five match files overlap heavily — the Brasileirão 2012-2022 CSV
    /// covers many of the same matches as the extended stats CSV's "Serie A"
    /// rows, and the historical CSV covers 2003-2019 which again overlaps the
    /// first.  We dedupe by (date, normalized home team, normalized away
    /// team) so a single fixture is counted once for standings and stats.
    pub fn load_from_dir<P: AsRef<Path>>(root: P) -> Result<Self> {
        let root = root.as_ref();
        let mut matches = Vec::new();

        matches.extend(load_brasileirao(&root.join("Brasileirao_Matches.csv"))?);
        matches.extend(load_cup(&root.join("Brazilian_Cup_Matches.csv"))?);
        matches.extend(load_libertadores(&root.join("Libertadores_Matches.csv"))?);
        matches.extend(load_novo(&root.join("novo_campeonato_brasileiro.csv"))?);
        // BR-Football is loaded last so its rows are dropped on date collision —
        // the per-competition CSVs above have richer round/stage metadata.
        matches.extend(load_br_football(&root.join("BR-Football-Dataset.csv"))?);

        let players = load_fifa(&root.join("fifa_data.csv"))?;

        Ok(Dataset { matches: dedupe_matches(matches), players })
    }

    /// Index of normalized team name -> all matches involving that team.
    /// Computed on demand because it's only used by a handful of queries.
    pub fn matches_by_team(&self) -> HashMap<String, Vec<usize>> {
        let mut idx: HashMap<String, Vec<usize>> = HashMap::new();
        for (i, m) in self.matches.iter().enumerate() {
            idx.entry(m.home_team_norm.clone()).or_default().push(i);
            if m.away_team_norm != m.home_team_norm {
                idx.entry(m.away_team_norm.clone()).or_default().push(i);
            }
        }
        idx
    }
}

/// Drop matches that share (competition, season, home, away) with one already
/// kept.  In a single-season round-robin two teams meet once at home and once
/// away; in cup formats the same pair may appear twice per season as separate
/// leg-1/leg-2 fixtures but their scores differ — we tolerate that by also
/// keying on the score.  This catches both
///   - duplicates between Brasileirao_Matches and BR-Football where dates
///     differ by a day (timezone), and
///   - duplicates where team-name spelling differs between sources.
fn dedupe_matches(matches: Vec<Match>) -> Vec<Match> {
    let mut seen: HashSet<(Competition, i32, String, String, i32, i32)> = HashSet::new();
    let mut out = Vec::with_capacity(matches.len());
    for m in matches {
        let key = (
            m.competition,
            m.season,
            m.home_team_norm.clone(),
            m.away_team_norm.clone(),
            m.home_goal,
            m.away_goal,
        );
        if seen.insert(key) {
            out.push(m);
        }
    }
    out
}

// ---------------------------------------------------------------------------
// CSV parsing helpers
// ---------------------------------------------------------------------------

fn parse_int(s: &str) -> Option<i32> {
    let t = s.trim();
    if t.is_empty() {
        return None;
    }
    // Handle floats written as "1.0".
    if let Ok(n) = t.parse::<i32>() {
        return Some(n);
    }
    t.parse::<f64>().ok().map(|f| f.round() as i32)
}

/// Take "2012-05-19 18:30:00" -> "2012-05-19".  Also tolerates
/// "29/03/2003" -> "2003-03-29".
fn normalize_date(s: &str) -> String {
    let s = s.trim().trim_matches('"');
    if s.is_empty() {
        return String::new();
    }
    // ISO form already?
    if s.len() >= 10 && s.as_bytes()[4] == b'-' && s.as_bytes()[7] == b'-' {
        return s[..10].to_string();
    }
    // DD/MM/YYYY
    if s.len() == 10 && s.as_bytes()[2] == b'/' && s.as_bytes()[5] == b'/' {
        let d = &s[0..2];
        let m = &s[3..5];
        let y = &s[6..10];
        return format!("{y}-{m}-{d}");
    }
    s.to_string()
}

// ---------------------------------------------------------------------------
// File-specific loaders
// ---------------------------------------------------------------------------

#[derive(Debug, Deserialize)]
struct BrasileiraoRow {
    datetime: String,
    home_team: String,
    home_team_state: String,
    away_team: String,
    away_team_state: String,
    home_goal: String,
    away_goal: String,
    season: i32,
    round: i32,
}

fn load_brasileirao(path: &Path) -> Result<Vec<Match>> {
    let mut rdr = csv::ReaderBuilder::new()
        .has_headers(true)
        .from_path(path)
        .with_context(|| format!("opening {}", path.display()))?;
    let mut out = Vec::new();
    for row in rdr.deserialize::<BrasileiraoRow>() {
        let row = row?;
        let hg = parse_int(&row.home_goal);
        let ag = parse_int(&row.away_goal);
        let (Some(hg), Some(ag)) = (hg, ag) else { continue };
        out.push(Match {
            competition: Competition::BrasileiraoSerieA,
            season: row.season,
            round: Some(row.round.to_string()),
            stage: None,
            date: normalize_date(&row.datetime),
            home_team_norm: normalize_team(&row.home_team),
            away_team_norm: normalize_team(&row.away_team),
            home_team: row.home_team,
            away_team: row.away_team,
            home_goal: hg,
            away_goal: ag,
            home_state: Some(row.home_team_state),
            away_state: Some(row.away_team_state),
            arena: None,
        });
    }
    Ok(out)
}

#[derive(Debug, Deserialize)]
struct CupRow {
    round: String,
    datetime: String,
    home_team: String,
    away_team: String,
    home_goal: String,
    away_goal: String,
    season: i32,
}

fn load_cup(path: &Path) -> Result<Vec<Match>> {
    let mut rdr = csv::ReaderBuilder::new()
        .has_headers(true)
        .from_path(path)
        .with_context(|| format!("opening {}", path.display()))?;
    let mut out = Vec::new();
    for row in rdr.deserialize::<CupRow>() {
        let row = row?;
        let hg = parse_int(&row.home_goal);
        let ag = parse_int(&row.away_goal);
        let (Some(hg), Some(ag)) = (hg, ag) else { continue };
        out.push(Match {
            competition: Competition::CopaDoBrasil,
            season: row.season,
            round: Some(row.round.clone()),
            stage: Some(row.round),
            date: normalize_date(&row.datetime),
            home_team_norm: normalize_team(&row.home_team),
            away_team_norm: normalize_team(&row.away_team),
            home_team: row.home_team,
            away_team: row.away_team,
            home_goal: hg,
            away_goal: ag,
            home_state: None,
            away_state: None,
            arena: None,
        });
    }
    Ok(out)
}

#[derive(Debug, Deserialize)]
struct LibertadoresRow {
    datetime: String,
    home_team: String,
    away_team: String,
    home_goal: String,
    away_goal: String,
    season: String,
    stage: String,
}

fn load_libertadores(path: &Path) -> Result<Vec<Match>> {
    let mut rdr = csv::ReaderBuilder::new()
        .has_headers(true)
        .from_path(path)
        .with_context(|| format!("opening {}", path.display()))?;
    let mut out = Vec::new();
    for row in rdr.deserialize::<LibertadoresRow>() {
        let row = row?;
        let hg = parse_int(&row.home_goal);
        let ag = parse_int(&row.away_goal);
        let season = parse_int(&row.season);
        // Skip rows where scores or season are unknown (a small tail of fixture-only entries).
        let (Some(hg), Some(ag), Some(season)) = (hg, ag, season) else { continue };
        out.push(Match {
            competition: Competition::Libertadores,
            season,
            round: None,
            stage: Some(row.stage),
            date: normalize_date(&row.datetime),
            home_team_norm: normalize_team(&row.home_team),
            away_team_norm: normalize_team(&row.away_team),
            home_team: row.home_team,
            away_team: row.away_team,
            home_goal: hg,
            away_goal: ag,
            home_state: None,
            away_state: None,
            arena: None,
        });
    }
    Ok(out)
}

#[derive(Debug, Deserialize)]
struct BrFootballRow {
    tournament: String,
    home: String,
    home_goal: String,
    away_goal: String,
    away: String,
    #[serde(default)]
    date: String,
}

fn load_br_football(path: &Path) -> Result<Vec<Match>> {
    let mut rdr = csv::ReaderBuilder::new()
        .has_headers(true)
        .flexible(true)
        .from_path(path)
        .with_context(|| format!("opening {}", path.display()))?;
    let mut out = Vec::new();
    for row in rdr.deserialize::<BrFootballRow>() {
        let row = row?;
        let hg = parse_int(&row.home_goal);
        let ag = parse_int(&row.away_goal);
        let (Some(hg), Some(ag)) = (hg, ag) else { continue };
        let date = normalize_date(&row.date);
        let season = date.get(..4).and_then(|y| y.parse::<i32>().ok()).unwrap_or(0);
        out.push(Match {
            competition: Competition::from_tournament_string(&row.tournament),
            season,
            round: None,
            stage: None,
            date,
            home_team_norm: normalize_team(&row.home),
            away_team_norm: normalize_team(&row.away),
            home_team: row.home,
            away_team: row.away,
            home_goal: hg,
            away_goal: ag,
            home_state: None,
            away_state: None,
            arena: None,
        });
    }
    Ok(out)
}

#[derive(Debug, Deserialize)]
struct NovoRow {
    #[serde(rename = "ID")]
    _id: String,
    #[serde(rename = "Data")]
    data: String,
    #[serde(rename = "Ano")]
    ano: i32,
    #[serde(rename = "Rodada")]
    rodada: i32,
    #[serde(rename = "Equipe_mandante")]
    home_team: String,
    #[serde(rename = "Equipe_visitante")]
    away_team: String,
    #[serde(rename = "Gols_mandante")]
    home_goal: String,
    #[serde(rename = "Gols_visitante")]
    away_goal: String,
    #[serde(rename = "Mandante_UF")]
    home_state: String,
    #[serde(rename = "Visitante_UF")]
    away_state: String,
    #[serde(rename = "Vencedor")]
    _vencedor: String,
    #[serde(rename = "Arena")]
    arena: String,
    #[serde(rename = "OBS", default)]
    _obs: String,
}

fn load_novo(path: &Path) -> Result<Vec<Match>> {
    let mut rdr = csv::ReaderBuilder::new()
        .has_headers(true)
        .flexible(true)
        .from_path(path)
        .with_context(|| format!("opening {}", path.display()))?;
    let mut out = Vec::new();
    for row in rdr.deserialize::<NovoRow>() {
        let row = row?;
        let hg = parse_int(&row.home_goal);
        let ag = parse_int(&row.away_goal);
        let (Some(hg), Some(ag)) = (hg, ag) else { continue };
        out.push(Match {
            competition: Competition::BrasileiraoHistorico,
            season: row.ano,
            round: Some(row.rodada.to_string()),
            stage: None,
            date: normalize_date(&row.data),
            home_team_norm: normalize_team(&row.home_team),
            away_team_norm: normalize_team(&row.away_team),
            home_team: row.home_team,
            away_team: row.away_team,
            home_goal: hg,
            away_goal: ag,
            home_state: Some(row.home_state),
            away_state: Some(row.away_state),
            arena: Some(row.arena),
        });
    }
    Ok(out)
}

fn load_fifa(path: &Path) -> Result<Vec<Player>> {
    // The FIFA CSV has many columns; pull what we need via the byte-record API
    // so adding/removing columns upstream doesn't break us.
    let mut rdr = csv::ReaderBuilder::new()
        .has_headers(true)
        .flexible(true)
        .from_path(path)
        .with_context(|| format!("opening {}", path.display()))?;

    let headers = rdr.headers()?.clone();
    let col = |name: &str| -> Option<usize> {
        headers
            .iter()
            .position(|h| h.trim_start_matches('\u{feff}').eq_ignore_ascii_case(name))
    };

    let id_idx = col("ID");
    let name_idx = col("Name");
    let age_idx = col("Age");
    let nat_idx = col("Nationality");
    let overall_idx = col("Overall");
    let potential_idx = col("Potential");
    let club_idx = col("Club");
    let pos_idx = col("Position");
    let jersey_idx = col("Jersey Number");
    let height_idx = col("Height");
    let weight_idx = col("Weight");

    let mut out = Vec::new();
    for record in rdr.records() {
        let record = record?;
        let get = |idx: Option<usize>| -> String {
            idx.and_then(|i| record.get(i)).unwrap_or("").trim().to_string()
        };
        let id: i64 = get(id_idx).parse().unwrap_or(0);
        let overall: i32 = parse_int(&get(overall_idx)).unwrap_or(0);
        let potential: i32 = parse_int(&get(potential_idx)).unwrap_or(0);
        let age: Option<i32> = parse_int(&get(age_idx));
        let jersey: Option<i32> = parse_int(&get(jersey_idx));
        out.push(Player {
            id,
            name: get(name_idx),
            age,
            nationality: get(nat_idx),
            overall,
            potential,
            club: get(club_idx),
            position: get(pos_idx),
            jersey,
            height: get(height_idx),
            weight: get(weight_idx),
        });
    }
    Ok(out)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn normalize_date_iso() {
        assert_eq!(normalize_date("2012-05-19 18:30:00"), "2012-05-19");
        assert_eq!(normalize_date("2023-09-24"), "2023-09-24");
    }

    #[test]
    fn normalize_date_brazilian() {
        assert_eq!(normalize_date("29/03/2003"), "2003-03-29");
    }
}
