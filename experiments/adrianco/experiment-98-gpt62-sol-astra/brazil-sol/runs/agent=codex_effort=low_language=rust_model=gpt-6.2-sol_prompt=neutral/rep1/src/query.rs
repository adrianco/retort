use crate::data::{Graph, Match, SOURCES, competition, date, fold, team_key};
use serde::{Deserialize, Serialize, de::DeserializeOwned};
use serde_json::{Value, json};
use std::{
    cmp::Reverse,
    collections::{BTreeMap, BTreeSet},
};

#[derive(Default, Deserialize)]
#[serde(default, deny_unknown_fields)]
struct Filter {
    team: Option<String>,
    opponent: Option<String>,
    venue: Option<Venue>,
    competition: Option<String>,
    season: Option<u32>,
    start_date: Option<String>,
    end_date: Option<String>,
    stage: Option<String>,
    round: Option<String>,
    source: Option<String>,
    derbies: bool,
    limit: Option<usize>,
    offset: usize,
    order: Option<Order>,
}

#[derive(Clone, Copy, Deserialize)]
#[serde(rename_all = "snake_case")]
enum Venue {
    Home,
    Away,
    Either,
}

#[derive(Deserialize)]
#[serde(rename_all = "snake_case")]
enum Order {
    Latest,
    Earliest,
    BiggestWin,
}

#[derive(Default, Deserialize)]
#[serde(default, deny_unknown_fields)]
struct PlayerFilter {
    name: Option<String>,
    nationality: Option<String>,
    club: Option<String>,
    position: Option<String>,
    limit: Option<usize>,
    offset: usize,
}

#[derive(Default, Serialize)]
struct Record {
    played: u32,
    wins: u32,
    draws: u32,
    losses: u32,
    goals_for: u32,
    goals_against: u32,
}

impl Record {
    fn add(&mut self, scored: u32, conceded: u32) {
        self.played += 1;
        self.wins += u32::from(scored > conceded);
        self.draws += u32::from(scored == conceded);
        self.losses += u32::from(scored < conceded);
        self.goals_for += scored;
        self.goals_against += conceded;
    }

    fn points(&self) -> u32 {
        self.wins * 3 + self.draws
    }

    fn difference(&self) -> i64 {
        i64::from(self.goals_for) - i64::from(self.goals_against)
    }

    fn rate(&self) -> f64 {
        if self.played == 0 {
            0.0
        } else {
            100.0 * f64::from(self.wins) / f64::from(self.played)
        }
    }

    fn json(&self) -> Value {
        let mut value = json!(self);
        value["win_rate_percent"] = json!(self.rate());
        value["points"] = json!(self.points());
        value["goal_difference"] = json!(self.difference());
        value
    }
}

fn derby(home: &str, away: &str) -> bool {
    const RIVALRIES: &[(&str, &str)] = &[
        ("flamengo", "fluminense"),
        ("flamengo", "vasco da gama"),
        ("flamengo", "botafogo rj"),
        ("fluminense", "vasco da gama"),
        ("fluminense", "botafogo rj"),
        ("vasco da gama", "botafogo rj"),
        ("corinthians", "palmeiras"),
        ("corinthians", "sao paulo"),
        ("corinthians", "santos"),
        ("palmeiras", "sao paulo"),
        ("palmeiras", "santos"),
        ("sao paulo", "santos"),
        ("gremio", "internacional"),
        ("atletico mineiro", "cruzeiro"),
        ("athletico paranaense", "coritiba"),
        ("bahia", "vitoria"),
        ("ceara", "fortaleza"),
        ("sport", "nautico"),
        ("sport", "santa cruz"),
        ("nautico", "santa cruz"),
        ("goias", "vila nova"),
        ("goias", "atletico goianiense"),
        ("ponte preta", "guarani"),
        ("paysandu", "remo"),
        ("abc", "america rn"),
        ("figueirense", "avai"),
    ];
    RIVALRIES
        .iter()
        .any(|&(a, b)| (a == home && b == away) || (b == home && a == away))
}

