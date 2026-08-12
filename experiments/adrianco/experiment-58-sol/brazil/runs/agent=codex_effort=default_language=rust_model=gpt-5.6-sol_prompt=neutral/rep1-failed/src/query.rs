use crate::{
    data::{
        DataStore, Match, Player, competition_matches, normalize_team, normalize_text, team_matches,
    },
    json::{Json, object},
};
use std::{
    cmp::Ordering,
    collections::{BTreeMap, HashSet},
    sync::Arc,
};

#[derive(Debug, Clone)]
pub struct ToolOutput {
    pub text: String,
    pub structured: Json,
}

#[derive(Clone)]
pub struct SoccerService {
    pub store: Arc<DataStore>,
}

#[derive(Default)]
struct MatchFilter {
    team: Option<String>,
    opponent: Option<String>,
    competition: Option<String>,
    season: Option<i32>,
    date_from: Option<String>,
    date_to: Option<String>,
    stage: Option<String>,
    venue: Option<String>,
    source: Option<String>,
    limit: usize,
    offset: usize,
}

#[derive(Debug, Clone, Default)]
struct TeamStats {
    matches: usize,
    wins: usize,
    draws: usize,
    losses: usize,
    goals_for: i32,
    goals_against: i32,
}

impl TeamStats {
    fn points(&self) -> usize {
        self.wins * 3 + self.draws
    }
    fn goal_difference(&self) -> i32 {
        self.goals_for - self.goals_against
    }
    fn win_rate(&self) -> f64 {
        if self.matches == 0 {
            0.0
        } else {
            self.wins as f64 * 100.0 / self.matches as f64
        }
    }
}

impl SoccerService {
    pub fn new(store: DataStore) -> Self {
        Self {
            store: Arc::new(store),
        }
    }

    pub fn call_tool(&self, name: &str, args: &Json) -> Result<ToolOutput, String> {
        match name {
            "dataset_info" => Ok(self.dataset_info()),
            "search_matches" => self.search_matches(MatchFilter::from_json(args)?),
            "team_statistics" => self.team_statistics(args),
            "team_overview" => self.team_overview(args),
            "head_to_head" => self.head_to_head(args),
            "search_derbies" => self.search_derbies(args),
            "search_players" => self.search_players(args),
            "standings" => self.standings(args),
            "competition_statistics" => self.competition_statistics(args),
            "team_rankings" => self.team_rankings(args),
            "biggest_wins" => self.biggest_wins(args),
            _ => Err(format!("unknown tool '{name}'")),
        }
    }

    fn dataset_info(&self) -> ToolOutput {
        let reports = self
            .store
            .reports
            .iter()
            .map(|report| {
                object([
                    ("file", report.file.clone().into()),
                    ("rows", report.rows.into()),
                    ("loaded", report.loaded.into()),
                    ("skipped", report.skipped.into()),
                ])
            })
            .collect();
        let text = format!(
            "Brazilian soccer knowledge graph loaded: {} match records, {} players, {} normalized teams from {} CSV files.",
            self.store.matches.len(),
            self.store.players.len(),
            self.store.teams.len(),
            self.store.reports.len()
        );
        ToolOutput {
            text,
            structured: object([
                ("match_records", self.store.matches.len().into()),
                ("players", self.store.players.len().into()),
                ("teams", self.store.teams.len().into()),
                ("datasets", Json::Array(reports)),
                (
                    "capabilities",
                    Json::Array(vec![
                        "match search by team/date/competition/season/stage".into(),
                        "team records and head-to-head comparison".into(),
                        "cross-file team overview with matches and FIFA players".into(),
                        "traditional Brazilian derby discovery".into(),
                        "player search and FIFA attributes".into(),
                        "calculated standings".into(),
                        "competition aggregates and home/away rankings".into(),
                        "biggest victories".into(),
                    ]),
                ),
            ]),
        }
    }

    fn search_matches(&self, filter: MatchFilter) -> Result<ToolOutput, String> {
        if filter.limit > 500 {
            return Err("limit must be at most 500".into());
        }
        let mut matches: Vec<_> = self.filtered_matches(&filter);
        matches.sort_by(|a, b| b.date.cmp(&a.date).then_with(|| a.id.cmp(&b.id)));
        let total = matches.len();
        let selected: Vec<_> = matches
            .into_iter()
            .skip(filter.offset)
            .take(filter.limit)
            .collect();
        let values = selected.iter().map(|item| match_json(item)).collect();
        let mut lines = vec![format!(
            "Found {total} matching games; showing {}.",
            selected.len()
        )];
        lines.extend(selected.iter().map(|item| format_match(item)));
        Ok(ToolOutput {
            text: lines.join("\n"),
            structured: object([
                ("total", total.into()),
                ("offset", filter.offset.into()),
                ("returned", selected.len().into()),
                ("matches", Json::Array(values)),
            ]),
        })
    }

