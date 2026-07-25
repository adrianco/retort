//! Feature: Team queries
//!
//! ```gherkin
//! Feature: Team Queries
//!   Scenario: Get team statistics
//!     Given the match data is loaded
//!     When I request statistics for "Palmeiras" in season "2023"
//!     Then I should receive wins, losses, draws, and goals
//! ```

mod common;

use common::*;
use serde_json::json;

#[test]
fn scenario_get_team_statistics_for_a_season() {
    // GIVEN the match data is loaded
    given_the_knowledge_graph_is_loaded();

    // WHEN I request statistics for "Palmeiras" in season "2023"
    let answer = when_i_call("team_stats", json!({ "team": "Palmeiras", "season": 2023 }));

    // THEN I should receive wins, losses, draws and goals
    let matches = as_i64(&answer.data, "record.matches");
    let wins = as_i64(&answer.data, "record.wins");
    let draws = as_i64(&answer.data, "record.draws");
    let losses = as_i64(&answer.data, "record.losses");
    assert!(matches > 30);
    assert_eq!(matches, wins + draws + losses);
    assert_eq!(as_i64(&answer.data, "record.points"), wins * 3 + draws);
    assert!(as_i64(&answer.data, "record.goals_for") > 0);
    assert!(as_i64(&answer.data, "record.goals_against") > 0);
    then_text_contains(&answer.text, "Win rate:");
}

#[test]
fn scenario_home_record_for_a_single_season_and_competition() {
    given_the_knowledge_graph_is_loaded();

    // "What is Corinthians' home record in 2022?"
    let answer = when_i_call(
        "team_stats",
        json!({ "team": "Corinthians", "season": 2022, "competition": "Serie A", "venue": "home" }),
    );

    // A 20-team Série A season gives every club 19 home matches.
    assert_eq!(as_i64(&answer.data, "record.matches"), 19);
    assert_eq!(
        as_i64(&answer.data, "record.matches"),
        as_i64(&answer.data, "record.wins")
            + as_i64(&answer.data, "record.draws")
            + as_i64(&answer.data, "record.losses")
    );
    then_text_contains(&answer.text, "home record");
}

#[test]
fn scenario_home_and_away_records_add_up_to_the_overall_record() {
    given_the_knowledge_graph_is_loaded();

    let answer = when_i_call(
        "team_stats",
        json!({ "team": "Santos", "competition": "Serie A" }),
    );
    for field in [
        "matches",
        "wins",
        "draws",
        "losses",
        "goals_for",
        "goals_against",
    ] {
        assert_eq!(
            as_i64(&answer.data, &format!("record.{field}")),
            as_i64(&answer.data, &format!("home.{field}"))
                + as_i64(&answer.data, &format!("away.{field}")),
            "home + away should equal the overall {field}"
        );
    }
}

#[test]
fn scenario_compare_two_clubs_head_to_head() {
    given_the_knowledge_graph_is_loaded();

    // "Compare Palmeiras and Santos head-to-head"
    let answer = when_i_call(
        "head_to_head",
        json!({ "team_a": "Palmeiras", "team_b": "Santos", "recent": 5 }),
    );
    let played = as_i64(&answer.data, "matches_played");
    assert!(played > 30, "the São Paulo clásico is well represented");
    assert_eq!(
        played,
        as_i64(&answer.data, "team_a_wins")
            + as_i64(&answer.data, "team_b_wins")
            + as_i64(&answer.data, "draws")
    );

    // AND the mirrored query reports the same numbers the other way round
    let mirrored = when_i_call(
        "head_to_head",
        json!({ "team_a": "Santos", "team_b": "Palmeiras" }),
    );
    assert_eq!(as_i64(&mirrored.data, "matches_played"), played);
    assert_eq!(
        as_i64(&mirrored.data, "team_b_wins"),
        as_i64(&answer.data, "team_a_wins")
    );
    assert_eq!(
        as_i64(&mirrored.data, "team_a_goals"),
        as_i64(&answer.data, "team_b_goals")
    );
}

