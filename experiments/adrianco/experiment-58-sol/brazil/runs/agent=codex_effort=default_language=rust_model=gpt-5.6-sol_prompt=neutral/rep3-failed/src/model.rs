use chrono::NaiveDate;
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MatchRecord {
    pub date: NaiveDate,
    pub season: u16,
    pub competition: String,
    pub home_team: String,
    pub away_team: String,
    pub home_goals: u16,
    pub away_goals: u16,
    pub round: Option<String>,
    pub stage: Option<String>,
    pub stadium: Option<String>,
    pub source: String,
    pub home_corners: Option<u16>,
    pub away_corners: Option<u16>,
    pub home_shots: Option<u16>,
    pub away_shots: Option<u16>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Player {
    pub id: u64,
    pub name: String,
    pub age: Option<u8>,
    pub nationality: String,
    pub overall: Option<u8>,
    pub potential: Option<u8>,
    pub club: Option<String>,
    pub position: Option<String>,
    pub jersey_number: Option<u8>,
    pub height: Option<String>,
    pub weight: Option<String>,
    pub attributes: BTreeMap<String, u8>,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq)]
pub struct DatasetCounts {
    pub matches_by_source: BTreeMap<String, usize>,
    pub players_by_source: BTreeMap<String, usize>,
    pub total_matches: usize,
    pub unique_matches: usize,
    pub total_players: usize,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq)]
pub struct TeamStats {
    pub team: String,
    pub matches: u32,
    pub wins: u32,
    pub draws: u32,
    pub losses: u32,
    pub goals_for: u32,
    pub goals_against: u32,
    pub points: u32,
    pub home_matches: u32,
    pub away_matches: u32,
}

impl TeamStats {
    pub fn win_rate(&self) -> f64 {
        if self.matches == 0 {
            0.0
        } else {
            self.wins as f64 * 100.0 / self.matches as f64
        }
    }

    pub fn goal_difference(&self) -> i32 {
        self.goals_for as i32 - self.goals_against as i32
    }
}

#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq)]
pub struct HeadToHead {
    pub team_a: String,
    pub team_b: String,
    pub matches: u32,
    pub team_a_wins: u32,
    pub team_b_wins: u32,
    pub draws: u32,
    pub team_a_goals: u32,
    pub team_b_goals: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Standing {
    pub position: usize,
    pub team: String,
    #[serde(flatten)]
    pub stats: TeamStats,
}

#[derive(Debug, Clone, Default)]
pub struct MatchFilter<'a> {
    pub team: Option<&'a str>,
    pub opponent: Option<&'a str>,
    pub competition: Option<&'a str>,
    pub season: Option<u16>,
    pub start_date: Option<NaiveDate>,
    pub end_date: Option<NaiveDate>,
    pub stage: Option<&'a str>,
    pub source: Option<&'a str>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CompetitionStats {
    pub competition: String,
    pub season: Option<u16>,
    pub matches: usize,
    pub goals: u64,
    pub goals_per_match: f64,
    pub home_wins: usize,
    pub away_wins: usize,
    pub draws: usize,
    pub home_win_rate: f64,
}