    fn team_statistics(&self, args: &Json) -> Result<ToolOutput, String> {
        let team = required_str(args, "team")?;
        let team_key = normalize_team(team);
        let filter = MatchFilter {
            team: Some(team.into()),
            competition: string_arg(args, "competition"),
            season: int_arg(args, "season"),
            date_from: string_arg(args, "date_from"),
            date_to: string_arg(args, "date_to"),
            venue: string_arg(args, "venue"),
            source: string_arg(args, "source"),
            limit: 500,
            ..Default::default()
        };
        let matches = self.filtered_matches(&filter);
        let stats = calculate_team_stats(&matches, &team_key);
        if stats.matches == 0 {
            return Err(format!("no matches found for '{team}' with those filters"));
        }
        let context = filter_context(
            filter.season,
            filter.competition.as_deref(),
            filter.venue.as_deref(),
        );
        let text = format!(
            "{} record{}: {} matches — {} wins, {} draws, {} losses; {} goals for, {} against (goal difference {:+}); {:.1}% win rate.",
            team,
            context,
            stats.matches,
            stats.wins,
            stats.draws,
            stats.losses,
            stats.goals_for,
            stats.goals_against,
            stats.goal_difference(),
            stats.win_rate()
        );
        Ok(ToolOutput {
            text,
            structured: team_stats_json(team, &stats),
        })
    }

    fn team_overview(&self, args: &Json) -> Result<ToolOutput, String> {
        let team = required_str(args, "team")?;
        let key = normalize_team(team);
        let season = int_arg(args, "season");
        let matches = self.filtered_matches(&MatchFilter {
            team: Some(team.into()),
            season,
            limit: 500,
            ..Default::default()
        });
        let stats = calculate_team_stats(&matches, &key);
        let mut competitions: BTreeMap<String, usize> = BTreeMap::new();
        for item in &matches {
            *competitions.entry(item.competition.clone()).or_default() += 1;
        }
        let mut players: Vec<_> = self
            .store
            .players
            .iter()
            .filter(|player| player.club_key == key)
            .collect();
        players.sort_by(|a, b| b.overall.cmp(&a.overall).then_with(|| a.name.cmp(&b.name)));
        let player_total = players.len();
        players.truncate(usize_arg(args, "player_limit").unwrap_or(25).min(100));
        if stats.matches == 0 && players.is_empty() {
            return Err(format!(
                "no match or FIFA player records found for '{team}'"
            ));
        }
        let competition_text = competitions
            .iter()
            .map(|(name, count)| format!("{name} ({count} matches)"))
            .collect::<Vec<_>>()
            .join(", ");
        let player_text = players
            .iter()
            .map(|player| {
                format!(
                    "{} ({}, overall {})",
                    player.name,
                    player.position,
                    optional_number(player.overall)
                )
            })
            .collect::<Vec<_>>()
            .join(", ");
        Ok(ToolOutput {
            text: format!(
                "{team} overview{}: {} matches ({}W, {}D, {}L), goals {}-{}. Competitions: {}. FIFA players in the snapshot ({}): {}",
                season.map(|year| format!(" in {year}")).unwrap_or_default(),
                stats.matches,
                stats.wins,
                stats.draws,
                stats.losses,
                stats.goals_for,
                stats.goals_against,
                if competition_text.is_empty() {
                    "none"
                } else {
                    &competition_text
                },
                player_total,
                if player_text.is_empty() {
                    "none"
                } else {
                    &player_text
                }
            ),
            structured: object([
                ("team", team.into()),
                ("season", season.map(Json::from).unwrap_or(Json::Null)),
                ("match_statistics", team_stats_json(team, &stats)),
                (
                    "competitions",
                    Json::Array(
                        competitions
                            .into_iter()
                            .map(|(name, matches)| {
                                object([("name", name.into()), ("matches", matches.into())])
                            })
                            .collect(),
                    ),
                ),
                ("player_total", player_total.into()),
                (
                    "players",
                    Json::Array(players.into_iter().map(player_json).collect()),
                ),
            ]),
        })
    }

