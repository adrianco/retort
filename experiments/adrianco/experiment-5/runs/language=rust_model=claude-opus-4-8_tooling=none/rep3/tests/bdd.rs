//! ============================================================================
//! Test suite: bdd
//! Project: Brazilian Soccer MCP Server (Rust)
//!
//! Context:
//!   Behaviour-Driven-Development tests written in explicit Given/When/Then
//!   structure, mirroring the Gherkin scenarios in the specification's "Testing
//!   Approach" section. They run against a small, deterministic in-memory
//!   fixture (`fixture_store`) so assertions are exact and fast, plus a handful
//!   of scenarios that load the real CSVs from `data/kaggle` when present to
//!   prove the full pipeline (loaders + queries + MCP dispatch) works on the
//!   provided data and meets the "answer 20+ questions" success criterion.
//!
//!   Each test name encodes the feature and scenario; comments label the G/W/T
//!   phases so the intent is readable as living documentation.
//! ============================================================================

use brazilian_soccer_mcp::model::{Competition, Match, Player};
use brazilian_soccer_mcp::store::{Store, Venue};
use serde_json::json;
use std::path::Path;

// ---- Fixtures --------------------------------------------------------------

fn m(
    comp: Competition,
    date: &str,
    home: &str,
    away: &str,
    hg: i32,
    ag: i32,
    season: i32,
) -> Match {
    use brazilian_soccer_mcp::normalize::normalize_team;
    Match {
        competition: comp,
        date: date.to_string(),
        home_team: normalize_team(home),
        away_team: normalize_team(away),
        home_team_raw: home.to_string(),
        away_team_raw: away.to_string(),
        home_goal: hg,
        away_goal: ag,
        season: Some(season),
        round: None,
        source: "fixture",
    }
}

fn player(id: i64, name: &str, nat: &str, overall: i32, club: &str, pos: &str) -> Player {
    Player {
        id,
        name: name.to_string(),
        age: Some(27),
        nationality: nat.to_string(),
        overall,
        potential: overall,
        club: club.to_string(),
        position: pos.to_string(),
        jersey_number: Some(10),
        height: "5'9".into(),
        weight: "150lbs".into(),
    }
}

/// A deterministic fixture covering the cases the scenarios assert on.
fn fixture_store() -> Store {
    let matches = vec![
        // Fla-Flu derby, three meetings.
        m(Competition::Brasileirao, "2023-09-03", "Flamengo-RJ", "Fluminense-RJ", 2, 1, 2023),
        m(Competition::Brasileirao, "2023-05-28", "Fluminense-RJ", "Flamengo-RJ", 1, 0, 2023),
        m(Competition::CopaDoBrasil, "2022-07-10", "Flamengo", "Fluminense", 3, 3, 2022),
        // Palmeiras matches in 2023.
        m(Competition::Brasileirao, "2023-04-16", "Palmeiras-SP", "Santos-SP", 4, 0, 2023),
        m(Competition::Brasileirao, "2023-08-20", "Grêmio-RS", "Palmeiras-SP", 1, 2, 2023),
        // A simple two-team league season (2019) for standings.
        m(Competition::Brasileirao, "2019-01-01", "Flamengo-RJ", "Santos-SP", 3, 0, 2019),
        m(Competition::Brasileirao, "2019-06-01", "Santos-SP", "Flamengo-RJ", 1, 1, 2019),
        // A Libertadores blowout for biggest_wins.
        m(Competition::Libertadores, "2012-05-27", "Santos-SP", "Bolivar", 8, 0, 2012),
    ];
    let players = vec![
        player(1, "Neymar Jr", "Brazil", 92, "Paris Saint-Germain", "LW"),
        player(2, "Gabriel Barbosa", "Brazil", 83, "Flamengo", "ST"),
        player(3, "Bruno Henrique", "Brazil", 80, "Flamengo", "LW"),
        player(4, "L. Messi", "Argentina", 94, "FC Barcelona", "RF"),
        player(5, "Dudu", "Brazil", 79, "Palmeiras", "RM"),
    ];
    Store::new(matches, players)
}

