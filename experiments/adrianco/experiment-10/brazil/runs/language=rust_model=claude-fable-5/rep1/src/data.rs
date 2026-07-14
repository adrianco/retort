//! Dataset loading: parses the six Kaggle CSV files into a unified
//! in-memory store with normalized team names and deduplicated matches.

use std::collections::HashMap;
use std::path::Path;

use chrono::NaiveDate;
use serde::Deserialize;

use crate::normalize::{canonical_team, fold_text};

/// Canonical competition names.
pub const SERIE_A: &str = "Brasileirão Série A";
pub const SERIE_B: &str = "Brasileirão Série B";
pub const SERIE_C: &str = "Brasileirão Série C";
pub const COPA_DO_BRASIL: &str = "Copa do Brasil";
pub const LIBERTADORES: &str = "Copa Libertadores";

/// Which CSV file a match came from (priority order for deduplication).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Source {
    /// Brasileirao_Matches.csv (2012+ Série A; richest naming).
    Brasileirao,
    /// Brazilian_Cup_Matches.csv.
    Cup,
    /// Libertadores_Matches.csv.
    Libertadores,
    /// novo_campeonato_brasileiro.csv (2003-2019 Série A).
    Historical,
    /// BR-Football-Dataset.csv (extended stats, several tournaments).
    Extended,
}

impl Source {
    pub fn name(self) -> &'static str {
        match self {
            Source::Brasileirao => "Brasileirao_Matches.csv",
            Source::Cup => "Brazilian_Cup_Matches.csv",
            Source::Libertadores => "Libertadores_Matches.csv",
            Source::Historical => "novo_campeonato_brasileiro.csv",
            Source::Extended => "BR-Football-Dataset.csv",
        }
    }

    /// Higher wins when two files describe the same fixture.
    fn priority(self) -> u8 {
        match self {
            Source::Brasileirao | Source::Cup | Source::Libertadores => 3,
            Source::Historical => 2,
            Source::Extended => 1,
        }
    }
}

/// Extra in-match statistics available only in BR-Football-Dataset.csv.
#[derive(Debug, Clone, Default)]
pub struct MatchStats {
    pub home_corners: Option<i32>,
    pub away_corners: Option<i32>,
    pub home_shots: Option<i32>,
    pub away_shots: Option<i32>,
    pub home_attacks: Option<i32>,
    pub away_attacks: Option<i32>,
}

/// A single match, normalized across all source files.
#[derive(Debug, Clone)]
pub struct Match {
    pub competition: &'static str,
    pub date: Option<NaiveDate>,
    pub home: String,
    pub away: String,
    pub home_key: String,
    pub away_key: String,
    pub home_goals: i32,
    pub away_goals: i32,
    pub season: i32,
    pub round: Option<String>,
    pub stage: Option<String>,
    pub stadium: Option<String>,
    pub source: Source,
    pub stats: MatchStats,
}

impl Match {
    pub fn winner_key(&self) -> Option<&str> {
        if self.home_goals > self.away_goals {
            Some(&self.home_key)
        } else if self.away_goals > self.home_goals {
            Some(&self.away_key)
        } else {
            None
        }
    }

    pub fn date_str(&self) -> String {
        self.date
            .map(|d| d.format("%Y-%m-%d").to_string())
            .unwrap_or_else(|| "unknown date".into())
    }
}