    fn head_to_head(&self, args: &Json) -> Result<ToolOutput, String> {
        let team_a = required_str(args, "team_a")?;
        let team_b = required_str(args, "team_b")?;
        let a_key = normalize_team(team_a);
        let b_key = normalize_team(team_b);
        if a_key == b_key {
            return Err("team_a and team_b must identify different teams".into());
        }
        let filter = MatchFilter {
            team: Some(team_a.into()),
            opponent: Some(team_b.into()),
            competition: string_arg(args, "competition"),
            season: int_arg(args, "season"),
            date_from: string_arg(args, "date_from"),
            date_to: string_arg(args, "date_to"),
            source: string_arg(args, "source"),
            limit: 500,
            ..Default::default()
        };
        let mut matches = self.filtered_matches(&filter);
        matches.sort_by(|a, b| b.date.cmp(&a.date));
        let mut a_wins = 0;
        let mut b_wins = 0;
        let mut draws = 0;
        for item in &matches {
            if item.home_goals == item.away_goals {
                draws += 1;
            } else {
                let winner = if item.home_goals > item.away_goals {
                    &item.home_key
                } else {
                    &item.away_key
                };
                if winner == &a_key {
                    a_wins += 1;
                } else if winner == &b_key {
                    b_wins += 1;
                }
            }
        }
        let limit = usize_arg(args, "limit").unwrap_or(20).min(100);
        let recent: Vec<_> = matches
            .iter()
            .take(limit)
            .map(|item| match_json(item))
            .collect();
        let text = format!(
            "{} vs {} in the dataset: {} matches — {} {} wins, {} {} wins, {} draws.\n{}",
            team_a,
            team_b,
            matches.len(),
            team_a,
            a_wins,
            team_b,
            b_wins,
            draws,
            matches
                .iter()
                .take(limit)
                .map(|item| format_match(item))
                .collect::<Vec<_>>()
                .join("\n")
        );
        Ok(ToolOutput {
            text,
            structured: object([
                ("team_a", team_a.into()),
                ("team_b", team_b.into()),
                ("matches", matches.len().into()),
                ("team_a_wins", a_wins.into()),
                ("team_b_wins", b_wins.into()),
                ("draws", draws.into()),
                ("recent_matches", Json::Array(recent)),
            ]),
        })
    }

    fn search_players(&self, args: &Json) -> Result<ToolOutput, String> {
        let name = string_arg(args, "name").map(|value| normalize_text(&value));
        let nationality = string_arg(args, "nationality").map(|value| normalize_text(&value));
        let club = string_arg(args, "club");
        let position = string_arg(args, "position").map(|value| normalize_text(&value));
        let min_overall = int_arg(args, "min_overall");
        let max_overall = int_arg(args, "max_overall");
        let limit = usize_arg(args, "limit").unwrap_or(50).min(500);
        let offset = usize_arg(args, "offset").unwrap_or(0);
        let mut players: Vec<&Player> = self
            .store
            .players
            .iter()
            .filter(|player| {
                name.as_ref()
                    .is_none_or(|query| player.name_key.contains(query))
                    && nationality
                        .as_ref()
                        .is_none_or(|query| player.nationality_key.contains(query))
                    && club
                        .as_ref()
                        .is_none_or(|query| team_matches(query, &player.club_key))
                    && position
                        .as_ref()
                        .is_none_or(|query| position_matches(query, &player.position))
                    && min_overall
                        .is_none_or(|minimum| player.overall.is_some_and(|value| value >= minimum))
                    && max_overall
                        .is_none_or(|maximum| player.overall.is_some_and(|value| value <= maximum))
            })
            .collect();
        players.sort_by(|a, b| b.overall.cmp(&a.overall).then_with(|| a.name.cmp(&b.name)));
        let total = players.len();
        let selected: Vec<_> = players.into_iter().skip(offset).take(limit).collect();
        let lines = selected
            .iter()
            .enumerate()
            .map(|(index, player)| {
                format!(
                    "{}. {} — Overall {}, {}, {}, age {}",
                    offset + index + 1,
                    player.name,
                    optional_number(player.overall),
                    player.position,
                    player.club,
                    optional_number(player.age)
                )
            })
            .collect::<Vec<_>>();
        Ok(ToolOutput {
            text: format!(
                "Found {total} players; showing {}.\n{}",
                selected.len(),
                lines.join("\n")
            ),
            structured: object([
                ("total", total.into()),
                ("offset", offset.into()),
                ("returned", selected.len().into()),
                (
                    "players",
                    Json::Array(selected.iter().map(|player| player_json(player)).collect()),
                ),
            ]),
        })
    }

    fn search_derbies(&self, args: &Json) -> Result<ToolOutput, String> {
        let season = int_arg(args, "season");
        let competition = string_arg(args, "competition");
        let team = string_arg(args, "team").map(|value| normalize_team(&value));
        let limit = usize_arg(args, "limit").unwrap_or(100).min(500);
        let base_filter = MatchFilter {
            season,
            competition: competition.clone(),
            limit: 500,
            ..Default::default()
        };
        let matches = self.filtered_matches(&base_filter);
        let mut found: Vec<(&Match, &str)> = matches
            .into_iter()
            .filter_map(|item| {
                DERBIES
                    .iter()
                    .find(|(_, a, b)| {
                        ((item.home_key == *a && item.away_key == *b)
                            || (item.home_key == *b && item.away_key == *a))
                            && team.as_ref().is_none_or(|query| query == a || query == b)
                    })
                    .map(|(name, _, _)| (item, *name))
            })
            .collect();
        found.sort_by(|a, b| b.0.date.cmp(&a.0.date));
        let total = found.len();
        found.truncate(limit);
        let rows = found
            .iter()
            .map(|(item, derby)| {
                let mut value = match_json(item);
                if let Json::Object(ref mut map) = value {
                    map.insert("derby".into(), (*derby).into());
                }
                value
            })
            .collect();
        let lines = found
            .iter()
            .map(|(item, derby)| {
                format!("{derby}: {}", format_match(item).trim_start_matches("- "))
            })
            .collect::<Vec<_>>();
        Ok(ToolOutput {
            text: format!(
                "Found {total} traditional derby matches{}:\n{}",
                filter_context(season, competition.as_deref(), None),
                lines.join("\n")
            ),
            structured: object([
                ("total", total.into()),
                ("returned", found.len().into()),
                ("matches", Json::Array(rows)),
            ]),
        })
    }

