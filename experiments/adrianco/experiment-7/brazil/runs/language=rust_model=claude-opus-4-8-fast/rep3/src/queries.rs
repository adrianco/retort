// =============================================================================
// queries — the analytical query layer
// -----------------------------------------------------------------------------
// Context:
//   These functions implement the five capability categories from TASK.md:
//     1. Match queries        -> `search_matches`
//     2. Team queries         -> `team_record`, `head_to_head`
//     3. Player queries       -> `search_players`
//     4. Competition queries  -> `standings`
//     5. Statistical analysis -> `competition_summary`
//   plus discovery helpers (`list_competitions`, `list_seasons`).
//
//   Each public function is pure over `&DataStore` and returns a human-readable
//   String (used verbatim as MCP tool output). The structured helpers
//   (`filter_matches`, `Record`, `compute_record`) are reused by the formatted
//   functions and asserted on directly by the test-suite.
// =============================================================================

use crate::data::{Match, Player};
use crate::normalize::{key_matches, team_key};
use crate::store::DataStore;
use std::collections::HashMap;

/// Which venue to restrict a team query to.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum Venue {
    #[default]
    All,
    Home,
    Away,
}

impl Venue {
    pub fn parse(s: &str) -> Venue {
        match s.trim().to_lowercase().as_str() {
            "home" => Venue::Home,
            "away" => Venue::Away,
            _ => Venue::All,
        }
    }
}

/// Filter criteria for match search. Empty/None fields are ignored.
#[derive(Debug, Default, Clone)]
pub struct MatchFilter {
    pub team: Option<String>,
    pub opponent: Option<String>,
    pub competition: Option<String>,
    pub season: Option<i64>,
    pub start_key: Option<i64>, // inclusive date sort-key bound
    pub end_key: Option<i64>,
    pub venue: Venue,
}

impl MatchFilter {
    pub fn new() -> Self {
        MatchFilter {
            venue: Venue::All,
            ..Default::default()
        }
    }
}

/// Aggregated win/draw/loss + goals record.
#[derive(Debug, Default, Clone, Copy, PartialEq, Eq)]
pub struct Record {
    pub played: i64,
    pub wins: i64,
    pub draws: i64,
    pub losses: i64,
    pub goals_for: i64,
    pub goals_against: i64,
}

impl Record {
    pub fn points(&self) -> i64 {
        self.wins * 3 + self.draws
    }
    pub fn goal_diff(&self) -> i64 {
        self.goals_for - self.goals_against
    }
    pub fn win_rate(&self) -> f64 {
        if self.played == 0 {
            0.0
        } else {
            self.wins as f64 / self.played as f64 * 100.0
        }
    }
    /// Fold a single match (already known to involve `team_key`) into the record.
    fn add_match(&mut self, m: &Match, team_key: &str) {
        let (hg, ag) = match (m.home_goal, m.away_goal) {
            (Some(h), Some(a)) => (h, a),
            _ => return,
        };
        let (gf, ga) = if m.home_key == team_key {
            (hg, ag)
        } else if m.away_key == team_key {
            (ag, hg)
        } else {
            return;
        };
        self.played += 1;
        self.goals_for += gf;
        self.goals_against += ga;
        match gf.cmp(&ga) {
            std::cmp::Ordering::Greater => self.wins += 1,
            std::cmp::Ordering::Equal => self.draws += 1,
            std::cmp::Ordering::Less => self.losses += 1,
        }
    }
}

// ----------------------------------------------------------------------------
// Structured filtering (shared core)
// ----------------------------------------------------------------------------

/// Resolve a free-text competition argument to a canonical competition name.
/// Returns `Some(exact name)` for recognised competitions (so filtering can use
/// exact equality and not, say, let "Brasileirão" also match Série B/C), or
/// `None` for unknown inputs (callers then fall back to substring matching).
pub fn resolve_competition(input: &str) -> Option<&'static str> {
    let k = team_key(input);
    if k.contains("libertadores") {
        Some("Copa Libertadores")
    } else if k.contains("copa do brasil") || k == "cup" || k.contains("brasil cup") {
        Some("Copa do Brasil")
    } else if k.contains("serie b") {
        Some("Brasileirão Série B")
    } else if k.contains("serie c") {
        Some("Brasileirão Série C")
    } else if k.contains("serie a")
        || k.contains("brasileirao")
        || k.contains("brasileiro")
    {
        Some("Brasileirão Série A")
    } else {
        None
    }
}

