//! Feature: MCP protocol conformance
//!
//! Drives the server the way an MCP host does — JSON-RPC 2.0 messages over a
//! newline-delimited stream — and checks the handshake, tool discovery, tool
//! invocation, resources, prompts and error handling.

mod common;

use std::io::{BufReader, Cursor};

use brazilian_soccer_mcp::mcp::{Server, SERVER_NAME, SUPPORTED_PROTOCOL_VERSIONS};

use serde_json::{json, Value};

/// A server sharing the process-wide graph would need ownership, so protocol
/// tests build their own (the graph loads once per test binary anyway).
fn server() -> Server {
    Server::new(
        brazilian_soccer_mcp::load_default_graph().expect("datasets should load from data/kaggle"),
    )
}

fn request(server: &mut Server, method: &str, params: Value) -> Value {
    let response = server
        .handle(json!({ "jsonrpc": "2.0", "id": 1, "method": method, "params": params }))
        .expect("a request with an id must get a response");
    assert_eq!(response["jsonrpc"], "2.0");
    assert_eq!(response["id"], 1);
    response
}

fn ok_result(server: &mut Server, method: &str, params: Value) -> Value {
    let response = request(server, method, params);
    assert!(
        response.get("error").is_none(),
        "unexpected error: {response}"
    );
    response["result"].clone()
}

fn call_tool(server: &mut Server, name: &str, arguments: Value) -> Value {
    ok_result(
        server,
        "tools/call",
        json!({ "name": name, "arguments": arguments }),
    )
}

#[test]
fn scenario_initialize_handshake() {
    let mut server = server();
    assert!(!server.is_initialized());

    let result = ok_result(
        &mut server,
        "initialize",
        json!({
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": { "name": "test-harness", "version": "1.0" }
        }),
    );

    assert_eq!(result["protocolVersion"], "2025-06-18");
    assert_eq!(result["serverInfo"]["name"], SERVER_NAME);
    assert!(result["capabilities"]["tools"].is_object());
    assert!(result["capabilities"]["resources"].is_object());
    assert!(result["instructions"].as_str().unwrap().contains("teams"));

    // The initialized notification carries no id and gets no response.
    assert!(server
        .handle(json!({ "jsonrpc": "2.0", "method": "notifications/initialized" }))
        .is_none());
    assert!(server.is_initialized());
}

#[test]
fn scenario_unsupported_protocol_version_falls_back_to_a_supported_one() {
    let mut server = server();
    let result = ok_result(
        &mut server,
        "initialize",
        json!({ "protocolVersion": "1999-01-01" }),
    );
    let negotiated = result["protocolVersion"].as_str().unwrap();
    assert!(SUPPORTED_PROTOCOL_VERSIONS.contains(&negotiated));
}

#[test]
fn scenario_tools_are_discoverable_with_valid_schemas() {
    let mut server = server();
    let result = ok_result(&mut server, "tools/list", json!({}));
    let tools = result["tools"].as_array().unwrap();
    assert!(tools.len() >= 13, "expected the full tool surface");

    let mut names: Vec<&str> = tools
        .iter()
        .map(|tool| tool["name"].as_str().unwrap())
        .collect();
    names.sort();
    for expected in [
        "biggest_wins",
        "club_players",
        "competition_stats",
        "dataset_overview",
        "find_team",
        "graph_neighbors",
        "head_to_head",
        "player_profile",
        "search_matches",
        "search_players",
        "standings",
        "team_profile",
        "team_rankings",
        "team_stats",
    ] {
        assert!(names.contains(&expected), "missing tool {expected}");
    }

    for tool in tools {
        assert!(!tool["description"].as_str().unwrap().is_empty());
        let schema = &tool["inputSchema"];
        assert_eq!(schema["type"], "object");
        assert!(schema["properties"].is_object());
        assert!(schema["required"].is_array());
        for (name, property) in schema["properties"].as_object().unwrap() {
            assert!(
                property["type"].is_string(),
                "property {name} of {} has no type",
                tool["name"]
            );
            assert!(property["description"].is_string());
        }
    }
}