    fn standings(&self, args: &Json) -> Result<ToolOutput, String> {
        let season = required_i32(args, "season")?;
        let competition =
            string_arg(args, "competition").unwrap_or_else(|| "Brasileirão Série A".into());
        let matches = self.authoritative_competition_matches(season, &competition);
        if matches.is_empty() {
            return Err(format!("no {competition} results found for {season}"));
        }
        let mut table: BTreeMap<String, (String, TeamStats)> = BTreeMap::new();
        for item in matches {
            for key in [&item.home_key, &item.away_key] {
                let display = self
                    .store
                    .teams
                    .get(key)
                    .cloned()
                    .unwrap_or_else(|| key.clone());
                table
                    .entry(key.clone())
                    .or_insert((display, TeamStats::default()));
            }
            update_stats(
                &mut table.get_mut(&item.home_key).unwrap().1,
                item.home_goals,
                item.away_goals,
            );
            update_stats(
                &mut table.get_mut(&item.away_key).unwrap().1,
                item.away_goals,
                item.home_goals,
            );
        }
        let mut standings: Vec<_> = table.into_values().collect();
        standings.sort_by(compare_standing);
        let limit = usize_arg(args, "limit")
            .unwrap_or(standings.len())
            .min(standings.len());
        let rows: Vec<_> = standings
            .iter()
            .take(limit)
            .enumerate()
            .map(|(index, (team, stats))| standings_json(index + 1, team, stats))
            .collect();
        let lines: Vec<_> = standings
            .iter()
            .take(limit)
            .enumerate()
            .map(|(index, (team, stats))| {
                format!(
                    "{}. {} — {} pts ({}W, {}D, {}L), GF {}, GA {}, GD {:+}",
                    index + 1,
                    team,
                    stats.points(),
                    stats.wins,
                    stats.draws,
                    stats.losses,
                    stats.goals_for,
                    stats.goals_against,
                    stats.goal_difference()
                )
            })
            .collect();
        Ok(ToolOutput {
            text: format!(
                "{season} {competition} standings calculated from completed results:\n{}",
                lines.join("\n")
            ),
            structured: object([
                ("season", season.into()),
                ("competition", competition.into()),
                ("standings", Json::Array(rows)),
            ]),
        })
    }

    fn competition_statistics(&self, args: &Json) -> Result<ToolOutput, String> {
        let competition = required_str(args, "competition")?;
        let season = int_arg(args, "season");
        let filter = MatchFilter {
            competition: Some(competition.into()),
            season,
            source: string_arg(args, "source"),
            limit: 500,
            ..Default::default()
        };
        let matches = self.filtered_matches(&filter);
        if matches.is_empty() {
            return Err(format!("no matches found for '{competition}'"));
        }
        let goals: i32 = matches
            .iter()
            .map(|item| item.home_goals + item.away_goals)
            .sum();
        let home_wins = matches
            .iter()
            .filter(|item| item.home_goals > item.away_goals)
            .count();
        let away_wins = matches
            .iter()
            .filter(|item| item.away_goals > item.home_goals)
            .count();
        let draws = matches.len() - home_wins - away_wins;
        let average = goals as f64 / matches.len() as f64;
        let text = format!(
            "{}{}: {} matches, {} goals ({average:.2} per match); {} home wins ({:.1}%), {} away wins ({:.1}%), {} draws ({:.1}%).",
            competition,
            season.map(|year| format!(" {year}")).unwrap_or_default(),
            matches.len(),
            goals,
            home_wins,
            percentage(home_wins, matches.len()),
            away_wins,
            percentage(away_wins, matches.len()),
            draws,
            percentage(draws, matches.len())
        );
        Ok(ToolOutput {
            text,
            structured: object([
                ("competition", competition.into()),
                ("season", season.map(Json::from).unwrap_or(Json::Null)),
                ("matches", matches.len().into()),
                ("goals", goals.into()),
                ("goals_per_match", average.into()),
                ("home_wins", home_wins.into()),
                ("away_wins", away_wins.into()),
                ("draws", draws.into()),
            ]),
        })
    }

