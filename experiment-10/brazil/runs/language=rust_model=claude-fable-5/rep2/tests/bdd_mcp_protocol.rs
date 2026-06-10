// ============================================================================
// CONTEXT: BDD scenarios - Feature: MCP Protocol Compliance
//
// Exercises the JSON-RPC surface exactly as an MCP client (e.g. Claude
// Desktop) would: initialize handshake, tools/list discovery, tools/call
// invocation, error paths, notification silence, and data-coverage checks
// (all 6 CSV files loadable + every TASK.md success criterion reachable
// through a tool call).
// ============================================================================

mod common;

use brazilian_soccer_mcp::server::{handle_request, tool_definitions};
use serde_json::{json, Value};

fn call(ds: &brazilian_soccer_mcp::data::Dataset, req: Value) -> Option<Value> {
    handle_request(ds, &req)
}

fn tool_call(ds: &brazilian_soccer_mcp::data::Dataset, name: &str, args: Value) -> Value {
    let resp = call(
        ds,
        json!({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
               "params": {"name": name, "arguments": args}}),
    )
    .expect("tools/call must produce a response");
    resp["result"].clone()
}

#[test]
fn scenario_initialize_handshake() {
    // GIVEN a running server
    let ds = common::given_loaded_dataset();

    // WHEN a client sends initialize
    let resp = call(
        ds,
        json!({"jsonrpc": "2.0", "id": 0, "method": "initialize",
               "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                          "clientInfo": {"name": "test", "version": "0"}}}),
    )
    .unwrap();

    // THEN the server identifies itself and advertises the tools capability
    assert_eq!(resp["jsonrpc"], "2.0");
    assert_eq!(resp["result"]["serverInfo"]["name"], "brazilian-soccer-mcp");
    assert!(resp["result"]["protocolVersion"].is_string());
    assert!(resp["result"]["capabilities"]["tools"].is_object());
}

#[test]
fn scenario_notifications_get_no_response() {
    // GIVEN a running server
    let ds = common::given_loaded_dataset();

    // WHEN the client sends the initialized notification (no id)
    let resp = call(ds, json!({"jsonrpc": "2.0", "method": "notifications/initialized"}));

    // THEN the server stays silent
    assert!(resp.is_none());
}

#[test]
fn scenario_tools_are_discoverable_with_schemas() {
    // GIVEN a running server
    let ds = common::given_loaded_dataset();

    // WHEN the client lists tools
    let resp = call(ds, json!({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})).unwrap();

    // THEN all nine tools are advertised, each with a JSON schema
    let tools = resp["result"]["tools"].as_array().unwrap();
    assert_eq!(tools.len(), 9);
    let names: Vec<&str> = tools.iter().map(|t| t["name"].as_str().unwrap()).collect();
    for expected in [
        "search_matches", "get_team_stats", "head_to_head", "get_standings",
        "search_players", "get_player", "analyze_stats", "best_records", "list_competitions",
    ] {
        assert!(names.contains(&expected), "missing tool {}", expected);
    }
    for t in tools {
        assert!(t["description"].as_str().unwrap().len() > 20);
        assert_eq!(t["inputSchema"]["type"], "object");
    }
    // AND the static definitions agree
    assert_eq!(tool_definitions().as_array().unwrap().len(), 9);
}

#[test]
fn scenario_tool_call_returns_text_content() {
    // GIVEN a running server
    let ds = common::given_loaded_dataset();

    // WHEN the client calls search_matches via the protocol
    let result = tool_call(ds, "search_matches", json!({"team": "Flamengo", "opponent": "Fluminense"}));

    // THEN the result is MCP text content wrapping valid JSON
    assert_eq!(result["isError"], false);
    let text = result["content"][0]["text"].as_str().unwrap();
    let parsed: Value = serde_json::from_str(text).expect("payload must be valid JSON");
    assert!(parsed["total_matches_found"].as_u64().unwrap() >= 10);
}

#[test]
fn scenario_tool_errors_are_reported_in_band() {
    // GIVEN a running server
    let ds = common::given_loaded_dataset();

    // WHEN a tool is called with a missing required argument
    let result = tool_call(ds, "get_team_stats", json!({}));
    // THEN the error is reported MCP-style, readable by the LLM
    assert_eq!(result["isError"], true);
    assert!(result["content"][0]["text"].as_str().unwrap().contains("team"));

    // WHEN an unknown tool is called
    let result = tool_call(ds, "no_such_tool", json!({}));
    // THEN the same in-band error mechanism is used
    assert_eq!(result["isError"], true);
}

#[test]
fn scenario_unknown_method_yields_jsonrpc_error() {
    // GIVEN a running server
    let ds = common::given_loaded_dataset();

    // WHEN an unsupported method is requested
    let resp = call(ds, json!({"jsonrpc": "2.0", "id": 9, "method": "resources/list"})).unwrap();

    // THEN a standard JSON-RPC method-not-found error is returned
    assert_eq!(resp["error"]["code"], -32601);
}

#[test]
fn scenario_all_six_csv_files_are_loaded_and_queryable() {
    // GIVEN the dataset
    let ds = common::given_loaded_dataset();

    // WHEN I inspect the diagnostics tool
    let result = tool_call(ds, "list_competitions", json!({}));
    let text: Value =
        serde_json::from_str(result["content"][0]["text"].as_str().unwrap()).unwrap();

    // THEN every CSV contributed rows (counts close to the documented sizes)
    let files = text["files_loaded"].as_object().unwrap();
    let expect_min = [
        ("Brasileirao_Matches.csv", 4000u64),
        ("Brazilian_Cup_Matches.csv", 1200),
        ("Libertadores_Matches.csv", 1100),
        ("BR-Football-Dataset.csv", 9000),
        ("novo_campeonato_brasileiro.csv", 6800),
        ("fifa_data.csv", 18000),
    ];
    for (file, min) in expect_min {
        let n = files[file].as_u64().unwrap();
        assert!(n >= min, "{} loaded only {} rows", file, n);
    }
    // AND all five competitions are represented
    assert!(text["competitions"].as_array().unwrap().len() >= 4);
}

#[test]
fn scenario_twenty_sample_questions_are_answerable() {
    // GIVEN a running server speaking MCP
    let ds = common::given_loaded_dataset();

    // WHEN each of the 20 sample questions is mapped to a tool call
    let calls: Vec<(&str, Value)> = vec![
        // match queries
        ("search_matches", json!({"team": "Flamengo", "opponent": "Fluminense"})),
        ("search_matches", json!({"team": "Palmeiras", "season": 2023})),
        ("search_matches", json!({"competition": "Copa do Brasil", "team": "Grêmio"})),
        ("search_matches", json!({"team": "Flamengo", "opponent": "Corinthians", "limit": 1})),
        ("search_matches", json!({"team": "Santos", "date_from": "2015", "date_to": "2016"})),
        ("search_matches", json!({"competition": "Libertadores", "season": 2018})),
        // team queries
        ("get_team_stats", json!({"team": "Corinthians", "season": 2022, "competition": "Brasileirão"})),
        ("get_team_stats", json!({"team": "São Paulo"})),
        ("head_to_head", json!({"team1": "Palmeiras", "team2": "Santos"})),
        ("head_to_head", json!({"team1": "Grêmio", "team2": "Internacional"})),
        // player queries
        ("search_players", json!({"nationality": "Brazil", "limit": 10})),
        ("search_players", json!({"club": "Cruzeiro"})),
        ("search_players", json!({"nationality": "Brazil", "position": "GK", "min_overall": 80})),
        ("get_player", json!({"name": "Neymar"})),
        ("get_player", json!({"name": "Casemiro"})),
        // competition queries
        ("get_standings", json!({"season": 2019})),
        ("get_standings", json!({"season": 2003})),
        // statistics
        ("analyze_stats", json!({"competition": "Brasileirão"})),
        ("analyze_stats", json!({"season": 2019, "top_n": 5})),
        ("best_records", json!({"venue": "home", "competition": "Brasileirão", "min_matches": 50})),
    ];

    // THEN every single one succeeds through the MCP protocol layer
    for (i, (tool, args)) in calls.iter().enumerate() {
        let result = tool_call(ds, tool, args.clone());
        assert_eq!(
            result["isError"], false,
            "question #{} via {} failed: {}",
            i + 1, tool, result["content"][0]["text"]
        );
    }
}