#[test]
fn scenario_tool_call_returns_text_and_structured_content() {
    let mut server = server();
    let result = call_tool(
        &mut server,
        "team_stats",
        json!({ "team": "Flamengo", "season": 2019, "competition": "Serie A" }),
    );

    assert_eq!(result["isError"], false);
    let text = result["content"][0]["text"].as_str().unwrap();
    assert_eq!(result["content"][0]["type"], "text");
    assert!(text.contains("Flamengo"));
    assert_eq!(result["structuredContent"]["record"]["wins"], 28);
    assert_eq!(result["structuredContent"]["record"]["points"], 90);
}

#[test]
fn scenario_tool_errors_are_results_not_protocol_failures() {
    let mut server = server();

    // Unknown tool.
    let result = call_tool(&mut server, "predict_the_future", json!({}));
    assert_eq!(result["isError"], true);
    assert!(result["content"][0]["text"]
        .as_str()
        .unwrap()
        .contains("unknown tool"));

    // Missing required argument.
    let result = call_tool(&mut server, "head_to_head", json!({ "team_a": "Santos" }));
    assert_eq!(result["isError"], true);
    assert!(result["content"][0]["text"]
        .as_str()
        .unwrap()
        .contains("team_b"));

    // Wrong argument type.
    let result = call_tool(&mut server, "team_stats", json!({ "team": 42 }));
    assert_eq!(result["isError"], true);

    // Unresolvable club.
    let result = call_tool(&mut server, "team_stats", json!({ "team": "Real Madrid" }));
    assert_eq!(result["isError"], true);
}

#[test]
fn scenario_protocol_level_errors_use_jsonrpc_error_objects() {
    let mut server = server();

    let response = request(&mut server, "tools/teleport", json!({}));
    assert_eq!(response["error"]["code"], -32601);

    let response = request(&mut server, "tools/call", json!({ "arguments": {} }));
    assert_eq!(response["error"]["code"], -32602);

    let raw = server.handle_line("{not json").expect("parse errors reply");
    let parsed: Value = serde_json::from_str(&raw).unwrap();
    assert_eq!(parsed["error"]["code"], -32700);
    assert!(parsed["id"].is_null());
}

#[test]
fn scenario_ping_and_notifications() {
    let mut server = server();
    assert_eq!(ok_result(&mut server, "ping", json!({})), json!({}));
    assert!(server
        .handle(json!({ "jsonrpc": "2.0", "method": "notifications/cancelled" }))
        .is_none());
    // An unknown notification is ignored rather than answered with an error.
    assert!(server
        .handle(json!({ "jsonrpc": "2.0", "method": "notifications/unknown" }))
        .is_none());
}

#[test]
fn scenario_batched_requests() {
    let mut server = server();
    let batch = json!([
        { "jsonrpc": "2.0", "id": 1, "method": "ping" },
        { "jsonrpc": "2.0", "method": "notifications/initialized" },
        { "jsonrpc": "2.0", "id": 2, "method": "tools/list" }
    ]);
    let raw = server.handle_line(&batch.to_string()).unwrap();
    let responses: Value = serde_json::from_str(&raw).unwrap();
    let responses = responses.as_array().unwrap();
    assert_eq!(responses.len(), 2, "notifications produce no response");
    assert_eq!(responses[0]["id"], 1);
    assert_eq!(responses[1]["id"], 2);
}

#[test]
fn scenario_resources_are_listed_and_readable() {
    let mut server = server();
    let result = ok_result(&mut server, "resources/list", json!({}));
    let resources = result["resources"].as_array().unwrap();
    assert!(resources.len() >= 9, "3 summaries plus one per source file");

    let uris: Vec<&str> = resources
        .iter()
        .map(|resource| resource["uri"].as_str().unwrap())
        .collect();
    assert!(uris.contains(&"soccer://overview"));
    assert!(uris.contains(&"soccer://teams"));
    assert!(uris.contains(&"soccer://competitions"));
    assert!(uris.contains(&"soccer://source/fifa_data.csv"));

    let overview = ok_result(
        &mut server,
        "resources/read",
        json!({ "uri": "soccer://overview" }),
    );
    assert!(overview["contents"][0]["text"]
        .as_str()
        .unwrap()
        .contains("Source files"));

    let teams = ok_result(
        &mut server,
        "resources/read",
        json!({ "uri": "soccer://teams" }),
    );
    let parsed: Value =
        serde_json::from_str(teams["contents"][0]["text"].as_str().unwrap()).unwrap();
    assert!(parsed["teams"].as_array().unwrap().len() > 300);

    let competitions = ok_result(
        &mut server,
        "resources/read",
        json!({ "uri": "soccer://competitions" }),
    );
    let parsed: Value =
        serde_json::from_str(competitions["contents"][0]["text"].as_str().unwrap()).unwrap();
    assert_eq!(parsed["competitions"].as_array().unwrap().len(), 5);

    let missing = request(
        &mut server,
        "resources/read",
        json!({ "uri": "soccer://nope" }),
    );
    assert_eq!(missing["error"]["code"], -32602);
}