fn position_matches(filter: &str, position: &str) -> bool {
    match filter {
        "forward" | "forwards" => {
            ["LS", "ST", "RS", "LW", "LF", "CF", "RF", "RW"].contains(&position)
        }
        "midfielder" | "midfielders" => [
            "LAM", "CAM", "RAM", "LM", "LCM", "CM", "RCM", "RM", "LDM", "CDM", "RDM",
        ]
        .contains(&position),
        "defender" | "defenders" => {
            ["LWB", "RWB", "LB", "LCB", "CB", "RCB", "RB"].contains(&position)
        }
        "goalkeeper" | "goalkeepers" => position == "GK",
        _ => position.eq_ignore_ascii_case(filter),
    }
}

impl Graph {
    fn matches(&self, filter: &Filter) -> Result<Vec<&Match>, String> {
        let source = match filter.source.as_deref() {
            Some(file) if SOURCES[..5].contains(&file) => Some(file),
            Some(file) => return Err(format!("Unknown match source {file}")),
            None => None,
        };
        let parse = |value: &str| date(value).ok_or_else(|| format!("Invalid date {value}"));
        let start = filter.start_date.as_deref().map(parse).transpose()?;
        let end = filter.end_date.as_deref().map(parse).transpose()?;
        if let (Some(a), Some(b)) = (&start, &end)
            && a > b
        {
            return Err("start_date must be on or before end_date".into());
        }
        if filter.team.is_none()
            && (filter.opponent.is_some()
                || matches!(filter.venue, Some(Venue::Home | Venue::Away)))
        {
            return Err("Specify a team when filtering by opponent or venue".into());
        }
        let team = filter.team.as_deref().map(|s| team_key(s, ""));
        let opponent = filter.opponent.as_deref().map(|s| team_key(s, ""));
        let comp = filter.competition.as_deref().map(competition);
        let stage = filter
            .stage
            .as_deref()
            .map(fold)
            .map(|s| if s == "finals" { "final".into() } else { s });
        let mut rows: Vec<_> = if source.is_some() {
            &self.raw
        } else {
            &self.fixtures
        }
        .iter()
        .filter(|m| {
            let home = team.as_ref().is_none_or(|t| &m.home == t)
                && opponent.as_ref().is_none_or(|t| &m.away == t);
            let away = team.as_ref().is_none_or(|t| &m.away == t)
                && opponent.as_ref().is_none_or(|t| &m.home == t);
            (match filter.venue.unwrap_or(Venue::Either) {
                Venue::Home => home,
                Venue::Away => away,
                Venue::Either => home || away,
            }) && source.is_none_or(|s| m.sources.contains(&s))
                && comp.as_ref().is_none_or(|c| &m.competition == c)
                && filter.season.is_none_or(|s| m.season == Some(s))
                && start
                    .as_ref()
                    .is_none_or(|s| m.date.as_ref().is_some_and(|d| d >= s))
                && end
                    .as_ref()
                    .is_none_or(|s| m.date.as_ref().is_some_and(|d| d <= s))
                && stage
                    .as_ref()
                    .is_none_or(|s| m.stage.as_deref().is_some_and(|v| fold(v) == *s))
                && filter
                    .round
                    .as_ref()
                    .is_none_or(|r| m.round.as_ref() == Some(r))
                && (!filter.derbies || derby(&m.home, &m.away))
        })
        .collect();
        match filter.order {
            Some(Order::Earliest) => rows.sort_by_key(|m| (m.date.is_none(), &m.date, &m.time)),
            Some(Order::BiggestWin) => {
                rows.retain(|m| m.score().is_some_and(|(h, a)| h != a));
                rows.sort_by_key(|m| Reverse(m.score().map(|(h, a)| h.abs_diff(a))));
            }
            _ => {}
        }
        Ok(rows)
    }

