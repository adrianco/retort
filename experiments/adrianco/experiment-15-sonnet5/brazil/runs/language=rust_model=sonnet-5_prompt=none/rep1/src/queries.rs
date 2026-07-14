//! Query implementations. Every function is a pure read over [`Store`] that
//! returns a human-readable, pre-formatted string, matching the answer
//! style shown in `TASK.md`.

use std::collections::HashMap;

use chrono::NaiveDate;

use crate::model::MatchRecord;
use crate::normalize::{normalize_team_name, parse_flexible_date};
use crate::store::Store;

fn matches_team(record_key: &str, user_key: &str) -> bool {
    // Guard both sides: `"anything".contains("")` is true in Rust, which
    // would otherwise make an empty record key (e.g. a FIFA player with no
    // club) match every team query.
    !user_key.is_empty()
        && !record_key.is_empty()
        && (record_key == user_key || record_key.contains(user_key) || user_key.contains(record_key))
}

fn matches_competition(record_competition: &str, query: &str) -> bool {
    query.is_empty() || record_competition.to_lowercase().contains(&query.to_lowercase())
}

struct MatchFilter<'a> {
    team: Option<&'a str>,
    opponent: Option<&'a str>,
    competition: Option<&'a str>,
    season: Option<i32>,
    date_from: Option<NaiveDate>,
    date_to: Option<NaiveDate>,
}

impl<'a> MatchFilter<'a> {
    fn matches(&self, m: &MatchRecord) -> bool {
        if let Some(c) = self.competition {
            if !matches_competition(&m.competition, c) {
                return false;
            }
        }
        if let Some(s) = self.season {
            if m.season != Some(s) {
                return false;
            }
        }
        if let Some(from) = self.date_from {
            if m.date.is_none_or(|d| d < from) {
                return false;
            }
        }
        if let Some(to) = self.date_to {
            if m.date.is_none_or(|d| d > to) {
                return false;
            }
        }
        match (self.team, self.opponent) {
            (Some(t), Some(o)) => {
                let t = normalize_team_name(t);
                let o = normalize_team_name(o);
                (matches_team(&m.home_team_key, &t) && matches_team(&m.away_team_key, &o))
                    || (matches_team(&m.home_team_key, &o) && matches_team(&m.away_team_key, &t))
            }
            (Some(t), None) => {
                let t = normalize_team_name(t);
                matches_team(&m.home_team_key, &t) || matches_team(&m.away_team_key, &t)
            }
            (None, Some(o)) => {
                let o = normalize_team_name(o);
                matches_team(&m.home_team_key, &o) || matches_team(&m.away_team_key, &o)
            }
            (None, None) => true,
        }
    }
}

fn filter_matches<'a>(store: &'a Store, f: &MatchFilter) -> Vec<&'a MatchRecord> {
    let mut v: Vec<&MatchRecord> = store.matches.iter().filter(|m| f.matches(m)).collect();
    v.sort_by_key(|m| std::cmp::Reverse(m.date));
    v
}

fn fmt_match(store: &Store, m: &MatchRecord) -> String {
    let score = match (m.home_goal, m.away_goal) {
        (Some(h), Some(a)) => format!("{h}-{a}"),
        _ => "unplayed".to_string(),
    };
    let date = m
        .date
        .map(|d| d.format("%Y-%m-%d").to_string())
        .unwrap_or_else(|| m.date_display.clone());
    let mut extra = m.competition.clone();
    if let Some(r) = &m.round {
        extra.push_str(&format!(" Round {r}"));
    }
    if let Some(s) = &m.stage {
        extra.push_str(&format!(" - {s}"));
    }
    if let Some(v) = &m.venue {
        extra.push_str(&format!(" at {v}"));
    }
    let _ = store; // display names already carried on the record
    format!("{date}: {} {score} {} ({extra})", m.home_team, m.away_team)
}

fn parse_date_arg(s: &str) -> Option<NaiveDate> {
    if s.is_empty() {
        None
    } else {
        parse_flexible_date(s)
    }
}

