//! Context: BDD scenarios for match queries (spec section 1).
//!
//! Feature: Match Queries
//!   Scenario: Find matches between two teams (Flamengo vs Fluminense)
//!   Scenario: Filter by season and competition
//!   Scenario: Filter by date range
//!   Scenario: Duplicate fixtures across sources are counted once

mod common;

use brazilian_soccer_mcp::query::{MatchFilter, search_matches};

#[test]
fn scenario_find_matches_between_two_teams() {
    // Given the match data is loaded
    let ds = common::fixture();
    // When I search for matches between "Flamengo" and "Fluminense"
    let filter = MatchFilter {
        team: Some("Flamengo".into()),
        opponent: Some("Fluminense".into()),
        ..Default::default()
    };
    let found = search_matches(&ds, &filter).unwrap();
    // Then I should receive a list of matches, most recent first
    assert_eq!(found.len(), 2);
    assert_eq!(found[0].date, "2019-09-01");
    // And each match should have date, scores, and competition
    assert_eq!((found[0].home_goals, found[0].away_goals), (2, 1));
    assert_eq!(found[1].competition, "Brasileirão Série A");
}

#[test]
fn scenario_team_on_either_side_is_found() {
    // Given the match data is loaded
    let ds = common::fixture();
    // When I search for matches involving "Flamengo" alone
    let filter = MatchFilter {
        team: Some("Flamengo".into()),
        ..Default::default()
    };
    let found = search_matches(&ds, &filter).unwrap();
    // Then matches where Flamengo is home or away are returned
    // (2 league matches, 1 cup final, 1 Libertadores quarter-final, 1 extended duplicate removed)
    assert!(found.iter().any(|m| m.home.key == "flamengo"));
    assert!(found.iter().any(|m| m.away.key == "flamengo"));
    assert_eq!(found.len(), 4);
}

#[test]
fn scenario_filter_by_season_and_competition() {
    // Given the match data is loaded
    let ds = common::fixture();
    // When I search for Palmeiras matches in season 2022 in the Brasileirão
    let filter = MatchFilter {
        team: Some("Palmeiras".into()),
        season: Some(2022),
        competition: Some("Serie A".into()),
        ..Default::default()
    };
    let found = search_matches(&ds, &filter).unwrap();
    // Then only 2022 Brasileirão matches are returned (unplayed NA fixture excluded)
    assert_eq!(found.len(), 2);
    assert!(found.iter().all(|m| m.season == 2022));
}

#[test]
fn scenario_copa_do_brasil_finals_are_findable() {
    // Given the match data is loaded
    let ds = common::fixture();
    // When I search for Copa do Brasil matches with round "final"
    let found = search_matches(
        &ds,
        &MatchFilter {
            competition: Some("Copa do Brasil".into()),
            ..Default::default()
        },
    )
    .unwrap();
    // Then the final is returned with its round label
    let final_match = found
        .iter()
        .find(|m| m.round.as_deref() == Some("final"))
        .expect("final");
    assert_eq!(final_match.home.key, "flamengo");
    assert_eq!(final_match.away.key, "atletico");
}

#[test]
fn scenario_date_range_is_inclusive() {
    // Given the match data is loaded
    let ds = common::fixture();
    // When I search between 2019-05-01 and 2019-06-08
    let filter = MatchFilter {
        date_from: Some("2019-05-01".into()),
        date_to: Some("2019-06-08".into()),
        ..Default::default()
    };
    let found = search_matches(&ds, &filter).unwrap();
    // Then only matches on those dates (inclusive) are returned
    let dates: Vec<&str> = found.iter().map(|m| m.date.as_str()).collect();
    assert!(
        dates.contains(&"2019-05-12")
            && dates.contains(&"2019-06-08")
            && dates.contains(&"2019-06-01")
    );
    assert!(
        dates
            .iter()
            .all(|d| *d >= "2019-05-01" && *d <= "2019-06-08")
    );
}

#[test]
fn scenario_duplicate_fixture_from_two_sources_is_counted_once() {
    // Given the Flamengo-Fluminense 2019-09-01 match is in Brasileirao and in the extended file
    let ds = common::fixture();
    // When I count matches on that date
    let count = ds.matches.iter().filter(|m| m.date == "2019-09-01").count();
    // Then it appears once
    assert_eq!(count, 1);
}

#[test]
fn scenario_unknown_competition_is_an_error() {
    // Given the match data is loaded
    let ds = common::fixture();
    // When I search with a competition that does not exist
    let result = search_matches(
        &ds,
        &MatchFilter {
            competition: Some("Premier League".into()),
            ..Default::default()
        },
    );
    // Then the query is rejected with a message
    assert!(result.unwrap_err().contains("unknown competition"));
}

#[test]
fn scenario_unplayed_fixtures_are_ignored() {
    // Given a fixture with NA scores in the source file
    let ds = common::fixture();
    // When I search for the 2022-11-13 fixture
    let found = search_matches(
        &ds,
        &MatchFilter {
            date_from: Some("2022-11-13".into()),
            date_to: Some("2022-11-13".into()),
            ..Default::default()
        },
    )
    .unwrap();
    // Then it is not loaded
    assert!(found.is_empty());
}
