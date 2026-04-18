use crate::data::{Competition, DataStore, Match, Player, normalize_team_name, team_matches};
use std::collections::HashMap;

// ---------------------------------------------------------------------------
// search_matches
// ---------------------------------------------------------------------------

pub struct SearchMatchesArgs {
    pub team: Option<String>,
    pub opponent: Option<String>,
    pub competition: Option<String>,
    pub season: Option<i32>,
    pub date_from: Option<String>,
    pub date_to: Option<String>,
    pub limit: usize,
}

impl SearchMatchesArgs {
    pub fn from_json(v: &serde_json::Value) -> Self {
        SearchMatchesArgs {
            team: v.get("team").and_then(|x| x.as_str()).map(|s| s.to_string()),
            opponent: v.get("opponent").and_then(|x| x.as_str()).map(|s| s.to_string()),
            competition: v.get("competition").and_then(|x| x.as_str()).map(|s| s.to_string()),
            season: v.get("season").and_then(|x| x.as_i64()).map(|n| n as i32),
            date_from: v.get("date_from").and_then(|x| x.as_str()).map(|s| s.to_string()),
            date_to: v.get("date_to").and_then(|x| x.as_str()).map(|s| s.to_string()),
            limit: v.get("limit").and_then(|x| x.as_u64()).unwrap_or(20) as usize,
        }
    }
}

fn match_competition_filter(m: &Match, comp_str: &str) -> bool {
    match Competition::from_str(comp_str) {
        Some(c) => m.competition == c,
        None => {
            // also try matching the extra/tournament label
            m.extra.to_lowercase().contains(&comp_str.to_lowercase())
        }
    }
}

pub fn search_matches(store: &DataStore, args: &SearchMatchesArgs) -> String {
    let mut results: Vec<&Match> = store
        .matches
        .iter()
        .filter(|m| {
            // competition filter
            if let Some(ref comp) = args.competition {
                if !match_competition_filter(m, comp) {
                    return false;
                }
            }
            // season filter
            if let Some(season) = args.season {
                if m.season != season {
                    return false;
                }
            }
            // date range
            if let Some(ref from) = args.date_from {
                if m.date < *from {
                    return false;
                }
            }
            if let Some(ref to) = args.date_to {
                if m.date > *to {
                    return false;
                }
            }
            // team filter
            if let Some(ref team) = args.team {
                let home_ok = team_matches(&m.home_team, team);
                let away_ok = team_matches(&m.away_team, team);
                if !home_ok && !away_ok {
                    return false;
                }
                // opponent filter (only relevant when team is specified)
                if let Some(ref opp) = args.opponent {
                    if home_ok && !team_matches(&m.away_team, opp) {
                        return false;
                    }
                    if away_ok && !team_matches(&m.home_team, opp) {
                        return false;
                    }
                }
            } else if let Some(ref opp) = args.opponent {
                // opponent without team = either side
                if !team_matches(&m.home_team, opp) && !team_matches(&m.away_team, opp) {
                    return false;
                }
            }
            true
        })
        .collect();

    // Sort by date desc
    results.sort_by(|a, b| b.date.cmp(&a.date));

    let total = results.len();
    let shown: Vec<&Match> = results.into_iter().take(args.limit).collect();

    if shown.is_empty() {
        return "No matches found.".to_string();
    }

    let mut out = format!("Found {} match(es)", total);
    if total > args.limit {
        out.push_str(&format!(" (showing first {})", args.limit));
    }
    out.push_str(":\n\n");

    for m in shown {
        let round_info = if !m.round.is_empty() {
            format!(" | Round {}", m.round)
        } else if !m.extra.is_empty() {
            format!(" | {}", m.extra)
        } else {
            String::new()
        };
        out.push_str(&format!(
            "{} | {} {}-{} {} | {}{}",
            m.date,
            normalize_team_name(&m.home_team),
            m.home_goal,
            m.away_goal,
            normalize_team_name(&m.away_team),
            m.competition.label(),
            round_info,
        ));
        if m.season > 0 {
            out.push_str(&format!(" | Season {}", m.season));
        }
        out.push('\n');
    }
    out
}

// ---------------------------------------------------------------------------
// get_team_stats
// ---------------------------------------------------------------------------

pub struct TeamStatsArgs {
    pub team: String,
    pub competition: Option<String>,
    pub season: Option<i32>,
}

