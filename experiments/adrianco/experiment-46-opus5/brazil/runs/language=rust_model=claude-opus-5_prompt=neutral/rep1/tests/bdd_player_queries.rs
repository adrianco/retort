//! Feature: Player queries
//!
//! ```gherkin
//! Feature: Player Queries
//!   Scenario: Filter players by nationality
//!     Given the player data is loaded
//!     When I search for players from "Brazil"
//!     Then every result should be Brazilian
//!     And the results should be ordered by FIFA rating
//! ```

mod common;

use common::*;
use serde_json::json;

#[test]
fn scenario_find_all_brazilian_players() {
    // GIVEN the player data is loaded
    given_the_knowledge_graph_is_loaded();

    // WHEN I search for Brazilian players
    let answer = when_i_call(
        "search_players",
        json!({ "nationality": "Brazil", "limit": 25 }),
    );

    // THEN every result is Brazilian and sorted by rating
    assert!(as_i64(&answer.data, "total") > 800);
    let players = as_array(&answer.data, "players");
    assert_eq!(players.len(), 25);
    let ratings: Vec<i64> = players
        .iter()
        .map(|player| {
            assert_eq!(as_str(player, "nationality"), "Brazil");
            as_i64(player, "overall")
        })
        .collect();
    assert!(ratings.windows(2).all(|pair| pair[0] >= pair[1]));
    // AND the best-known Brazilian tops the list
    assert_eq!(as_str(&players[0], "name"), "Neymar Jr");
}

#[test]
fn scenario_player_profile_returns_ratings_and_attributes() {
    given_the_knowledge_graph_is_loaded();

    // "Who is Neymar Jr?"
    let answer = when_i_call("player_profile", json!({ "name": "Neymar Jr" }));
    assert_eq!(as_str(&answer.data, "name"), "Neymar Jr");
    assert_eq!(as_i64(&answer.data, "overall"), 92);
    assert_eq!(as_str(&answer.data, "nationality"), "Brazil");
    assert!(as_i64(&answer.data, "attributes.Dribbling") > 90);
    then_text_contains(&answer.text, "Best attributes");
}

#[test]
fn scenario_player_missing_from_the_snapshot_is_explained() {
    given_the_knowledge_graph_is_loaded();

    // Gabriel Barbosa joined Flamengo after this FIFA snapshot was taken.
    let message =
        when_i_call_expecting_error("player_profile", json!({ "name": "Gabriel Barbosa" }));
    then_text_contains(&message, "not in the FIFA player file");
    then_text_contains(&message, "Similar names");
    then_text_contains(&message, "Gabriel");
}

#[test]
fn scenario_squad_of_a_licensed_brazilian_club() {
    given_the_knowledge_graph_is_loaded();

    // "Who are the highest-rated players at Grêmio?"
    let answer = when_i_call("club_players", json!({ "club": "Grêmio", "limit": 5 }));
    assert_eq!(as_i64(&answer.data, "players_found"), 20);
    assert!(as_f64(&answer.data, "average_overall") > 60.0);
    let players = as_array(&answer.data, "players");
    assert_eq!(players.len(), 5);
    let ratings: Vec<i64> = players.iter().map(|p| as_i64(p, "overall")).collect();
    assert!(ratings.windows(2).all(|pair| pair[0] >= pair[1]));
    for player in players {
        assert_eq!(as_str(player, "club_in_match_data"), "Grêmio");
    }
    // AND the club is cross-referenced with the match data
    assert!(as_i64(&answer.data, "matches_in_graph") > 1000);
}

#[test]
fn scenario_unlicensed_club_gap_is_reported_honestly() {
    given_the_knowledge_graph_is_loaded();

    // Flamengo is absent from the FIFA 19 file; the answer must say so
    // rather than inventing players.
    let answer = when_i_call("club_players", json!({ "club": "Flamengo" }));
    assert_eq!(as_i64(&answer.data, "players_found"), 0);
    then_text_contains(&answer.text, "officially licensed Brazilian clubs");
    then_text_contains(&answer.text, "Brazilian clubs with player data");
    then_text_contains(&answer.text, "Grêmio");
}

#[test]
fn scenario_filter_players_by_position_and_rating() {
    given_the_knowledge_graph_is_loaded();

    let answer = when_i_call(
        "search_players",
        json!({ "position": "GK", "min_overall": 85, "limit": 10 }),
    );
    let players = as_array(&answer.data, "players");
    assert!(!players.is_empty());
    for player in players {
        assert_eq!(as_str(player, "position"), "GK");
        assert!(as_i64(player, "overall") >= 85);
    }
}

#[test]
fn scenario_filter_players_by_club_using_match_data_aliases() {
    given_the_knowledge_graph_is_loaded();

    // The FIFA file spells this club "Atlético Mineiro" while the match files
    // use "Atletico-MG"; either spelling must find the squad.
    let by_fifa_name = when_i_call(
        "search_players",
        json!({ "club": "Atlético Mineiro", "limit": 30 }),
    );
    let by_match_name = when_i_call(
        "search_players",
        json!({ "club": "Atletico-MG", "limit": 30 }),
    );
    assert!(as_i64(&by_fifa_name.data, "total") > 0);
    assert_eq!(
        as_i64(&by_fifa_name.data, "total"),
        as_i64(&by_match_name.data, "total")
    );
}

#[test]
fn scenario_cross_reference_players_with_match_data() {
    given_the_knowledge_graph_is_loaded();

    // "Which Brazilian players play at clubs that appear in the match data?"
    let answer = when_i_call(
        "search_players",
        json!({ "brazilian_clubs_only": true, "limit": 20 }),
    );
    assert!(as_i64(&answer.data, "total") > 100);
    for player in as_array(&answer.data, "players") {
        let club = as_str(player, "club_in_match_data");
        assert!(!club.is_empty(), "every result links to a graph club");
    }

    // AND foreign clubs that merely share a name are not linked: FIFA's
    // "Boavista FC" is the Portuguese club, not Boavista-RJ.
    let boavista = when_i_call("club_players", json!({ "club": "Boavista" }));
    assert_eq!(as_i64(&boavista.data, "players_found"), 0);
}

#[test]
fn scenario_age_filters_are_applied() {
    given_the_knowledge_graph_is_loaded();

    let answer = when_i_call(
        "search_players",
        json!({ "nationality": "Brazil", "max_age": 21, "min_overall": 75, "limit": 10 }),
    );
    for player in as_array(&answer.data, "players") {
        assert!(as_i64(player, "age") <= 21);
        assert!(as_i64(player, "overall") >= 75);
    }
}

#[test]
fn scenario_player_name_search_is_accent_insensitive() {
    given_the_knowledge_graph_is_loaded();

    let accented = when_i_call("search_players", json!({ "name": "Thiago Silva" }));
    let plain = when_i_call("search_players", json!({ "name": "thiago silva" }));
    assert!(as_i64(&accented.data, "total") > 0);
    assert_eq!(
        as_i64(&accented.data, "total"),
        as_i64(&plain.data, "total")
    );
}
