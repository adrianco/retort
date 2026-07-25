//! Feature: Competition queries
//!
//! ```gherkin
//! Feature: Competition Queries
//!   Scenario: Calculate a final league table from match results
//!     Given the match data is loaded
//!     When I request the 2019 Brasileirão standings
//!     Then Flamengo should be champion with 90 points
//!     And the table should contain 20 clubs
//! ```

mod common;

use common::*;
use serde_json::json;

#[test]
fn scenario_who_won_the_2019_brasileirao() {
    // GIVEN the match data is loaded
    given_the_knowledge_graph_is_loaded();

    // WHEN I request the 2019 Série A table
    let answer = when_i_call(
        "standings",
        json!({ "competition": "Serie A", "season": 2019 }),
    );

    // THEN Flamengo are champions with 90 points from 28 wins
    assert_eq!(as_str(&answer.data, "champion"), "Flamengo");
    let leader = &as_array(&answer.data, "table")[0];
    assert_eq!(as_i64(leader, "record.points"), 90);
    assert_eq!(as_i64(leader, "record.wins"), 28);
    assert_eq!(as_i64(leader, "record.draws"), 6);
    assert_eq!(as_i64(leader, "record.losses"), 4);
    then_text_contains(&answer.text, "Champion");

    // AND the table has 20 clubs built from a full 380-match season
    assert_eq!(as_array(&answer.data, "table").len(), 20);
    assert_eq!(as_i64(&answer.data, "matches_counted"), 380);
    assert!(field(&answer.data, "complete_season").as_bool().unwrap());
}

#[test]
fn scenario_which_teams_were_relegated_in_2020() {
    given_the_knowledge_graph_is_loaded();

    let answer = when_i_call(
        "standings",
        json!({ "competition": "Serie A", "season": 2020 }),
    );
    let relegated: Vec<&str> = as_array(&answer.data, "relegated")
        .iter()
        .map(|name| name.as_str().unwrap())
        .collect();
    assert_eq!(relegated, vec!["Vasco", "Goiás", "Coritiba", "Botafogo"]);
    then_text_contains(&answer.text, "Relegated");
}

#[test]
fn scenario_table_is_internally_consistent() {
    given_the_knowledge_graph_is_loaded();

    let answer = when_i_call(
        "standings",
        json!({ "competition": "Serie A", "season": 2018 }),
    );
    let table = as_array(&answer.data, "table");
    let mut wins = 0;
    let mut losses = 0;
    let mut draws = 0;
    let mut goals_for = 0;
    let mut goals_against = 0;
    let mut previous_points = i64::MAX;
    for (index, row) in table.iter().enumerate() {
        assert_eq!(as_i64(row, "position"), index as i64 + 1);
        let points = as_i64(row, "record.points");
        assert!(points <= previous_points, "table must be sorted by points");
        previous_points = points;
        wins += as_i64(row, "record.wins");
        losses += as_i64(row, "record.losses");
        draws += as_i64(row, "record.draws");
        goals_for += as_i64(row, "record.goals_for");
        goals_against += as_i64(row, "record.goals_against");
        assert_eq!(
            as_i64(row, "record.matches"),
            as_i64(row, "home.matches") + as_i64(row, "away.matches")
        );
    }
    assert_eq!(wins, losses, "every win is somebody's loss");
    assert_eq!(draws % 2, 0, "draws are counted twice");
    assert_eq!(goals_for, goals_against, "every goal scored is conceded");
    assert_eq!(
        wins + losses + draws,
        as_i64(&answer.data, "matches_counted") * 2
    );
}

#[test]
fn scenario_standings_for_the_second_division() {
    given_the_knowledge_graph_is_loaded();

    let answer = when_i_call(
        "standings",
        json!({ "competition": "Serie B", "season": 2015, "limit": 4 }),
    );
    assert_eq!(as_str(&answer.data, "competition"), "Brasileirão Série B");
    assert_eq!(as_array(&answer.data, "table").len(), 20);
    assert!(as_i64(&answer.data, "matches_counted") > 300);
}

#[test]
fn scenario_knockout_competitions_do_not_claim_a_champion_from_points() {
    given_the_knowledge_graph_is_loaded();

    // A cup is not a round-robin, so no champion is inferred from points.
    let answer = when_i_call(
        "standings",
        json!({ "competition": "Copa do Brasil", "season": 2019, "limit": 5 }),
    );
    assert!(field(&answer.data, "champion").is_null());
    assert!(as_array(&answer.data, "relegated").is_empty());
    then_text_contains(&answer.text, "partial");
}

#[test]
fn scenario_season_without_data_is_reported_with_available_seasons() {
    given_the_knowledge_graph_is_loaded();

    let message = when_i_call_expecting_error(
        "standings",
        json!({ "competition": "Serie A", "season": 1975 }),
    );
    then_text_contains(&message, "1975");
    then_text_contains(&message, "Seasons available");
    then_text_contains(&message, "2003-2023");
}

#[test]
fn scenario_competition_coverage_is_discoverable() {
    given_the_knowledge_graph_is_loaded();

    let answer = when_i_call("dataset_overview", json!({}));
    let competitions: Vec<&str> = as_array(&answer.data, "competitions")
        .iter()
        .map(|entry| as_str(entry, "competition"))
        .collect();
    assert_eq!(competitions.len(), 5);
    assert!(competitions.contains(&"Copa Libertadores"));
    assert!(competitions.contains(&"Copa do Brasil"));
    assert_eq!(as_array(&answer.data, "sources").len(), 6);
    for source in as_array(&answer.data, "sources") {
        assert!(
            as_i64(source, "rows_used") > 1000,
            "every CSV file should contribute rows: {source}"
        );
    }
}

#[test]
fn scenario_libertadores_includes_foreign_clubs() {
    given_the_knowledge_graph_is_loaded();

    let answer = when_i_call(
        "search_matches",
        json!({ "competition": "Libertadores", "team": "Boca Juniors", "limit": 5 }),
    );
    assert!(as_i64(&answer.data, "total_matches") > 10);
    let profile = when_i_call("team_profile", json!({ "team": "Boca Juniors" }));
    assert!(field(&profile.data, "state").is_null());
    assert_eq!(as_array(&profile.data, "competitions").len(), 1);
}
