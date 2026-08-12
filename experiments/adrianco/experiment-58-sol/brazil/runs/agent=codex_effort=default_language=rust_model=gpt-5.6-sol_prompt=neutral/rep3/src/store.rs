use crate::model::*;
use crate::normalize::{
    competition_key, display_competition, fold, parse_date, team_key, team_matches,
};
use anyhow::{Context, Result};
use chrono::{Datelike, Duration, NaiveDate};
use csv::{ReaderBuilder, StringRecord};
use serde::Serialize;
use std::collections::{HashMap, HashSet};
use std::path::Path;

#[derive(Debug, Clone)]
pub struct SoccerStore {
    matches: Vec<MatchRecord>,
    players: Vec<Player>,
    counts: DatasetCounts,
    unique_match_indices: Vec<usize>,
}

impl SoccerStore {
    pub fn load(data_dir: impl AsRef<Path>) -> Result<Self> {
        let data_dir = data_dir.as_ref();
        let mut store = Self {
            matches: Vec::new(),
            players: Vec::new(),
            counts: DatasetCounts::default(),
            unique_match_indices: Vec::new(),
        };
        store.load_standard_matches(
            &data_dir.join("Brasileirao_Matches.csv"),
            "Brasileirao_Matches.csv",
            "Brasileirão",
        )?;
        store.load_standard_matches(
            &data_dir.join("Brazilian_Cup_Matches.csv"),
            "Brazilian_Cup_Matches.csv",
            "Copa do Brasil",
        )?;
        store.load_standard_matches(
            &data_dir.join("Libertadores_Matches.csv"),
            "Libertadores_Matches.csv",
            "Copa Libertadores",
        )?;
        store.load_extended_matches(&data_dir.join("BR-Football-Dataset.csv"))?;
        store.load_historical_matches(&data_dir.join("novo_campeonato_brasileiro.csv"))?;
        store.load_players(&data_dir.join("fifa_data.csv"))?;
        store.counts.total_matches = store.matches.len();
        store.counts.total_players = store.players.len();
        store.unique_match_indices = store.build_unique_match_indices(None);
        store.counts.unique_matches = store.unique_match_indices.len();
        Ok(store)
    }

    pub fn counts(&self) -> &DatasetCounts {
        &self.counts
    }
    pub fn matches(&self) -> &[MatchRecord] {
        &self.matches
    }
    pub fn players(&self) -> &[Player] {
        &self.players
    }

    fn reader(path: &Path) -> Result<csv::Reader<std::fs::File>> {
        ReaderBuilder::new()
            .flexible(true)
            .from_path(path)
            .with_context(|| format!("failed to open required dataset {}", path.display()))
    }

    fn load_standard_matches(
        &mut self,
        path: &Path,
        source: &str,
        competition: &str,
    ) -> Result<()> {
        let mut reader = Self::reader(path)?;
        let headers = reader.headers()?.clone();
        let map = HeaderMap::new(&headers);
        let mut loaded = 0;
        for (line, row) in reader.records().enumerate() {
            let row = row.with_context(|| {
                format!("invalid CSV record at {}:{}", path.display(), line + 2)
            })?;
            let Some(date) = parse_date(map.get(&row, "datetime")) else {
                continue;
            };
            let home = map.get(&row, "home_team").trim();
            let away = map.get(&row, "away_team").trim();
            let Some(home_goals) = parse_goal(map.get(&row, "home_goal")) else {
                continue;
            };
            let Some(away_goals) = parse_goal(map.get(&row, "away_goal")) else {
                continue;
            };
            if home.is_empty() || away.is_empty() {
                continue;
            }
            self.matches.push(MatchRecord {
                date,
                season: parse_u16(map.get(&row, "season")).unwrap_or(date.year() as u16),
                competition: competition.into(),
                home_team: home.into(),
                away_team: away.into(),
                home_goals,
                away_goals,
                round: nonempty(map.get(&row, "round")),
                stage: nonempty(map.get(&row, "stage")),
                stadium: None,
                source: source.into(),
                home_corners: None,
                away_corners: None,
                home_shots: None,
                away_shots: None,
            });
            loaded += 1;
        }
        self.counts.matches_by_source.insert(source.into(), loaded);
        Ok(())
    }