impl TeamStatsArgs {
    pub fn from_json(v: &serde_json::Value) -> Option<Self> {
        let team = v.get("team")?.as_str()?.to_string();
        Some(TeamStatsArgs {
            team,
            competition: v.get("competition").and_then(|x| x.as_str()).map(|s| s.to_string()),
            season: v.get("season").and_then(|x| x.as_i64()).map(|n| n as i32),
        })
    }
}

#[derive(Default)]
struct Record {
    played: i32,
    wins: i32,
    draws: i32,
    losses: i32,
    gf: i32,
    ga: i32,
}

impl Record {
    fn add_result(&mut self, gf: i32, ga: i32) {
        self.played += 1;
        self.gf += gf;
        self.ga += ga;
        if gf > ga {
            self.wins += 1;
        } else if gf == ga {
            self.draws += 1;
        } else {
            self.losses += 1;
        }
    }
}

pub fn get_team_stats(store: &DataStore, args: &TeamStatsArgs) -> String {
    let mut overall = Record::default();
    let mut home_rec = Record::default();
    let mut away_rec = Record::default();

    for m in &store.matches {
        if let Some(ref comp) = args.competition {
            if !match_competition_filter(m, comp) {
                continue;
            }
        }
        if let Some(season) = args.season {
            if m.season != season {
                continue;
            }
        }
        let is_home = team_matches(&m.home_team, &args.team);
        let is_away = team_matches(&m.away_team, &args.team);
        if is_home {
            overall.add_result(m.home_goal, m.away_goal);
            home_rec.add_result(m.home_goal, m.away_goal);
        } else if is_away {
            overall.add_result(m.away_goal, m.home_goal);
            away_rec.add_result(m.away_goal, m.home_goal);
        }
    }

    if overall.played == 0 {
        return format!("No data found for team '{}'.", args.team);
    }

    let win_rate = if overall.played > 0 {
        (overall.wins as f64 / overall.played as f64) * 100.0
    } else {
        0.0
    };

    let mut out = format!("Stats for '{}'", args.team);
    if let Some(s) = args.season {
        out.push_str(&format!(" (season {})", s));
    }
    if let Some(ref c) = args.competition {
        out.push_str(&format!(" [{}]", c));
    }
    out.push_str(&format!(
        "\n\nOverall:\n  Played: {}, Wins: {}, Draws: {}, Losses: {}\n  Goals For: {}, Goals Against: {}, Goal Diff: {:+}\n  Win Rate: {:.1}%",
        overall.played, overall.wins, overall.draws, overall.losses,
        overall.gf, overall.ga, overall.gf - overall.ga, win_rate
    ));
    out.push_str(&format!(
        "\n\nHome:\n  Played: {}, Wins: {}, Draws: {}, Losses: {}\n  Goals For: {}, Goals Against: {}",
        home_rec.played, home_rec.wins, home_rec.draws, home_rec.losses,
        home_rec.gf, home_rec.ga
    ));
    out.push_str(&format!(
        "\n\nAway:\n  Played: {}, Wins: {}, Draws: {}, Losses: {}\n  Goals For: {}, Goals Against: {}",
        away_rec.played, away_rec.wins, away_rec.draws, away_rec.losses,
        away_rec.gf, away_rec.ga
    ));
    out
}

// ---------------------------------------------------------------------------
// search_players
// ---------------------------------------------------------------------------

pub struct SearchPlayersArgs {
    pub name: Option<String>,
    pub nationality: Option<String>,
    pub club: Option<String>,
    pub position: Option<String>,
    pub min_overall: Option<i32>,
    pub max_results: usize,
}

impl SearchPlayersArgs {
    pub fn from_json(v: &serde_json::Value) -> Self {
        SearchPlayersArgs {
            name: v.get("name").and_then(|x| x.as_str()).map(|s| s.to_string()),
            nationality: v.get("nationality").and_then(|x| x.as_str()).map(|s| s.to_string()),
            club: v.get("club").and_then(|x| x.as_str()).map(|s| s.to_string()),
            position: v.get("position").and_then(|x| x.as_str()).map(|s| s.to_string()),
            min_overall: v.get("min_overall").and_then(|x| x.as_i64()).map(|n| n as i32),
            max_results: v.get("max_results").and_then(|x| x.as_u64()).unwrap_or(20) as usize,
        }
    }
}

