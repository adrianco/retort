// ============================================================================
// CONTEXT: BDD scenarios - Feature: Match Queries
//
// Gherkin shape mirrored in code: each test is one Scenario whose body is
// structured as GIVEN (load fixture) / WHEN (run query) / THEN (assertions).
//
// Covers TASK.md "Match Queries" and several Sample Questions:
//   - "Show me all Flamengo vs Fluminense matches"
//   - "What matches did Palmeiras play in 2023?"
//   - "When did Flamengo last play Corinthians?" (+ "What was the score?")
//   - competition / date-range filters, team-name normalization,
//     cross-file deduplication of Serie A 2012-2019 fixtures.
// ============================================================================

mod common;

use brazilian_soccer_mcp::queries::{search_matches, MatchFilters};

fn filters<'a>() -> MatchFilters<'a> {
    MatchFilters {
        team: None,
        opponent: None,
        competition: None,
        season: None,
        date_from: None,
        date_to: None,
        limit: 20,
    }
}

#[test]
fn scenario_find_matches_between_two_teams() {
    // GIVEN the match data is loaded
    let ds = common::given_loaded_dataset();

    // WHEN I search for matches between "Flamengo" and "Fluminense"
    let result = search_matches(
        ds,
        &MatchFilters { team: Some("Flamengo"), opponent: Some("Fluminense"), ..filters() },
    )
    .expect("query should succeed");

    // THEN I should receive a list of matches
    let total = result["total_matches_found"].as_u64().unwrap();
    assert!(total >= 10, "Fla-Flu derby should appear many times, got {}", total);

    // AND each match should have date, scores, and competition
    for m in result["matches"].as_array().unwrap() {
        assert!(m["date"].is_string(), "match should have a date: {}", m);
        assert!(m["score"].as_str().unwrap().contains('-'));
        assert!(m["competition"].is_string());
    }

    // AND a head-to-head summary is included
    let h2h = &result["head_to_head"];
    assert!(h2h["team1_wins"].is_u64() && h2h["team2_wins"].is_u64() && h2h["draws"].is_u64());
}

#[test]
fn scenario_matches_for_a_team_in_a_season() {
    // GIVEN the match data is loaded
    let ds = common::given_loaded_dataset();

    // WHEN I ask "What matches did Palmeiras play in 2023?"
    let result = search_matches(
        ds,
        &MatchFilters { team: Some("Palmeiras"), season: Some(2023), limit: 100, ..filters() },
    )
    .unwrap();

    // THEN matches are returned and all involve Palmeiras in 2023
    assert!(result["total_matches_found"].as_u64().unwrap() > 10);
    for m in result["matches"].as_array().unwrap() {
        let teams = format!("{}{}", m["home_team"], m["away_team"]).to_lowercase();
        assert!(teams.contains("palmeiras"), "match should involve Palmeiras: {}", m);
        assert!(m["date"].as_str().unwrap().starts_with("2023"));
    }
}

#[test]
fn scenario_filter_matches_by_competition() {
    // GIVEN the match data is loaded
    let ds = common::given_loaded_dataset();

    // WHEN I search Flamengo matches in the Copa do Brasil
    let result = search_matches(
        ds,
        &MatchFilters {
            team: Some("Flamengo"),
            competition: Some("Copa do Brasil"),
            limit: 100,
            ..filters()
        },
    )
    .unwrap();

    // THEN every returned match is a Copa do Brasil match
    let matches = result["matches"].as_array().unwrap();
    assert!(!matches.is_empty());
    for m in matches {
        assert_eq!(m["competition"], "Copa do Brasil");
    }
}

#[test]
fn scenario_filter_matches_by_date_range() {
    // GIVEN the match data is loaded
    let ds = common::given_loaded_dataset();

    // WHEN I search Flamengo matches between 2019-01-01 and 2019-12-31
    let result = search_matches(
        ds,
        &MatchFilters {
            team: Some("Flamengo"),
            date_from: Some("2019-01-01"),
            date_to: Some("2019-12-31"),
            limit: 100,
            ..filters()
        },
    )
    .unwrap();

    // THEN all matches fall inside the range
    let matches = result["matches"].as_array().unwrap();
    assert!(!matches.is_empty());
    for m in matches {
        let d = m["date"].as_str().unwrap();
        assert!(("2019-01-01"..="2019-12-31").contains(&d), "date out of range: {}", d);
    }
}

#[test]
fn scenario_most_recent_meeting_is_first() {
    // GIVEN the match data is loaded
    let ds = common::given_loaded_dataset();

    // WHEN I ask "When did Flamengo last play Corinthians?"
    let result = search_matches(
        ds,
        &MatchFilters { team: Some("Flamengo"), opponent: Some("Corinthians"), limit: 50, ..filters() },
    )
    .unwrap();

    // THEN the list is sorted with the most recent match first
    let matches = result["matches"].as_array().unwrap();
    assert!(matches.len() >= 2);
    let dates: Vec<&str> = matches.iter().map(|m| m["date"].as_str().unwrap()).collect();
    for w in dates.windows(2) {
        assert!(w[0] >= w[1], "dates should be descending: {} then {}", w[0], w[1]);
    }
    // AND "What was the score?" is answerable from the same record
    assert!(matches[0]["home_goals"].is_i64() || matches[0]["home_goals"].is_u64());
    assert!(matches[0]["away_goals"].is_i64() || matches[0]["away_goals"].is_u64());
}

#[test]
fn scenario_team_name_variations_are_normalized() {
    // GIVEN the match data is loaded
    let ds = common::given_loaded_dataset();

    // WHEN I search with two different spellings of the same club
    let a = search_matches(ds, &MatchFilters { team: Some("Atlético Mineiro"), ..filters() }).unwrap();
    let b = search_matches(ds, &MatchFilters { team: Some("Atletico-MG"), ..filters() }).unwrap();

    // THEN both spellings find the same set of matches
    assert!(a["total_matches_found"].as_u64().unwrap() > 100);
    assert_eq!(a["total_matches_found"], b["total_matches_found"]);

    // AND the suffix never bleeds into a different club (Atlético-GO)
    let go = search_matches(ds, &MatchFilters { team: Some("Atlético-GO"), ..filters() }).unwrap();
    assert_ne!(a["total_matches_found"], go["total_matches_found"]);
}

#[test]
fn scenario_duplicate_fixtures_across_files_are_deduplicated() {
    // GIVEN the match data is loaded (Serie A 2015 exists in 3 source files)
    let ds = common::given_loaded_dataset();

    // WHEN I search Serie A season 2015 with a high limit
    let result = search_matches(
        ds,
        &MatchFilters { competition: Some("Brasileirão"), season: Some(2015), limit: 100, ..filters() },
    )
    .unwrap();

    // THEN the deduplicated total is one full season (380 matches), not 2-3x that
    let total = result["total_matches_found"].as_u64().unwrap();
    assert!(
        (370..=385).contains(&total),
        "expected ~380 deduplicated 2015 Serie A matches, got {}",
        total
    );
}

#[test]
fn scenario_libertadores_data_is_queryable() {
    // GIVEN the match data is loaded
    let ds = common::given_loaded_dataset();

    // WHEN I search Libertadores matches for a Brazilian club
    let result = search_matches(
        ds,
        &MatchFilters { team: Some("Grêmio"), competition: Some("Libertadores"), limit: 50, ..filters() },
    )
    .unwrap();

    // THEN matches from the Libertadores dataset are returned
    let matches = result["matches"].as_array().unwrap();
    assert!(!matches.is_empty());
    for m in matches {
        assert_eq!(m["competition"], "Copa Libertadores");
    }
}