/// Return references to all matches satisfying `filter`, sorted chronologically.
pub fn filter_matches<'a>(store: &'a DataStore, filter: &MatchFilter) -> Vec<&'a Match> {
    let team_k = filter.team.as_deref().map(team_key);
    let opp_k = filter.opponent.as_deref().map(team_key);
    // Prefer an exact canonical competition; fall back to substring matching for
    // unrecognised competition labels.
    let comp_exact = filter.competition.as_deref().and_then(resolve_competition);
    let comp_k = filter
        .competition
        .as_deref()
        .filter(|_| comp_exact.is_none())
        .map(team_key);

    let mut out: Vec<&Match> = store
        .matches
        .iter()
        .filter(|m| {
            if let Some(season) = filter.season {
                if m.season != season {
                    return false;
                }
            }
            if let Some(exact) = comp_exact {
                if m.competition != exact {
                    return false;
                }
            } else if let Some(ck) = &comp_k {
                // Unrecognised competition label: fall back to substring match.
                if !key_matches(&team_key(&m.competition), ck) {
                    return false;
                }
            }
            if let Some(sk) = filter.start_key {
                if m.date_key != 0 && m.date_key < sk {
                    return false;
                }
            }
            if let Some(ek) = filter.end_key {
                if m.date_key != 0 && m.date_key > ek {
                    return false;
                }
            }
            // Team / venue handling.
            if let Some(tk) = &team_k {
                let home = key_matches(&m.home_key, tk);
                let away = key_matches(&m.away_key, tk);
                let venue_ok = match filter.venue {
                    Venue::All => home || away,
                    Venue::Home => home,
                    Venue::Away => away,
                };
                if !venue_ok {
                    return false;
                }
            }
            if let Some(ok) = &opp_k {
                // Opponent must be the other side relative to `team`.
                if let Some(tk) = &team_k {
                    let team_home = key_matches(&m.home_key, tk);
                    let opp_present = if team_home {
                        key_matches(&m.away_key, ok)
                    } else {
                        key_matches(&m.home_key, ok)
                    };
                    if !opp_present {
                        return false;
                    }
                } else if !(key_matches(&m.home_key, ok) || key_matches(&m.away_key, ok)) {
                    return false;
                }
            }
            true
        })
        .collect();

    out.sort_by(|a, b| a.date_key.cmp(&b.date_key).then(a.date_iso.cmp(&b.date_iso)));
    out
}

/// Compute a team's record over a slice of matches.
pub fn compute_record(matches: &[&Match], team_k: &str, venue: Venue) -> Record {
    let mut rec = Record::default();
    for m in matches {
        let is_home = m.home_key == team_k;
        let is_away = m.away_key == team_k;
        let counts = match venue {
            Venue::All => is_home || is_away,
            Venue::Home => is_home,
            Venue::Away => is_away,
        };
        if counts {
            rec.add_match(m, team_k);
        }
    }
    rec
}

// ----------------------------------------------------------------------------
// Formatted query functions (MCP tool outputs)
// ----------------------------------------------------------------------------

fn date_label(m: &Match) -> String {
    if m.date_iso.is_empty() {
        format!("{}", m.season)
    } else {
        m.date_iso.clone()
    }
}

fn comp_label(m: &Match) -> String {
    match &m.stage {
        Some(s) => format!("{} {}", m.competition, s),
        None => m.competition.clone(),
    }
}