    fn players(&self, f: &PlayerFilter) -> Value {
        let name = f.name.as_deref().map(fold);
        let nationality = f.nationality.as_deref().map(fold).map(|n| {
            if n == "brazilian" || n == "brasil" {
                "brazil".into()
            } else {
                n
            }
        });
        let club = f.club.as_deref().map(|c| team_key(c, ""));
        let position = f.position.as_deref().map(fold);
        let rows: Vec<_> = self
            .players
            .iter()
            .filter(|p| {
                name.as_ref().is_none_or(|n| p.name_key.contains(n))
                    && nationality.as_ref().is_none_or(|n| p.nationality_key == *n)
                    && club
                        .as_ref()
                        .is_none_or(|c| p.club.is_some() && p.club_key == *c)
                    && position.as_ref().is_none_or(|code| {
                        p.position
                            .as_deref()
                            .is_some_and(|p| position_matches(code, p))
                    })
            })
            .collect();
        let mut clubs: BTreeMap<&str, (usize, u32, u32)> = BTreeMap::new();
        for player in &rows {
            if self.teams.contains_key(&player.club_key)
                && let Some(club) = player.club.as_deref()
            {
                let entry = clubs.entry(club).or_default();
                entry.0 += 1;
                if let Some(rating) = player.overall {
                    entry.1 += rating;
                    entry.2 += 1;
                }
            }
        }
        let clubs: Vec<_> = clubs.into_iter().map(|(club,(count,sum,rated))|
            json!({"club":club,"count":count,"average_overall": ratio(sum,rated)})).collect();
        let mut result = page("players", &rows, f.offset, f.limit.unwrap_or(10).min(100));
        result["clubs_in_match_data"] = json!(clubs);
        result
    }

    fn team_stats(&self, filter: &Filter) -> Result<Value, String> {
        let team = filter.team.as_deref().ok_or("Specify a team")?;
        let key = team_key(team, "");
        let rows = self.matches(filter)?;
        let mut total = Record::default();
        let mut by_venue: BTreeMap<_, Record> =
            [("home", Record::default()), ("away", Record::default())].into();
        let mut by_competition: BTreeMap<_, Record> = BTreeMap::new();
        let mut by_season: BTreeMap<_, Record> = BTreeMap::new();
        for m in &rows {
            let comp = by_competition.entry(&m.competition).or_default();
            if let Some((h, a)) = m.score() {
                let (venue, scored, conceded) = if m.home == key {
                    ("home", h, a)
                } else {
                    ("away", a, h)
                };
                total.add(scored, conceded);
                by_venue.get_mut(venue).unwrap().add(scored, conceded);
                comp.add(scored, conceded);
                if let Some(year) = m.season {
                    by_season.entry(year).or_default().add(scored, conceded);
                }
            }
        }
        let players = self.players(&PlayerFilter {
            club: Some(team.into()),
            ..Default::default()
        });
        let mut result = page(
            "matches",
            &rows,
            filter.offset,
            filter.limit.unwrap_or(10).min(200),
        );
        result["team"] = json!(self.teams.get(&key).map(String::as_str).unwrap_or(team));
        result["opponent"] = json!(filter.opponent);
        result["opponent_wins"] = json!(filter.opponent.as_ref().map(|_| total.losses));
        result["record"] = total.json();
        result["by_venue"] = json!(
            by_venue
                .into_iter()
                .map(|(k, v)| (k, v.json()))
                .collect::<BTreeMap<_, _>>()
        );
        result["by_competition"] = json!(
            by_competition
                .into_iter()
                .map(|(k, v)| (k, v.json()))
                .collect::<BTreeMap<_, _>>()
        );
        result["by_season"] = json!(
            by_season
                .into_iter()
                .map(|(k, v)| (k, v.json()))
                .collect::<BTreeMap<_, _>>()
        );
        result["fifa_players"] = players;
        Ok(result)
    }

