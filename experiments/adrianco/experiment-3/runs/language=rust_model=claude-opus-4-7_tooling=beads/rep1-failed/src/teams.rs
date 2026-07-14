//! Team statistics and head-to-head records.
//!
//! Context: implements requirement category 2 ("Team Queries") and the
//! head-to-head part of category 5 ("Statistical Analysis") from `TASK.md`.
//! Win/draw/loss records, goals for/against and win rates are computed live
//! from match results; head-to-head tallies are derived from every fixture in
//! which both clubs appear.

use crate::data::Database;
use crate::model::{Match, Outcome};

/// Which fixtures count towards a team record.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Venue {
    All,
    Home,
    Away,
}

impl Venue {
    /// Parse a venue from a free-text argument; defaults to `All`.
    pub fn parse(s: &str) -> Venue {
        match s.trim().to_lowercase().as_str() {
            "home" => Venue::Home,
            "away" => Venue::Away,
            _ => Venue::All,
        }
    }

    fn label(&self) -> &'static str {
        match self {
            Venue::All => "overall",
            Venue::Home => "home",
            Venue::Away => "away",
        }
    }
}

/// Aggregated win/draw/loss record for a club.
#[derive(Debug, Default, Clone)]
pub struct TeamRecord {
    pub played: u32,
    pub won: u32,
    pub drawn: u32,
    pub lost: u32,
    pub goals_for: i32,
    pub goals_against: i32,
}

impl TeamRecord {
    /// League points (3 per win, 1 per draw).
    pub fn points(&self) -> u32 {
        self.won * 3 + self.drawn
    }

    /// Goal difference.
    pub fn goal_diff(&self) -> i32 {
        self.goals_for - self.goals_against
    }

    /// Win rate as a percentage (0.0 when no matches played).
    pub fn win_rate(&self) -> f64 {
        if self.played == 0 {
            0.0
        } else {
            self.won as f64 / self.played as f64 * 100.0
        }
    }

    /// Fold one fixture result into the record.
    pub fn record_outcome(&mut self, outcome: Outcome, gf: i32, ga: i32) {
        self.played += 1;
        self.goals_for += gf;
        self.goals_against += ga;
        match outcome {
            Outcome::Win => self.won += 1,
            Outcome::Draw => self.drawn += 1,
            Outcome::Loss => self.lost += 1,
        }
    }
}

/// Compute a team's record, optionally restricted by season, competition and
/// venue. Returns the resolved display name alongside the record.
pub fn team_stats(
    db: &Database,
    team_query: &str,
    season: Option<i32>,
    competition: Option<&str>,
    venue: Venue,
) -> Option<(String, TeamRecord)> {
    let (key, display) = db.resolve_team(team_query)?;
    let mut rec = TeamRecord::default();

    for m in &db.matches {
        if let Some(s) = season {
            if m.season != s {
                continue;
            }
        }
        if let Some(c) = competition {
            if m.competition != c {
                continue;
            }
        }
        let is_home = m.home_key == key;
        let is_away = m.away_key == key;
        let counts = match venue {
            Venue::All => is_home || is_away,
            Venue::Home => is_home,
            Venue::Away => is_away,
        };
        if !counts {
            continue;
        }
        if let Some(outcome) = m.outcome_for(&key) {
            let (gf, ga) = if is_home {
                (m.home_goal, m.away_goal)
            } else {
                (m.away_goal, m.home_goal)
            };
            rec.record_outcome(outcome, gf, ga);
        }
    }
    Some((display, rec))
}

/// Format a [`TeamRecord`] in the style of the `TASK.md` examples.
pub fn format_record(
    display: &str,
    rec: &TeamRecord,
    season: Option<i32>,
    competition: Option<&str>,
    venue: Venue,
) -> String {
    let mut scope = format!("{} record", display);
    let mut qualifiers: Vec<String> = Vec::new();
    if venue != Venue::All {
        qualifiers.push(venue.label().to_string());
    }
    if let Some(s) = season {
        qualifiers.push(s.to_string());
    }
    if let Some(c) = competition {
        qualifiers.push(c.to_string());
    }
    if !qualifiers.is_empty() {
        scope.push_str(&format!(" ({})", qualifiers.join(" ")));
    }
    format!(
        "{scope}:\n\
         - Matches: {}\n\
         - Wins: {}, Draws: {}, Losses: {}\n\
         - Goals For: {}, Goals Against: {} (diff {:+})\n\
         - Points: {}\n\
         - Win rate: {:.1}%",
        rec.played,
        rec.won,
        rec.drawn,
        rec.lost,
        rec.goals_for,
        rec.goals_against,
        rec.goal_diff(),
        rec.points(),
        rec.win_rate(),
    )
}

/// Head-to-head record between two clubs.
pub struct HeadToHead<'a> {
    pub team_a: String,
    pub team_b: String,
    pub a_wins: u32,
    pub b_wins: u32,
    pub draws: u32,
    pub a_goals: i32,
    pub b_goals: i32,
    pub matches: Vec<&'a Match>,
}

/// Compute the head-to-head record between `a_query` and `b_query`. Returns
/// `None` if either club cannot be resolved.
pub fn head_to_head<'a>(
    db: &'a Database,
    a_query: &str,
    b_query: &str,
) -> Option<HeadToHead<'a>> {
    let (key_a, name_a) = db.resolve_team(a_query)?;
    let (key_b, name_b) = db.resolve_team(b_query)?;

    let mut h = HeadToHead {
        team_a: name_a,
        team_b: name_b,
        a_wins: 0,
        b_wins: 0,
        draws: 0,
        a_goals: 0,
        b_goals: 0,
        matches: Vec::new(),
    };

    for m in &db.matches {
        if !m.involves(&key_a, &key_b) {
            continue;
        }
        let (a_goal, b_goal) = if m.home_key == key_a {
            (m.home_goal, m.away_goal)
        } else {
            (m.away_goal, m.home_goal)
        };
        h.a_goals += a_goal;
        h.b_goals += b_goal;
        match a_goal.cmp(&b_goal) {
            std::cmp::Ordering::Greater => h.a_wins += 1,
            std::cmp::Ordering::Equal => h.draws += 1,
            std::cmp::Ordering::Less => h.b_wins += 1,
        }
        h.matches.push(m);
    }
    h.matches.sort_by(|x, y| y.date.cmp(&x.date));
    Some(h)
}

/// Format a head-to-head record, listing up to `limit` recent fixtures.
pub fn format_head_to_head(h: &HeadToHead, limit: usize) -> String {
    if h.matches.is_empty() {
        return format!(
            "No matches found between {} and {} in the dataset.",
            h.team_a, h.team_b
        );
    }
    let mut out = format!("{} vs {} — head-to-head:\n", h.team_a, h.team_b);
    for (i, m) in h.matches.iter().take(limit).enumerate() {
        out.push_str(&format!("{}. {}\n", i + 1, m.summary()));
    }
    if h.matches.len() > limit {
        out.push_str(&format!(
            "... ({} more match(es) in dataset)\n",
            h.matches.len() - limit
        ));
    }
    out.push_str(&format!(
        "\nHead-to-head in dataset ({} matches): {} {} win(s), {} {} win(s), {} draw(s)\n",
        h.matches.len(),
        h.team_a,
        h.a_wins,
        h.team_b,
        h.b_wins,
        h.draws
    ));
    out.push_str(&format!(
        "Goals: {} {} - {} {}",
        h.team_a, h.a_goals, h.b_goals, h.team_b
    ));
    out
}