/// Real-data store, or None if the CSVs are not present.
fn real_store() -> Option<Store> {
    let dir = Path::new("data/kaggle");
    if dir.join("Brasileirao_Matches.csv").exists() {
        Store::load_from_dir(dir).ok()
    } else {
        None
    }
}

// ===========================================================================
// Feature: Match Queries
// ===========================================================================

#[test]
fn scenario_find_matches_between_two_teams() {
    // Given the match data is loaded
    let store = fixture_store();
    // When I search for matches between "Flamengo" and "Fluminense"
    let result = store.search_matches(Some("Flamengo"), Some("Fluminense"), None, None, None, None, 0);
    // Then I should receive a list of matches
    assert_eq!(result.len(), 3, "expected the three derby meetings");
    // And each match should have a date, scores and a competition
    for game in &result {
        assert!(!game.date.is_empty());
        assert!(game.home_goal >= 0 && game.away_goal >= 0);
        let _ = game.competition.label();
    }
    // And results are sorted newest first
    assert_eq!(result[0].date, "2023-09-03");
}

#[test]
fn scenario_filter_matches_by_team_and_season() {
    // Given the match data is loaded
    let store = fixture_store();
    // When I ask what matches Palmeiras played in 2023
    let result = store.search_matches(Some("Palmeiras"), None, None, Some(2023), None, None, 0);
    // Then both 2023 Palmeiras matches are returned (home and away)
    assert_eq!(result.len(), 2);
    assert!(result.iter().all(|g| g.season == Some(2023)));
}

#[test]
fn scenario_filter_matches_by_competition() {
    // Given the match data is loaded
    let store = fixture_store();
    // When I search Libertadores matches
    let result = store.search_matches(None, None, Some("Libertadores"), None, None, None, 0);
    // Then only Libertadores matches come back
    assert!(!result.is_empty());
    assert!(result.iter().all(|g| g.competition == Competition::Libertadores));
}

#[test]
fn scenario_filter_matches_by_date_range() {
    // Given the match data is loaded
    let store = fixture_store();
    // When I bound the search to the 2023 first half
    let result =
        store.search_matches(None, None, None, None, Some("2023-01-01"), Some("2023-06-30"), 0);
    // Then only matches inside that window are returned
    assert!(result.iter().all(|g| g.date.as_str() >= "2023-01-01" && g.date.as_str() <= "2023-06-30"));
    assert!(result.iter().any(|g| g.date == "2023-05-28"));
}

// ===========================================================================
// Feature: Team Queries
// ===========================================================================

#[test]
fn scenario_head_to_head_record() {
    // Given the match data is loaded
    let store = fixture_store();
    // When I request the head-to-head between Flamengo and Fluminense
    let h = store.head_to_head("Flamengo", "Fluminense");
    // Then totals add up and goals are attributed to the right side
    assert_eq!(h.total, 3);
    assert_eq!(h.team_a_wins + h.team_b_wins + h.draws, 3);
    // Flamengo won 2-1 and 0-1(loss) and drew 3-3 => 1 win, 1 loss, 1 draw
    assert_eq!(h.team_a_wins, 1);
    assert_eq!(h.team_b_wins, 1);
    assert_eq!(h.draws, 1);
    // Flamengo goals: 2 + 0 + 3 = 5 ; Fluminense: 1 + 1 + 3 = 5
    assert_eq!(h.team_a_goals, 5);
    assert_eq!(h.team_b_goals, 5);
}

#[test]
fn scenario_team_home_record_for_season() {
    // Given the match data is loaded
    let store = fixture_store();
    // When I request Palmeiras' home record in 2023 Brasileirão
    let rec = store.team_stats("Palmeiras", Some(2023), Some("Brasileirão"), Venue::Home);
    // Then only the home win over Santos counts
    assert_eq!(rec.matches, 1);
    assert_eq!(rec.wins, 1);
    assert_eq!(rec.goals_for, 4);
    assert_eq!(rec.goals_against, 0);
    assert_eq!(rec.points, 3);
}

#[test]
fn scenario_team_overall_record_handles_name_suffix() {
    // Given the match data is loaded (teams stored with "-SP"/"-RJ" suffixes)
    let store = fixture_store();
    // When I query "Flamengo" without any suffix
    let rec = store.team_stats("Flamengo", None, None, Venue::Any);
    // Then suffix-variant names still match and are aggregated
    assert!(rec.matches >= 4);
}