/// A FIFA player record (only the columns the server uses).
#[derive(Debug, Clone)]
pub struct Player {
    pub id: i64,
    pub name: String,
    pub name_folded: String,
    pub age: Option<i32>,
    pub nationality: String,
    pub nationality_folded: String,
    pub overall: i32,
    pub potential: i32,
    pub club: String,
    pub club_folded: String,
    pub position: String,
    pub jersey_number: Option<i32>,
    pub height: String,
    pub weight: String,
    pub value: String,
    pub wage: String,
    pub preferred_foot: String,
    pub skills: Vec<(&'static str, i32)>,
}

/// The fully loaded, query-ready dataset.
pub struct Store {
    /// All matches after deduplication across the overlapping files.
    pub matches: Vec<Match>,
    /// Raw row counts per source file (before dedup), for reporting.
    pub raw_counts: Vec<(&'static str, usize)>,
    pub players: Vec<Player>,
}

fn parse_date(s: &str) -> Option<NaiveDate> {
    let s = s.trim();
    if s.is_empty() {
        return None;
    }
    let date_part = s.split_whitespace().next().unwrap_or(s);
    NaiveDate::parse_from_str(date_part, "%Y-%m-%d")
        .or_else(|_| NaiveDate::parse_from_str(date_part, "%d/%m/%Y"))
        .ok()
}

fn parse_goals(s: &str) -> Option<i32> {
    let s = s.trim();
    if s.is_empty() {
        return None;
    }
    s.parse::<i32>()
        .ok()
        .or_else(|| s.parse::<f64>().ok().map(|f| f.round() as i32))
}

fn parse_opt_int(s: &str) -> Option<i32> {
    parse_goals(s)
}

#[derive(Deserialize)]
struct BrasileiraoRow {
    datetime: String,
    home_team: String,
    away_team: String,
    home_goal: String,
    away_goal: String,
    season: String,
    round: String,
}

#[derive(Deserialize)]
struct CupRow {
    round: String,
    datetime: String,
    home_team: String,
    away_team: String,
    home_goal: String,
    away_goal: String,
    season: String,
}

#[derive(Deserialize)]
struct LibertadoresRow {
    datetime: String,
    home_team: String,
    away_team: String,
    home_goal: String,
    away_goal: String,
    season: String,
    stage: String,
}

#[derive(Deserialize)]
struct HistoricalRow {
    #[serde(rename = "Data")]
    data: String,
    #[serde(rename = "Ano")]
    ano: String,
    #[serde(rename = "Rodada")]
    rodada: String,
    #[serde(rename = "Equipe_mandante")]
    home: String,
    #[serde(rename = "Equipe_visitante")]
    away: String,
    #[serde(rename = "Gols_mandante")]
    home_goals: String,
    #[serde(rename = "Gols_visitante")]
    away_goals: String,
    #[serde(rename = "Arena")]
    arena: String,
}

#[derive(Deserialize)]
struct ExtendedRow {
    tournament: String,
    home: String,
    home_goal: String,
    away_goal: String,
    away: String,
    home_corner: String,
    away_corner: String,
    home_attack: String,
    away_attack: String,
    home_shots: String,
    away_shots: String,
    date: String,
}

fn reader(path: &Path) -> Result<csv::Reader<std::fs::File>, String> {
    csv::ReaderBuilder::new()
        .flexible(true)
        .trim(csv::Trim::All)
        .from_path(path)
        .map_err(|e| format!("cannot open {}: {}", path.display(), e))
}

#[allow(clippy::too_many_arguments)]
fn make_match(
    competition: &'static str,
    date: Option<NaiveDate>,
    home: &str,
    away: &str,
    home_goals: i32,
    away_goals: i32,
    season: i32,
    source: Source,
) -> Match {
    let h = canonical_team(home);
    let a = canonical_team(away);
    Match {
        competition,
        date,
        home: h.display,
        away: a.display,
        home_key: h.key,
        away_key: a.key,
        home_goals,
        away_goals,
        season,
        round: None,
        stage: None,
        stadium: None,
        source,
        stats: MatchStats::default(),
    }
}

impl Store {
    /// Load every CSV file under `data_dir` (e.g. `data/kaggle`).
    pub fn load(data_dir: &Path) -> Result<Store, String> {
        let mut matches: Vec<Match> = Vec::new();
        let mut raw_counts = Vec::new();

        // 1. Brasileirão Série A (2012+).
        let mut n = 0;
        for row in reader(&data_dir.join("Brasileirao_Matches.csv"))?.deserialize() {
            let row: BrasileiraoRow = row.map_err(|e| format!("Brasileirao_Matches: {e}"))?;
            n += 1;
            let (Some(hg), Some(ag)) = (parse_goals(&row.home_goal), parse_goals(&row.away_goal))
            else {
                continue;
            };
            let season = row.season.trim().parse().unwrap_or(0);
            let mut m = make_match(
                SERIE_A,
                parse_date(&row.datetime),
                &row.home_team,
                &row.away_team,
                hg,
                ag,
                season,
                Source::Brasileirao,
            );
            m.round = Some(row.round.trim().to_string());
            matches.push(m);
        }
        raw_counts.push((Source::Brasileirao.name(), n));

        // 2. Copa do Brasil.
        let mut cup_rows: Vec<(Match, i32)> = Vec::new();
        let mut n = 0;
        for row in reader(&data_dir.join("Brazilian_Cup_Matches.csv"))?.deserialize() {
            let row: CupRow = row.map_err(|e| format!("Brazilian_Cup_Matches: {e}"))?;
            n += 1;
            let (Some(hg), Some(ag)) = (parse_goals(&row.home_goal), parse_goals(&row.away_goal))
            else {
                continue;
            };
            let season = row.season.trim().parse().unwrap_or(0);
            let round_num = row.round.trim().parse::<i32>().unwrap_or(0);
            let mut m = make_match(
                COPA_DO_BRASIL,
                parse_date(&row.datetime),
                &row.home_team,
                &row.away_team,
                hg,
                ag,
                season,
                Source::Cup,
            );
            m.round = Some(row.round.trim().to_string());
            cup_rows.push((m, round_num));
        }
        raw_counts.push((Source::Cup.name(), n));
        // The cup's last round each season is the final; label it so that
        // questions like "find all Copa do Brasil finals" work. A final is a
        // two-legged tie at most, so seasons whose data is truncated mid-
        // tournament (their "last" round holds many matches) are left alone.
        let mut max_round: HashMap<i32, i32> = HashMap::new();
        for (m, r) in &cup_rows {
            let e = max_round.entry(m.season).or_insert(0);
            *e = (*e).max(*r);
        }
        let mut max_round_count: HashMap<i32, usize> = HashMap::new();
        for (m, r) in &cup_rows {
            if *r == max_round[&m.season] {
                *max_round_count.entry(m.season).or_insert(0) += 1;
            }
        }
        for (mut m, r) in cup_rows {
            if r > 0 && r == max_round[&m.season] && max_round_count[&m.season] <= 2 {
                m.stage = Some("Final".into());
            }
            matches.push(m);
        }

        // 3. Copa Libertadores.
        let mut n = 0;
        for row in reader(&data_dir.join("Libertadores_Matches.csv"))?.deserialize() {
            let row: LibertadoresRow = row.map_err(|e| format!("Libertadores_Matches: {e}"))?;
            n += 1;
            let (Some(hg), Some(ag)) = (parse_goals(&row.home_goal), parse_goals(&row.away_goal))
            else {
                continue;
            };
            let season = row.season.trim().parse().unwrap_or(0);
            let mut m = make_match(
                LIBERTADORES,
                parse_date(&row.datetime),
                &row.home_team,
                &row.away_team,
                hg,
                ag,
                season,
                Source::Libertadores,
            );
            let stage = row.stage.trim();
            if !stage.is_empty() {
                m.stage = Some(stage.to_string());
            }
            matches.push(m);
        }
        raw_counts.push((Source::Libertadores.name(), n));

        // 4. Historical Brasileirão 2003-2019.
        let mut n = 0;
        for row in reader(&data_dir.join("novo_campeonato_brasileiro.csv"))?.deserialize() {
            let row: HistoricalRow = row.map_err(|e| format!("novo_campeonato_brasileiro: {e}"))?;
            n += 1;
            let (Some(hg), Some(ag)) =
                (parse_goals(&row.home_goals), parse_goals(&row.away_goals))
            else {
                continue;
            };
            let season = row.ano.trim().parse().unwrap_or(0);
            let mut m = make_match(
                SERIE_A,
                parse_date(&row.data),
                &row.home,
                &row.away,
                hg,
                ag,
                season,
                Source::Historical,
            );
            m.round = Some(row.rodada.trim().to_string());
            let arena = row.arena.trim();
            if !arena.is_empty() {
                m.stadium = Some(arena.to_string());
            }
            matches.push(m);
        }
        raw_counts.push((Source::Historical.name(), n));

        // 5. Extended stats dataset (Série A/B/C + Copa do Brasil).
        let mut n = 0;
        for row in reader(&data_dir.join("BR-Football-Dataset.csv"))?.deserialize() {
            let row: ExtendedRow = row.map_err(|e| format!("BR-Football-Dataset: {e}"))?;
            n += 1;
            let (Some(hg), Some(ag)) = (parse_goals(&row.home_goal), parse_goals(&row.away_goal))
            else {
                continue;
            };
            let competition = match row.tournament.trim() {
                "Serie A" => SERIE_A,
                "Serie B" => SERIE_B,
                "Serie C" => SERIE_C,
                "Copa do Brasil" => COPA_DO_BRASIL,
                _ => SERIE_A,
            };
            let date = parse_date(&row.date);
            let season = date.map(|d| {
                use chrono::Datelike;
                d.year()
            });
            let mut m = make_match(
                competition,
                date,
                &row.home,
                &row.away,
                hg,
                ag,
                season.unwrap_or(0),
                Source::Extended,
            );
            m.stats = MatchStats {
                home_corners: parse_opt_int(&row.home_corner),
                away_corners: parse_opt_int(&row.away_corner),
                home_shots: parse_opt_int(&row.home_shots),
                away_shots: parse_opt_int(&row.away_shots),
                home_attacks: parse_opt_int(&row.home_attack),
                away_attacks: parse_opt_int(&row.away_attack),
            };
            matches.push(m);
        }
        raw_counts.push((Source::Extended.name(), n));

        let matches = dedupe(matches);
        let players = load_players(&data_dir.join("fifa_data.csv"))?;

        Ok(Store {
            matches,
            raw_counts,
            players,
        })
    }