/// "Show me all Flamengo vs Fluminense matches" / "What matches did
/// Palmeiras play in 2023?" / "Find all Copa do Brasil finals" (via
/// `competition`/`season`/`date_from`/`date_to` filters).
pub fn search_matches(
    store: &Store,
    team: &str,
    opponent: &str,
    competition: &str,
    season: Option<i32>,
    date_from: &str,
    date_to: &str,
    limit: usize,
) -> String {
    let filter = MatchFilter {
        team: (!team.is_empty()).then_some(team),
        opponent: (!opponent.is_empty()).then_some(opponent),
        competition: (!competition.is_empty()).then_some(competition),
        season,
        date_from: parse_date_arg(date_from),
        date_to: parse_date_arg(date_to),
    };
    let results = filter_matches(store, &filter);
    if results.is_empty() {
        return "No matches found for the given criteria.".to_string();
    }
    let total = results.len();
    let limit = if limit == 0 { 20 } else { limit };
    let mut out = String::new();
    if !team.is_empty() && !opponent.is_empty() {
        out.push_str(&format!("{team} vs {opponent}:\n"));
    } else {
        out.push_str(&format!("Found {total} match(es):\n"));
    }
    for m in results.iter().take(limit) {
        out.push_str("- ");
        out.push_str(&fmt_match(store, m));
        out.push('\n');
    }
    if total > limit {
        out.push_str(&format!("... ({} more matches in dataset)\n", total - limit));
    }
    if !team.is_empty() && !opponent.is_empty() {
        out.push('\n');
        out.push_str(&head_to_head_summary(store, team, opponent, &results));
    }
    out
}

fn head_to_head_summary(store: &Store, team: &str, opponent: &str, results: &[&MatchRecord]) -> String {
    let t_key = normalize_team_name(team);
    let mut team_wins = 0;
    let mut opp_wins = 0;
    let mut draws = 0;
    for m in results {
        let Some(outcome) = m.home_outcome() else { continue };
        let team_is_home = matches_team(&m.home_team_key, &t_key);
        let effective = if team_is_home { outcome } else { -outcome };
        match effective {
            1 => team_wins += 1,
            -1 => opp_wins += 1,
            _ => draws += 1,
        }
    }
    format!(
        "Head-to-head in dataset: {} {} wins, {} {} wins, {} draws",
        store.display_name_for(&t_key),
        team_wins,
        store.display_name_for(&normalize_team_name(opponent)),
        opp_wins,
        draws
    )
}

/// "Compare Palmeiras and Santos head-to-head"
pub fn compare_teams(store: &Store, team_a: &str, team_b: &str, competition: &str, season: Option<i32>) -> String {
    search_matches(store, team_a, team_b, competition, season, "", "", 10_000)
}

#[derive(Default, Clone)]
struct TeamStat {
    played: u32,
    wins: u32,
    draws: u32,
    losses: u32,
    goals_for: i64,
    goals_against: i64,
}

impl TeamStat {
    fn points(&self) -> u32 {
        self.wins * 3 + self.draws
    }
    fn goal_diff(&self) -> i64 {
        self.goals_for - self.goals_against
    }
    fn win_rate(&self) -> f64 {
        if self.played == 0 {
            0.0
        } else {
            self.wins as f64 / self.played as f64 * 100.0
        }
    }
}

#[derive(Clone, Copy, PartialEq)]
enum Venue {
    Home,
    Away,
    All,
}

fn parse_venue(s: &str) -> Venue {
    match s.to_lowercase().as_str() {
        "home" => Venue::Home,
        "away" => Venue::Away,
        _ => Venue::All,
    }
}