    fn team_rankings(&self, args: &Json) -> Result<ToolOutput, String> {
        let competition = string_arg(args, "competition");
        let season = int_arg(args, "season");
        let venue = string_arg(args, "venue").unwrap_or_else(|| "all".into());
        if !matches!(venue.as_str(), "home" | "away" | "all" | "either") {
            return Err("venue must be home, away, or all".into());
        }
        let minimum_matches = usize_arg(args, "minimum_matches").unwrap_or(3);
        let limit = usize_arg(args, "limit").unwrap_or(20).min(100);
        let filter = MatchFilter {
            competition: competition.clone(),
            season,
            limit: 500,
            ..Default::default()
        };
        let matches = self.filtered_matches(&filter);
        let mut rows: BTreeMap<String, (String, TeamStats)> = BTreeMap::new();
        for item in matches {
            if venue != "away" {
                let display = self
                    .store
                    .teams
                    .get(&item.home_key)
                    .cloned()
                    .unwrap_or_else(|| item.home_team.clone());
                update_stats(
                    &mut rows
                        .entry(item.home_key.clone())
                        .or_insert((display, TeamStats::default()))
                        .1,
                    item.home_goals,
                    item.away_goals,
                );
            }
            if venue != "home" {
                let display = self
                    .store
                    .teams
                    .get(&item.away_key)
                    .cloned()
                    .unwrap_or_else(|| item.away_team.clone());
                update_stats(
                    &mut rows
                        .entry(item.away_key.clone())
                        .or_insert((display, TeamStats::default()))
                        .1,
                    item.away_goals,
                    item.home_goals,
                );
            }
        }
        let mut rows: Vec<_> = rows
            .into_values()
            .filter(|(_, stats)| stats.matches >= minimum_matches)
            .collect();
        rows.sort_by(|a, b| {
            b.1.win_rate()
                .partial_cmp(&a.1.win_rate())
                .unwrap_or(Ordering::Equal)
                .then_with(|| b.1.points().cmp(&a.1.points()))
                .then_with(|| b.1.goal_difference().cmp(&a.1.goal_difference()))
        });
        let selected: Vec<_> = rows.into_iter().take(limit).collect();
        let lines = selected
            .iter()
            .enumerate()
            .map(|(index, (team, stats))| {
                format!(
                    "{}. {} — {:.1}% win rate, {}-{}-{}, {} matches",
                    index + 1,
                    team,
                    stats.win_rate(),
                    stats.wins,
                    stats.draws,
                    stats.losses,
                    stats.matches
                )
            })
            .collect::<Vec<_>>();
        Ok(ToolOutput {
            text: format!(
                "Team ranking ({venue} record{}):\n{}",
                filter_context(season, competition.as_deref(), None),
                lines.join("\n")
            ),
            structured: object([
                ("venue", venue.into()),
                ("season", season.map(Json::from).unwrap_or(Json::Null)),
                (
                    "competition",
                    competition.map(Json::from).unwrap_or(Json::Null),
                ),
                (
                    "teams",
                    Json::Array(
                        selected
                            .iter()
                            .enumerate()
                            .map(|(index, (team, stats))| standings_json(index + 1, team, stats))
                            .collect(),
                    ),
                ),
            ]),
        })
    }

    fn biggest_wins(&self, args: &Json) -> Result<ToolOutput, String> {
        let filter = MatchFilter {
            team: string_arg(args, "team"),
            competition: string_arg(args, "competition"),
            season: int_arg(args, "season"),
            source: string_arg(args, "source"),
            limit: 500,
            ..Default::default()
        };
        let limit = usize_arg(args, "limit").unwrap_or(20).min(100);
        let mut matches = self.filtered_matches(&filter);
        matches.sort_by(|a, b| {
            victory_margin(b)
                .cmp(&victory_margin(a))
                .then_with(|| (b.home_goals + b.away_goals).cmp(&(a.home_goals + a.away_goals)))
                .then_with(|| b.date.cmp(&a.date))
        });
        matches.truncate(limit);
        let text = format!(
            "Biggest victories:\n{}",
            matches
                .iter()
                .map(|item| format!("{} (margin {})", format_match(item), victory_margin(item)))
                .collect::<Vec<_>>()
                .join("\n")
        );
        Ok(ToolOutput {
            text,
            structured: object([(
                "matches",
                Json::Array(
                    matches
                        .iter()
                        .map(|item| {
                            let mut value = match_json(item);
                            if let Json::Object(ref mut map) = value {
                                map.insert("margin".into(), victory_margin(item).into());
                            }
                            value
                        })
                        .collect(),
                ),
            )]),
        })
    }