    fn load_extended_matches(&mut self, path: &Path) -> Result<()> {
        let source = "BR-Football-Dataset.csv";
        let mut reader = Self::reader(path)?;
        let headers = reader.headers()?.clone();
        let map = HeaderMap::new(&headers);
        let mut loaded = 0;
        for (line, row) in reader.records().enumerate() {
            let row = row.with_context(|| {
                format!("invalid CSV record at {}:{}", path.display(), line + 2)
            })?;
            let Some(date) = parse_date(map.get(&row, "date")) else {
                continue;
            };
            let Some(home_goals) = parse_goal(map.get(&row, "home_goal")) else {
                continue;
            };
            let Some(away_goals) = parse_goal(map.get(&row, "away_goal")) else {
                continue;
            };
            let home = map.get(&row, "home").trim();
            let away = map.get(&row, "away").trim();
            if home.is_empty() || away.is_empty() {
                continue;
            }
            let competition = display_competition(map.get(&row, "tournament"));
            self.matches.push(MatchRecord {
                date,
                season: date.year() as u16,
                competition,
                home_team: home.into(),
                away_team: away.into(),
                home_goals,
                away_goals,
                round: None,
                stage: None,
                stadium: None,
                source: source.into(),
                home_corners: parse_goal(map.get(&row, "home_corner")),
                away_corners: parse_goal(map.get(&row, "away_corner")),
                home_shots: parse_goal(map.get(&row, "home_shots")),
                away_shots: parse_goal(map.get(&row, "away_shots")),
            });
            loaded += 1;
        }
        self.counts.matches_by_source.insert(source.into(), loaded);
        Ok(())
    }

    fn load_historical_matches(&mut self, path: &Path) -> Result<()> {
        let source = "novo_campeonato_brasileiro.csv";
        let mut reader = Self::reader(path)?;
        let headers = reader.headers()?.clone();
        let map = HeaderMap::new(&headers);
        let mut loaded = 0;
        for (line, row) in reader.records().enumerate() {
            let row = row.with_context(|| {
                format!("invalid CSV record at {}:{}", path.display(), line + 2)
            })?;
            let Some(date) = parse_date(map.get(&row, "Data")) else {
                continue;
            };
            let Some(home_goals) = parse_goal(map.get(&row, "Gols_mandante")) else {
                continue;
            };
            let Some(away_goals) = parse_goal(map.get(&row, "Gols_visitante")) else {
                continue;
            };
            let home = map.get(&row, "Equipe_mandante").trim();
            let away = map.get(&row, "Equipe_visitante").trim();
            if home.is_empty() || away.is_empty() {
                continue;
            }
            self.matches.push(MatchRecord {
                date,
                season: parse_u16(map.get(&row, "Ano")).unwrap_or(date.year() as u16),
                competition: "Brasileirão".into(),
                home_team: home.into(),
                away_team: away.into(),
                home_goals,
                away_goals,
                round: nonempty(map.get(&row, "Rodada")),
                stage: None,
                stadium: nonempty(map.get(&row, "Arena")),
                source: source.into(),
                home_corners: None,
                away_corners: None,
                home_shots: None,
                away_shots: None,
            });
            loaded += 1;
        }
        self.counts.matches_by_source.insert(source.into(), loaded);
        Ok(())
    }

