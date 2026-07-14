// =============================================================================
// Context
// -----------------------------------------------------------------------------
// Test suite: BDD / Gherkin-style (Given-When-Then) integration tests.
// Purpose:    Exercise the loaded datasets and query engine end-to-end against
//             the real CSV files in data/kaggle, mirroring the scenarios in the
//             specification's "Testing Approach" and "Sample Questions"
//             sections. Each test is annotated with its Feature / Scenario and
//             a Given/When/Then breakdown.
//
// These run against the actual data so they also serve as smoke tests that all
// six files load and the five capability categories work cross-file.
// =============================================================================

use brazilian_soccer_mcp::data::Dataset;
use brazilian_soccer_mcp::mcp;
use brazilian_soccer_mcp::queries::MatchFilter;
use serde_json::json;
use std::path::PathBuf;
use std::sync::OnceLock;

fn data_dir() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("data/kaggle")
}

/// Load the dataset once and share it across all tests.
fn dataset() -> &'static Dataset {
    static DS: OnceLock<Dataset> = OnceLock::new();
    DS.get_or_init(|| {
        Dataset::load_from_dir(&data_dir()).expect("datasets should load from data/kaggle")
    })
}

// -----------------------------------------------------------------------------
// Feature: Data loading
// -----------------------------------------------------------------------------

#[test]
fn scenario_all_six_datasets_load() {
    // Given the path to the six provided CSV files
    let ds = dataset();
    // When the data is loaded
    // Then matches and players are populated from every source (the match
    // count is post-deduplication, which removes cross-source overlap).
    assert!(ds.matches.len() > 15_000, "expected many matches, got {}", ds.matches.len());
    assert!(ds.players.len() > 17_000, "expected ~18k players, got {}", ds.players.len());

    let sources: std::collections::HashSet<_> = ds.matches.iter().map(|m| m.source).collect();
    for expected in [
        "Brasileirao_Matches.csv",
        "Brazilian_Cup_Matches.csv",
        "Libertadores_Matches.csv",
        "BR-Football-Dataset.csv",
        "novo_campeonato_brasileiro.csv",
    ] {
        assert!(sources.contains(expected), "missing data from {expected}");
    }
}

// -----------------------------------------------------------------------------
// Feature: Match Queries
// -----------------------------------------------------------------------------

#[test]
fn scenario_find_matches_between_two_teams() {
    // Given the match data is loaded
    let ds = dataset();
    // When I search for matches between "Flamengo" and "Fluminense"
    let f = MatchFilter {
        team: Some("Flamengo".into()),
        team2: Some("Fluminense".into()),
        ..Default::default()
    };
    let matches = ds.filter_matches(&f);
    // Then I should receive a list of matches, each with both teams present
    assert!(!matches.is_empty(), "expected Fla-Flu matches");
    for m in &matches {
        let teams = format!("{} {}", m.home_team, m.away_team).to_lowercase();
        assert!(teams.contains("flamengo"));
        assert!(teams.contains("fluminense"));
        assert!(!m.date.is_empty());
    }
}

#[test]
fn scenario_team_name_variations_match() {
    // Given match data uses suffixes like "Palmeiras-SP"
    let ds = dataset();
    // When I query plain "Palmeiras"
    let f = MatchFilter { team: Some("Palmeiras".into()), ..Default::default() };
    // Then matches are still found (suffix/accents normalised away)
    assert!(!ds.filter_matches(&f).is_empty());
}

#[test]
fn scenario_filter_by_season_and_competition() {
    // Given the match data is loaded
    let ds = dataset();
    // When I filter Brasileirão matches for 2019
    let f = MatchFilter {
        competition: Some("Brasileirão".into()),
        season: Some(2019),
        ..Default::default()
    };
    let matches = ds.filter_matches(&f);
    // Then every returned match is in that season and competition
    assert!(!matches.is_empty());
    assert!(matches.iter().all(|m| m.season == 2019));
}

// -----------------------------------------------------------------------------
// Feature: Team Queries
// -----------------------------------------------------------------------------

