use chrono::NaiveDate;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum Competition {
    Brasileirao,
    BrasileiraoHistoric,
    CopaDoBrasil,
    Libertadores,
    BrFootball,
}

impl Competition {
    pub fn label(&self) -> &'static str {
        match self {
            Competition::Brasileirao => "Brasileirão",
            Competition::BrasileiraoHistoric => "Brasileirão (Historic)",
            Competition::CopaDoBrasil => "Copa do Brasil",
            Competition::Libertadores => "Copa Libertadores",
            Competition::BrFootball => "BR-Football",
        }
    }

    pub fn parse(s: &str) -> Option<Competition> {
        let lower = s.to_lowercase();
        if lower.contains("brasileir") && lower.contains("hist") {
            Some(Competition::BrasileiraoHistoric)
        } else if lower.contains("brasileir") || lower == "serie a" || lower == "série a" {
            Some(Competition::Brasileirao)
        } else if lower.contains("copa do brasil") || lower.contains("cup") {
            Some(Competition::CopaDoBrasil)
        } else if lower.contains("libertadores") {
            Some(Competition::Libertadores)
        } else if lower.contains("br-football") || lower.contains("br_football") {
            Some(Competition::BrFootball)
        } else {
            None
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Match {
    pub competition: Competition,
    pub date: Option<NaiveDate>,
    pub home_team: String,
    pub away_team: String,
    pub home_team_norm: String,
    pub away_team_norm: String,
    pub home_goal: i32,
    pub away_goal: i32,
    pub season: Option<i32>,
    pub round: Option<String>,
    pub stage: Option<String>,
    pub arena: Option<String>,
    pub home_state: Option<String>,
    pub away_state: Option<String>,
    pub home_shots: Option<i32>,
    pub away_shots: Option<i32>,
    pub home_corner: Option<i32>,
    pub away_corner: Option<i32>,
}

impl Match {
    pub fn winner(&self) -> MatchResult {
        if self.home_goal > self.away_goal {
            MatchResult::HomeWin
        } else if self.home_goal < self.away_goal {
            MatchResult::AwayWin
        } else {
            MatchResult::Draw
        }
    }

    pub fn date_string(&self) -> String {
        self.date
            .map(|d| d.format("%Y-%m-%d").to_string())
            .unwrap_or_else(|| "????-??-??".to_string())
    }

    pub fn score_line(&self) -> String {
        format!(
            "{}: {} {}-{} {} ({}{})",
            self.date_string(),
            self.home_team,
            self.home_goal,
            self.away_goal,
            self.away_team,
            self.competition.label(),
            self.round
                .as_ref()
                .map(|r| format!(" Round {}", r))
                .unwrap_or_default(),
        )
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MatchResult {
    HomeWin,
    AwayWin,
    Draw,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct Player {
    pub id: u64,
    pub name: String,
    pub age: Option<i32>,
    pub nationality: String,
    pub overall: Option<i32>,
    pub potential: Option<i32>,
    pub club: String,
    pub club_norm: String,
    pub position: Option<String>,
    pub jersey_number: Option<String>,
    pub height: Option<String>,
    pub weight: Option<String>,
    pub preferred_foot: Option<String>,
    pub wage: Option<String>,
    pub value: Option<String>,
}