    /// Matches usable for Série A standings of one season. The deduplication
    /// pass guarantees each fixture appears once, so the union of all source
    /// files is safe — and necessary, because some files are mid-season
    /// snapshots whose final rounds only exist in another file.
    pub fn serie_a_season(&self, season: i32) -> Vec<&Match> {
        self.matches
            .iter()
            .filter(|m| m.competition == SERIE_A && m.season == season)
            .collect()
    }
}

type DedupeKey = (&'static str, i32, String, String, Option<NaiveDate>);

/// Identity of a fixture for cross-file deduplication.
///
/// In the league competitions and the cup, a given (home, away) pairing
/// occurs at most once per season, and the overlapping files sometimes
/// disagree on the exact date of the same fixture — so the key is
/// (competition, season, home, away). The Libertadores comes from a single
/// file where the same pairing can legitimately repeat within a season
/// (group stage + knockout), so there the date disambiguates.
fn dedupe_key(m: &Match) -> DedupeKey {
    let date = if m.competition == LIBERTADORES {
        m.date
    } else {
        None
    };
    (
        m.competition,
        m.season,
        m.home_key.clone(),
        m.away_key.clone(),
        date,
    )
}

/// Deduplicate fixtures that appear in more than one file. The
/// higher-priority source wins; extended stats (corners/shots) and any
/// missing fields are merged into the surviving record.
fn dedupe(matches: Vec<Match>) -> Vec<Match> {
    let mut by_key: HashMap<DedupeKey, usize> = HashMap::new();
    let mut out: Vec<Match> = Vec::new();
    for m in matches {
        let key = dedupe_key(&m);
        match by_key.get(&key) {
            None => {
                by_key.insert(key, out.len());
                out.push(m);
            }
            Some(&idx) => {
                // Within one file a repeated (season, home, away) pairing is
                // usually a real second match (e.g. a replayed fixture), so
                // same-source records only merge when they are exact
                // duplicates; cross-source hits are the same fixture seen
                // through two datasets.
                if m.source == out[idx].source
                    && !(m.date == out[idx].date
                        && m.home_goals == out[idx].home_goals
                        && m.away_goals == out[idx].away_goals)
                {
                    out.push(m);
                    continue;
                }
                let keep_new = m.source.priority() > out[idx].source.priority();
                let (kept, dropped) = if keep_new {
                    let old = std::mem::replace(&mut out[idx], m);
                    (&mut out[idx], old)
                } else {
                    (&mut out[idx], m)
                };
                // Merge fields only the dropped record had.
                if kept.stats.home_corners.is_none() {
                    kept.stats = dropped.stats;
                }
                if kept.round.is_none() {
                    kept.round = dropped.round;
                }
                if kept.stage.is_none() {
                    kept.stage = dropped.stage;
                }
                if kept.stadium.is_none() {
                    kept.stadium = dropped.stadium;
                }
                if kept.date.is_none() {
                    kept.date = dropped.date;
                }
            }
        }
    }
    out
}

fn load_players(path: &Path) -> Result<Vec<Player>, String> {
    let mut rdr = reader(path)?;
    let headers = rdr
        .headers()
        .map_err(|e| format!("fifa_data: {e}"))?
        .clone();
    let idx = |name: &str| -> Option<usize> {
        headers
            .iter()
            .position(|h| h.trim_start_matches('\u{feff}') == name)
    };
    let col = |rec: &csv::StringRecord, i: Option<usize>| -> String {
        i.and_then(|i| rec.get(i)).unwrap_or("").trim().to_string()
    };

    let i_id = idx("ID");
    let i_name = idx("Name");
    let i_age = idx("Age");
    let i_nat = idx("Nationality");
    let i_overall = idx("Overall");
    let i_potential = idx("Potential");
    let i_club = idx("Club");
    let i_pos = idx("Position");
    let i_jersey = idx("Jersey Number");
    let i_height = idx("Height");
    let i_weight = idx("Weight");
    let i_value = idx("Value");
    let i_wage = idx("Wage");
    let i_foot = idx("Preferred Foot");
    let skill_cols: Vec<(&'static str, Option<usize>)> = vec![
        ("Crossing", idx("Crossing")),
        ("Finishing", idx("Finishing")),
        ("Dribbling", idx("Dribbling")),
        ("ShortPassing", idx("ShortPassing")),
        ("BallControl", idx("BallControl")),
        ("SprintSpeed", idx("SprintSpeed")),
        ("ShotPower", idx("ShotPower")),
        ("Vision", idx("Vision")),
        ("Composure", idx("Composure")),
        ("StandingTackle", idx("StandingTackle")),
        ("GKDiving", idx("GKDiving")),
        ("GKReflexes", idx("GKReflexes")),
    ];

    let mut players = Vec::new();
    for rec in rdr.records() {
        let rec = rec.map_err(|e| format!("fifa_data: {e}"))?;
        let name = col(&rec, i_name);
        if name.is_empty() {
            continue;
        }
        let nationality = col(&rec, i_nat);
        let club = col(&rec, i_club);
        let skills = skill_cols
            .iter()
            .filter_map(|(label, i)| {
                col(&rec, *i).parse::<i32>().ok().map(|v| (*label, v))
            })
            .collect();
        players.push(Player {
            id: col(&rec, i_id).parse().unwrap_or(0),
            name_folded: fold_text(&name),
            name,
            age: col(&rec, i_age).parse().ok(),
            nationality_folded: fold_text(&nationality),
            nationality,
            overall: col(&rec, i_overall).parse().unwrap_or(0),
            potential: col(&rec, i_potential).parse().unwrap_or(0),
            club_folded: fold_text(&club),
            club,
            position: col(&rec, i_pos),
            jersey_number: col(&rec, i_jersey)
                .parse::<f64>()
                .ok()
                .map(|v| v as i32),
            height: col(&rec, i_height),
            weight: col(&rec, i_weight),
            value: col(&rec, i_value),
            wage: col(&rec, i_wage),
            preferred_foot: col(&rec, i_foot),
            skills,
        });
    }
    Ok(players)
}