fn player_field_matches(field: &str, query: &str) -> bool {
    field.to_lowercase().contains(&query.to_lowercase())
}

pub fn search_players(store: &DataStore, args: &SearchPlayersArgs) -> String {
    let mut results: Vec<&Player> = store
        .players
        .iter()
        .filter(|p| {
            if let Some(ref name) = args.name {
                if !player_field_matches(&p.name, name) {
                    return false;
                }
            }
            if let Some(ref nat) = args.nationality {
                if !player_field_matches(&p.nationality, nat) {
                    return false;
                }
            }
            if let Some(ref club) = args.club {
                if !player_field_matches(&p.club, club) {
                    return false;
                }
            }
            if let Some(ref pos) = args.position {
                if !player_field_matches(&p.position, pos) {
                    return false;
                }
            }
            if let Some(min) = args.min_overall {
                if p.overall < min {
                    return false;
                }
            }
            true
        })
        .collect();

    // Sort by overall desc
    results.sort_by(|a, b| b.overall.cmp(&a.overall));

    let total = results.len();
    let shown: Vec<&Player> = results.into_iter().take(args.max_results).collect();

    if shown.is_empty() {
        return "No players found.".to_string();
    }

    let mut out = format!("Found {} player(s)", total);
    if total > args.max_results {
        out.push_str(&format!(" (showing top {})", args.max_results));
    }
    out.push_str(":\n\n");

    for p in shown {
        out.push_str(&format!(
            "{} | Age: {} | {} | Overall: {} | Potential: {} | Club: {} | Position: {}\n",
            p.name, p.age, p.nationality, p.overall, p.potential, p.club, p.position
        ));
    }
    out
}

// ---------------------------------------------------------------------------
// get_standings
// ---------------------------------------------------------------------------

pub struct StandingsArgs {
    pub season: i32,
    pub competition: Option<String>,
}

impl StandingsArgs {
    pub fn from_json(v: &serde_json::Value) -> Option<Self> {
        let season = v.get("season")?.as_i64()? as i32;
        Some(StandingsArgs {
            season,
            competition: v.get("competition").and_then(|x| x.as_str()).map(|s| s.to_string()),
        })
    }
}

#[derive(Default, Clone)]
struct StandingsEntry {
    team: String,
    played: i32,
    wins: i32,
    draws: i32,
    losses: i32,
    gf: i32,
    ga: i32,
}

impl StandingsEntry {
    fn points(&self) -> i32 {
        self.wins * 3 + self.draws
    }
    fn gd(&self) -> i32 {
        self.gf - self.ga
    }
}

pub fn get_standings(store: &DataStore, args: &StandingsArgs) -> String {
    let mut table: HashMap<String, StandingsEntry> = HashMap::new();

    for m in &store.matches {
        if m.season != args.season {
            continue;
        }
        if let Some(ref comp) = args.competition {
            if !match_competition_filter(m, comp) {
                continue;
            }
        }
        let home_norm = normalize_team_name(&m.home_team);
        let away_norm = normalize_team_name(&m.away_team);

        let he = table.entry(home_norm.clone()).or_insert_with(|| StandingsEntry {
            team: home_norm.clone(),
            ..Default::default()
        });
        he.played += 1;
        he.gf += m.home_goal;
        he.ga += m.away_goal;
        if m.home_goal > m.away_goal {
            he.wins += 1;
        } else if m.home_goal == m.away_goal {
            he.draws += 1;
        } else {
            he.losses += 1;
        }

        let ae = table.entry(away_norm.clone()).or_insert_with(|| StandingsEntry {
            team: away_norm.clone(),
            ..Default::default()
        });
        ae.played += 1;
        ae.gf += m.away_goal;
        ae.ga += m.home_goal;
        if m.away_goal > m.home_goal {
            ae.wins += 1;
        } else if m.home_goal == m.away_goal {
            ae.draws += 1;
        } else {
            ae.losses += 1;
        }
    }

    if table.is_empty() {
        return format!("No data found for season {}.", args.season);
    }

    let mut entries: Vec<StandingsEntry> = table.into_values().collect();
    entries.sort_by(|a, b| {
        b.points()
            .cmp(&a.points())
            .then(b.gd().cmp(&a.gd()))
            .then(b.gf.cmp(&a.gf))
            .then(a.team.cmp(&b.team))
    });

    let comp_label = args
        .competition
        .as_deref()
        .unwrap_or("all competitions");
    let mut out = format!(
        "Standings for season {} ({}):\n\n",
        args.season, comp_label
    );
    out.push_str(&format!(
        "{:<4} {:<30} {:>4} {:>4} {:>4} {:>4} {:>4} {:>4} {:>4} {:>4}\n",
        "Pos", "Team", "P", "W", "D", "L", "GF", "GA", "GD", "Pts"
    ));
    out.push_str(&"-".repeat(72));
    out.push('\n');

    for (i, e) in entries.iter().enumerate() {
        out.push_str(&format!(
            "{:<4} {:<30} {:>4} {:>4} {:>4} {:>4} {:>4} {:>4} {:>4} {:>4}\n",
            i + 1,
            &e.team[..e.team.len().min(30)],
            e.played,
            e.wins,
            e.draws,
            e.losses,
            e.gf,
            e.ga,
            e.gd(),
            e.points()
        ));
    }
    out
}