    fn standings(&self, args: StandingArgs) -> Result<Value, String> {
        let comp = competition(&args.competition);
        if !matches!(comp.as_str(), "Brasileirão" | "Série B") {
            return Err(
                "Standings are available for Brasileirão and Série B. Use cup_bracket for cups."
                    .into(),
            );
        }
        let filter = Filter {
            competition: Some(comp.clone()),
            season: Some(args.season),
            source: args.source,
            ..Default::default()
        };
        let rows = self.matches(&filter)?;
        let mut records = BTreeMap::<&str, Record>::new();
        for m in &rows {
            records.entry(&m.home).or_default();
            records.entry(&m.away).or_default();
            if let Some((h, a)) = m.score() {
                records.get_mut(m.home.as_str()).unwrap().add(h, a);
                records.get_mut(m.away.as_str()).unwrap().add(a, h);
            }
        }
        let played = rows.iter().filter(|m| m.score().is_some()).count();
        let mut table: Vec<_> = records.into_iter().collect();
        table.sort_by_key(|(k, r)| {
            (
                Reverse(r.points()),
                Reverse(r.wins),
                Reverse(r.difference()),
                Reverse(r.goals_for),
                *k,
            )
        });
        let n = table.len();
        let double_round_robin = n >= 2
            && played == n * (n - 1)
            && rows
                .iter()
                .filter(|m| m.score().is_some())
                .map(|m| (&m.home, &m.away))
                .collect::<BTreeSet<_>>()
                .len()
                == played;
        let table: Vec<_> = table
            .into_iter()
            .enumerate()
            .map(|(i, (key, record))| {
                let mut row = record.json();
                row["team"] = json!(self.teams[key]);
                row["rank"] = json!(i + 1);
                row
            })
            .collect();
        let relegated: Vec<_> =
            if comp == "Brasileirão" && args.season >= 2006 && double_round_robin {
                table
                    .iter()
                    .rev()
                    .take(4)
                    .rev()
                    .map(|row| &row["team"])
                    .collect()
            } else {
                Vec::new()
            };
        Ok(
            json!({"competition":comp,"season":args.season,"matches_played":played,
            "matches_in_data":rows.len(),"complete_double_round_robin":double_round_robin,
            "leader":table.first().map(|r| &r["team"]),
            "champion":if double_round_robin { table.first().map(|r| &r["team"]) } else { None },
            "standings":table,"relegated":relegated,
            "note":"Calculated from recorded scores using 3 points per win and 1 per draw. Administrative adjustments and unavailable competition tiebreakers are excluded.",
            "top_scorers_available":false}),
        )
    }

    fn cup_bracket(&self, args: StandingArgs) -> Result<Value, String> {
        let comp = competition(&args.competition);
        if !matches!(comp.as_str(), "Copa do Brasil" | "Copa Libertadores") {
            return Err("Choose Copa do Brasil or Copa Libertadores".into());
        }
        let rows = self.matches(&Filter {
            competition: Some(comp.clone()),
            season: Some(args.season),
            source: args.source,
            order: Some(Order::Earliest),
            ..Default::default()
        })?;
        let mut groups = BTreeMap::<_, Vec<&Match>>::new();
        for m in rows {
            let key = match m.stage.as_deref() {
                Some("group stage") => continue,
                Some("round of 16") => (16, "round of 16".into()),
                Some("quarterfinals") => (17, "quarterfinals".into()),
                Some("semifinals") => (18, "semifinals".into()),
                Some("final") => (19, "final".into()),
                Some(stage) => (20, stage.into()),
                None => m
                    .round
                    .as_deref()
                    .and_then(|r| r.parse::<u32>().ok().map(|n| (n, format!("round {r}"))))
                    .unwrap_or((0, "stage unavailable".into())),
            };
            groups.entry(key).or_default().push(m);
        }
        let rounds: Vec<_> = groups
            .into_iter()
            .map(|((_, stage), matches)| json!({"stage": stage, "matches": matches}))
            .collect();
        Ok(
            json!({"competition":comp,"season":args.season,"rounds":rounds,
            "note":"Fixture dates and scores are shown as recorded. Some stages, penalty shootouts and other advancement details may be missing."}),
        )
    }

