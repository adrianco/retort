use crate::{
    data::DataStore,
    domain::{SoccerMatch, Standing, TeamRecord},
    normalize::{competition_key, normalize_text, parse_date, team_key},
};
use serde::Deserialize;
use serde_json::{json, Value};
use std::{cmp::Reverse, collections::BTreeMap};

#[derive(Clone)]
pub struct SoccerService {
    pub store: DataStore,
}

#[derive(Debug)]
pub enum ToolError {
    Invalid(String),
    Unsupported(String),
}

impl SoccerService {
    pub fn new(store: DataStore) -> Self {
        Self { store }
    }

    pub fn call(&self, name: &str, arguments: Value) -> Result<Value, ToolError> {
        match name {
            "search_matches" => self.search_matches(from_value(arguments)?),
            "get_team_record" => self.team_record(from_value(arguments)?),
            "search_players" => self.search_players(from_value(arguments)?),
            "analyze_competition" => self.analyze_competition(from_value(arguments)?),
            "ask_soccer" => self.ask(from_value(arguments)?),
            _ => Err(ToolError::Invalid(format!("unknown tool: {name}"))),
        }
    }

    fn search_matches(&self, args: MatchArgs) -> Result<Value, ToolError> {
        validate_page(args.limit, args.offset)?;
        let from = args.date_from.as_deref().map(valid_date).transpose()?;
        let to = args.date_to.as_deref().map(valid_date).transpose()?;
        let anchor = args.team.as_deref().map(team_key);
        let opponent = args.opponent.as_deref().map(team_key);
        let comp = args.competition.as_deref().map(competition_key);
        let mut matches: Vec<&SoccerMatch> = self
            .store
            .matches
            .iter()
            .filter(|m| {
                let anchor_ok = anchor
                    .as_ref()
                    .map(|t| match args.venue.as_deref().unwrap_or("any") {
                        "home" => &m.home_team_key == t,
                        "away" => &m.away_team_key == t,
                        _ => &m.home_team_key == t || &m.away_team_key == t,
                    })
                    .unwrap_or(true);
                let opp_ok = opponent
                    .as_ref()
                    .map(|t| {
                        if let Some(a) = &anchor {
                            (&m.home_team_key == a && &m.away_team_key == t)
                                || (&m.away_team_key == a && &m.home_team_key == t)
                        } else {
                            &m.home_team_key == t || &m.away_team_key == t
                        }
                    })
                    .unwrap_or(true);
                anchor_ok
                    && opp_ok
                    && comp
                        .as_ref()
                        .map(|c| competition_key(&m.competition) == *c)
                        .unwrap_or(true)
                    && args.season.map(|s| m.season == s).unwrap_or(true)
                    && from.map(|d| m.date >= d).unwrap_or(true)
                    && to.map(|d| m.date <= d).unwrap_or(true)
                    && text_filter(m.stage.as_deref(), args.stage.as_deref())
                    && text_filter(m.round.as_deref(), args.round.as_deref())
            })
            .collect();
        match args.sort.as_deref().unwrap_or("newest") {
            "oldest" => matches.sort_by_key(|m| (m.date, m.id.as_str())),
            "largest_margin" => matches.sort_by_key(|m| {
                (
                    Reverse((m.home_goals as i32 - m.away_goals as i32).unsigned_abs()),
                    Reverse(m.date),
                    m.id.as_str(),
                )
            }),
            "newest" => matches.sort_by_key(|m| (Reverse(m.date), m.id.as_str())),
            other => return Err(ToolError::Invalid(format!("invalid sort: {other}"))),
        }
        let total = matches.len();
        let offset = args.offset.unwrap_or(0);
        let limit = args.limit.unwrap_or(50);
        let page: Vec<_> = matches
            .into_iter()
            .skip(offset)
            .take(limit)
            .cloned()
            .collect();
        Ok(
            json!({"matches":page,"total":total,"returned":page.len(),"truncated":offset+page.len()<total,"next_offset":if offset+page.len()<total{Some(offset+page.len())}else{None},"provenance":{"datasets":datasets_for_matches(&page)}}),
        )
    }

