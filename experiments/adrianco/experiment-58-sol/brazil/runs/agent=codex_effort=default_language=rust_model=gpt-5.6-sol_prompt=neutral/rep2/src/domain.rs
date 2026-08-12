use chrono::NaiveDate;
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

#[derive(Clone, Debug, Default, Serialize, Deserialize, PartialEq)]
pub struct MatchMetrics {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub home_corners: Option<u16>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub away_corners: Option<u16>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub home_attacks: Option<u16>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub away_attacks: Option<u16>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub home_shots: Option<u16>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub away_shots: Option<u16>,
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
pub struct SoccerMatch {
    pub id: String,
    pub date: NaiveDate,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub time: Option<String>,
    pub season: u16,
    pub competition: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub round: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub stage: Option<String>,
    pub home_team: String,
    pub home_team_key: String,
    pub away_team: String,
    pub away_team_key: String,
    pub home_goals: u16,
    pub away_goals: u16,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub arena: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub metrics: Option<MatchMetrics>,
    pub sources: Vec<String>,
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
pub struct Player {
    pub id: u32,
    pub name: String,
    pub age: u8,
    pub nationality: String,
    pub overall: u8,
    pub potential: u8,
    pub club: Option<String>,
    pub position: Option<String>,
    pub jersey_number: Option<u8>,
    pub height: Option<String>,
    pub weight: Option<String>,
    pub preferred_foot: Option<String>,
    pub attributes: BTreeMap<String, u8>,
}

#[derive(Clone, Debug, Default, Serialize, Deserialize, PartialEq, Eq)]
pub struct TeamRecord {
    pub team: String,
    pub matches: u32,
    pub wins: u32,
    pub draws: u32,
    pub losses: u32,
    pub goals_for: u32,
    pub goals_against: u32,
    pub points: u32,
}

impl TeamRecord {
    pub fn goal_difference(&self) -> i32 {
        self.goals_for as i32 - self.goals_against as i32
    }

    pub fn win_rate(&self) -> f64 {
        if self.matches == 0 {
            0.0
        } else {
            self.wins as f64 * 100.0 / self.matches as f64
        }
    }
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
pub struct Standing {
    pub position: usize,
    #[serde(flatten)]
    pub record: TeamRecord,
    pub goal_difference: i32,
}