// ===========================================================================
// Feature: Player Queries
// ===========================================================================

#[test]
fn scenario_find_brazilian_players() {
    // Given the player data is loaded
    let store = fixture_store();
    // When I filter by nationality Brazil
    let result = store.search_players(None, Some("Brazil"), None, None, None, 0);
    // Then only Brazilian players are returned, sorted by rating
    assert!(result.iter().all(|p| p.nationality == "Brazil"));
    assert_eq!(result.first().unwrap().name, "Neymar Jr");
}

#[test]
fn scenario_highest_rated_players_at_a_club() {
    // Given the player data is loaded
    let store = fixture_store();
    // When I ask for Flamengo players
    let result = store.search_players(None, None, Some("Flamengo"), None, None, 0);
    // Then both Flamengo players appear, top rated first
    assert_eq!(result.len(), 2);
    assert_eq!(result[0].name, "Gabriel Barbosa");
}

#[test]
fn scenario_search_player_by_name() {
    // Given the player data is loaded
    let store = fixture_store();
    // When I search for "Gabriel"
    let result = store.search_players(Some("Gabriel"), None, None, None, None, 0);
    // Then Gabriel Barbosa is found
    assert_eq!(result.len(), 1);
    assert_eq!(result[0].name, "Gabriel Barbosa");
}

#[test]
fn scenario_filter_players_by_position_and_rating() {
    // Given the player data is loaded
    let store = fixture_store();
    // When I ask for left-wingers rated at least 81
    let result = store.search_players(None, None, None, Some("LW"), Some(81), 0);
    // Then only Neymar (92, LW) qualifies (Bruno Henrique is 80)
    assert_eq!(result.len(), 1);
    assert_eq!(result[0].name, "Neymar Jr");
}

// ===========================================================================
// Feature: Competition Queries
// ===========================================================================

#[test]
fn scenario_compute_standings_from_matches() {
    // Given the match data is loaded
    let store = fixture_store();
    // When I compute the 2019 Brasileirão standings
    let table = store.standings(Some("Brasileirão"), 2019);
    // Then Flamengo (1W 1D = 4pts) leads Santos (1D 1L = 1pt)
    assert_eq!(table.len(), 2);
    assert!(table[0].team.to_lowercase().contains("flamengo"));
    assert_eq!(table[0].points, 4);
    assert_eq!(table[1].points, 1);
}

// ===========================================================================
// Feature: Statistical Analysis
// ===========================================================================

#[test]
fn scenario_biggest_wins() {
    // Given the match data is loaded
    let store = fixture_store();
    // When I ask for the biggest victories
    let result = store.biggest_wins(None, None, 3);
    // Then the 8-0 Santos win is first
    assert_eq!(result[0].home_goal - result[0].away_goal, 8);
}

#[test]
fn scenario_average_goals_and_home_win_rate() {
    // Given the match data is loaded
    let store = fixture_store();
    // When I compute aggregate goal stats over all matches
    let g = store.average_goals(None, None);
    // Then counts are consistent
    assert_eq!(g.matches, 8);
    assert_eq!(g.home_wins + g.away_wins + g.draws, 8);
    assert!(g.avg_goals_per_match > 0.0);
}

#[test]
fn scenario_data_summary_counts_sources() {
    // Given the match and player data are loaded
    let store = fixture_store();
    // When I request a summary
    let s = store.summary();
    // Then totals match the fixture
    assert_eq!(s.total_matches, 8);
    assert_eq!(s.total_players, 5);
}

// ===========================================================================
// Feature: MCP tool dispatch (protocol surface)
// ===========================================================================

#[test]
fn scenario_mcp_dispatch_search_matches() {
    use brazilian_soccer_mcp::mcp::dispatch_tool;
    // Given the data is loaded into a store
    let store = fixture_store();
    // When the MCP "search_matches" tool is called for the derby
    let text = dispatch_tool(&store, "search_matches", &json!({"team": "Flamengo", "opponent": "Fluminense"})).unwrap();
    // Then the rendered answer mentions both clubs and is non-empty
    assert!(text.contains("Flamengo"));
    assert!(text.contains("Fluminense"));
}