    fn analysis(&self, args: AnalysisArgs) -> Result<Value, String> {
        let f = Filter {
            competition: args.competition,
            season: args.season,
            source: args.source,
            ..Default::default()
        };
        let size = args.limit.unwrap_or(10).min(100);
        let rows = self.matches(&f)?;
        let mut totals = Record::default();
        let mut seasons: BTreeMap<u32, Record> = BTreeMap::new();
        let mut teams = BTreeMap::<&str, Record>::new();
        for m in &rows {
            if args
                .seasons
                .as_ref()
                .is_some_and(|years| m.season.is_none_or(|y| !years.contains(&y)))
            {
                continue;
            }
            let Some((h, a)) = m.score() else { continue };
            totals.add(h, a);
            if let Some(year) = m.season {
                seasons.entry(year).or_default().add(h, a);
            }
            if !matches!(args.venue, Some(Venue::Away)) {
                teams.entry(&m.home).or_default().add(h, a);
            }
            if !matches!(args.venue, Some(Venue::Home)) {
                teams.entry(&m.away).or_default().add(a, h);
            }
        }
        let mut ranked: Vec<_> = teams
            .into_iter()
            .filter(|(_, r)| r.played >= args.min_matches.unwrap_or(1))
            .collect();
        ranked.sort_by(|(ak, a), (bk, b)| {
            let ordering = match args.rank_by.unwrap_or(Ranking::WinRate) {
                Ranking::WinRate => b.rate().total_cmp(&a.rate()),
                Ranking::Goals => b.goals_for.cmp(&a.goals_for),
                Ranking::Wins => b.wins.cmp(&a.wins),
                Ranking::Points => b.points().cmp(&a.points()),
            };
            ordering
                .then_with(|| b.played.cmp(&a.played))
                .then_with(|| ak.cmp(bk))
        });
        let leaders: Vec<_> = ranked
            .into_iter()
            .take(size)
            .map(|(team, record)| {
                let mut row = record.json();
                row["team"] = json!(self.teams[team]);
                row
            })
            .collect();
        let season_totals: Vec<_> = seasons
            .into_iter()
            .map(|(year, r)| metrics(&r, Some(year)))
            .collect();
        let mut result = metrics(&totals, None);
        result["by_season"] = json!(season_totals);
        result["team_rankings"] = json!(leaders);
        Ok(result)
    }