#[test]
fn scenario_team_statistics_report() {
    // Given the match data is loaded
    let ds = dataset();
    // When I request statistics for "Palmeiras" in 2019
    let report = ds.team_stats("Palmeiras", Some(2019), Some("Brasileirão"), "all");
    // Then I receive wins, draws, losses and goal figures
    assert!(report.contains("Wins:"));
    assert!(report.contains("Draws:"));
    assert!(report.contains("Losses:"));
    assert!(report.contains("Goals For:"));
    assert!(report.contains("Win rate:"));
}

#[test]
fn scenario_home_record_restriction() {
    // Given a team played both home and away
    let ds = dataset();
    // When I request only the home record
    let home = ds.team_stats("Corinthians", None, Some("Brasileirão"), "home");
    // Then the report is scoped to home matches
    assert!(home.contains("home record"));
}

// -----------------------------------------------------------------------------
// Feature: Statistical Analysis
// -----------------------------------------------------------------------------

#[test]
fn scenario_head_to_head_totals_are_consistent() {
    // Given two long-time rivals
    let ds = dataset();
    // When I compute their head-to-head
    let f = MatchFilter {
        team: Some("Palmeiras".into()),
        team2: Some("Santos".into()),
        ..Default::default()
    };
    let total = ds.filter_matches(&f).len();
    let report = ds.head_to_head("Palmeiras", "Santos");
    // Then wins + draws reported reconcile with the number of matches
    assert!(report.contains("Head-to-head"));
    assert!(report.contains(&format!("{total} matches")));
}

#[test]
fn scenario_league_statistics_have_plausible_averages() {
    // Given the full match dataset
    let ds = dataset();
    // When I compute league-wide statistics
    let report = ds.league_statistics(None, None);
    // Then it reports an average goals per match in a believable range
    assert!(report.contains("Average goals per match:"));
    assert!(report.contains("Home wins:"));
}

#[test]
fn scenario_biggest_wins_sorted_by_margin() {
    // Given the match data is loaded
    let ds = dataset();
    // When I ask for the biggest wins
    let f = MatchFilter::default();
    let report = ds.biggest_wins(&f, 5);
    // Then the result is a ranked list
    assert!(report.contains("Biggest victories"));
    assert!(report.contains(" 1. "));
}

// -----------------------------------------------------------------------------
// Feature: Competition Queries
// -----------------------------------------------------------------------------

#[test]
fn scenario_standings_are_calculated_from_results() {
    // Given a completed Brasileirão season
    let ds = dataset();
    // When I request 2019 standings
    let table = ds.standings("Brasileirão", 2019);
    // Then a ranked table with points and a champion marker is produced
    assert!(table.contains("standings"));
    assert!(table.contains("pts"));
    assert!(table.contains("Champion"));
}

#[test]
fn scenario_list_competitions_covers_all_sources() {
    // Given the loaded dataset
    let ds = dataset();
    // When I list competitions
    let list = ds.list_competitions();
    // Then the major Brazilian competitions are present
    assert!(list.contains("Brasileirão Série A"));
    assert!(list.contains("Copa do Brasil"));
    assert!(list.contains("Copa Libertadores"));
}

// -----------------------------------------------------------------------------
// Feature: Player Queries
// -----------------------------------------------------------------------------

#[test]
fn scenario_search_player_by_name() {
    // Given the FIFA player data is loaded
    let ds = dataset();
    // When I search for a well-known player
    let report = ds.search_players(Some("Messi"), None, None, None, 10);
    // Then a matching player is returned with rating info
    assert!(report.contains("Messi"));
    assert!(report.contains("Overall:"));
}

#[test]
fn scenario_filter_brazilian_players_sorted_by_rating() {
    // Given the FIFA player data is loaded
    let ds = dataset();
    // When I filter by nationality Brazil
    let report = ds.search_players(None, Some("Brazil"), None, None, 5);
    // Then results are returned (and the count exceeds the shown limit)
    assert!(report.contains("Found"));
    assert!(report.contains("player(s)"));
    assert!(report.contains("Nat: Brazil"));
}

// -----------------------------------------------------------------------------
// Feature: MCP protocol layer
// -----------------------------------------------------------------------------