    fn load_players(&mut self, path: &Path) -> Result<()> {
        let source = "fifa_data.csv";
        let mut reader = Self::reader(path)?;
        let headers = reader.headers()?.clone();
        let map = HeaderMap::new(&headers);
        let skill_names = [
            "Crossing",
            "Finishing",
            "Dribbling",
            "ShortPassing",
            "LongPassing",
            "BallControl",
            "ShotPower",
            "Stamina",
            "Strength",
            "GKDiving",
            "GKHandling",
            "GKReflexes",
        ];
        let mut loaded = 0;
        for (line, row) in reader.records().enumerate() {
            let row = row.with_context(|| {
                format!("invalid CSV record at {}:{}", path.display(), line + 2)
            })?;
            let name = map.get(&row, "Name").trim();
            if name.is_empty() {
                continue;
            }
            let attributes = skill_names
                .iter()
                .filter_map(|name| parse_u8(map.get(&row, name)).map(|v| ((*name).into(), v)))
                .collect();
            self.players.push(Player {
                id: map.get(&row, "ID").trim().parse().unwrap_or(0),
                name: name.into(),
                age: parse_u8(map.get(&row, "Age")),
                nationality: map.get(&row, "Nationality").trim().into(),
                overall: parse_u8(map.get(&row, "Overall")),
                potential: parse_u8(map.get(&row, "Potential")),
                club: nonempty(map.get(&row, "Club")),
                position: nonempty(map.get(&row, "Position")),
                jersey_number: parse_goal(map.get(&row, "Jersey Number"))
                    .and_then(|n| u8::try_from(n).ok()),
                height: nonempty(map.get(&row, "Height")),
                weight: nonempty(map.get(&row, "Weight")),
                attributes,
            });
            loaded += 1;
        }
        self.counts.players_by_source.insert(source.into(), loaded);
        Ok(())
    }

    pub fn search_matches(&self, filter: &MatchFilter<'_>, limit: usize) -> Vec<&MatchRecord> {
        let mut rows: Vec<_> = self
            .unique_match_indices(filter.source)
            .into_iter()
            .map(|index| &self.matches[index])
            .filter(|m| match_filter(m, filter))
            .collect();
        rows.sort_by(|a, b| {
            b.date
                .cmp(&a.date)
                .then_with(|| a.home_team.cmp(&b.home_team))
        });
        if limit != usize::MAX {
            rows.truncate(limit.min(1000));
        }
        rows
    }

    pub fn team_statistics(
        &self,
        team: &str,
        season: Option<u16>,
        competition: Option<&str>,
        venue: Option<&str>,
    ) -> TeamStats {
        let filter = MatchFilter {
            team: Some(team),
            season,
            competition,
            ..Default::default()
        };
        let rows = self.search_matches(&filter, usize::MAX);
        let mut stats = TeamStats {
            team: team.into(),
            ..Default::default()
        };
        for m in rows {
            let home = team_matches(&m.home_team, team);
            if venue == Some("home") && !home || venue == Some("away") && home {
                continue;
            }
            apply_match(&mut stats, m, home);
        }
        stats
    }

    pub fn head_to_head(
        &self,
        team_a: &str,
        team_b: &str,
        season: Option<u16>,
        competition: Option<&str>,
    ) -> (HeadToHead, Vec<&MatchRecord>) {
        let filter = MatchFilter {
            team: Some(team_a),
            opponent: Some(team_b),
            season,
            competition,
            ..Default::default()
        };
        let rows = self.search_matches(&filter, 1000);
        let mut result = HeadToHead {
            team_a: team_a.into(),
            team_b: team_b.into(),
            ..Default::default()
        };
        for m in &rows {
            let a_home = team_matches(&m.home_team, team_a);
            let (a_goals, b_goals) = if a_home {
                (m.home_goals, m.away_goals)
            } else {
                (m.away_goals, m.home_goals)
            };
            result.matches += 1;
            result.team_a_goals += a_goals as u32;
            result.team_b_goals += b_goals as u32;
            match a_goals.cmp(&b_goals) {
                std::cmp::Ordering::Greater => result.team_a_wins += 1,
                std::cmp::Ordering::Less => result.team_b_wins += 1,
                std::cmp::Ordering::Equal => result.draws += 1,
            }
        }
        (result, rows)
    }