    fn team_record(&self, args: RecordArgs) -> Result<Value, ToolError> {
        if args.team.trim().is_empty() {
            return Err(ToolError::Invalid("team is required".into()));
        }
        let filters = MatchArgs {
            team: Some(args.team.clone()),
            opponent: args.opponent.clone(),
            venue: args.venue.clone(),
            competition: args.competition.clone(),
            season: args.season,
            date_from: args.date_from.clone(),
            date_to: args.date_to.clone(),
            stage: None,
            round: None,
            sort: Some("oldest".into()),
            limit: Some(200),
            offset: Some(0),
        };
        let anchor = team_key(&args.team);
        let all = self.filter_for_record(&filters)?;
        let mut record = TeamRecord {
            team: self
                .store
                .team_names
                .get(&anchor)
                .cloned()
                .unwrap_or(args.team),
            ..Default::default()
        };
        for m in &all {
            update_record(&mut record, m, &anchor);
        }
        Ok(
            json!({"record":record,"goal_difference":record.goal_difference(),"win_rate":round1(record.win_rate()),"provenance":{"datasets":datasets_for_refs(&all)}}),
        )
    }

    fn filter_for_record<'a>(&'a self, a: &MatchArgs) -> Result<Vec<&'a SoccerMatch>, ToolError> {
        let anchor = team_key(a.team.as_deref().unwrap_or(""));
        let opp = a.opponent.as_deref().map(team_key);
        let comp = a.competition.as_deref().map(competition_key);
        let from = a.date_from.as_deref().map(valid_date).transpose()?;
        let to = a.date_to.as_deref().map(valid_date).transpose()?;
        Ok(self
            .store
            .matches
            .iter()
            .filter(|m| {
                let in_venue = match a.venue.as_deref().unwrap_or("any") {
                    "home" => m.home_team_key == anchor,
                    "away" => m.away_team_key == anchor,
                    "any" => m.home_team_key == anchor || m.away_team_key == anchor,
                    _ => false,
                };
                in_venue
                    && opp
                        .as_ref()
                        .map(|o| m.home_team_key == *o || m.away_team_key == *o)
                        .unwrap_or(true)
                    && comp
                        .as_ref()
                        .map(|c| competition_key(&m.competition) == *c)
                        .unwrap_or(true)
                    && a.season.map(|s| m.season == s).unwrap_or(true)
                    && from.map(|d| m.date >= d).unwrap_or(true)
                    && to.map(|d| m.date <= d).unwrap_or(true)
            })
            .collect())
    }

    fn search_players(&self, args: PlayerArgs) -> Result<Value, ToolError> {
        validate_page(args.limit, args.offset)?;
        if args.name.is_none()
            && args.nationality.is_none()
            && args.club.is_none()
            && args.position.is_none()
            && args.min_overall.is_none()
        {
            return Err(ToolError::Invalid(
                "provide at least one player filter".into(),
            ));
        }
        let mut players: Vec<_> = self
            .store
            .players
            .iter()
            .filter(|p| {
                contains(&p.name, args.name.as_deref())
                    && contains(&p.nationality, args.nationality.as_deref())
                    && contains(p.club.as_deref().unwrap_or(""), args.club.as_deref())
                    && contains(
                        p.position.as_deref().unwrap_or(""),
                        args.position.as_deref(),
                    )
                    && args.min_overall.map(|v| p.overall >= v).unwrap_or(true)
                    && args.max_age.map(|v| p.age <= v).unwrap_or(true)
            })
            .collect();
        match args.sort.as_deref().unwrap_or("overall_desc") {
            "overall_desc" => players.sort_by_key(|p| (Reverse(p.overall), p.name.as_str())),
            "potential_desc" => players.sort_by_key(|p| (Reverse(p.potential), p.name.as_str())),
            "name" => players.sort_by_key(|p| normalize_text(&p.name)),
            other => return Err(ToolError::Invalid(format!("invalid sort: {other}"))),
        }
        let total = players.len();
        let offset = args.offset.unwrap_or(0);
        let limit = args.limit.unwrap_or(50);
        let page: Vec<_> = players
            .into_iter()
            .skip(offset)
            .take(limit)
            .cloned()
            .collect();
        Ok(
            json!({"players":page,"total":total,"returned":page.len(),"truncated":offset+page.len()<total,"next_offset":if offset+page.len()<total{Some(offset+page.len())}else{None},"provenance":{"datasets":["fifa_data.csv"]}}),
        )
    }

    fn analyze_competition(&self, args: AnalysisArgs) -> Result<Value, ToolError> {
        let comp = competition_key(&args.competition);
        let mut matches: Vec<_> = self
            .store
            .matches
            .iter()
            .filter(|m| {
                competition_key(&m.competition) == comp
                    && args.season.map(|s| m.season == s).unwrap_or(true)
            })
            .collect();
        // The dedicated league file is the authoritative complete schedule for
        // its seasons. Other files overlap it and are still queryable, but must
        // not inflate a season table when aliases or dates disagree.
        if comp == "brasileirao"
            && matches
                .iter()
                .any(|m| m.sources.iter().any(|s| s == "Brasileirao_Matches.csv"))
        {
            matches.retain(|m| m.sources.iter().any(|s| s == "Brasileirao_Matches.csv"));
        }
        if matches.is_empty() {
            return Ok(
                json!({"analysis":args.analysis,"matches":0,"data":[],"provenance":{"datasets":[]}}),
            );
        }
        let limit = args.limit.unwrap_or(30).min(200);
        let data = match args.analysis.as_str() {
            "standings" => {
                if comp != "brasileirao" {
                    return Err(ToolError::Unsupported(
                        "standings are only valid for league-format Brasileirão data".into(),
                    ));
                }
                json!(standings(&matches)
                    .into_iter()
                    .take(limit)
                    .collect::<Vec<_>>())
            }
            "summary" => {
                let goals: u32 = matches
                    .iter()
                    .map(|m| m.home_goals as u32 + m.away_goals as u32)
                    .sum();
                let home_wins = matches
                    .iter()
                    .filter(|m| m.home_goals > m.away_goals)
                    .count();
                let draws = matches
                    .iter()
                    .filter(|m| m.home_goals == m.away_goals)
                    .count();
                json!({"matches":matches.len(),"goals":goals,"goals_per_match":round2(goals as f64/matches.len() as f64),"home_wins":home_wins,"draws":draws,"away_wins":matches.len()-home_wins-draws})
            }
            "biggest_wins" => {
                let mut v = matches.clone();
                v.sort_by_key(|m| {
                    (
                        Reverse((m.home_goals as i32 - m.away_goals as i32).unsigned_abs()),
                        Reverse(m.date),
                    )
                });
                json!(v.into_iter().take(limit).collect::<Vec<_>>())
            }
            "team_ranking" => {
                let metric = args.metric.as_deref().ok_or_else(|| {
                    ToolError::Invalid("metric is required for team_ranking".into())
                })?;
                let mut rows: Vec<_> = standings(&matches);
                match metric {
                    "points" => {
                        rows.sort_by_key(|s| (Reverse(s.record.points), s.record.team.clone()))
                    }
                    "goals_for" => {
                        rows.sort_by_key(|s| (Reverse(s.record.goals_for), s.record.team.clone()))
                    }
                    "win_rate" => rows.sort_by(|a, b| {
                        b.record
                            .win_rate()
                            .total_cmp(&a.record.win_rate())
                            .then_with(|| a.record.team.cmp(&b.record.team))
                    }),
                    _ => return Err(ToolError::Invalid(format!("unsupported metric: {metric}"))),
                }
                json!(rows.into_iter().take(limit).collect::<Vec<_>>())
            }
            other => return Err(ToolError::Invalid(format!("invalid analysis: {other}"))),
        };
        Ok(
            json!({"analysis":args.analysis,"competition":args.competition,"season":args.season,"matches":matches.len(),"data":data,"provenance":{"datasets":datasets_for_refs(&matches)}}),
        )
    }

    fn ask(&self, args: AskArgs) -> Result<Value, ToolError> {
        let q = normalize_text(&args.question);
        let limit = args.limit.unwrap_or(20);
        if q.contains("highest rated") || q.contains("top brazilian players") {
            return self.search_players(PlayerArgs {
                name: None,
                nationality: if q.contains("brazilian") {
                    Some("Brazil".into())
                } else {
                    None
                },
                club: extract_after(&q, " at "),
                position: None,
                min_overall: Some(1),
                max_age: None,
                sort: Some("overall_desc".into()),
                limit: Some(limit),
                offset: Some(0),
            });
        }
        if q.contains("average goals") {
            let comp = if q.contains("libertadores") {
                "Libertadores"
            } else if q.contains("copa do brasil") {
                "Copa do Brasil"
            } else {
                "Brasileirão"
            };
            return self.analyze_competition(AnalysisArgs {
                competition: comp.into(),
                season: find_year(&q),
                analysis: "summary".into(),
                metric: None,
                limit: Some(limit),
            });
        }
        let known: Vec<_> = self
            .store
            .team_names
            .keys()
            .filter(|k| q.contains(k.as_str()))
            .cloned()
            .collect();
        if (q.contains("compare") || q.contains(" vs ") || q.contains("head to head"))
            && known.len() >= 2
        {
            return self.search_matches(MatchArgs {
                team: Some(known[0].clone()),
                opponent: Some(known[1].clone()),
                season: find_year(&q),
                limit: Some(limit),
                sort: Some("newest".into()),
                ..Default::default()
            });
        }
        if let Some(team) = known.first() {
            if q.contains("record") {
                return self.team_record(RecordArgs {
                    team: team.clone(),
                    opponent: None,
                    venue: if q.contains("home") {
                        Some("home".into())
                    } else if q.contains("away") {
                        Some("away".into())
                    } else {
                        None
                    },
                    competition: competition_in(&q),
                    season: find_year(&q),
                    date_from: None,
                    date_to: None,
                });
            }
            return self.search_matches(MatchArgs {
                team: Some(team.clone()),
                competition: competition_in(&q),
                season: find_year(&q),
                limit: Some(limit),
                sort: Some("newest".into()),
                ..Default::default()
            });
        }
        Err(ToolError::Unsupported("I could not map that question to the available dataset operations; use a structured tool for precise filters".into()))
    }
}