    fn filtered_matches<'a>(&'a self, filter: &MatchFilter) -> Vec<&'a Match> {
        let venue = filter.venue.as_deref().unwrap_or("either");
        let team_key = filter.team.as_deref().map(normalize_team);
        let opponent_key = filter.opponent.as_deref().map(normalize_team);
        let mut seen = HashSet::new();
        self.store
            .matches
            .iter()
            .filter(|item| {
                let team_ok = team_key.as_ref().is_none_or(|key| match venue {
                    "home" => &item.home_key == key,
                    "away" => &item.away_key == key,
                    _ => &item.home_key == key || &item.away_key == key,
                });
                let opponent_ok = opponent_key
                    .as_ref()
                    .is_none_or(|key| &item.home_key == key || &item.away_key == key);
                let source_ok = filter.source.as_ref().is_none_or(|source| {
                    normalize_text(&item.source).contains(&normalize_text(source))
                });
                team_ok
                    && opponent_ok
                    && source_ok
                    && filter
                        .competition
                        .as_ref()
                        .is_none_or(|value| competition_matches(value, &item.competition))
                    && filter.season.is_none_or(|value| value == item.season)
                    && filter
                        .date_from
                        .as_ref()
                        .is_none_or(|value| &item.date >= value)
                    && filter
                        .date_to
                        .as_ref()
                        .is_none_or(|value| &item.date <= value)
                    && filter.stage.as_ref().is_none_or(|value| {
                        item.round_or_stage.as_ref().is_some_and(|stage| {
                            normalize_text(stage).contains(&normalize_text(value))
                        })
                    })
                    && (filter.source.is_some() || seen.insert(match_signature(item)))
            })
            .collect()
    }

    fn authoritative_competition_matches<'a>(
        &'a self,
        season: i32,
        competition: &str,
    ) -> Vec<&'a Match> {
        let all: Vec<_> = self
            .store
            .matches
            .iter()
            .filter(|item| {
                item.season == season && competition_matches(competition, &item.competition)
            })
            .collect();
        let preferred = if competition_matches("Brasileirão", competition) {
            "Brasileirao_Matches.csv"
        } else if competition_matches("Copa do Brasil", competition) {
            "Brazilian_Cup_Matches.csv"
        } else if competition_matches("Libertadores", competition) {
            "Libertadores_Matches.csv"
        } else {
            ""
        };
        let selected: Vec<_> = all
            .iter()
            .copied()
            .filter(|item| item.source == preferred)
            .collect();
        if !selected.is_empty() {
            selected
        } else if competition_matches("Brasileirão", competition) {
            let historical: Vec<_> = all
                .iter()
                .copied()
                .filter(|item| item.source == "novo_campeonato_brasileiro.csv")
                .collect();
            if !historical.is_empty() {
                historical
            } else {
                deduplicate(all)
            }
        } else {
            deduplicate(all)
        }
    }
}

impl MatchFilter {
    fn from_json(args: &Json) -> Result<Self, String> {
        let venue = string_arg(args, "venue");
        if venue
            .as_ref()
            .is_some_and(|value| !matches!(value.as_str(), "home" | "away" | "either" | "all"))
        {
            return Err("venue must be home, away, or either".into());
        }
        Ok(Self {
            team: string_arg(args, "team"),
            opponent: string_arg(args, "opponent"),
            competition: string_arg(args, "competition"),
            season: int_arg(args, "season"),
            date_from: string_arg(args, "date_from"),
            date_to: string_arg(args, "date_to"),
            stage: string_arg(args, "stage"),
            venue,
            source: string_arg(args, "source"),
            limit: usize_arg(args, "limit").unwrap_or(50),
            offset: usize_arg(args, "offset").unwrap_or(0),
        })
    }
}

fn calculate_team_stats(matches: &[&Match], team_key: &str) -> TeamStats {
    let mut stats = TeamStats::default();
    for item in matches {
        if item.home_key == team_key {
            update_stats(&mut stats, item.home_goals, item.away_goals);
        } else if item.away_key == team_key {
            update_stats(&mut stats, item.away_goals, item.home_goals);
        }
    }
    stats
}

fn update_stats(stats: &mut TeamStats, goals_for: i32, goals_against: i32) {
    stats.matches += 1;
    stats.goals_for += goals_for;
    stats.goals_against += goals_against;
    match goals_for.cmp(&goals_against) {
        Ordering::Greater => stats.wins += 1,
        Ordering::Equal => stats.draws += 1,
        Ordering::Less => stats.losses += 1,
    }
}

fn compare_standing(a: &(String, TeamStats), b: &(String, TeamStats)) -> Ordering {
    b.1.points()
        .cmp(&a.1.points())
        .then_with(|| b.1.wins.cmp(&a.1.wins))
        .then_with(|| b.1.goal_difference().cmp(&a.1.goal_difference()))
        .then_with(|| b.1.goals_for.cmp(&a.1.goals_for))
        .then_with(|| a.0.cmp(&b.0))
}