/// Capability 1 — search matches by team(s), competition, season and date range.
pub fn search_matches(store: &DataStore, filter: &MatchFilter, limit: usize) -> String {
    let matches = filter_matches(store, filter);
    if matches.is_empty() {
        return "No matches found for the given criteria.".to_string();
    }

    let mut out = String::new();
    let header = describe_filter(filter);
    out.push_str(&format!("{} — {} match(es) found.\n\n", header, matches.len()));

    // Newest first for display.
    let mut display: Vec<&&Match> = matches.iter().collect();
    display.sort_by(|a, b| b.date_key.cmp(&a.date_key));
    for m in display.iter().take(limit) {
        out.push_str(&format!(
            "- {}: {} ({})\n",
            date_label(m),
            m.scoreline(),
            comp_label(m)
        ));
    }
    if matches.len() > limit {
        out.push_str(&format!("- ... ({} more not shown)\n", matches.len() - limit));
    }

    // If two teams are specified, append the head-to-head summary.
    if let (Some(t), Some(o)) = (&filter.team, &filter.opponent) {
        out.push('\n');
        out.push_str(&h2h_summary(&matches, &team_key(t), t, o));
    }
    out
}

fn describe_filter(filter: &MatchFilter) -> String {
    let mut parts: Vec<String> = Vec::new();
    match (&filter.team, &filter.opponent) {
        (Some(t), Some(o)) => parts.push(format!("{} vs {}", t, o)),
        (Some(t), None) => {
            let v = match filter.venue {
                Venue::Home => " (home)",
                Venue::Away => " (away)",
                Venue::All => "",
            };
            parts.push(format!("{}{}", t, v));
        }
        (None, Some(o)) => parts.push(o.clone()),
        (None, None) => parts.push("Matches".to_string()),
    }
    if let Some(c) = &filter.competition {
        parts.push(c.clone());
    }
    if let Some(s) = filter.season {
        parts.push(s.to_string());
    }
    parts.join(", ")
}

/// Head-to-head record text relative to `team_k` (the first/anchor team).
fn h2h_summary(matches: &[&Match], team_k: &str, team_name: &str, opp_name: &str) -> String {
    let mut w = 0;
    let mut d = 0;
    let mut l = 0;
    let mut gf = 0;
    let mut ga = 0;
    for m in matches {
        if !m.has_score() {
            continue;
        }
        match m.result_for(team_k) {
            1 => w += 1,
            0 => d += 1,
            -1 => l += 1,
            _ => {}
        }
        if m.home_key == team_k {
            gf += m.home_goal.unwrap_or(0);
            ga += m.away_goal.unwrap_or(0);
        } else {
            gf += m.away_goal.unwrap_or(0);
            ga += m.home_goal.unwrap_or(0);
        }
    }
    format!(
        "Head-to-head in dataset: {} {} wins, {} {} wins, {} draws (goals {}-{}).",
        team_name, w, opp_name, l, d, gf, ga
    )
}

/// Capability 2 — head-to-head between two teams.
pub fn head_to_head(
    store: &DataStore,
    team1: &str,
    team2: &str,
    competition: Option<&str>,
    season: Option<i64>,
    limit: usize,
) -> String {
    let mut filter = MatchFilter::new();
    filter.team = Some(team1.to_string());
    filter.opponent = Some(team2.to_string());
    filter.competition = competition.map(|s| s.to_string());
    filter.season = season;
    search_matches(store, &filter, limit)
}

/// Capability 2 — a team's record, optionally scoped by season/competition/venue.
pub fn team_record(
    store: &DataStore,
    team: &str,
    season: Option<i64>,
    competition: Option<&str>,
    venue: Venue,
) -> String {
    let mut filter = MatchFilter::new();
    filter.team = Some(team.to_string());
    filter.season = season;
    filter.competition = competition.map(|s| s.to_string());
    filter.venue = venue;

    let matches = filter_matches(store, &filter);
    let tk = team_key(team);
    let rec = compute_record(&matches, &tk, venue);

    if rec.played == 0 {
        return format!("No completed matches found for {} with those filters.", team);
    }

    let scope = {
        let mut p = Vec::new();
        if let Some(s) = season {
            p.push(s.to_string());
        }
        if let Some(c) = competition {
            p.push(c.to_string());
        }
        match venue {
            Venue::Home => p.push("home".to_string()),
            Venue::Away => p.push("away".to_string()),
            Venue::All => {}
        }
        if p.is_empty() {
            "all data".to_string()
        } else {
            p.join(", ")
        }
    };

    format!(
        "{} record ({}):\n\
         - Matches: {}\n\
         - Wins: {}, Draws: {}, Losses: {}\n\
         - Goals For: {}, Goals Against: {} (GD {:+})\n\
         - Points: {}\n\
         - Win rate: {:.1}%",
        team,
        scope,
        rec.played,
        rec.wins,
        rec.draws,
        rec.losses,
        rec.goals_for,
        rec.goals_against,
        rec.goal_diff(),
        rec.points(),
        rec.win_rate(),
    )
}

