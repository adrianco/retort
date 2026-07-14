use crate::models::{Match, Player};
use crate::queries::{HeadToHead, StandingRow, TeamRecord};

pub fn format_head_to_head(h2h: &HeadToHead, team_a: &str, team_b: &str) -> String {
    let matches = format_matches(&h2h.matches);
    format!(
        "{matches}\n\nHead-to-head: {team_a} {} wins, {team_b} {} wins, {} draws",
        h2h.wins_a, h2h.wins_b, h2h.draws
    )
}

pub fn format_team_record(record: &TeamRecord, team: &str) -> String {
    format!(
        "{team} record:\n- Matches: {}\n- Wins: {}, Draws: {}, Losses: {}\n- Goals For: {}, Goals Against: {}\n- Win rate: {:.1}%",
        record.played,
        record.wins,
        record.draws,
        record.losses,
        record.goals_for,
        record.goals_against,
        record.win_rate() * 100.0
    )
}

pub fn format_standings(rows: &[StandingRow]) -> String {
    if rows.is_empty() {
        return "No standings available.".to_string();
    }
    rows.iter()
        .enumerate()
        .map(|(i, row)| {
            format!(
                "{}. {} - {} pts ({}W, {}D, {}L), GD {:+}",
                i + 1,
                row.team,
                row.points,
                row.wins,
                row.draws,
                row.losses,
                row.goal_difference
            )
        })
        .collect::<Vec<_>>()
        .join("\n")
}

pub fn format_match_line(m: &Match) -> String {
    let date = m
        .date
        .map(|d| d.format("%Y-%m-%d").to_string())
        .unwrap_or_else(|| "date unknown".to_string());
    let round = m
        .round
        .as_ref()
        .map(|r| format!(" Round {r}"))
        .unwrap_or_default();
    let stage = m
        .stage
        .as_ref()
        .map(|s| format!(" ({s})"))
        .unwrap_or_default();
    format!(
        "{date}: {} {}-{} {} ({}{}{})",
        m.home_team, m.home_goal, m.away_goal, m.away_team, m.competition, round, stage
    )
}

pub fn format_matches(matches: &[&Match]) -> String {
    if matches.is_empty() {
        return "No matches found.".to_string();
    }
    matches
        .iter()
        .map(|m| format_match_line(m))
        .collect::<Vec<_>>()
        .join("\n")
}

pub fn format_player_line(p: &Player) -> String {
    format!(
        "{} - Overall: {}, Position: {}, Club: {}",
        p.name,
        p.overall.map(|o| o.to_string()).unwrap_or_else(|| "?".to_string()),
        p.position.as_deref().unwrap_or("?"),
        p.club.as_deref().unwrap_or("Free agent"),
    )
}

pub fn format_players(players: &[&Player]) -> String {
    if players.is_empty() {
        return "No players found.".to_string();
    }
    players
        .iter()
        .enumerate()
        .map(|(i, p)| format!("{}. {}", i + 1, format_player_line(p)))
        .collect::<Vec<_>>()
        .join("\n")
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::models::{Competition, Match, Player};
    use chrono::NaiveDate;

    fn sample_match() -> Match {
        Match {
            date: NaiveDate::from_ymd_opt(2023, 9, 3),
            competition: Competition::BrasileiraoSerieA,
            season: 2023,
            round: Some("22".to_string()),
            stage: None,
            home_team: "Flamengo".to_string(),
            away_team: "Fluminense".to_string(),
            home_goal: 2,
            away_goal: 1,
            venue: None,
            source: "test",
        }
    }

    #[test]
    fn formats_a_single_match_line() {
        let m = sample_match();
        assert_eq!(
            format_match_line(&m),
            "2023-09-03: Flamengo 2-1 Fluminense (Brasileirao Serie A Round 22)"
        );
    }

    #[test]
    fn formats_a_match_with_unknown_date_and_no_round() {
        let mut m = sample_match();
        m.date = None;
        m.round = None;
        assert_eq!(
            format_match_line(&m),
            "date unknown: Flamengo 2-1 Fluminense (Brasileirao Serie A)"
        );
    }

    #[test]
    fn formats_empty_match_list() {
        assert_eq!(format_matches(&[]), "No matches found.");
    }

    #[test]
    fn formats_head_to_head_summary() {
        use crate::queries::head_to_head;
        let matches = vec![sample_match()];
        let h2h = head_to_head(&matches, "Flamengo", "Fluminense");
        assert_eq!(
            format_head_to_head(&h2h, "Flamengo", "Fluminense"),
            "2023-09-03: Flamengo 2-1 Fluminense (Brasileirao Serie A Round 22)\n\nHead-to-head: Flamengo 1 wins, Fluminense 0 wins, 0 draws"
        );
    }

    #[test]
    fn formats_team_record_summary() {
        let record = crate::queries::TeamRecord {
            played: 19,
            wins: 11,
            draws: 5,
            losses: 3,
            goals_for: 28,
            goals_against: 15,
        };
        assert_eq!(
            format_team_record(&record, "Corinthians"),
            "Corinthians record:\n- Matches: 19\n- Wins: 11, Draws: 5, Losses: 3\n- Goals For: 28, Goals Against: 15\n- Win rate: 57.9%"
        );
    }

    #[test]
    fn formats_standings_table() {
        let rows = vec![crate::queries::StandingRow {
            team: "Flamengo".to_string(),
            played: 38,
            wins: 28,
            draws: 6,
            losses: 4,
            goals_for: 81,
            goals_against: 33,
            goal_difference: 48,
            points: 90,
        }];
        assert_eq!(
            format_standings(&rows),
            "1. Flamengo - 90 pts (28W, 6D, 4L), GD +48"
        );
    }

    #[test]
    fn formats_a_player_line() {
        let player = Player {
            id: 1,
            name: "Neymar Jr".to_string(),
            age: Some(31),
            nationality: "Brazil".to_string(),
            overall: Some(92),
            potential: Some(92),
            club: Some("Paris Saint-Germain".to_string()),
            position: Some("LW".to_string()),
            jersey_number: Some(10),
            height: None,
            weight: None,
        };
        assert_eq!(
            format_player_line(&player),
            "Neymar Jr - Overall: 92, Position: LW, Club: Paris Saint-Germain"
        );
    }
}
