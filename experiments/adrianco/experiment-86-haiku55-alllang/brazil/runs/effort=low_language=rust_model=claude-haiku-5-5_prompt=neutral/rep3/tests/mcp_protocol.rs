//! Context: BDD scenarios for the MCP JSON-RPC layer.
//!
//! Feature: MCP server
//!   Scenario: Client initialises the session
//!   Scenario: Client lists the tools
//!   Scenario: Client calls a tool and gets formatted text
//!   Scenario: Notifications are not answered; unknown methods are errors

mod common;

use brazilian_soccer_mcp::mcp::handle_message;
use serde_json::{Value, json};

fn call(ds: &brazilian_soccer_mcp::data::Dataset, msg: Value) -> Option<Value> {
    handle_message(ds, &msg.to_string())
}

fn tool_text(resp: &Value) -> &str {
    resp["result"]["content"][0]["text"]
        .as_str()
        .expect("text content")
}

#[test]
fn scenario_initialize_advertises_tools() {
    // Given a running server
    let ds = common::fixture();
    // When the client sends initialize
    let resp = call(
        &ds,
        json!({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}),
    )
    .unwrap();
    // Then the server reports its protocol version, name and tool capability
    assert_eq!(resp["id"], 1);
    assert_eq!(resp["result"]["serverInfo"]["name"], "brazilian-soccer-mcp");
    assert!(resp["result"]["capabilities"]["tools"].is_object());
}

#[test]
fn scenario_tools_list_has_all_six_tools() {
    // Given a running server
    let ds = common::fixture();
    // When the client lists tools
    let resp = call(
        &ds,
        json!({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}),
    )
    .unwrap();
    // Then all query tools are described with an input schema
    let names: Vec<&str> = resp["result"]["tools"]
        .as_array()
        .unwrap()
        .iter()
        .map(|t| t["name"].as_str().unwrap())
        .collect();
    for expected in [
        "search_matches",
        "team_record",
        "head_to_head",
        "standings",
        "league_stats",
        "search_players",
    ] {
        assert!(names.contains(&expected), "missing {expected}");
    }
}

#[test]
fn scenario_head_to_head_tool_returns_formatted_answer() {
    // Given a running server
    let ds = common::fixture();
    // When the client calls head_to_head for Palmeiras and Santos
    let resp = call(&ds, json!({
        "jsonrpc": "2.0", "id": 3, "method": "tools/call",
        "params": {"name": "head_to_head", "arguments": {"team_a": "Palmeiras", "team_b": "Santos"}}
    })).unwrap();
    // Then the answer lists meetings and the head-to-head summary
    assert_eq!(resp["result"]["isError"], false);
    let text = tool_text(&resp);
    assert!(text.starts_with("Palmeiras vs Santos:"));
    assert!(text.contains("2022-05-01: Santos 1-1 Palmeiras"));
    assert!(text.contains("Head-to-head in dataset: Palmeiras 1 wins"));
}

#[test]
fn scenario_bad_arguments_are_reported_as_tool_errors() {
    // Given a running server
    let ds = common::fixture();
    // When the client calls team_record without a team
    let resp = call(
        &ds,
        json!({
            "jsonrpc": "2.0", "id": 4, "method": "tools/call",
            "params": {"name": "team_record", "arguments": {}}
        }),
    )
    .unwrap();
    // Then the result is flagged as an error rather than a JSON-RPC failure
    assert_eq!(resp["result"]["isError"], true);
    assert!(tool_text(&resp).contains("`team` is required"));
}

#[test]
fn scenario_notifications_get_no_reply() {
    // Given a running server
    let ds = common::fixture();
    // When the client sends the initialized notification (no id)
    let resp = handle_message(
        &ds,
        r#"{"jsonrpc":"2.0","method":"notifications/initialized"}"#,
    );
    // Then nothing is returned
    assert!(resp.is_none());
}

#[test]
fn scenario_unknown_method_returns_jsonrpc_error() {
    // Given a running server
    let ds = common::fixture();
    // When the client calls a method that does not exist
    let resp = call(&ds, json!({"jsonrpc": "2.0", "id": 5, "method": "nope"})).unwrap();
    // Then a method-not-found error is returned
    assert_eq!(resp["error"]["code"], -32601);
}

#[test]
fn scenario_invalid_json_returns_parse_error() {
    // Given a running server
    let ds = common::fixture();
    // When the client sends malformed JSON
    let resp = handle_message(&ds, "{not json").unwrap();
    // Then a parse error is returned
    assert_eq!(resp["error"]["code"], -32700);
}