// ----------------------------------------------------------------------------
// Player queries (capability 3)
// ----------------------------------------------------------------------------

#[derive(Debug, Default, Clone)]
pub struct PlayerFilter {
    pub name: Option<String>,
    pub nationality: Option<String>,
    pub club: Option<String>,
    pub position: Option<String>,
    pub min_overall: Option<i64>,
}

#[derive(Debug, Clone, Copy)]
pub enum PlayerSort {
    Overall,
    Potential,
    Age,
    Name,
}

impl PlayerSort {
    pub fn parse(s: &str) -> PlayerSort {
        match s.trim().to_lowercase().as_str() {
            "potential" => PlayerSort::Potential,
            "age" => PlayerSort::Age,
            "name" => PlayerSort::Name,
            _ => PlayerSort::Overall,
        }
    }
}

/// Structured player filtering, used by both the formatter and tests.
pub fn filter_players<'a>(store: &'a DataStore, f: &PlayerFilter) -> Vec<&'a Player> {
    let name_l = f.name.as_deref().map(|s| s.to_lowercase());
    let nat_l = f.nationality.as_deref().map(|s| s.to_lowercase());
    let club_k = f.club.as_deref().map(team_key);
    let pos_l = f.position.as_deref().map(|s| s.to_lowercase());

    store
        .players
        .iter()
        .filter(|p| {
            if let Some(n) = &name_l {
                if !p.name.to_lowercase().contains(n) {
                    return false;
                }
            }
            if let Some(nat) = &nat_l {
                if !p.nationality.to_lowercase().contains(nat) {
                    return false;
                }
            }
            if let Some(ck) = &club_k {
                if !key_matches(&p.club_key, ck) {
                    return false;
                }
            }
            if let Some(pos) = &pos_l {
                if p.position.to_lowercase() != *pos {
                    return false;
                }
            }
            if let Some(mo) = f.min_overall {
                if p.overall.unwrap_or(0) < mo {
                    return false;
                }
            }
            true
        })
        .collect()
}

/// Capability 3 — search players, formatted and sorted.
pub fn search_players(
    store: &DataStore,
    f: &PlayerFilter,
    sort: PlayerSort,
    limit: usize,
) -> String {
    let mut players = filter_players(store, f);
    if players.is_empty() {
        return "No players found for the given criteria.".to_string();
    }
    match sort {
        PlayerSort::Overall => players.sort_by(|a, b| b.overall.cmp(&a.overall)),
        PlayerSort::Potential => players.sort_by(|a, b| b.potential.cmp(&a.potential)),
        PlayerSort::Age => players.sort_by(|a, b| a.age.cmp(&b.age)),
        PlayerSort::Name => players.sort_by(|a, b| a.name.cmp(&b.name)),
    }

    let total = players.len();
    let mut out = format!("{} player(s) found:\n\n", total);
    for (i, p) in players.iter().take(limit).enumerate() {
        out.push_str(&format!(
            "{}. {} — Overall: {}, Potential: {}, Position: {}, Age: {}, Nationality: {}, Club: {}\n",
            i + 1,
            p.name,
            p.overall.map(|v| v.to_string()).unwrap_or_else(|| "?".into()),
            p.potential.map(|v| v.to_string()).unwrap_or_else(|| "?".into()),
            if p.position.is_empty() { "?" } else { &p.position },
            p.age.map(|v| v.to_string()).unwrap_or_else(|| "?".into()),
            p.nationality,
            if p.club.is_empty() { "(free agent)" } else { &p.club },
        ));
    }
    if total > limit {
        out.push_str(&format!("... ({} more not shown)\n", total - limit));
    }
    out
}