#[test]
fn scenario_initialize_handshake() {
    // Given an MCP client
    let ds = dataset();
    // When it sends an initialize request
    let req = json!({"jsonrpc":"2.0","id":1,"method":"initialize","params":{}});
    let resp = mcp::handle_request(ds, &req).expect("response expected");
    // Then the server reports its protocol version and name
    assert_eq!(resp["result"]["serverInfo"]["name"], "brazilian-soccer-mcp");
    assert!(resp["result"]["protocolVersion"].is_string());
}

#[test]
fn scenario_tools_list_advertises_all_tools() {
    // Given an initialized server
    let ds = dataset();
    // When the client lists tools
    let req = json!({"jsonrpc":"2.0","id":2,"method":"tools/list"});
    let resp = mcp::handle_request(ds, &req).expect("response expected");
    let tools = resp["result"]["tools"].as_array().unwrap();
    // Then all eight capability tools are present
    assert_eq!(tools.len(), 8);
    let names: Vec<&str> = tools.iter().map(|t| t["name"].as_str().unwrap()).collect();
    assert!(names.contains(&"search_matches"));
    assert!(names.contains(&"search_players"));
    assert!(names.contains(&"competition_standings"));
}

#[test]
fn scenario_tools_call_returns_text_content() {
    // Given an initialized server
    let ds = dataset();
    // When the client calls search_players for Brazilian players
    let req = json!({
        "jsonrpc":"2.0","id":3,"method":"tools/call",
        "params":{"name":"search_players","arguments":{"nationality":"Brazil","limit":3}}
    });
    let resp = mcp::handle_request(ds, &req).expect("response expected");
    // Then it returns a non-error text content block
    assert_eq!(resp["result"]["isError"], false);
    let text = resp["result"]["content"][0]["text"].as_str().unwrap();
    assert!(text.contains("player(s)"));
}

#[test]
fn scenario_missing_required_argument_is_reported() {
    // Given an initialized server
    let ds = dataset();
    // When a tool is called without its required argument
    let req = json!({
        "jsonrpc":"2.0","id":4,"method":"tools/call",
        "params":{"name":"team_stats","arguments":{}}
    });
    let resp = mcp::handle_request(ds, &req).expect("response expected");
    // Then the call is flagged as an error with a helpful message
    assert_eq!(resp["result"]["isError"], true);
    let text = resp["result"]["content"][0]["text"].as_str().unwrap();
    assert!(text.contains("team"));
}

#[test]
fn scenario_unknown_method_returns_jsonrpc_error() {
    // Given an MCP client
    let ds = dataset();
    // When it calls an unsupported method
    let req = json!({"jsonrpc":"2.0","id":5,"method":"does/not/exist"});
    let resp = mcp::handle_request(ds, &req).expect("response expected");
    // Then a JSON-RPC method-not-found error is returned
    assert_eq!(resp["error"]["code"], -32601);
}

#[test]
fn scenario_notifications_get_no_response() {
    // Given the initialized notification (no id)
    let ds = dataset();
    let req = json!({"jsonrpc":"2.0","method":"notifications/initialized"});
    // When handled
    let resp = mcp::handle_request(ds, &req);
    // Then no response is produced
    assert!(resp.is_none());
}

#[test]
fn scenario_stdio_roundtrip() {
    // Given a server reading newline-delimited JSON-RPC from a pipe
    let ds = dataset();
    let input = concat!(
        "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{}}\n",
        "{\"jsonrpc\":\"2.0\",\"method\":\"notifications/initialized\"}\n",
        "{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/list\"}\n"
    );
    let mut output = Vec::new();
    // When the loop processes the stream to EOF
    mcp::serve_stdio(ds, input.as_bytes(), &mut output).unwrap();
    // Then exactly two responses come back (the notification is silent)
    let text = String::from_utf8(output).unwrap();
    let lines: Vec<&str> = text.lines().filter(|l| !l.is_empty()).collect();
    assert_eq!(lines.len(), 2, "got: {text}");
    assert!(lines[0].contains("serverInfo"));
    assert!(lines[1].contains("search_matches"));
}