#[test]
fn scenario_head_to_head_can_be_scoped_to_one_competition() {
    given_the_knowledge_graph_is_loaded();

    let all = when_i_call(
        "head_to_head",
        json!({ "team_a": "Flamengo", "team_b": "Corinthians" }),
    );
    let league_only = when_i_call(
        "head_to_head",
        json!({ "team_a": "Flamengo", "team_b": "Corinthians", "competition": "Serie A" }),
    );
    assert!(as_i64(&league_only.data, "matches_played") < as_i64(&all.data, "matches_played"));
    let competitions = as_array(&league_only.data, "by_competition");
    assert_eq!(competitions.len(), 1);
    assert_eq!(
        as_str(&competitions[0], "competition"),
        "Brasileirão Série A"
    );
}

#[test]
fn scenario_team_profile_lists_every_competition_played() {
    given_the_knowledge_graph_is_loaded();

    // "What competitions has Palmeiras played in?"
    let answer = when_i_call("team_profile", json!({ "team": "Palmeiras" }));
    let competitions: Vec<&str> = as_array(&answer.data, "competitions")
        .iter()
        .map(|entry| as_str(entry, "competition"))
        .collect();
    assert!(competitions.contains(&"Brasileirão Série A"));
    assert!(competitions.contains(&"Copa do Brasil"));
    assert!(competitions.contains(&"Copa Libertadores"));
    then_text_contains(&answer.text, "Name variants in the data");
    assert_eq!(as_str(&answer.data, "team_key"), "palmeiras-SP");
}

#[test]
fn scenario_rank_clubs_by_goals_scored_in_a_season() {
    given_the_knowledge_graph_is_loaded();

    // "Which team scored the most goals in Série A 2023?"
    let answer = when_i_call(
        "team_rankings",
        json!({ "metric": "goals_for", "competition": "Serie A", "season": 2023, "limit": 5 }),
    );
    let ranking = as_array(&answer.data, "ranking");
    assert_eq!(ranking.len(), 5);
    let values: Vec<f64> = ranking.iter().map(|entry| as_f64(entry, "value")).collect();
    assert!(
        values.windows(2).all(|pair| pair[0] >= pair[1]),
        "ranking must be sorted descending: {values:?}"
    );

    // AND the leader agrees with the calculated league table
    let table = when_i_call(
        "standings",
        json!({ "competition": "Serie A", "season": 2023 }),
    );
    let best_in_table = as_array(&table.data, "table")
        .iter()
        .map(|row| as_i64(row, "record.goals_for"))
        .max()
        .unwrap();
    assert_eq!(values[0] as i64, best_in_table);
}

#[test]
fn scenario_rank_clubs_by_away_record() {
    given_the_knowledge_graph_is_loaded();

    // "Which team has the best away record?"
    let answer = when_i_call(
        "team_rankings",
        json!({
            "metric": "win_rate",
            "competition": "Serie A",
            "venue": "away",
            "min_matches": 100,
            "limit": 5
        }),
    );
    let ranking = as_array(&answer.data, "ranking");
    assert_eq!(ranking.len(), 5);
    for entry in ranking {
        assert!(as_i64(entry, "record.matches") >= 100);
        assert!((0.0..=100.0).contains(&as_f64(entry, "value")));
    }
    then_text_contains(&answer.text, "away matches");
}

#[test]
fn scenario_conceding_metric_ranks_ascending() {
    given_the_knowledge_graph_is_loaded();

    let answer = when_i_call(
        "team_rankings",
        json!({
            "metric": "goals_against",
            "competition": "Serie A",
            "season": 2019,
            "min_matches": 30,
            "limit": 5
        }),
    );
    let values: Vec<f64> = as_array(&answer.data, "ranking")
        .iter()
        .map(|entry| as_f64(entry, "value"))
        .collect();
    assert!(
        values.windows(2).all(|pair| pair[0] <= pair[1]),
        "fewest goals conceded should come first: {values:?}"
    );
}

#[test]
fn scenario_find_team_resolves_and_disambiguates_names() {
    given_the_knowledge_graph_is_loaded();

    let unique = when_i_call("find_team", json!({ "query": "sao paulo" }));
    assert_eq!(as_str(&unique.data, "status"), "unique");
    assert_eq!(as_str(&unique.data, "candidates.0.key"), "sao_paulo-SP");

    let ambiguous = when_i_call("find_team", json!({ "query": "América" }));
    assert_eq!(as_str(&ambiguous.data, "status"), "ambiguous");
    let keys: Vec<&str> = as_array(&ambiguous.data, "candidates")
        .iter()
        .map(|entry| as_str(entry, "key"))
        .collect();
    assert!(keys.contains(&"america-MG") && keys.contains(&"america-RN"));
}