// ----------------------------------------------------------------------------
// Competition standings (capability 4)
// ----------------------------------------------------------------------------

/// Capability 4 — compute a league table from match results.
pub fn standings(store: &DataStore, competition: &str, season: i64) -> String {
    let mut filter = MatchFilter::new();
    filter.competition = Some(competition.to_string());
    filter.season = Some(season);
    let matches = filter_matches(store, &filter);
    if matches.is_empty() {
        return format!("No matches found for {} in {}.", competition, season);
    }

    // Accumulate a record per team (display name kept for output).
    let mut table: HashMap<String, (String, Record)> = HashMap::new();
    for m in &matches {
        if !m.has_score() {
            continue;
        }
        for (key, name) in [(&m.home_key, &m.home), (&m.away_key, &m.away)] {
            let entry = table
                .entry(key.clone())
                .or_insert_with(|| (name.clone(), Record::default()));
            entry.1.add_match(m, key);
        }
    }
    if table.is_empty() {
        return format!(
            "Matches for {} {} have no recorded scores to build a table.",
            competition, season
        );
    }

    let mut rows: Vec<(String, Record)> = table.into_values().collect();
    rows.sort_by(|a, b| {
        b.1.points()
            .cmp(&a.1.points())
            .then(b.1.goal_diff().cmp(&a.1.goal_diff()))
            .then(b.1.goals_for.cmp(&a.1.goals_for))
            .then(b.1.wins.cmp(&a.1.wins))
            .then(a.0.cmp(&b.0))
    });

    let comp_display = matches[0].competition.clone();
    let mut out = format!(
        "{} {} — Final Standings (calculated from {} matches):\n\n",
        comp_display, season, matches.len()
    );
    out.push_str("Pos  Team                          Pld   W   D   L   GF   GA   GD  Pts\n");
    for (i, (name, rec)) in rows.iter().enumerate() {
        out.push_str(&format!(
            "{:>3}  {:<28}  {:>3} {:>3} {:>3} {:>3} {:>4} {:>4} {:>4} {:>4}\n",
            i + 1,
            truncate(name, 28),
            rec.played,
            rec.wins,
            rec.draws,
            rec.losses,
            rec.goals_for,
            rec.goals_against,
            rec.goal_diff(),
            rec.points(),
        ));
    }
    if let Some((champ, _)) = rows.first() {
        out.push_str(&format!("\nChampion (by points): {}", champ));
    }
    out
}

fn truncate(s: &str, n: usize) -> String {
    if s.chars().count() <= n {
        s.to_string()
    } else {
        let mut t: String = s.chars().take(n.saturating_sub(1)).collect();
        t.push('…');
        t
    }
}

// ----------------------------------------------------------------------------
// Statistical analysis (capability 5)
// ----------------------------------------------------------------------------