#[derive(Default, Deserialize)]
struct MatchArgs {
    team: Option<String>,
    opponent: Option<String>,
    venue: Option<String>,
    competition: Option<String>,
    season: Option<u16>,
    date_from: Option<String>,
    date_to: Option<String>,
    stage: Option<String>,
    round: Option<String>,
    sort: Option<String>,
    limit: Option<usize>,
    offset: Option<usize>,
}
#[derive(Deserialize)]
struct RecordArgs {
    team: String,
    opponent: Option<String>,
    venue: Option<String>,
    competition: Option<String>,
    season: Option<u16>,
    date_from: Option<String>,
    date_to: Option<String>,
}
#[derive(Deserialize)]
struct PlayerArgs {
    name: Option<String>,
    nationality: Option<String>,
    club: Option<String>,
    position: Option<String>,
    min_overall: Option<u8>,
    max_age: Option<u8>,
    sort: Option<String>,
    limit: Option<usize>,
    offset: Option<usize>,
}
#[derive(Deserialize)]
struct AnalysisArgs {
    competition: String,
    season: Option<u16>,
    analysis: String,
    metric: Option<String>,
    limit: Option<usize>,
}
#[derive(Deserialize)]
struct AskArgs {
    question: String,
    limit: Option<usize>,
}
fn from_value<T: for<'de> Deserialize<'de>>(v: Value) -> Result<T, ToolError> {
    serde_json::from_value(v).map_err(|e| ToolError::Invalid(e.to_string()))
}
fn valid_date(s: &str) -> Result<chrono::NaiveDate, ToolError> {
    parse_date(s).ok_or_else(|| ToolError::Invalid(format!("invalid date: {s}")))
}
fn validate_page(l: Option<usize>, _: Option<usize>) -> Result<(), ToolError> {
    if l == Some(0) || l.unwrap_or(1) > 200 {
        Err(ToolError::Invalid("limit must be between 1 and 200".into()))
    } else {
        Ok(())
    }
}
fn text_filter(a: Option<&str>, b: Option<&str>) -> bool {
    b.map(|q| {
        a.map(|v| normalize_text(v).contains(&normalize_text(q)))
            .unwrap_or(false)
    })
    .unwrap_or(true)
}
fn contains(a: &str, b: Option<&str>) -> bool {
    b.map(|q| normalize_text(a).contains(&normalize_text(q)))
        .unwrap_or(true)
}
fn update_record(r: &mut TeamRecord, m: &SoccerMatch, key: &str) {
    let home = m.home_team_key == key;
    r.matches += 1;
    let (gf, ga) = if home {
        (m.home_goals, m.away_goals)
    } else {
        (m.away_goals, m.home_goals)
    };
    r.goals_for += gf as u32;
    r.goals_against += ga as u32;
    if gf > ga {
        r.wins += 1;
        r.points += 3
    } else if gf == ga {
        r.draws += 1;
        r.points += 1
    } else {
        r.losses += 1
    }
}
fn standings(matches: &[&SoccerMatch]) -> Vec<Standing> {
    let mut map: BTreeMap<String, TeamRecord> = BTreeMap::new();
    for m in matches {
        for key in [&m.home_team_key, &m.away_team_key] {
            let mut r = map.remove(key).unwrap_or_else(|| TeamRecord {
                team: if key == &m.home_team_key {
                    m.home_team.clone()
                } else {
                    m.away_team.clone()
                },
                ..Default::default()
            });
            update_record(&mut r, m, key);
            map.insert(key.clone(), r);
        }
    }
    let mut v: Vec<_> = map.into_values().collect();
    v.sort_by_key(|r| {
        (
            Reverse(r.points),
            Reverse(r.goal_difference()),
            Reverse(r.goals_for),
            r.team.clone(),
        )
    });
    v.into_iter()
        .enumerate()
        .map(|(i, r)| Standing {
            position: i + 1,
            goal_difference: r.goal_difference(),
            record: r,
        })
        .collect()
}
fn datasets_for_matches(ms: &[SoccerMatch]) -> Vec<String> {
    let refs: Vec<_> = ms.iter().collect();
    datasets_for_refs(&refs)
}
fn datasets_for_refs(ms: &[&SoccerMatch]) -> Vec<String> {
    let mut d: BTreeMap<String, ()> = BTreeMap::new();
    for m in ms {
        for s in &m.sources {
            d.insert(s.clone(), ());
        }
    }
    d.into_keys().collect()
}
fn round1(v: f64) -> f64 {
    (v * 10.0).round() / 10.0
}
fn round2(v: f64) -> f64 {
    (v * 100.0).round() / 100.0
}
fn find_year(q: &str) -> Option<u16> {
    q.split_whitespace()
        .find_map(|s| s.parse::<u16>().ok().filter(|y| *y >= 1900 && *y <= 2100))
}
fn competition_in(q: &str) -> Option<String> {
    if q.contains("libertadores") {
        Some("Libertadores".into())
    } else if q.contains("copa do brasil") {
        Some("Copa do Brasil".into())
    } else if q.contains("brasile") || q.contains("serie a") {
        Some("Brasileirão".into())
    } else {
        None
    }
}
fn extract_after(q: &str, needle: &str) -> Option<String> {
    q.split_once(needle)
        .map(|(_, v)| v.trim().to_owned())
        .filter(|v| !v.is_empty())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn record_math() {
        let m = SoccerMatch {
            id: "x".into(),
            date: valid_date("2023-01-01").unwrap(),
            time: None,
            season: 2023,
            competition: "Brasileirão".into(),
            round: None,
            stage: None,
            home_team: "A".into(),
            home_team_key: "a".into(),
            away_team: "B".into(),
            away_team_key: "b".into(),
            home_goals: 2,
            away_goals: 1,
            arena: None,
            metrics: None,
            sources: vec!["x.csv".into()],
        };
        let mut r = TeamRecord::default();
        update_record(&mut r, &m, "a");
        assert_eq!((r.wins, r.points, r.goals_for), (1, 3, 2));
    }
}
