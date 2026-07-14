//! BDD-style behaviour tests for the Brazilian Soccer MCP server.
//!
//! Each test reads as Given / When / Then. They load the real datasets from
//! `data/kaggle` (override with `SOCCER_DATA_DIR`).

use brazilian_soccer_mcp::data::Dataset;
use brazilian_soccer_mcp::mcp;
use brazilian_soccer_mcp::queries::{self, MatchQuery, PlayerQuery, Venue};
use serde_json::{json, Value};

fn dataset() -> Dataset {
    Dataset::load_default().expect("datasets should load from data/kaggle")
}

// --- Feature: data loading -------------------------------------------------

#[test]
fn given_all_csv_files_when_loaded_then_matches_and_players_are_available() {
    let ds = dataset();
    // All six CSV files contribute rows.
    assert_eq!(ds.source_counts.len(), 6, "all six datasets reported");
    for (label, count) in &ds.source_counts {
        assert!(*count > 0, "{label} should contribute rows");
    }
    assert!(ds.matches.len() > 15_000, "thousands of unique matches");
    assert_eq!(ds.players.len(), 18_207, "all FIFA players loaded");
}

// --- Feature: match queries ------------------------------------------------

#[test]
fn given_match_data_when_searching_between_two_teams_then_matches_with_head_to_head() {
    let ds = dataset();
    let answer = queries::search_matches(
        &ds,
        &MatchQuery {
            team: Some("Flamengo"),
            team2: Some("Fluminense"),
            ..Default::default()
        },
    );
    assert!(answer.contains("Flamengo"));
    assert!(answer.contains("Fluminense"));
    assert!(answer.contains("Head-to-head"), "includes a H2H summary");
    // Each listed match carries a date and a score.
    assert!(answer.contains('-'));
}

#[test]
fn given_match_data_when_filtering_by_season_then_only_that_season() {
    let ds = dataset();
    let matches = ds
        .matches
        .iter()
        .filter(|m| m.involves(&brazilian_soccer_mcp::normalize::canon("Palmeiras").key))
        .filter(|m| m.season == Some(2019))
        .count();
    assert!(matches > 0, "Palmeiras played in 2019");
}

#[test]
fn given_team_name_variants_when_searching_then_they_are_normalized() {
    let ds = dataset();
    // "São Paulo" and "Sao Paulo-SP" must resolve to the same club.
    let a = queries::team_stats(&ds, "São Paulo", Some(2019), Some("Brasileirão"), Venue::All);
    let b = queries::team_stats(&ds, "Sao Paulo", Some(2019), Some("Brasileirão"), Venue::All);
    assert_eq!(a, b, "accented and plain names give the same record");
    assert!(a.contains("Matches: 38"), "a full Serie A season");
}

#[test]
fn given_distinct_clubs_sharing_a_name_when_querying_then_kept_separate() {
    use brazilian_soccer_mcp::normalize::canon;
    // Atlético Mineiro (MG) and Athletico Paranaense (PR) must not merge.
    assert_ne!(canon("Atletico-MG").key, canon("Athletico-PR").key);
}

// --- Feature: team statistics ----------------------------------------------

#[test]
fn given_match_data_when_requesting_team_stats_then_wins_losses_draws_and_goals() {
    let ds = dataset();
    let answer = queries::team_stats(&ds, "Palmeiras", Some(2019), None, Venue::All);
    for needle in ["Wins:", "Draws:", "Losses:", "Goals For:", "Win rate:"] {
        assert!(answer.contains(needle), "stats include {needle}");
    }
}

#[test]
fn given_venue_filter_when_requesting_home_record_then_only_home_matches() {
    let ds = dataset();
    let answer = queries::team_stats(&ds, "Corinthians", Some(2022), None, Venue::Home);
    assert!(answer.contains("home record"));
}

// --- Feature: competition standings ----------------------------------------

#[test]
fn given_2019_season_when_computing_standings_then_flamengo_is_champion_with_90_points() {
    let ds = dataset();
    let table = queries::standings(&ds, 2019, Some("Brasileirão"));
    // The 2019 Brasileirão was won by Flamengo with 90 points — a strong
    // correctness check against reality and the spec example.
    let first_line = table.lines().nth(1).unwrap_or("");
    assert!(first_line.contains("Flamengo"), "Flamengo tops the table");
    assert!(first_line.contains("90 pts"), "with 90 points");
    assert!(first_line.contains("Champion"));
    assert!(table.contains("calculated from 380 matches"), "a 20-team season");
}

// --- Feature: aggregate statistics -----------------------------------------

#[test]
fn given_competition_when_computing_stats_then_averages_and_biggest_wins() {
    let ds = dataset();
    let answer = queries::competition_stats(&ds, Some("Brasileirão"), None);
    assert!(answer.contains("Average goals per match"));
    assert!(answer.contains("Home wins"));
    assert!(answer.contains("Biggest victories"));
    assert!(answer.contains("Top scoring teams"));
}

// --- Feature: player queries -----------------------------------------------

#[test]
fn given_player_data_when_searching_by_name_then_the_player_is_found() {
    let ds = dataset();
    let answer = queries::search_players(
        &ds,
        &PlayerQuery {
            name: Some("Neymar"),
            ..Default::default()
        },
    );
    assert!(answer.contains("Neymar"));
    assert!(answer.contains("Overall: 92"));
}

#[test]
fn given_player_data_when_filtering_brazilians_then_many_results() {
    let ds = dataset();
    let answer = queries::search_players(
        &ds,
        &PlayerQuery {
            nationality: Some("Brazil"),
            ..Default::default()
        },
    );
    assert!(answer.contains("827 found"), "all Brazilian players");
}