#[test]
fn scenario_mcp_dispatch_unknown_tool_errors() {
    use brazilian_soccer_mcp::mcp::dispatch_tool;
    // Given a store
    let store = fixture_store();
    // When an unknown tool is dispatched
    let res = dispatch_tool(&store, "no_such_tool", &json!({}));
    // Then an error is returned
    assert!(res.is_err());
}

#[test]
fn scenario_mcp_tool_catalogue_lists_all_tools() {
    use brazilian_soccer_mcp::mcp::tool_catalogue;
    // Given the catalogue
    let cat = tool_catalogue();
    // Then it exposes the eight query tools
    let names: Vec<&str> = cat
        .as_array()
        .unwrap()
        .iter()
        .map(|t| t["name"].as_str().unwrap())
        .collect();
    for expected in [
        "search_matches",
        "head_to_head",
        "team_stats",
        "search_players",
        "standings",
        "biggest_wins",
        "average_goals",
        "data_summary",
    ] {
        assert!(names.contains(&expected), "missing tool {expected}");
    }
}

#[test]
fn scenario_mcp_initialize_handshake() {
    use brazilian_soccer_mcp::mcp::handle_request;
    // Given a store and an initialize request
    let store = fixture_store();
    let req = json!({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}});
    // When handled
    let resp = handle_request(&store, &req).unwrap();
    // Then it reports server info and capabilities
    assert_eq!(resp["result"]["serverInfo"]["name"], "brazilian-soccer-mcp");
    assert!(resp["result"]["capabilities"]["tools"].is_object());
}

#[test]
fn scenario_mcp_notification_has_no_response() {
    use brazilian_soccer_mcp::mcp::handle_request;
    // Given an initialized notification (no id)
    let store = fixture_store();
    let req = json!({"jsonrpc": "2.0", "method": "notifications/initialized"});
    // When handled, there is no response
    assert!(handle_request(&store, &req).is_none());
}

// ===========================================================================
// Feature: Real dataset smoke tests (skipped if CSVs absent)
// ===========================================================================

#[test]
fn scenario_real_data_loads_all_files() {
    let Some(store) = real_store() else { return };
    // Then a substantial number of matches and players are loaded (the figure
    // is below the raw ~23.8k row total because cross-source duplicate fixtures
    // are collapsed during loading).
    let s = store.summary();
    assert!(s.total_matches > 15_000, "got {}", s.total_matches);
    assert!(s.total_players > 17_000, "got {}", s.total_players);
    // And all five match sources are represented
    assert_eq!(s.matches_by_source.len(), 5);
}

#[test]
fn scenario_real_data_neymar_lookup() {
    let Some(store) = real_store() else { return };
    // When searching for Neymar among Brazilians
    let result = store.search_players(Some("Neymar"), Some("Brazil"), None, None, None, 5);
    // Then at least one high-rated result is returned
    assert!(!result.is_empty());
    assert!(result[0].overall >= 85);
}

#[test]
fn scenario_real_data_flamengo_has_matches() {
    let Some(store) = real_store() else { return };
    // When querying Flamengo's overall record
    let rec = store.team_stats("Flamengo", None, None, Venue::Any);
    // Then it has played many matches across the datasets
    assert!(rec.matches > 50, "got {}", rec.matches);
}

#[test]
fn scenario_real_data_standings_have_twenty_teams() {
    let Some(store) = real_store() else { return };
    // When computing the 2019 Brasileirão season
    let table = store.standings(Some("Brasileirão"), 2019);
    // Then exactly the 20 top-flight clubs are produced (no double-counting and
    // no state-suffix conflation of Atlético-MG with Atlético-PR)...
    assert_eq!(table.len(), 20, "expected a 20-team table");
    // ...sorted by points...
    assert!(table[0].points >= table[table.len() - 1].points);
    // ...with Flamengo the champion on 90 points (matches the spec example).
    assert!(table[0].team.to_lowercase().contains("flamengo"));
    assert_eq!(table[0].points, 90);
    assert_eq!((table[0].wins, table[0].draws, table[0].losses), (28, 6, 4));
}
