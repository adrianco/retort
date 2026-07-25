//! Feature: Statistical analysis
//!
//! ```gherkin
//! Feature: Statistical Analysis
//!   Scenario: Average goals per match
//!     Given the match data is loaded
//!     When I request Brasileirão aggregate statistics
//!     Then I should get goals per match and a home/draw/away split
//!     And the percentages should add up to 100
//! ```

mod common;

use common::*;
use serde_json::json;

#[test]
fn scenario_average_goals_per_match_in_the_brasileirao() {
    // GIVEN the match data is loaded
    given_the_knowledge_graph_is_loaded();

    // WHEN I ask for competition-wide statistics
    let answer = when_i_call("competition_stats", json!({ "competition": "Serie A" }));

    // THEN goals per match is a plausible football number
    let goals_per_match = as_f64(&answer.data, "goals_per_match");
    assert!(
        (2.0..3.2).contains(&goals_per_match),
        "unexpected goals per match: {goals_per_match}"
    );

    // AND home/draw/away shares add up to 100%
    let total = as_f64(&answer.data, "home_win_pct")
        + as_f64(&answer.data, "draw_pct")
        + as_f64(&answer.data, "away_win_pct");
    assert!((total - 100.0).abs() < 0.5, "shares sum to {total}");

    // AND home advantage is visible
    assert!(as_f64(&answer.data, "home_win_pct") > as_f64(&answer.data, "away_win_pct"));

    // AND the totals equal the sum of the per-season rows
    let per_season: i64 = as_array(&answer.data, "seasons")
        .iter()
        .map(|season| as_i64(season, "matches"))
        .sum();
    assert_eq!(per_season, as_i64(&answer.data, "matches"));
    then_text_contains(&answer.text, "Goals:");
}

#[test]
fn scenario_compare_two_seasons() {
    given_the_knowledge_graph_is_loaded();

    // "Compare the 2018 and 2019 seasons"
    let answer = when_i_call(
        "competition_stats",
        json!({ "competition": "Serie A", "seasons": [2018, 2019] }),
    );
    let seasons = as_array(&answer.data, "seasons");
    assert_eq!(seasons.len(), 2);
    assert_eq!(as_i64(&seasons[0], "season"), 2018);
    assert_eq!(as_i64(&seasons[1], "season"), 2019);
    for season in seasons {
        assert_eq!(as_i64(season, "matches"), 380);
        assert_eq!(as_i64(season, "teams"), 20);
        assert_eq!(
            as_i64(season, "home_wins") + as_i64(season, "draws") + as_i64(season, "away_wins"),
            as_i64(season, "matches")
        );
    }
}

#[test]
fn scenario_biggest_wins_are_sorted_by_margin() {
    given_the_knowledge_graph_is_loaded();

    // "Show me the biggest wins in the dataset"
    let answer = when_i_call("biggest_wins", json!({ "limit": 10 }));
    let matches = as_array(&answer.data, "matches");
    assert_eq!(matches.len(), 10);
    let margins: Vec<i64> = matches
        .iter()
        .map(|entry| (as_i64(entry, "home_goals") - as_i64(entry, "away_goals")).abs())
        .collect();
    assert!(margins.windows(2).all(|pair| pair[0] >= pair[1]));
    assert!(margins[0] >= 6, "the record win should be a rout");
}

#[test]
fn scenario_biggest_wins_can_be_scoped_to_a_club() {
    given_the_knowledge_graph_is_loaded();

    let answer = when_i_call("biggest_wins", json!({ "team": "Flamengo", "limit": 5 }));
    for entry in as_array(&answer.data, "matches") {
        let (home, away) = (as_str(entry, "home_team"), as_str(entry, "away_team"));
        let (home_goals, away_goals) = (as_i64(entry, "home_goals"), as_i64(entry, "away_goals"));
        let flamengo_won = (home == "Flamengo" && home_goals > away_goals)
            || (away == "Flamengo" && away_goals > home_goals);
        assert!(flamengo_won, "only Flamengo wins should be listed: {entry}");
    }
}

#[test]
fn scenario_overlapping_source_files_are_not_double_counted() {
    given_the_knowledge_graph_is_loaded();

    // Série A 2019 appears in three files. The canonical view keeps 380
    // matches; asking for every source shows the raw overlap.
    let canonical = when_i_call(
        "competition_stats",
        json!({ "competition": "Serie A", "season": 2019 }),
    );
    assert_eq!(as_i64(&canonical.data, "matches"), 380);

    let all_sources = when_i_call(
        "competition_stats",
        json!({ "competition": "Serie A", "season": 2019, "include_all_sources": true }),
    );
    assert!(
        as_i64(&all_sources.data, "matches") > 1000,
        "three files each carry the 2019 season"
    );
    // The average is unaffected by the duplication, which is the point of the
    // canonical view: the same fixtures are simply counted three times.
    assert!(
        (as_f64(&canonical.data, "goals_per_match") - as_f64(&all_sources.data, "goals_per_match"))
            .abs()
            < 0.15
    );
}

#[test]
fn scenario_home_advantage_across_competitions() {
    given_the_knowledge_graph_is_loaded();

    for competition in ["Serie A", "Serie B", "Copa do Brasil", "Libertadores"] {
        let answer = when_i_call("competition_stats", json!({ "competition": competition }));
        let home = as_f64(&answer.data, "home_win_pct");
        let away = as_f64(&answer.data, "away_win_pct");
        assert!(
            home > away,
            "{competition}: home {home}% should beat away {away}%"
        );
        assert!(as_i64(&answer.data, "matches") > 500);
    }
}

#[test]
fn scenario_clean_sheet_ranking() {
    given_the_knowledge_graph_is_loaded();

    let answer = when_i_call(
        "team_rankings",
        json!({
            "metric": "clean_sheets",
            "competition": "Serie A",
            "min_matches": 200,
            "limit": 5
        }),
    );
    for entry in as_array(&answer.data, "ranking") {
        assert_eq!(
            as_f64(entry, "value") as i64,
            as_i64(entry, "record.clean_sheets")
        );
        assert!(as_i64(entry, "record.clean_sheets") <= as_i64(entry, "record.matches"));
    }
}

#[test]
fn scenario_unknown_metric_is_rejected() {
    given_the_knowledge_graph_is_loaded();

    let message = when_i_call_expecting_error("team_rankings", json!({ "metric": "vibes" }));
    then_text_contains(&message, "unknown metric");
}

#[test]
fn scenario_top_scorer_data_is_not_invented() {
    given_the_knowledge_graph_is_loaded();

    // The datasets have no goalscorer column; the overview must say so instead
    // of the server guessing.
    let answer = when_i_call("dataset_overview", json!({}));
    then_text_contains(&answer.text, "no goalscorer or lineup data");
}
