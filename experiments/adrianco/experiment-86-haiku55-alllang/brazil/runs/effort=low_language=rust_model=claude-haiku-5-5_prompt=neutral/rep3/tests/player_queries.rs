//! Context: BDD scenarios for FIFA player queries (spec section 3).
//!
//! Feature: Player Queries
//!   Scenario: Search a player by name
//!   Scenario: Filter by nationality
//!   Scenario: Filter by club and minimum rating, highest rated first

mod common;

use brazilian_soccer_mcp::query::{PlayerFilter, search_players};

#[test]
fn scenario_search_player_by_name() {
    // Given the FIFA data is loaded
    let ds = common::fixture();
    // When I search for "Gabriel Barbosa"
    let found = search_players(
        &ds,
        &PlayerFilter {
            name: Some("Gabriel Barbosa".into()),
            ..Default::default()
        },
    );
    // Then I should receive that player with rating and club
    assert_eq!(found.len(), 1);
    assert_eq!(found[0].club.as_deref(), Some("Flamengo"));
    assert_eq!(found[0].overall, 80);
}

#[test]
fn scenario_all_brazilian_players() {
    // Given the FIFA data is loaded
    let ds = common::fixture();
    // When I filter by nationality "brazil" (case-insensitive)
    let found = search_players(
        &ds,
        &PlayerFilter {
            nationality: Some("brazil".into()),
            ..Default::default()
        },
    );
    // Then only Brazilian players are returned, highest overall first
    assert_eq!(found.len(), 3);
    assert_eq!(found[0].name, "Neymar Jr");
    assert!(found.iter().all(|p| p.nationality == "Brazil"));
}

#[test]
fn scenario_club_position_and_rating_filters_combine() {
    // Given the FIFA data is loaded
    let ds = common::fixture();
    // When I ask for strikers (ST) rated at least 75 at a club containing "Flamengo"
    let found = search_players(
        &ds,
        &PlayerFilter {
            club: Some("flamengo".into()),
            position: Some("ST".into()),
            min_overall: Some(75),
            ..Default::default()
        },
    );
    // Then only matching players are returned
    assert_eq!(found.len(), 1);
    assert_eq!(found[0].name, "Gabriel Barbosa");
}

#[test]
fn scenario_players_without_club_are_kept_when_no_club_filter() {
    // Given a free agent with no club in the data
    let ds = common::fixture();
    // When I search with no club filter
    let found = search_players(
        &ds,
        &PlayerFilter {
            name: Some("Pratto".into()),
            ..Default::default()
        },
    );
    // Then the player is found and has no club
    assert_eq!(found.len(), 1);
    assert!(found[0].club.is_none());
    // And a club filter excludes them
    let none = search_players(
        &ds,
        &PlayerFilter {
            name: Some("Pratto".into()),
            club: Some("Flamengo".into()),
            ..Default::default()
        },
    );
    assert!(none.is_empty());
}
