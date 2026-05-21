//! Aggregated statistical analysis.
//!
//! Context: implements requirement category 5 ("Statistical Analysis") from
//! `TASK.md` — goals-per-match averages, home/away win rates, biggest
//! victories and team performance rankings. Every figure is computed live
//! from the loaded match data.

use std::collections::HashMap;

use crate::data::Database;
use crate::model::Match;
use crate::teams::{TeamRecord, Venue};

/// True when a match passes the optional competition/season scope. The
/// `competition`, when set, must be an exact canonical competition label.
fn in_scope(m: &Match, competition: Option<&str>, season: Option<i32>) -> bool {
    if let Some(s) = season {
        if m.season != s {
            return false;
        }
    }
    if let Some(c) = competition {
        if m.competition != c {
            return false;
        }
    }
    true
}

/// Aggregate match statistics over an optional competition/season scope.
#[derive(Debug, Default, Clone)]
pub struct Aggregate {
    pub total_matches: usize,
    pub total_goals: i32,
    pub home_wins: u32,
    pub away_wins: u32,
    pub draws: u32,
}

impl Aggregate {
    /// Mean goals scored per match.
    pub fn avg_goals(&self) -> f64 {
        if self.total_matches == 0 {
            0.0
        } else {
            self.total_goals as f64 / self.total_matches as f64
        }
    }

    fn rate(&self, count: u32) -> f64 {
        if self.total_matches == 0 {
            0.0
        } else {
            count as f64 / self.total_matches as f64 * 100.0
        }
    }

    /// Percentage of matches won by the home side.
    pub fn home_win_rate(&self) -> f64 {
        self.rate(self.home_wins)
    }

    /// Percentage of matches won by the away side.
    pub fn away_win_rate(&self) -> f64 {
        self.rate(self.away_wins)
    }

    /// Percentage of drawn matches.
    pub fn draw_rate(&self) -> f64 {
        self.rate(self.draws)
    }
}

/// Compute [`Aggregate`] statistics over the given scope.
pub fn aggregate(db: &Database, competition: Option<&str>, season: Option<i32>) -> Aggregate {
    let mut a = Aggregate::default();
    for m in &db.matches {
        if !in_scope(m, competition, season) {
            continue;
        }
        a.total_matches += 1;
        a.total_goals += m.total_goals();
        match m.home_goal.cmp(&m.away_goal) {
            std::cmp::Ordering::Greater => a.home_wins += 1,
            std::cmp::Ordering::Equal => a.draws += 1,
            std::cmp::Ordering::Less => a.away_wins += 1,
        }
    }
    a
}

/// Render an [`Aggregate`] as a human-readable block.
pub fn format_aggregate(a: &Aggregate, competition: Option<&str>, season: Option<i32>) -> String {
    let scope = describe_scope(competition, season);
    format!(
        "Match statistics {scope}:\n\
         - Matches analysed: {}\n\
         - Total goals: {}\n\
         - Average goals per match: {:.2}\n\
         - Home wins: {} ({:.1}%)\n\
         - Away wins: {} ({:.1}%)\n\
         - Draws: {} ({:.1}%)",
        a.total_matches,
        a.total_goals,
        a.avg_goals(),
        a.home_wins,
        a.home_win_rate(),
        a.away_wins,
        a.away_win_rate(),
        a.draws,
        a.draw_rate(),
    )
}

fn describe_scope(competition: Option<&str>, season: Option<i32>) -> String {
    match (competition, season) {
        (Some(c), Some(s)) => format!("for {c} {s}"),
        (Some(c), None) => format!("for {c} (all seasons)"),
        (None, Some(s)) => format!("for the {s} season (all competitions)"),
        (None, None) => "across all competitions and seasons".to_string(),
    }
}

/// Return the matches with the largest goal margin, biggest first.
pub fn biggest_wins<'a>(
    db: &'a Database,
    competition: Option<&str>,
    season: Option<i32>,
    limit: usize,
) -> Vec<&'a Match> {
    let mut wins: Vec<&Match> = db
        .matches
        .iter()
        .filter(|m| in_scope(m, competition, season) && m.margin() > 0)
        .collect();
    wins.sort_by(|a, b| {
        b.margin()
            .cmp(&a.margin())
            .then(b.total_goals().cmp(&a.total_goals()))
            .then(b.date.cmp(&a.date))
    });
    wins.truncate(limit);
    wins
}

/// Rank teams by win rate over a scope, optionally restricted to home or away
/// fixtures. Teams with fewer than `min_played` matches are excluded.
pub fn team_rankings(
    db: &Database,
    competition: Option<&str>,
    season: Option<i32>,
    venue: Venue,
    min_played: u32,
) -> Vec<(String, TeamRecord)> {
    let mut table: HashMap<String, (String, TeamRecord)> = HashMap::new();
    for m in &db.matches {
        if !in_scope(m, competition, season) {
            continue;
        }
        let sides: &[(bool, &String, &String)] = &[
            (true, &m.home_key, &m.home_team),
            (false, &m.away_key, &m.away_team),
        ];
        for &(is_home, key, display) in sides {
            let include = match venue {
                Venue::All => true,
                Venue::Home => is_home,
                Venue::Away => !is_home,
            };
            if !include {
                continue;
            }
            let entry = table
                .entry(key.clone())
                .or_insert_with(|| (display.clone(), TeamRecord::default()));
            if let Some(outcome) = m.outcome_for(key) {
                let (gf, ga) = if is_home {
                    (m.home_goal, m.away_goal)
                } else {
                    (m.away_goal, m.home_goal)
                };
                entry.1.record_outcome(outcome, gf, ga);
            }
        }
    }
    let mut ranked: Vec<(String, TeamRecord)> = table
        .into_values()
        .filter(|(_, r)| r.played >= min_played)
        .collect();
    ranked.sort_by(|a, b| {
        b.1
            .win_rate()
            .partial_cmp(&a.1.win_rate())
            .unwrap_or(std::cmp::Ordering::Equal)
            .then(b.1.points().cmp(&a.1.points()))
            .then(b.1.goal_diff().cmp(&a.1.goal_diff()))
    });
    ranked
}

/// Render the biggest-victories list.
pub fn format_biggest_wins(matches: &[&Match]) -> String {
    if matches.is_empty() {
        return "No matches found for the given criteria.".to_string();
    }
    let mut out = String::from("Biggest victories:\n");
    for (i, m) in matches.iter().enumerate() {
        out.push_str(&format!("{}. {}\n", i + 1, m.summary()));
    }
    out
}

/// Render a team performance ranking.
pub fn format_rankings(
    ranked: &[(String, TeamRecord)],
    venue: Venue,
    limit: usize,
) -> String {
    if ranked.is_empty() {
        return "No teams matched the given criteria.".to_string();
    }
    let venue_label = match venue {
        Venue::All => "overall",
        Venue::Home => "home",
        Venue::Away => "away",
    };
    let mut out = format!("Team rankings by {venue_label} win rate:\n");
    for (i, (team, r)) in ranked.iter().take(limit).enumerate() {
        out.push_str(&format!(
            "{:>2}. {} - {:.1}% ({}W {}D {}L, {} pts, GD {:+})\n",
            i + 1,
            team,
            r.win_rate(),
            r.won,
            r.drawn,
            r.lost,
            r.points(),
            r.goal_diff(),
        ));
    }
    out
}