/// Capability 5 — aggregate statistics: avg goals/match, home-win rate, biggest
/// wins, scoped by optional competition and/or season.
pub fn competition_summary(
    store: &DataStore,
    competition: Option<&str>,
    season: Option<i64>,
    biggest_n: usize,
) -> String {
    let mut filter = MatchFilter::new();
    filter.competition = competition.map(|s| s.to_string());
    filter.season = season;
    let matches = filter_matches(store, &filter);

    let scored: Vec<&&Match> = matches.iter().filter(|m| m.has_score()).collect();
    if scored.is_empty() {
        return "No matches with recorded scores found for the given criteria.".to_string();
    }

    let total_goals: i64 = scored
        .iter()
        .map(|m| m.home_goal.unwrap_or(0) + m.away_goal.unwrap_or(0))
        .sum();
    let n = scored.len() as f64;
    let home_wins = scored.iter().filter(|m| m.result_for(&m.home_key) == 1).count();
    let away_wins = scored.iter().filter(|m| m.result_for(&m.away_key) == 1).count();
    let draws = scored.len() - home_wins - away_wins;

    let scope = describe_scope(competition, season);
    let mut out = format!("Statistics ({}):\n", scope);
    out.push_str(&format!("- Matches with scores: {}\n", scored.len()));
    out.push_str(&format!("- Total goals: {}\n", total_goals));
    out.push_str(&format!("- Average goals per match: {:.2}\n", total_goals as f64 / n));
    out.push_str(&format!(
        "- Home win rate: {:.1}% ({} wins)\n",
        home_wins as f64 / n * 100.0,
        home_wins
    ));
    out.push_str(&format!(
        "- Away win rate: {:.1}% ({} wins)\n",
        away_wins as f64 / n * 100.0,
        away_wins
    ));
    out.push_str(&format!(
        "- Draw rate: {:.1}% ({} draws)\n",
        draws as f64 / n * 100.0,
        draws
    ));

    // Biggest victories by goal margin.
    let mut by_margin: Vec<&&Match> = scored.clone();
    by_margin.sort_by(|a, b| {
        let ma = (a.home_goal.unwrap_or(0) - a.away_goal.unwrap_or(0)).abs();
        let mb = (b.home_goal.unwrap_or(0) - b.away_goal.unwrap_or(0)).abs();
        mb.cmp(&ma).then(b.date_key.cmp(&a.date_key))
    });
    out.push_str(&format!("\nBiggest victories (top {}):\n", biggest_n));
    for (i, m) in by_margin.iter().take(biggest_n).enumerate() {
        out.push_str(&format!(
            "{}. {}: {} ({})\n",
            i + 1,
            date_label(m),
            m.scoreline(),
            comp_label(m)
        ));
    }
    out
}

fn describe_scope(competition: Option<&str>, season: Option<i64>) -> String {
    let mut p = Vec::new();
    if let Some(c) = competition {
        p.push(c.to_string());
    }
    if let Some(s) = season {
        p.push(s.to_string());
    }
    if p.is_empty() {
        "all competitions and seasons".to_string()
    } else {
        p.join(", ")
    }
}

// ----------------------------------------------------------------------------
// Discovery helpers
// ----------------------------------------------------------------------------

/// List the distinct competitions present in the data, with match counts.
pub fn list_competitions(store: &DataStore) -> String {
    let mut counts: HashMap<&str, usize> = HashMap::new();
    for m in &store.matches {
        *counts.entry(m.competition.as_str()).or_insert(0) += 1;
    }
    let mut rows: Vec<(&str, usize)> = counts.into_iter().collect();
    rows.sort_by(|a, b| b.1.cmp(&a.1));
    let mut out = String::from("Competitions in dataset:\n");
    for (comp, c) in rows {
        out.push_str(&format!("- {} ({} matches)\n", comp, c));
    }
    out.push_str(&format!(
        "\nTotals: {} matches, {} players.",
        store.match_count(),
        store.player_count()
    ));
    out
}

/// List the seasons available, optionally for a single competition.
pub fn list_seasons(store: &DataStore, competition: Option<&str>) -> String {
    let comp_exact = competition.and_then(resolve_competition);
    let comp_k = competition
        .filter(|_| comp_exact.is_none())
        .map(team_key);
    let mut seasons: Vec<i64> = store
        .matches
        .iter()
        .filter(|m| match (comp_exact, &comp_k) {
            (Some(exact), _) => m.competition == exact,
            (None, Some(ck)) => key_matches(&team_key(&m.competition), ck),
            (None, None) => true,
        })
        .map(|m| m.season)
        .filter(|s| *s > 0)
        .collect();
    seasons.sort_unstable();
    seasons.dedup();
    if seasons.is_empty() {
        return "No seasons found.".to_string();
    }
    let label = competition.unwrap_or("all competitions");
    format!(
        "Seasons for {}: {}",
        label,
        seasons
            .iter()
            .map(|s| s.to_string())
            .collect::<Vec<_>>()
            .join(", ")
    )
}
