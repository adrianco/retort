//! Feature: Match queries
//!
//! ```gherkin
//! Feature: Match Queries
//!   Scenario: Find matches between two teams
//!     Given the match data is loaded
//!     When I search for matches between "Flamengo" and "Fluminense"
//!     Then I should receive a list of matches
//!     And each match should have date, scores, and competition
//! ```

mod common;

use common::*;
use serde_json::json;

#[test]
fn scenario_find_matches_between_two_teams() {
    // GIVEN the match data is loaded
    given_the_knowledge_graph_is_loaded();

    // WHEN I search for matches between "Flamengo" and "Fluminense"
    let answer = when_i_call(
        "search_matches",
        json!({ "team": "Flamengo", "opponent": "Fluminense", "limit": 10 }),
    );

    // THEN I should receive a list of matches
    let matches = as_array(&answer.data, "matches");
    assert_eq!(matches.len(), 10, "the limit should be honoured");
    assert!(
        as_i64(&answer.data, "total_matches") > 30,
        "the Fla-Flu derby should appear dozens of times"
    );

    // AND each match should have date, scores and competition
    for entry in matches {
        assert!(entry.get("date").and_then(|d| d.as_str()).is_some());
        assert!(entry.get("home_goals").is_some());
        assert!(entry.get("away_goals").is_some());
        assert!(!as_str(entry, "competition").is_empty());
        let teams = [as_str(entry, "home_team"), as_str(entry, "away_team")];
        assert!(teams.contains(&"Flamengo") && teams.contains(&"Fluminense"));
    }

    // AND a head-to-head tally accompanies the list
    let played = as_i64(&answer.data, "head_to_head.matches_played");
    let wins_a = as_i64(&answer.data, "head_to_head.team_a_wins");
    let wins_b = as_i64(&answer.data, "head_to_head.team_b_wins");
    let draws = as_i64(&answer.data, "head_to_head.draws");
    assert_eq!(played, wins_a + wins_b + draws);
    then_text_contains(&answer.text, "Head-to-head in dataset");
}

#[test]
fn scenario_matches_for_a_club_in_one_season() {
    given_the_knowledge_graph_is_loaded();

    // WHEN I ask what matches Palmeiras played in 2023
    let answer = when_i_call(
        "search_matches",
        json!({ "team": "Palmeiras", "season": 2023, "limit": 0 }),
    );

    // THEN every returned match is from that season and involves the club
    let matches = as_array(&answer.data, "matches");
    assert!(matches.len() > 30, "a full season plus cup ties");
    for entry in matches {
        assert_eq!(as_i64(entry, "season"), 2023);
        let teams = [as_str(entry, "home_team"), as_str(entry, "away_team")];
        assert!(teams.contains(&"Palmeiras"), "unexpected match: {entry}");
    }
}

#[test]
fn scenario_find_competition_finals_by_stage() {
    given_the_knowledge_graph_is_loaded();

    // WHEN I ask for Copa Libertadores finals
    let answer = when_i_call(
        "search_matches",
        json!({ "competition": "Libertadores", "stage": "final", "limit": 0 }),
    );

    // THEN only finals come back - not semifinals or quarterfinals
    let matches = as_array(&answer.data, "matches");
    assert!(!matches.is_empty());
    for entry in matches {
        assert_eq!(as_str(entry, "stage"), "final", "leaked: {entry}");
        assert_eq!(as_str(entry, "competition"), "Copa Libertadores");
    }
    // AND the 2019 final between Flamengo and River Plate is one of them
    then_text_contains(&answer.text, "2019-11-23");
    then_text_contains(&answer.text, "Flamengo 2-1 River Plate");
}

#[test]
fn scenario_filter_matches_by_date_range() {
    given_the_knowledge_graph_is_loaded();

    let answer = when_i_call(
        "search_matches",
        json!({
            "competition": "Serie A",
            "date_from": "2019-11-01",
            "date_to": "2019-11-07",
            "limit": 0
        }),
    );

    let matches = as_array(&answer.data, "matches");
    assert!(!matches.is_empty());
    for entry in matches {
        let date = as_str(entry, "date");
        assert!(
            ("2019-11-01"..="2019-11-07").contains(&date),
            "date {date} is outside the requested window"
        );
    }
}

#[test]
fn scenario_restrict_to_home_or_away_side() {
    given_the_knowledge_graph_is_loaded();

    let answer = when_i_call(
        "search_matches",
        json!({ "home_team": "Santos", "season": 2019, "competition": "Serie A", "limit": 0 }),
    );

    let matches = as_array(&answer.data, "matches");
    assert_eq!(matches.len(), 19, "a 20-team season means 19 home matches");
    for entry in matches {
        assert_eq!(as_str(entry, "home_team"), "Santos");
    }
}

#[test]
fn scenario_matches_are_sorted_most_recent_first_by_default() {
    given_the_knowledge_graph_is_loaded();

    let answer = when_i_call("search_matches", json!({ "team": "Grêmio", "limit": 25 }));
    let matches = as_array(&answer.data, "matches");
    let dates: Vec<&str> = matches.iter().map(|m| as_str(m, "date")).collect();
    let mut sorted = dates.clone();
    sorted.sort_by(|a, b| b.cmp(a));
    assert_eq!(dates, sorted, "default ordering should be newest first");

    let oldest = when_i_call(
        "search_matches",
        json!({ "team": "Grêmio", "limit": 5, "oldest_first": true }),
    );
    assert!(as_str(&as_array(&oldest.data, "matches")[0], "date") < dates[0]);
}

#[test]
fn scenario_unknown_club_is_reported_with_suggestions() {
    given_the_knowledge_graph_is_loaded();

    // WHEN I misspell a club name
    let message = when_i_call_expecting_error("search_matches", json!({ "team": "Flamngo" }));

    // THEN the error explains the problem and suggests the real club
    then_text_contains(&message, "Flamngo");
    then_text_contains(&message, "Flamengo");
}

#[test]
fn scenario_ambiguous_club_name_is_rejected_with_candidates() {
    given_the_knowledge_graph_is_loaded();

    // "Atlético" could be Mineiro, Goianiense, Paranaense ...
    let message = when_i_call_expecting_error("team_stats", json!({ "team": "Atlético" }));
    then_text_contains(&message, "ambiguous");
    then_text_contains(&message, "Atlético-MG");
}

#[test]
fn scenario_invalid_arguments_are_rejected() {
    given_the_knowledge_graph_is_loaded();

    let message =
        when_i_call_expecting_error("search_matches", json!({ "competition": "Premier League" }));
    then_text_contains(&message, "unknown competition");

    let message =
        when_i_call_expecting_error("search_matches", json!({ "date_from": "yesterday" }));
    then_text_contains(&message, "date_from");

    let message = when_i_call_expecting_error("search_matches", json!({ "season": "recent" }));
    then_text_contains(&message, "season");
}

#[test]
fn scenario_match_statistics_are_exposed_when_the_source_has_them() {
    given_the_knowledge_graph_is_loaded();

    // The BR-Football file adds shots, corners and attacks for 2023.
    let answer = when_i_call(
        "search_matches",
        json!({ "team": "São Paulo", "season": 2023, "competition": "Copa do Brasil", "limit": 5 }),
    );
    let with_stats = as_array(&answer.data, "matches")
        .iter()
        .filter(|entry| entry.get("statistics").is_some())
        .count();
    assert!(
        with_stats > 0,
        "2023 cup ties should carry shot/corner data"
    );
}