    pub fn search_players(
        &self,
        name: Option<&str>,
        nationality: Option<&str>,
        club: Option<&str>,
        position: Option<&str>,
        min_overall: Option<u8>,
        limit: usize,
    ) -> Vec<&Player> {
        let mut rows: Vec<_> = self
            .players
            .iter()
            .filter(|p| {
                name.map(|q| fold(&p.name).contains(&fold(q)))
                    .unwrap_or(true)
                    && nationality
                        .map(|q| fold(&p.nationality).contains(&fold(q)))
                        .unwrap_or(true)
                    && club
                        .map(|q| {
                            p.club
                                .as_deref()
                                .map(|v| team_matches(v, q) || fold(v).contains(&fold(q)))
                                .unwrap_or(false)
                        })
                        .unwrap_or(true)
                    && position
                        .map(|q| {
                            p.position
                                .as_deref()
                                .map(|v| fold(v).contains(&fold(q)))
                                .unwrap_or(false)
                        })
                        .unwrap_or(true)
                    && min_overall
                        .map(|min| p.overall.unwrap_or(0) >= min)
                        .unwrap_or(true)
            })
            .collect();
        rows.sort_by(|a, b| b.overall.cmp(&a.overall).then_with(|| a.name.cmp(&b.name)));
        rows.truncate(limit.min(1000));
        rows
    }

    pub fn standings(&self, season: u16, competition: &str) -> Vec<Standing> {
        let filter = MatchFilter {
            season: Some(season),
            competition: Some(competition),
            ..Default::default()
        };
        let rows = self.search_matches(&filter, usize::MAX);
        let mut by_team: HashMap<String, TeamStats> = HashMap::new();
        for m in rows {
            let home_key = team_key(&m.home_team);
            let away_key = team_key(&m.away_team);
            apply_match(
                by_team
                    .entry(home_key.clone())
                    .or_insert_with(|| TeamStats {
                        team: display_team(&m.home_team),
                        ..Default::default()
                    }),
                m,
                true,
            );
            apply_match(
                by_team
                    .entry(away_key.clone())
                    .or_insert_with(|| TeamStats {
                        team: display_team(&m.away_team),
                        ..Default::default()
                    }),
                m,
                false,
            );
        }
        let mut stats: Vec<_> = by_team.into_values().collect();
        stats.sort_by(|a, b| {
            b.points
                .cmp(&a.points)
                .then_with(|| b.goal_difference().cmp(&a.goal_difference()))
                .then_with(|| b.goals_for.cmp(&a.goals_for))
                .then_with(|| a.team.cmp(&b.team))
        });
        stats
            .into_iter()
            .enumerate()
            .map(|(i, stats)| Standing {
                position: i + 1,
                team: stats.team.clone(),
                stats,
            })
            .collect()
    }

    pub fn competition_statistics(
        &self,
        competition: &str,
        season: Option<u16>,
    ) -> CompetitionStats {
        let filter = MatchFilter {
            competition: Some(competition),
            season,
            ..Default::default()
        };
        let rows = self.search_matches(&filter, usize::MAX);
        let mut result = CompetitionStats {
            competition: display_competition(competition),
            season,
            matches: rows.len(),
            goals: 0,
            goals_per_match: 0.0,
            home_wins: 0,
            away_wins: 0,
            draws: 0,
            home_win_rate: 0.0,
        };
        for m in rows {
            result.goals += (m.home_goals + m.away_goals) as u64;
            match m.home_goals.cmp(&m.away_goals) {
                std::cmp::Ordering::Greater => result.home_wins += 1,
                std::cmp::Ordering::Less => result.away_wins += 1,
                std::cmp::Ordering::Equal => result.draws += 1,
            }
        }
        if result.matches > 0 {
            result.goals_per_match = result.goals as f64 / result.matches as f64;
            result.home_win_rate = result.home_wins as f64 * 100.0 / result.matches as f64;
        }
        result
    }