fn match_signature(item: &Match) -> String {
    // Round/stage is intentionally excluded: the extended and competition-specific
    // files often describe the same result with different metadata.
    format!(
        "{}|{}|{}|{}|{}|{}",
        item.date,
        normalize_text(&item.competition),
        item.home_key,
        item.away_key,
        item.home_goals,
        item.away_goals
    )
}

fn deduplicate(matches: Vec<&Match>) -> Vec<&Match> {
    let mut seen = HashSet::new();
    matches
        .into_iter()
        .filter(|item| seen.insert(match_signature(item)))
        .collect()
}

fn match_json(item: &Match) -> Json {
    object([
        ("id", item.id.clone().into()),
        ("date", item.date.clone().into()),
        ("season", item.season.into()),
        ("competition", item.competition.clone().into()),
        ("home_team", item.home_team.clone().into()),
        ("away_team", item.away_team.clone().into()),
        ("home_goals", item.home_goals.into()),
        ("away_goals", item.away_goals.into()),
        (
            "round_or_stage",
            item.round_or_stage
                .clone()
                .map(Json::from)
                .unwrap_or(Json::Null),
        ),
        (
            "stadium",
            item.stadium.clone().map(Json::from).unwrap_or(Json::Null),
        ),
        ("source", item.source.clone().into()),
        (
            "extended_statistics",
            object([
                ("home_corners", option_i32(item.extended.home_corners)),
                ("away_corners", option_i32(item.extended.away_corners)),
                ("home_attacks", option_i32(item.extended.home_attacks)),
                ("away_attacks", option_i32(item.extended.away_attacks)),
                ("home_shots", option_i32(item.extended.home_shots)),
                ("away_shots", option_i32(item.extended.away_shots)),
            ]),
        ),
    ])
}

fn player_json(player: &Player) -> Json {
    object([
        ("id", player.id.clone().into()),
        ("name", player.name.clone().into()),
        ("age", option_i32(player.age)),
        ("nationality", player.nationality.clone().into()),
        ("overall", option_i32(player.overall)),
        ("potential", option_i32(player.potential)),
        ("club", player.club.clone().into()),
        ("position", player.position.clone().into()),
        ("jersey_number", option_i32(player.jersey_number)),
        (
            "height",
            player.height.clone().map(Json::from).unwrap_or(Json::Null),
        ),
        (
            "weight",
            player.weight.clone().map(Json::from).unwrap_or(Json::Null),
        ),
        (
            "attributes",
            Json::Object(
                player
                    .attributes
                    .iter()
                    .map(|(key, value)| (key.clone(), (*value).into()))
                    .collect(),
            ),
        ),
    ])
}

fn team_stats_json(team: &str, stats: &TeamStats) -> Json {
    object([
        ("team", team.into()),
        ("matches", stats.matches.into()),
        ("wins", stats.wins.into()),
        ("draws", stats.draws.into()),
        ("losses", stats.losses.into()),
        ("goals_for", stats.goals_for.into()),
        ("goals_against", stats.goals_against.into()),
        ("goal_difference", stats.goal_difference().into()),
        ("points", stats.points().into()),
        ("win_rate_percent", stats.win_rate().into()),
    ])
}

fn standings_json(rank: usize, team: &str, stats: &TeamStats) -> Json {
    let mut value = team_stats_json(team, stats);
    if let Json::Object(ref mut map) = value {
        map.insert("rank".into(), rank.into());
    }
    value
}

fn format_match(item: &Match) -> String {
    format!(
        "- {}: {} {}-{} {} ({}{})",
        item.date,
        item.home_team,
        item.home_goals,
        item.away_goals,
        item.away_team,
        item.competition,
        item.round_or_stage
            .as_ref()
            .map(|value| format!(", {value}"))
            .unwrap_or_default()
    )
}

fn filter_context(season: Option<i32>, competition: Option<&str>, venue: Option<&str>) -> String {
    let mut values = Vec::new();
    if let Some(year) = season {
        values.push(year.to_string());
    }
    if let Some(value) = competition {
        values.push(value.into());
    }
    if let Some(value) = venue
        && value != "either"
        && value != "all"
    {
        values.push(format!("{value} matches"));
    }
    if values.is_empty() {
        String::new()
    } else {
        format!(" ({})", values.join(", "))
    }
}

fn position_matches(query: &str, position: &str) -> bool {
    let position = normalize_text(position);
    match query {
        "forward" | "forwards" | "attacker" | "attackers" => {
            matches!(position.as_str(), "st" | "cf" | "lw" | "rw" | "lf" | "rf")
        }
        "midfielder" | "midfielders" => position.contains('m'),
        "defender" | "defenders" => position.contains('b'),
        "goalkeeper" | "goalkeepers" | "keeper" => position == "gk",
        _ => position == query || position.contains(query),
    }
}