    pub fn call(&self, tool: &str, args: Value) -> Result<Value, String> {
        match tool {
            "search_matches" => {
                let f: Filter = parse(args)?;
                let rows = self.matches(&f)?;
                Ok(page(
                    "matches",
                    &rows,
                    f.offset,
                    f.limit.unwrap_or(20).min(200),
                ))
            }
            "team_stats" => self.team_stats(&parse(args)?),
            "search_players" => Ok(self.players(&parse(args)?)),
            "standings" => self.standings(parse(args)?),
            "cup_bracket" => self.cup_bracket(parse(args)?),
            "analyze_matches" => self.analysis(parse(args)?),
            "dataset_info" => {
                let _: Empty = parse(args)?;
                Ok(
                    json!({"sources":self.counts,"merged_fixtures":self.fixtures.len(),
                    "competitions":self.fixtures.iter().map(|m| &m.competition).collect::<BTreeSet<_>>(),
                    "note":"FIFA club and player details are a snapshot. Match files do not identify individual goal scorers."}),
                )
            }
            _ => Err(format!("Unknown tool {tool}")),
        }
    }
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Empty {}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct StandingArgs {
    competition: String,
    season: u32,
    source: Option<String>,
}

#[derive(Default, Deserialize)]
#[serde(default, deny_unknown_fields)]
struct AnalysisArgs {
    competition: Option<String>,
    season: Option<u32>,
    seasons: Option<Vec<u32>>,
    venue: Option<Venue>,
    rank_by: Option<Ranking>,
    min_matches: Option<u32>,
    limit: Option<usize>,
    source: Option<String>,
}

#[derive(Clone, Copy, Deserialize)]
#[serde(rename_all = "snake_case")]
enum Ranking {
    WinRate,
    Goals,
    Wins,
    Points,
}

fn parse<T: DeserializeOwned>(value: Value) -> Result<T, String> {
    serde_json::from_value(value).map_err(|err| err.to_string())
}

fn page<T: Serialize>(key: &str, entries: &[T], offset: usize, limit: usize) -> Value {
    let end = offset.saturating_add(limit).min(entries.len());
    json!({ (key): &entries[offset.min(end)..end], "total":entries.len(),
        "next_offset": (limit > 0 && end < entries.len()).then_some(end) })
}

fn ratio(n: u32, d: u32) -> Option<f64> {
    (d != 0).then(|| f64::from(n) / f64::from(d))
}

fn metrics(r: &Record, season: Option<u32>) -> Value {
    json!({"season":season,"matches_played":r.played,"home_wins":r.wins,"draws":r.draws,
        "away_wins":r.losses,"home_goals":r.goals_for,"away_goals":r.goals_against,
        "average_goals":ratio(r.goals_for+r.goals_against,r.played),
        "home_win_rate_percent":ratio(r.wins*100,r.played)})
}

pub fn tools() -> Value {
    let text = |description| json!({"type":"string","description":description});
    let unsigned = |description| json!({"type":"integer","minimum":0,"description":description});
    let choices = |values: &[&str]| json!({"type":"string","enum":values});
    let venue = choices(&["home", "away", "either"]);
    let source = json!({"type":"string","enum":&SOURCES[..5],"description":"Use rows directly from this CSV. Omit to use merged fixtures."});
    let season = unsigned("Season year");
    let comp = text(
        "Competition, e.g. Brasileirão (Série A), Copa do Brasil, Copa Libertadores, Série B or Série C",
    );
    let limit = unsigned("Maximum number of entries returned");
    let offset = unsigned("Pagination offset, given by next_offset");
    let filter = json!({
        "team":text("Team name"), "opponent":text("Opponent of team, in either orientation by default"),
        "venue":venue,"competition":comp,"season":season,"source":source,
        "start_date":text("Inclusive start date, YYYY-MM-DD or DD/MM/YYYY"),
        "end_date":text("Inclusive end date, YYYY-MM-DD or DD/MM/YYYY"),
        "stage":text("Stage, e.g. final, semifinals, quarterfinals, round of 16, group stage"),
        "round":text("Round number as a string"),"derbies":{"type":"boolean"},
        "order":choices(&["latest","earliest","biggest_win"]),"limit":limit,"offset":offset
    });
    let tool = |name, description, properties: Value, required: &[&str]| {
        json!({
            "name":name,"description":description,
            "inputSchema":{"type":"object","properties":properties,"required":required,"additionalProperties":false},
            "annotations":{"readOnlyHint":true,"openWorldHint":false}
        })
    };
    json!([
        tool(
            "search_matches",
            "Find schedules and results, most recent meetings, cup brackets by stage, derbies, or biggest wins. Returns source files and available match details.",
            filter.clone(),
            &[]
        ),
        tool(
            "team_stats",
            "Calculate a team's record by competition, venue and season. Set opponent for a head-to-head comparison. Includes matches and associated FIFA club players.",
            filter,
            &["team"]
        ),
        tool(
            "search_players",
            "Search the FIFA snapshot by partial name, nationality, club, or position. Highest overall ratings come first. Position accepts FIFA codes or broad groups like forward.",
            json!({
                "name":text("Full or partial player name"),"nationality":text("Nationality, e.g. Brazil"),
                "club":text("Club name"),"position":text("Position code or forward, midfielder, defender, goalkeeper"),
                "limit": limit,"offset":offset
            }),
            &[]
        ),
        tool(
            "cup_bracket",
            "Show knockout rounds and recorded legs by stage for Copa Libertadores or Copa do Brasil.",
            json!({"competition":comp,"season":season,"source":source}),
            &["competition", "season"]
        ),
        tool(
            "standings",
            "Calculate a league table, leader, and relegation where coverage permits. Use cup_bracket for cups. Individual scorer data is unavailable.",
            json!({
                "competition":comp,"season":season,"source":source
            }),
            &["competition", "season"]
        ),
        tool(
            "analyze_matches",
            "Compare season scoring and outcome trends and rank teams by home/away or overall results. Venue applies to team rankings.",
            json!({
                "competition":comp,"season":season,"seasons":{"type":"array","items":season},
                "source":source,"venue":venue,"rank_by":choices(&["win_rate","goals","wins","points"]),
                "min_matches":unsigned("Minimum scored matches for a ranked team"),"limit":limit
            }),
            &[]
        ),
        tool(
            "dataset_info",
            "List supplied datasets, row counts, competitions and data limitations.",
            json!({}),
            &[]
        )
    ])
}