#[test]
fn scenario_prompts_are_offered() {
    let mut server = server();
    let result = ok_result(&mut server, "prompts/list", json!({}));
    let prompts = result["prompts"].as_array().unwrap();
    assert_eq!(prompts.len(), 2);

    let prompt = ok_result(
        &mut server,
        "prompts/get",
        json!({ "name": "season_review", "arguments": { "season": 2019 } }),
    );
    assert!(prompt["messages"][0]["content"]["text"]
        .as_str()
        .unwrap()
        .contains("2019"));

    let unknown = request(&mut server, "prompts/get", json!({ "name": "nope" }));
    assert_eq!(unknown["error"]["code"], -32602);
}

#[test]
fn scenario_full_stdio_session() {
    // A complete session as an MCP host would run it, over a byte stream.
    let script = [
        json!({ "jsonrpc": "2.0", "id": 1, "method": "initialize", "params": { "protocolVersion": "2024-11-05" } }),
        json!({ "jsonrpc": "2.0", "method": "notifications/initialized" }),
        json!({ "jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {
            "name": "standings",
            "arguments": { "competition": "Serie A", "season": 2019, "limit": 3 }
        }}),
        json!({ "jsonrpc": "2.0", "id": 3, "method": "ping" }),
    ]
    .iter()
    .map(|message| message.to_string())
    .collect::<Vec<_>>()
    .join("\n");

    let mut output = Vec::new();
    server()
        .serve(BufReader::new(Cursor::new(script)), &mut output)
        .expect("the stdio loop should finish cleanly at EOF");

    let text = String::from_utf8(output).unwrap();
    let responses: Vec<Value> = text
        .lines()
        .filter(|line| !line.trim().is_empty())
        .map(|line| serde_json::from_str(line).expect("each line is one JSON-RPC message"))
        .collect();
    assert_eq!(responses.len(), 3, "the notification is not answered");
    assert_eq!(responses[0]["result"]["protocolVersion"], "2024-11-05");
    assert_eq!(
        responses[1]["result"]["structuredContent"]["champion"],
        "Flamengo"
    );
    assert_eq!(responses[2]["result"], json!({}));
}

#[test]
fn scenario_every_advertised_tool_can_be_invoked() {
    let mut server = server();
    let listed = ok_result(&mut server, "tools/list", json!({}));
    let arguments = |name: &str| match name {
        "search_matches" => json!({ "team": "Santos", "limit": 3 }),
        "head_to_head" => json!({ "team_a": "Santos", "team_b": "Palmeiras" }),
        "team_stats" => json!({ "team": "Santos" }),
        "team_profile" => json!({ "team": "Santos" }),
        "standings" => json!({ "season": 2019 }),
        "competition_stats" => json!({ "competition": "Serie A", "season": 2019 }),
        "team_rankings" => json!({ "metric": "points", "season": 2019 }),
        "biggest_wins" => json!({ "limit": 3 }),
        "search_players" => json!({ "nationality": "Brazil", "limit": 3 }),
        "player_profile" => json!({ "name": "Casemiro" }),
        "club_players" => json!({ "club": "Santos", "limit": 3 }),
        "find_team" => json!({ "query": "Santos" }),
        "graph_neighbors" => json!({ "node_type": "team", "name": "Santos", "limit": 2 }),
        "dataset_overview" => json!({}),
        other => panic!("no sample arguments for tool '{other}'"),
    };

    for tool in listed["tools"].as_array().unwrap() {
        let name = tool["name"].as_str().unwrap();
        let result = call_tool(&mut server, name, arguments(name));
        assert_eq!(result["isError"], false, "tool {name} failed: {result}");
        assert!(
            result["content"][0]["text"].as_str().unwrap().len() > 20,
            "tool {name} produced no substantive answer"
        );
        assert!(result["structuredContent"].is_object());
    }
}