// ---------------------------------------------------------------------------
// get_head_to_head
// ---------------------------------------------------------------------------

pub struct HeadToHeadArgs {
    pub team1: String,
    pub team2: String,
    pub competition: Option<String>,
    pub season: Option<i32>,
}

impl HeadToHeadArgs {
    pub fn from_json(v: &serde_json::Value) -> Option<Self> {
        let team1 = v.get("team1")?.as_str()?.to_string();
        let team2 = v.get("team2")?.as_str()?.to_string();
        Some(HeadToHeadArgs {
            team1,
            team2,
            competition: v.get("competition").and_then(|x| x.as_str()).map(|s| s.to_string()),
            season: v.get("season").and_then(|x| x.as_i64()).map(|n| n as i32),
        })
    }
}

pub fn get_head_to_head(store: &DataStore, args: &HeadToHeadArgs) -> String {
    let mut matches_h2h: Vec<&Match> = store
        .matches
        .iter()
        .filter(|m| {
            if let Some(ref comp) = args.competition {
                if !match_competition_filter(m, comp) {
                    return false;
                }
            }
            if let Some(season) = args.season {
                if m.season != season {
                    return false;
                }
            }
            let t1h = team_matches(&m.home_team, &args.team1);
            let t1a = team_matches(&m.away_team, &args.team1);
            let t2h = team_matches(&m.home_team, &args.team2);
            let t2a = team_matches(&m.away_team, &args.team2);
            (t1h && t2a) || (t1a && t2h)
        })
        .collect();

    matches_h2h.sort_by(|a, b| b.date.cmp(&a.date));

    if matches_h2h.is_empty() {
        return format!(
            "No head-to-head matches found between '{}' and '{}'.",
            args.team1, args.team2
        );
    }

    let mut t1_wins = 0i32;
    let mut t2_wins = 0i32;
    let mut draws = 0i32;
    let mut t1_goals = 0i32;
    let mut t2_goals = 0i32;

    for m in &matches_h2h {
        let t1_is_home = team_matches(&m.home_team, &args.team1);
        let (g1, g2) = if t1_is_home {
            (m.home_goal, m.away_goal)
        } else {
            (m.away_goal, m.home_goal)
        };
        t1_goals += g1;
        t2_goals += g2;
        if g1 > g2 {
            t1_wins += 1;
        } else if g1 == g2 {
            draws += 1;
        } else {
            t2_wins += 1;
        }
    }

    let mut out = format!(
        "Head-to-head: {} vs {}\n",
        args.team1, args.team2
    );
    out.push_str(&format!(
        "Summary: {} wins: {}, {} wins: {}, Draws: {}\n",
        args.team1, t1_wins, args.team2, t2_wins, draws
    ));
    out.push_str(&format!(
        "Goals: {} {}-{} {}\n\n",
        args.team1, t1_goals, t2_goals, args.team2
    ));
    out.push_str("Matches (most recent first):\n");

    for m in &matches_h2h {
        let round_info = if !m.round.is_empty() {
            format!(" | Round {}", m.round)
        } else if !m.extra.is_empty() {
            format!(" | {}", m.extra)
        } else {
            String::new()
        };
        out.push_str(&format!(
            "  {} | {} {}-{} {} | {}{}",
            m.date,
            normalize_team_name(&m.home_team),
            m.home_goal,
            m.away_goal,
            normalize_team_name(&m.away_team),
            m.competition.label(),
            round_info,
        ));
        if m.season > 0 {
            out.push_str(&format!(" | {}", m.season));
        }
        out.push('\n');
    }
    out
}