/// "What is Corinthians' home record in 2022?"
pub fn team_record(store: &Store, team: &str, competition: &str, season: Option<i32>, venue: &str) -> String {
    if team.is_empty() {
        return "A team name is required.".to_string();
    }
    let t_key = normalize_team_name(team);
    let venue = parse_venue(venue);
    // Some base names (e.g. "Atletico") are shared by distinct clubs in
    // different states; when that's the case for this query, only count
    // matches for the specific club identity the caller asked for.
    let ambiguous = store.is_ambiguous_base(&t_key);
    let user_identity = store.resolve_identity(team);
    let filter = MatchFilter {
        team: Some(team),
        opponent: None,
        competition: (!competition.is_empty()).then_some(competition),
        season,
        date_from: None,
        date_to: None,
    };
    let mut stat = TeamStat::default();
    for m in filter_matches(store, &filter) {
        let Some(outcome) = m.home_outcome() else { continue };
        // When the base name is ambiguous, `matches_team` on the loose key
        // can't tell home from away for a fixture between two clubs that
        // share that base (e.g. Atletico-MG vs Atletico-PR: both sides'
        // loose key is "atletico"), so decide by identity instead.
        let is_home = if ambiguous {
            if m.home_identity == user_identity {
                true
            } else if m.away_identity == user_identity {
                false
            } else {
                continue;
            }
        } else {
            matches_team(&m.home_team_key, &t_key)
        };
        if venue == Venue::Home && !is_home {
            continue;
        }
        if venue == Venue::Away && is_home {
            continue;
        }
        stat.played += 1;
        let (gf, ga) = if is_home {
            (m.home_goal.unwrap(), m.away_goal.unwrap())
        } else {
            (m.away_goal.unwrap(), m.home_goal.unwrap())
        };
        stat.goals_for += gf as i64;
        stat.goals_against += ga as i64;
        let effective = if is_home { outcome } else { -outcome };
        match effective {
            1 => stat.wins += 1,
            -1 => stat.losses += 1,
            _ => stat.draws += 1,
        }
    }
    if stat.played == 0 {
        return format!("No matches found for {team} with the given filters.");
    }
    let venue_label = match venue {
        Venue::Home => " home",
        Venue::Away => " away",
        Venue::All => "",
    };
    let season_label = season.map(|s| format!(" ({s})")).unwrap_or_default();
    let display = if ambiguous {
        store.display_name_by_identity_for(&user_identity)
    } else {
        store.display_name_for(&t_key)
    };
    format!(
        "{}{} record{}:\n- Matches: {}\n- Wins: {}, Draws: {}, Losses: {}\n- Goals For: {}, Goals Against: {}\n- Win rate: {:.1}%",
        display,
        venue_label,
        season_label,
        stat.played,
        stat.wins,
        stat.draws,
        stat.losses,
        stat.goals_for,
        stat.goals_against,
        stat.win_rate()
    )
}

fn is_duplicate_brasileirao(m: &MatchRecord) -> bool {
    // Belt-and-suspenders: Store::load already resolves the 2012-2019
    // overlap between Brasileirao_Matches.csv and the historical file, but
    // keep this guard in case a future loader path skips that step.
    m.source_file == "novo_campeonato_brasileiro.csv" && m.season.is_none_or(|s| s >= 2012)
}

fn team_stats_by_competition(store: &Store, competition: &str, season: Option<i32>, venue: Venue) -> HashMap<String, TeamStat> {
    let mut table: HashMap<String, TeamStat> = HashMap::new();
    for m in &store.matches {
        if is_duplicate_brasileirao(m) {
            continue;
        }
        if !matches_competition(&m.competition, competition) {
            continue;
        }
        if let Some(s) = season {
            if m.season != Some(s) {
                continue;
            }
        }
        let Some(outcome) = m.home_outcome() else { continue };
        let (h, a) = (m.home_goal.unwrap(), m.away_goal.unwrap());

        if venue != Venue::Away {
            // Group by identity, not the loose key: a handful of base names
            // (e.g. "Atletico") are shared by distinct clubs in different
            // states, and merging them would silently corrupt the table.
            let entry = table.entry(m.home_identity.clone()).or_default();
            entry.played += 1;
            entry.goals_for += h as i64;
            entry.goals_against += a as i64;
            match outcome {
                1 => entry.wins += 1,
                -1 => entry.losses += 1,
                _ => entry.draws += 1,
            }
        }
        if venue != Venue::Home {
            let entry = table.entry(m.away_identity.clone()).or_default();
            entry.played += 1;
            entry.goals_for += a as i64;
            entry.goals_against += h as i64;
            match -outcome {
                1 => entry.wins += 1,
                -1 => entry.losses += 1,
                _ => entry.draws += 1,
            }
        }
    }
    table
}