    pub fn biggest_wins(
        &self,
        competition: Option<&str>,
        season: Option<u16>,
        limit: usize,
    ) -> Vec<&MatchRecord> {
        let filter = MatchFilter {
            competition,
            season,
            ..Default::default()
        };
        let mut rows = self.search_matches(&filter, usize::MAX);
        rows.sort_by(|a, b| {
            goal_margin(b)
                .cmp(&goal_margin(a))
                .then_with(|| b.date.cmp(&a.date))
        });
        rows.truncate(limit.min(100));
        rows
    }

    pub fn competitions_for_team(&self, team: &str) -> Vec<String> {
        let mut values: Vec<_> = self
            .search_matches(
                &MatchFilter {
                    team: Some(team),
                    ..Default::default()
                },
                usize::MAX,
            )
            .into_iter()
            .map(|m| m.competition.clone())
            .collect::<HashSet<_>>()
            .into_iter()
            .collect();
        values.sort();
        values
    }

    fn unique_match_indices(&self, source: Option<&str>) -> Vec<usize> {
        match source {
            None => self.unique_match_indices.clone(),
            Some(source) => self.build_unique_match_indices(Some(source)),
        }
    }

    fn build_unique_match_indices(&self, source: Option<&str>) -> Vec<usize> {
        let mut seen: HashMap<FixtureKey, usize> = HashMap::new();
        let mut result = Vec::new();
        for (index, m) in self.matches.iter().enumerate() {
            if source.map(|s| fold(&m.source) != fold(s)).unwrap_or(false) {
                continue;
            }
            let base = FixtureKey::new(m, m.date);
            let duplicate = [-1_i64, 0, 1].into_iter().find_map(|offset| {
                let date = m.date.checked_add_signed(Duration::days(offset))?;
                seen.get(&FixtureKey {
                    date,
                    ..base.clone()
                })
                .copied()
            });
            if duplicate.is_none() {
                seen.insert(base, index);
                result.push(index);
            }
        }
        result
    }
}

#[derive(Clone, Debug, Eq, Hash, PartialEq)]
struct FixtureKey {
    date: NaiveDate,
    season: u16,
    competition: String,
    home_team: String,
    away_team: String,
}

impl FixtureKey {
    fn new(record: &MatchRecord, date: NaiveDate) -> Self {
        Self {
            date,
            season: record.season,
            competition: competition_key(&record.competition),
            home_team: team_key(&record.home_team),
            away_team: team_key(&record.away_team),
        }
    }
}

fn match_filter(m: &MatchRecord, filter: &MatchFilter<'_>) -> bool {
    let team_ok = filter
        .team
        .map(|team| team_matches(&m.home_team, team) || team_matches(&m.away_team, team))
        .unwrap_or(true);
    let opponent_ok = filter
        .opponent
        .map(|team| team_matches(&m.home_team, team) || team_matches(&m.away_team, team))
        .unwrap_or(true);
    team_ok
        && opponent_ok
        && filter
            .competition
            .map(|c| competition_key(&m.competition) == competition_key(c))
            .unwrap_or(true)
        && filter.season.map(|s| m.season == s).unwrap_or(true)
        && filter.start_date.map(|d| m.date >= d).unwrap_or(true)
        && filter.end_date.map(|d| m.date <= d).unwrap_or(true)
        && filter
            .stage
            .map(|s| {
                m.stage
                    .as_deref()
                    .map(|v| fold(v).contains(&fold(s)))
                    .unwrap_or(false)
                    || m.round
                        .as_deref()
                        .map(|v| fold(v).contains(&fold(s)))
                        .unwrap_or(false)
            })
            .unwrap_or(true)
}

