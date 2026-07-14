//! Domain model: the two entities the server reasons about — matches and players.

use crate::{normalize, teams};

#[derive(Debug, Clone)]
pub struct Match {
    pub competition: String,
    pub season: i32,
    pub round: Option<String>,
    pub stage: Option<String>,
    /// ISO `YYYY-MM-DD`, or empty when the source had no usable date.
    pub date: String,
    pub home_display: String,
    pub away_display: String,
    pub home_key: String,
    pub away_key: String,
    pub home_goal: i32,
    pub away_goal: i32,
}

impl Match {
    /// Build a match from raw field values, normalizing names and the date.
    pub fn new(
        competition: &str,
        season: i32,
        round: Option<String>,
        stage: Option<String>,
        raw_date: &str,
        raw_home: &str,
        raw_away: &str,
        home_goal: i32,
        away_goal: i32,
    ) -> Self {
        let (date, _) = normalize::parse_date(raw_date).unwrap_or_default();
        let (home_key, home_display) = teams::canonical(raw_home);
        let (away_key, away_display) = teams::canonical(raw_away);
        Match {
            competition: competition.to_string(),
            season,
            round,
            stage,
            date,
            home_display,
            away_display,
            home_key,
            away_key,
            home_goal,
            away_goal,
        }
    }

    /// The de-duplication identity: one fixture per competition/season/pairing.
    pub fn dedup_key(&self) -> (String, i32, String, String) {
        (
            self.competition.clone(),
            self.season,
            self.home_key.clone(),
            self.away_key.clone(),
        )
    }

    pub fn involves(&self, team_query: &str) -> bool {
        teams::query_matches(team_query, &self.home_key)
            || teams::query_matches(team_query, &self.away_key)
    }
}

#[derive(Debug, Clone)]
pub struct Player {
    pub name: String,
    pub age: i32,
    pub nationality: String,
    pub overall: i32,
    pub potential: i32,
    pub club: String,
    pub position: String,
    pub jersey_number: String,
    pub height: String,
    pub weight: String,
}