/// "Who won the 2019 Brasileirao?" / "Which teams were relegated in 2020?"
pub fn standings(store: &Store, competition: &str, season: i32) -> String {
    let table = team_stats_by_competition(store, competition, Some(season), Venue::All);
    if table.is_empty() {
        return format!("No data found for '{competition}' in {season}.");
    }
    let mut rows: Vec<(&String, &TeamStat)> = table.iter().collect();
    // CBF tiebreak order: points, wins, goal difference, goals scored.
    rows.sort_by(|a, b| {
        b.1.points()
            .cmp(&a.1.points())
            .then(b.1.wins.cmp(&a.1.wins))
            .then(b.1.goal_diff().cmp(&a.1.goal_diff()))
            .then(b.1.goals_for.cmp(&a.1.goals_for))
    });
    let n = rows.len();
    let is_brasileirao = competition.to_lowercase().contains("brasileirao") || competition.to_lowercase().contains("brasileir");
    let mut out = format!("{competition} {season} standings (calculated from {n} teams' matches):\n");
    for (i, (key, stat)) in rows.iter().enumerate() {
        let pos = i + 1;
        let tag = if pos == 1 {
            " - Champion"
        } else if is_brasileirao && n >= 20 && pos > n - 4 {
            " - Relegation zone"
        } else {
            ""
        };
        out.push_str(&format!(
            "{pos}. {} - {} pts ({}W, {}D, {}L, GF {}, GA {}, GD {}){tag}\n",
            store.display_name_by_identity_for(key),
            stat.points(),
            stat.wins,
            stat.draws,
            stat.losses,
            stat.goals_for,
            stat.goals_against,
            stat.goal_diff()
        ));
    }
    out
}

/// "Which team scored the most goals in Serie A 2023?" / "Which team has
/// the best home/away record?"
pub fn team_leaderboard(store: &Store, competition: &str, season: Option<i32>, metric: &str, venue: &str, limit: usize) -> String {
    let venue_p = parse_venue(venue);
    let table = team_stats_by_competition(store, competition, season, venue_p);
    if table.is_empty() {
        return "No data found for the given filters.".to_string();
    }
    let limit = if limit == 0 { 10 } else { limit };
    let metric_key = metric.to_lowercase();
    let mut rows: Vec<(&String, &TeamStat)> = table.iter().filter(|(_, s)| s.played > 0).collect();
    let (label, value_fn): (&str, Box<dyn Fn(&TeamStat) -> f64>) = match metric_key.as_str() {
        "goals_against" | "goals_conceded" => ("Goals Against", Box::new(|s: &TeamStat| s.goals_against as f64)),
        "goal_diff" | "goal_difference" => ("Goal Difference", Box::new(|s: &TeamStat| s.goal_diff() as f64)),
        "wins" => ("Wins", Box::new(|s: &TeamStat| s.wins as f64)),
        "win_rate" => ("Win Rate %", Box::new(|s: &TeamStat| s.win_rate())),
        _ => ("Goals For", Box::new(|s: &TeamStat| s.goals_for as f64)),
    };
    let ascending = metric_key == "goals_against" || metric_key == "goals_conceded";
    rows.sort_by(|a, b| {
        let (va, vb) = (value_fn(a.1), value_fn(b.1));
        if ascending {
            va.partial_cmp(&vb).unwrap()
        } else {
            vb.partial_cmp(&va).unwrap()
        }
    });
    let venue_label = match venue_p {
        Venue::Home => " (home only)",
        Venue::Away => " (away only)",
        Venue::All => "",
    };
    let mut out = format!("Leaderboard by {label}{venue_label}:\n");
    for (i, (key, stat)) in rows.iter().take(limit).enumerate() {
        out.push_str(&format!(
            "{}. {} - {:.1} ({}P {}W {}D {}L, GF {} GA {})\n",
            i + 1,
            store.display_name_by_identity_for(key),
            value_fn(stat),
            stat.played,
            stat.wins,
            stat.draws,
            stat.losses,
            stat.goals_for,
            stat.goals_against
        ));
    }
    out
}

/// "Show me the biggest wins in the dataset"
pub fn biggest_wins(store: &Store, competition: &str, season: Option<i32>, limit: usize) -> String {
    let limit = if limit == 0 { 10 } else { limit };
    let mut results: Vec<&MatchRecord> = store
        .matches
        .iter()
        .filter(|m| !is_duplicate_brasileirao(m))
        .filter(|m| matches_competition(&m.competition, competition))
        .filter(|m| season.is_none_or(|s| m.season == Some(s)))
        .filter(|m| m.has_result())
        .collect();
    results.sort_by_key(|m| std::cmp::Reverse(m.goal_diff()));
    if results.is_empty() {
        return "No matches found for the given filters.".to_string();
    }
    let mut out = "Biggest victories (provided data):\n".to_string();
    for (i, m) in results.iter().take(limit).enumerate() {
        out.push_str(&format!("{}. {}\n", i + 1, fmt_match(store, m)));
    }
    out
}