fn apply_match(stats: &mut TeamStats, m: &MatchRecord, home: bool) {
    let (for_goals, against_goals) = if home {
        (m.home_goals, m.away_goals)
    } else {
        (m.away_goals, m.home_goals)
    };
    stats.matches += 1;
    stats.goals_for += for_goals as u32;
    stats.goals_against += against_goals as u32;
    if home {
        stats.home_matches += 1
    } else {
        stats.away_matches += 1
    }
    match for_goals.cmp(&against_goals) {
        std::cmp::Ordering::Greater => {
            stats.wins += 1;
            stats.points += 3;
        }
        std::cmp::Ordering::Equal => {
            stats.draws += 1;
            stats.points += 1;
        }
        std::cmp::Ordering::Less => stats.losses += 1,
    }
}

fn display_team(value: &str) -> String {
    let key = team_key(value);
    key.split_whitespace()
        .map(|word| {
            let mut chars = word.chars();
            match chars.next() {
                None => String::new(),
                Some(first) => first.to_uppercase().collect::<String>() + chars.as_str(),
            }
        })
        .collect::<Vec<_>>()
        .join(" ")
}

fn goal_margin(m: &MatchRecord) -> u16 {
    m.home_goals.abs_diff(m.away_goals)
}
fn parse_goal(value: &str) -> Option<u16> {
    value
        .trim()
        .parse::<u16>()
        .ok()
        .or_else(|| value.trim().parse::<f64>().ok().map(|v| v as u16))
}
fn parse_u16(value: &str) -> Option<u16> {
    value.trim().parse().ok()
}
fn parse_u8(value: &str) -> Option<u8> {
    value.trim().parse().ok()
}
fn nonempty(value: &str) -> Option<String> {
    let value = value.trim();
    (!value.is_empty()).then(|| value.to_string())
}

struct HeaderMap(HashMap<String, usize>);
impl HeaderMap {
    fn new(headers: &StringRecord) -> Self {
        Self(
            headers
                .iter()
                .enumerate()
                .map(|(i, name)| (name.trim_start_matches('\u{feff}').to_string(), i))
                .collect(),
        )
    }
    fn get<'a>(&self, row: &'a StringRecord, name: &str) -> &'a str {
        self.0.get(name).and_then(|i| row.get(*i)).unwrap_or("")
    }
}

pub fn format_matches<T: AsRef<MatchRecord>>(rows: &[T]) -> String {
    if rows.is_empty() {
        return "No matching matches were found in the provided datasets.".into();
    }
    rows.iter()
        .map(|row| {
            let m = row.as_ref();
            let context = m
                .stage
                .as_deref()
                .or(m.round.as_deref())
                .map(|v| format!(" — {v}"))
                .unwrap_or_default();
            format!(
                "{}: {} {}-{} {} ({}{})",
                m.date,
                m.home_team,
                m.home_goals,
                m.away_goals,
                m.away_team,
                m.competition,
                context
            )
        })
        .collect::<Vec<_>>()
        .join("\n")
}

impl AsRef<MatchRecord> for MatchRecord {
    fn as_ref(&self) -> &MatchRecord {
        self
    }
}

#[derive(Serialize)]
pub struct TeamOverview<'a> {
    pub team: &'a str,
    pub statistics: TeamStats,
    pub competitions: Vec<String>,
    pub players: Vec<&'a Player>,
    pub recent_matches: Vec<&'a MatchRecord>,
}

impl SoccerStore {
    pub fn team_overview<'a>(&'a self, team: &'a str, season: Option<u16>) -> TeamOverview<'a> {
        TeamOverview {
            team,
            statistics: self.team_statistics(team, season, None, None),
            competitions: self.competitions_for_team(team),
            players: self.search_players(None, None, Some(team), None, None, 100),
            recent_matches: self.search_matches(
                &MatchFilter {
                    team: Some(team),
                    season,
                    ..Default::default()
                },
                10,
            ),
        }
    }
}