fn victory_margin(item: &Match) -> i32 {
    (item.home_goals - item.away_goals).abs()
}
fn percentage(count: usize, total: usize) -> f64 {
    if total == 0 {
        0.0
    } else {
        count as f64 * 100.0 / total as f64
    }
}
fn optional_number(value: Option<i32>) -> String {
    value
        .map(|number| number.to_string())
        .unwrap_or_else(|| "unknown".into())
}
fn option_i32(value: Option<i32>) -> Json {
    value.map(Json::from).unwrap_or(Json::Null)
}
fn string_arg(args: &Json, name: &str) -> Option<String> {
    args.get(name)
        .and_then(Json::as_str)
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .map(str::to_string)
}
fn int_arg(args: &Json, name: &str) -> Option<i32> {
    args.get(name)
        .and_then(Json::as_i64)
        .and_then(|value| value.try_into().ok())
}
fn usize_arg(args: &Json, name: &str) -> Option<usize> {
    args.get(name)
        .and_then(Json::as_u64)
        .and_then(|value| value.try_into().ok())
}
fn required_str<'a>(args: &'a Json, name: &str) -> Result<&'a str, String> {
    args.get(name)
        .and_then(Json::as_str)
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .ok_or_else(|| format!("missing required string '{name}'"))
}
fn required_i32(args: &Json, name: &str) -> Result<i32, String> {
    int_arg(args, name).ok_or_else(|| format!("missing required integer '{name}'"))
}

const DERBIES: &[(&str, &str, &str)] = &[
    ("Fla-Flu", "flamengo", "fluminense"),
    ("Clássico dos Milhões", "flamengo", "vasco"),
    ("Clássico da Rivalidade", "flamengo", "botafogo"),
    ("Derby Paulista", "corinthians", "palmeiras"),
    ("Majestoso", "corinthians", "sao paulo"),
    ("Choque-Rei", "palmeiras", "sao paulo"),
    ("San-São", "santos", "sao paulo"),
    ("Grenal", "gremio", "internacional"),
    ("Clássico Mineiro", "atletico mineiro", "cruzeiro"),
    ("Ba-Vi", "bahia", "vitoria"),
    ("Re-Pa", "remo", "paysandu"),
    ("Atletiba", "athletico paranaense", "coritiba"),
    ("Clássico-Rei", "ceara", "fortaleza"),
    ("Clássico dos Clássicos", "nautico", "sport"),
];

#[cfg(test)]
mod tests {
    use super::*;
    use crate::data::{DatasetReport, ExtendedStats};
    use std::path::PathBuf;

    fn match_item(date: &str, home: &str, away: &str, hg: i32, ag: i32) -> Match {
        Match {
            id: date.into(),
            date: date.into(),
            season: 2023,
            competition: "Brasileirão Série A".into(),
            home_team: home.into(),
            home_key: normalize_team(home),
            away_team: away.into(),
            away_key: normalize_team(away),
            home_goals: hg,
            away_goals: ag,
            round_or_stage: None,
            stadium: None,
            source: "Brasileirao_Matches.csv".into(),
            extended: ExtendedStats::default(),
        }
    }

    fn service() -> SoccerService {
        let matches = vec![
            match_item("2023-01-01", "Flamengo-RJ", "Fluminense-RJ", 2, 1),
            match_item("2023-02-01", "Fluminense-RJ", "Flamengo-RJ", 0, 0),
        ];
        let teams = [
            ("flamengo".into(), "Flamengo".into()),
            ("fluminense".into(), "Fluminense".into()),
        ]
        .into_iter()
        .collect();
        SoccerService::new(DataStore {
            matches,
            players: vec![],
            teams,
            reports: Vec::<DatasetReport>::new(),
            data_dir: PathBuf::new(),
        })
    }

    #[test]
    fn computes_head_to_head_and_team_stats() {
        let service = service();
        let args = object([
            ("team_a", "Flamengo".into()),
            ("team_b", "Fluminense".into()),
        ]);
        let output = service.head_to_head(&args).unwrap();
        assert_eq!(
            output.structured.get("team_a_wins").and_then(Json::as_i64),
            Some(1)
        );
        assert_eq!(
            output.structured.get("draws").and_then(Json::as_i64),
            Some(1)
        );
        let stats = service
            .team_statistics(&object([("team", "Flamengo".into())]))
            .unwrap();
        assert_eq!(
            stats.structured.get("goals_for").and_then(Json::as_i64),
            Some(2)
        );
    }

    #[test]
    fn calculates_standings() {
        let output = service()
            .standings(&object([("season", 2023.into())]))
            .unwrap();
        let Json::Array(rows) = output.structured.get("standings").unwrap() else {
            panic!()
        };
        assert_eq!(rows[0].get("team").and_then(Json::as_str), Some("Flamengo"));
        assert_eq!(rows[0].get("points").and_then(Json::as_i64), Some(4));
    }
}