/// "What's the average goals per match in the Brasileirao?"
pub fn average_stats(store: &Store, competition: &str, season: Option<i32>) -> String {
    let results: Vec<&MatchRecord> = store
        .matches
        .iter()
        .filter(|m| !is_duplicate_brasileirao(m))
        .filter(|m| matches_competition(&m.competition, competition))
        .filter(|m| season.is_none_or(|s| m.season == Some(s)))
        .filter(|m| m.has_result())
        .collect();
    if results.is_empty() {
        return "No matches found for the given filters.".to_string();
    }
    let n = results.len() as f64;
    let total_goals: i64 = results.iter().map(|m| m.home_goal.unwrap() as i64 + m.away_goal.unwrap() as i64).sum();
    let home_wins = results.iter().filter(|m| m.home_outcome() == Some(1)).count();
    let draws = results.iter().filter(|m| m.home_outcome() == Some(0)).count();
    let away_wins = results.iter().filter(|m| m.home_outcome() == Some(-1)).count();
    format!(
        "Average goals per match: {:.2}\nHome win rate: {:.1}%\nDraw rate: {:.1}%\nAway win rate: {:.1}%\n(based on {} matches)",
        total_goals as f64 / n,
        home_wins as f64 / n * 100.0,
        draws as f64 / n * 100.0,
        away_wins as f64 / n * 100.0,
        results.len()
    )
}

const DERBIES: &[(&str, &str, &str)] = &[
    ("flamengo", "fluminense", "Fla-Flu"),
    ("corinthians", "palmeiras", "Choque-Rei"),
    ("corinthians", "sao paulo", "Majestoso"),
    ("sao paulo", "palmeiras", "Choque-Rei Palestra"),
    ("santos", "sao paulo", "Clássico da Saudade"),
    ("internacional", "gremio", "Gre-Nal"),
    ("atletico", "cruzeiro", "Clássico Mineiro"),
    ("vasco", "flamengo", "Clássico dos Milhões"),
    ("botafogo", "flamengo", "Clássico da Rivalidade"),
    ("bahia", "vitoria", "Ba-Vi"),
    ("sport", "santa cruz", "Classico das Multidoes"),
    ("nautico", "santa cruz", "Clássico dos Clássicos"),
    ("gremio", "juventude", "Grenal da Serra"),
];

/// "Show me all derbies in 2023"
pub fn derby_matches(store: &Store, season: Option<i32>, rivalry: &str) -> String {
    let mut out = String::new();
    for (a, b, label) in DERBIES {
        if !rivalry.is_empty() && !label.to_lowercase().contains(&rivalry.to_lowercase()) {
            continue;
        }
        let filter = MatchFilter {
            team: Some(a),
            opponent: Some(b),
            competition: None,
            season,
            date_from: None,
            date_to: None,
        };
        let results = filter_matches(store, &filter);
        if results.is_empty() {
            continue;
        }
        out.push_str(&format!("{label} ({a} vs {b}):\n"));
        for m in &results {
            out.push_str("- ");
            out.push_str(&fmt_match(store, m));
            out.push('\n');
        }
        out.push('\n');
    }
    if out.is_empty() {
        "No derby matches found for the given filters.".to_string()
    } else {
        out
    }
}

/// "What competitions has Palmeiras played in?"
pub fn team_competitions(store: &Store, team: &str) -> String {
    if team.is_empty() {
        return "A team name is required.".to_string();
    }
    let t_key = normalize_team_name(team);
    let mut per_competition: HashMap<String, (u32, Option<i32>, Option<i32>)> = HashMap::new();
    for m in &store.matches {
        if !matches_team(&m.home_team_key, &t_key) && !matches_team(&m.away_team_key, &t_key) {
            continue;
        }
        let entry = per_competition.entry(m.competition.clone()).or_insert((0, None, None));
        entry.0 += 1;
        if let Some(s) = m.season {
            entry.1 = Some(entry.1.map_or(s, |min| min.min(s)));
            entry.2 = Some(entry.2.map_or(s, |max| max.max(s)));
        }
    }
    if per_competition.is_empty() {
        return format!("No matches found for '{team}'.");
    }
    let mut rows: Vec<_> = per_competition.into_iter().collect();
    rows.sort_by_key(|r| std::cmp::Reverse(r.1 .0));
    let mut out = format!("Competitions played by {}:\n", store.display_name_for(&t_key));
    for (comp, (count, min, max)) in rows {
        let years = match (min, max) {
            (Some(a), Some(b)) if a == b => format!(" ({a})"),
            (Some(a), Some(b)) => format!(" ({a}-{b})"),
            _ => String::new(),
        };
        out.push_str(&format!("- {comp}{years}: {count} matches\n"));
    }
    out
}

