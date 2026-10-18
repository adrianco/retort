//! Protocol scenarios: JSON-RPC requests in, MCP responses out.

mod common;

use std::io::Write;
use std::process::{Command, Stdio};

use brazilian_soccer_mcp::mcp::{handle_line, PROTOCOL_VERSION};
use serde_json::{json, Value};

use common::dataset;

fn request(method: &str, params: Value) -> String {
    json!({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).to_string()
}

fn call_tool(name: &str, arguments: Value) -> Value {
    let line = request("tools/call", json!({"name": name, "arguments": arguments}));
    handle_line(dataset(), &line).expect("tool calls get a response")["result"].clone()
}

fn text_of(result: &Value) -> &str {
    result["content"][0]["text"].as_str().expect("text content")
}

#[test]
fn scenario_client_initializes_the_session() {
    let response = handle_line(dataset(), &request("initialize", json!({}))).unwrap();
    let result = &response["result"];
    assert_eq!(result["protocolVersion"], PROTOCOL_VERSION);
    assert!(result["capabilities"]["tools"].is_object());
    assert_eq!(result["serverInfo"]["name"], "brazilian-soccer-mcp");
}

#[test]
fn scenario_client_discovers_all_tools() {
    let response = handle_line(dataset(), &request("tools/list", json!({}))).unwrap();
    let names: Vec<&str> = response["result"]["tools"]
        .as_array()
        .unwrap()
        .iter()
        .map(|tool| tool["name"].as_str().unwrap())
        .collect();
    for expected in ["search_matches", "team_stats", "head_to_head", "standings", "league_stats", "search_players", "dataset_info"] {
        assert!(names.contains(&expected), "missing tool {expected}");
    }
    let schemas_ok = response["result"]["tools"]
        .as_array()
        .unwrap()
        .iter()
        .all(|tool| tool["inputSchema"]["type"] == "object");
    assert!(schemas_ok);
}

#[test]
fn scenario_flamengo_fluminense_question_is_answered() {
    let result = call_tool("search_matches", json!({"team": "Flamengo", "opponent": "Fluminense", "limit": 3}));
    assert_eq!(result["isError"], false);
    let text = text_of(&result);
    let first_line = text.lines().next().unwrap();
    assert!(first_line.contains("Flamengo") && first_line.contains("Fluminense"), "{first_line}");
    assert!(text.contains("Head-to-head in dataset"));
}

#[test]
fn scenario_corinthians_home_record_2022() {
    let result = call_tool("team_stats", json!({"team": "Corinthians", "season": 2022, "competition": "brasileirao"}));
    let text = text_of(&result);
    assert!(text.contains("Corinthians record (Brasileirão 2022)"));
    assert!(text.contains("Home:"));
}

#[test]
fn scenario_biggest_wins_and_averages_are_reported() {
    let result = call_tool("league_stats", json!({"competition": "brasileirao"}));
    let text = text_of(&result);
    assert!(text.contains("Average goals per match"));
    assert!(text.contains("Biggest wins:"));
}

#[test]
fn scenario_search_players_returns_ratings() {
    let result = call_tool("search_players", json!({"nationality": "Brazil", "min_overall": 85, "limit": 3}));
    let text = text_of(&result);
    assert!(text.contains("Overall:"));
    assert_eq!(text.lines().count(), 3);
}

#[test]
fn scenario_bad_arguments_are_reported_as_tool_errors() {
    let unknown_competition = call_tool("standings", json!({"season": 2019, "competition": "premier league"}));
    assert_eq!(unknown_competition["isError"], true);
    assert!(text_of(&unknown_competition).contains("unknown competition"));

    let missing_season = call_tool("standings", json!({}));
    assert_eq!(missing_season["isError"], true);

    let bad_date = call_tool("search_matches", json!({"team": "Palmeiras", "date_from": "31-02-2020"}));
    assert_eq!(bad_date["isError"], true);

    let unknown_tool = call_tool("does_not_exist", json!({}));
    assert_eq!(unknown_tool["isError"], true);
}

#[test]
fn scenario_no_results_is_a_normal_answer() {
    let result = call_tool("head_to_head", json!({"team_a": "Palmeiras", "team_b": "Nonexistent FC"}));
    assert_eq!(result["isError"], false);
    assert!(text_of(&result).contains("No matches"));
}

#[test]
fn scenario_notifications_get_no_reply() {
    let line = json!({"jsonrpc": "2.0", "method": "notifications/initialized"}).to_string();
    assert!(handle_line(dataset(), &line).is_none());
}

#[test]
fn scenario_malformed_input_gets_a_json_rpc_error() {
    let parse = handle_line(dataset(), "{not json").unwrap();
    assert_eq!(parse["error"]["code"], -32700);

    let unknown = handle_line(dataset(), &request("resources/list", json!({}))).unwrap();
    assert_eq!(unknown["error"]["code"], -32601);
    assert_eq!(unknown["id"], 1);
}

#[test]
fn scenario_server_binary_speaks_over_stdio() {
    let dir = format!("{}/data/kaggle", env!("CARGO_MANIFEST_DIR"));
    let mut child = Command::new(env!("CARGO_BIN_EXE_brazilian-soccer-mcp"))
        .arg(&dir)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .spawn()
        .expect("server starts");
    {
        let stdin = child.stdin.as_mut().unwrap();
        writeln!(stdin, "{}", request("initialize", json!({}))).unwrap();
        writeln!(stdin, "{}", json!({"jsonrpc": "2.0", "method": "notifications/initialized"})).unwrap();
        writeln!(stdin, "{}", request("ping", json!({}))).unwrap();
    }
    drop(child.stdin.take());
    let output = child.wait_with_output().unwrap();
    let lines: Vec<Value> = String::from_utf8(output.stdout)
        .unwrap()
        .lines()
        .map(|line| serde_json::from_str(line).expect("each stdout line is JSON"))
        .collect();
    assert_eq!(lines.len(), 2, "notifications must not produce output");
    assert_eq!(lines[0]["result"]["protocolVersion"], PROTOCOL_VERSION);
    assert_eq!(lines[1]["result"], json!({}));
}