#[test]
fn given_top_players_for_brazil_then_neymar_leads_and_club_breakdown_present() {
    let ds = dataset();
    let answer = queries::top_players(&ds, Some("Brazil"), None, None, 5);
    assert!(answer.lines().nth(1).unwrap_or("").contains("Neymar"));
    assert!(answer.contains("players by club"));
}

#[test]
fn given_club_filter_when_searching_players_then_only_that_club() {
    let ds = dataset();
    // NB: the FIFA 19 dataset omits several big Brazilian clubs (Flamengo,
    // Palmeiras, Corinthians, São Paulo were unlicensed). Santos is present.
    let answer = queries::search_players(
        &ds,
        &PlayerQuery {
            club: Some("Santos"),
            ..Default::default()
        },
    );
    assert!(answer.contains("found"));
    assert!(!answer.contains("No players"));
}

// --- Feature: MCP protocol -------------------------------------------------

#[test]
fn given_mcp_initialize_when_handled_then_server_info_returned() {
    let ds = dataset();
    let req = json!({"jsonrpc":"2.0","id":1,"method":"initialize","params":{}});
    let resp = mcp::handle_request(&ds, &req).expect("initialize returns a response");
    assert_eq!(resp["result"]["serverInfo"]["name"], "brazilian-soccer-mcp");
    assert_eq!(resp["result"]["protocolVersion"], mcp::PROTOCOL_VERSION);
}

#[test]
fn given_tools_list_when_handled_then_all_tools_have_schemas() {
    let ds = dataset();
    let req = json!({"jsonrpc":"2.0","id":2,"method":"tools/list"});
    let resp = mcp::handle_request(&ds, &req).expect("tools/list returns a response");
    let tools = resp["result"]["tools"].as_array().expect("tools array");
    assert_eq!(tools.len(), 8, "eight tools exposed");
    for t in tools {
        assert!(t["name"].is_string());
        assert_eq!(t["inputSchema"]["type"], "object");
    }
}

#[test]
fn given_tools_call_when_invoked_then_text_content_returned() {
    let ds = dataset();
    let req = json!({
        "jsonrpc":"2.0","id":3,"method":"tools/call",
        "params":{"name":"head_to_head","arguments":{"team1":"Palmeiras","team2":"Santos"}}
    });
    let resp = mcp::handle_request(&ds, &req).expect("tools/call returns a response");
    let text = resp["result"]["content"][0]["text"].as_str().unwrap();
    assert!(text.contains("Head-to-head"));
    assert!(resp["result"].get("isError").is_none());
}

#[test]
fn given_notification_when_handled_then_no_response() {
    let ds = dataset();
    let req = json!({"jsonrpc":"2.0","method":"notifications/initialized"});
    assert!(mcp::handle_request(&ds, &req).is_none());
}

#[test]
fn given_unknown_method_when_handled_then_method_not_found_error() {
    let ds = dataset();
    let req = json!({"jsonrpc":"2.0","id":9,"method":"does/not/exist"});
    let resp = mcp::handle_request(&ds, &req).expect("a response for a request id");
    assert_eq!(resp["error"]["code"], -32601);
}

#[test]
fn given_missing_required_argument_when_calling_tool_then_iserror_true() {
    let ds = dataset();
    let req = json!({
        "jsonrpc":"2.0","id":4,"method":"tools/call",
        "params":{"name":"head_to_head","arguments":{"team1":"Flamengo"}}
    });
    let resp = mcp::handle_request(&ds, &req).unwrap();
    assert_eq!(resp["result"]["isError"], Value::Bool(true));
}

// --- Feature: at least 20 sample questions ---------------------------------

#[test]
fn twenty_sample_questions_all_produce_non_empty_answers() {
    let ds = dataset();
    let cases: Vec<(&str, Value)> = vec![
        ("search_matches", json!({"team":"Flamengo","team2":"Fluminense"})),
        ("search_matches", json!({"team":"Palmeiras","season":2019})),
        ("search_matches", json!({"competition":"Copa do Brasil"})),
        ("search_matches", json!({"team":"Flamengo","team2":"Corinthians","limit":1})),
        ("search_matches", json!({"competition":"Libertadores","season":2018})),
        ("team_stats", json!({"team":"Corinthians","season":2022,"venue":"home"})),
        ("team_stats", json!({"team":"Palmeiras","season":2019})),
        ("team_stats", json!({"team":"Santos","venue":"away"})),
        ("head_to_head", json!({"team1":"Palmeiras","team2":"Santos"})),
        ("head_to_head", json!({"team1":"Gremio","team2":"Internacional"})),
        ("standings", json!({"season":2019})),
        ("standings", json!({"season":2018})),
        ("standings", json!({"season":2020})),
        ("competition_stats", json!({"competition":"Brasileirão"})),
        ("competition_stats", json!({"competition":"Libertadores","season":2018})),
        ("search_players", json!({"name":"Coutinho"})),
        ("search_players", json!({"nationality":"Brazil"})),
        ("search_players", json!({"club":"Santos"})),
        ("search_players", json!({"position":"GK","min_overall":85})),
        ("top_players", json!({"nationality":"Brazil","limit":10})),
        ("list_datasets", json!({})),
    ];
    assert!(cases.len() >= 20);
    for (tool, args) in cases {
        let answer = mcp::dispatch_tool(&ds, tool, &args)
            .unwrap_or_else(|e| panic!("{tool} {args} failed: {e}"));
        assert!(!answer.trim().is_empty(), "{tool} produced an answer");
        assert!(
            !answer.starts_with("No matches found") && !answer.starts_with("No players"),
            "{tool} {args} should find data, got: {answer}"
        );
    }
}