/// "Find all Brazilian players in the dataset" / "Who are the highest-rated
/// players at Flamengo?" / "Show me all forwards from Sao Paulo FC"
pub fn search_players(store: &Store, name: &str, nationality: &str, club: &str, position: &str, min_overall: Option<i32>, limit: usize) -> String {
    let limit = if limit == 0 { 25 } else { limit };
    let name_l = name.to_lowercase();
    let nat_l = nationality.to_lowercase();
    let pos_l = position.to_lowercase();
    let club_key = if club.is_empty() { None } else { Some(normalize_team_name(club)) };
    let mut results: Vec<_> = store
        .players
        .iter()
        .filter(|p| name.is_empty() || p.name.to_lowercase().contains(&name_l))
        .filter(|p| nationality.is_empty() || p.nationality.to_lowercase() == nat_l)
        .filter(|p| position.is_empty() || p.position.to_lowercase() == pos_l)
        .filter(|p| club_key.as_deref().is_none_or(|k| matches_team(&p.club_key, k)))
        .filter(|p| min_overall.is_none_or(|min| p.overall.is_some_and(|o| o >= min)))
        .collect();
    if results.is_empty() {
        return "No players found for the given criteria.".to_string();
    }
    let total = results.len();
    results.sort_by_key(|p| std::cmp::Reverse(p.overall.unwrap_or(0)));
    let mut out = format!("Found {total} player(s):\n");
    for (i, p) in results.iter().take(limit).enumerate() {
        out.push_str(&format!(
            "{}. {} (ID {}) - Overall: {}, Potential: {}, Age: {}, Position: {}, Club: {}, Nationality: {}\n",
            i + 1,
            p.name,
            p.id,
            p.overall.map(|o| o.to_string()).unwrap_or_else(|| "?".to_string()),
            p.potential.map(|o| o.to_string()).unwrap_or_else(|| "?".to_string()),
            p.age.map(|o| o.to_string()).unwrap_or_else(|| "?".to_string()),
            if p.position.is_empty() { "?" } else { &p.position },
            if p.club.is_empty() { "Free Agent" } else { &p.club },
            p.nationality
        ));
    }
    if total > limit {
        out.push_str(&format!("... ({} more players in dataset)\n", total - limit));
    }
    out
}

/// "Brazilian players at Brazilian clubs" breakdown, cross-referencing the
/// FIFA dataset's `Club` field against team names known from the match
/// datasets (so `Palmeiras`/`Flamengo`/etc. are resolved dynamically, not
/// hardcoded).
pub fn brazilian_club_squads(store: &Store, limit_clubs: usize) -> String {
    let limit_clubs = if limit_clubs == 0 { 15 } else { limit_clubs };
    let mut per_club: HashMap<String, (u32, i64)> = HashMap::new();
    for p in &store.players {
        if p.nationality != "Brazil" {
            continue;
        }
        if !store.is_brazilian_club(&p.club_key) {
            continue;
        }
        let entry = per_club.entry(p.club_key.clone()).or_insert((0, 0));
        entry.0 += 1;
        entry.1 += p.overall.unwrap_or(0) as i64;
    }
    if per_club.is_empty() {
        return "No matching players found.".to_string();
    }
    let mut rows: Vec<_> = per_club.into_iter().collect();
    rows.sort_by_key(|r| std::cmp::Reverse(r.1 .0));
    let mut out = "Brazilian players at Brazilian clubs (FIFA dataset):\n".to_string();
    for (key, (count, sum)) in rows.iter().take(limit_clubs) {
        out.push_str(&format!(
            "- {}: {} players (avg rating: {:.0})\n",
            store.display_name_for(key),
            count,
            *sum as f64 / *count as f64
        ));
    }
    out
}

/// "All 6 CSV files are loadable and queryable" sanity/coverage check.
pub fn list_datasets(store: &Store) -> String {
    let mut out = String::from("Loaded datasets:\n");
    for d in &store.dataset_info {
        out.push_str(&format!("- {}: {} rows\n", d.file, d.rows));
    }
    out.push_str(&format!(
        "\nTotal matches indexed (post-dedup): {}\nTotal players indexed: {}\n",
        store.matches.len(),
        store.players.len()
    ));
    out
}