// ---------------------------------------------------------------------------
// get_global_stats
// ---------------------------------------------------------------------------

pub struct GlobalStatsArgs {
    pub competition: Option<String>,
    pub season: Option<i32>,
}

impl GlobalStatsArgs {
    pub fn from_json(v: &serde_json::Value) -> Self {
        GlobalStatsArgs {
            competition: v.get("competition").and_then(|x| x.as_str()).map(|s| s.to_string()),
            season: v.get("season").and_then(|x| x.as_i64()).map(|n| n as i32),
        }
    }
}

pub fn get_global_stats(store: &DataStore, args: &GlobalStatsArgs) -> String {
    let filtered: Vec<&Match> = store
        .matches
        .iter()
        .filter(|m| {
            if let Some(ref comp) = args.competition {
                if !match_competition_filter(m, comp) {
                    return false;
                }
            }
            if let Some(season) = args.season {
                if m.season != season {
                    return false;
                }
            }
            true
        })
        .collect();

    if filtered.is_empty() {
        return "No data found for the given filters.".to_string();
    }

    let total = filtered.len() as f64;
    let total_goals: i32 = filtered.iter().map(|m| m.home_goal + m.away_goal).sum();
    let home_wins = filtered.iter().filter(|m| m.home_goal > m.away_goal).count();
    let away_wins = filtered.iter().filter(|m| m.away_goal > m.home_goal).count();
    let draws = filtered.iter().filter(|m| m.home_goal == m.away_goal).count();

    let avg_goals = total_goals as f64 / total;
    let home_win_rate = home_wins as f64 / total * 100.0;
    let draw_rate = draws as f64 / total * 100.0;
    let away_win_rate = away_wins as f64 / total * 100.0;

    // Top scoring teams (combined home + away)
    let mut team_goals: HashMap<String, i32> = HashMap::new();
    for m in &filtered {
        let h = normalize_team_name(&m.home_team);
        let a = normalize_team_name(&m.away_team);
        *team_goals.entry(h).or_insert(0) += m.home_goal;
        *team_goals.entry(a).or_insert(0) += m.away_goal;
    }
    let mut top_teams: Vec<(String, i32)> = team_goals.into_iter().collect();
    top_teams.sort_by(|a, b| b.1.cmp(&a.1));

    // Biggest wins
    let mut big_wins: Vec<&Match> = filtered.clone();
    big_wins.sort_by(|a, b| {
        let da = (a.home_goal - a.away_goal).abs();
        let db = (b.home_goal - b.away_goal).abs();
        db.cmp(&da)
    });

    let mut out = String::new();
    if let Some(ref comp) = args.competition {
        out.push_str(&format!("Global stats for {} ", comp));
    } else {
        out.push_str("Global stats (all competitions) ");
    }
    if let Some(season) = args.season {
        out.push_str(&format!("season {}:\n\n", season));
    } else {
        out.push_str("(all seasons):\n\n");
    }

    out.push_str(&format!("Matches analyzed: {}\n", filtered.len()));
    out.push_str(&format!("Total goals: {}\n", total_goals));
    out.push_str(&format!("Average goals/match: {:.2}\n", avg_goals));
    out.push_str(&format!("Home win rate: {:.1}%\n", home_win_rate));
    out.push_str(&format!("Draw rate: {:.1}%\n", draw_rate));
    out.push_str(&format!("Away win rate: {:.1}%\n", away_win_rate));

    out.push_str("\nTop scoring teams (goals scored):\n");
    for (team, goals) in top_teams.iter().take(10) {
        out.push_str(&format!("  {} - {} goals\n", team, goals));
    }

    out.push_str("\nBiggest wins:\n");
    for m in big_wins.iter().take(10) {
        let diff = (m.home_goal - m.away_goal).abs();
        out.push_str(&format!(
            "  {} | {} {}-{} {} | {} | diff={}\n",
            m.date,
            normalize_team_name(&m.home_team),
            m.home_goal,
            m.away_goal,
            normalize_team_name(&m.away_team),
            m.competition.label(),
            diff
        ));
    }
    out
}
