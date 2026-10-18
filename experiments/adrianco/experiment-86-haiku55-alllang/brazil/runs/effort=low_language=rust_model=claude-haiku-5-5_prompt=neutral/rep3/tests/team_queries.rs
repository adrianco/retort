//! Context: BDD scenarios for team, head-to-head, standings and statistics
//! queries (spec sections 2, 4 and 5).
//!
//! Feature: Team Queries
//!   Scenario: Team record for a season and venue
//!   Scenario: Head-to-head comparison
//!   Scenario: Standings calculated from results
//!   Scenario: League statistics

mod common;

use brazilian_soccer_mcp::query::{Venue, head_to_head, league_stats, standings, team_record};

#[test]
fn scenario_home_record_for_a_season() {
    // Given the match data is loaded
    let ds = common::fixture();
    // When I request Palmeiras' home record in 2022
    let (_, rec) = team_record(&ds, "Palmeiras", Some(2022), None, Venue::Home).unwrap();
    // Then I should receive wins, draws, losses and goals
    assert_eq!(rec.played, 1);
    assert_eq!((rec.wins, rec.draws, rec.losses), (1, 0, 0));
    assert_eq!((rec.goals_for, rec.goals_against), (2, 0));
    assert!((rec.win_rate() - 100.0).abs() < f64::EPSILON);
}

#[test]
fn scenario_record_with_state_suffix_in_query() {
    // Given the match data is loaded
    let ds = common::fixture();
    // When I ask for "Palmeiras-SP" across all seasons
    let (_, rec) = team_record(&ds, "Palmeiras-SP", None, None, Venue::Any).unwrap();
    // Then the suffix is ignored and the team is matched
    assert_eq!(rec.played, 4);
}

#[test]
fn scenario_head_to_head_between_palmeiras_and_santos() {
    // Given the match data is loaded
    let ds = common::fixture();
    // When I compare Palmeiras and Santos head-to-head
    let (_, _, meetings, rec) = head_to_head(&ds, "Palmeiras", "Santos", None).unwrap();
    // Then the meetings are listed most recent first with the tally from Palmeiras' view
    assert_eq!(meetings.len(), 2);
    assert_eq!(meetings[0].date, "2022-05-01");
    assert_eq!((rec.wins, rec.draws, rec.losses), (1, 1, 0));
}

#[test]
fn scenario_standings_are_calculated_from_results() {
    // Given the 2019 Brasileirão matches are loaded
    let ds = common::fixture();
    // When I request the 2019 standings
    let table = standings(&ds, "Brasileirão Série A", 2019).unwrap();
    // Then teams are ranked by points with 3 for a win and 1 for a draw
    // (Palmeiras: win 3-0 + draw 1-1 = 4; Flamengo: win 2-1 + defeat 0-1 = 3)
    assert_eq!(table[0].team, "Palmeiras (SP)");
    assert_eq!(table[0].points, 4);
    let flamengo = table
        .iter()
        .find(|r| r.team.starts_with("Flamengo"))
        .unwrap();
    assert_eq!(flamengo.points, 3);
    let corinthians = table
        .iter()
        .find(|r| r.team.starts_with("Corinthians"))
        .unwrap();
    assert_eq!(corinthians.points, 1);
}

#[test]
fn scenario_league_statistics_for_a_season() {
    // Given the 2019 Brasileirão matches are loaded
    let ds = common::fixture();
    // When I request statistics for that season
    let stats = league_stats(&ds, Some("Brasileirão Série A"), Some(2019)).unwrap();
    // Then I should see matches, average goals and home/draw/away percentages
    assert_eq!(stats.matches, 4);
    assert!((stats.avg_goals - 2.25).abs() < 1e-9);
    assert!((stats.home_win_pct - 75.0).abs() < 1e-9);
    assert!((stats.draw_pct - 25.0).abs() < 1e-9);
    assert!((stats.away_win_pct - 0.0).abs() < 1e-9);
    assert_eq!(
        stats.biggest_wins[0].home_goals + stats.biggest_wins[0].away_goals,
        3
    );
}

#[test]
fn scenario_unknown_team_has_no_matches() {
    // Given the match data is loaded
    let ds = common::fixture();
    // When I ask for the record of a team that is not in the dataset
    let (_, rec) = team_record(&ds, "Time Inexistente", None, None, Venue::Any).unwrap();
    // Then the record is empty
    assert_eq!(rec.played, 0);
}
