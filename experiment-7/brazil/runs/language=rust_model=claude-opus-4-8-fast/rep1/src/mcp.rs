// =============================================================================
// Context: Brazilian Soccer MCP Server
// File:    src/mcp.rs
// Purpose: A minimal, dependency-light implementation of the Model Context
//          Protocol JSON-RPC 2.0 message layer over stdio. Handles the
//          `initialize` handshake, `tools/list`, `tools/call` and `ping`, and
//          turns tool output into MCP `content` blocks. Notifications (such as
//          `notifications/initialized`) yield no response.
//
//          Keeping the protocol logic separate from the data/query/tool layers
//          means the entire server can be driven in tests by feeding request
//          `Value`s to `handle_request`.
// =============================================================================

use serde_json::{json, Value};

use crate::data::Database;
use crate::tools;

/// MCP protocol revision advertised to clients.
pub const PROTOCOL_VERSION: &str = "2024-11-05";

/// Handle a single JSON-RPC request. Returns `Some(response)` for requests and
/// `None` for notifications (messages without an `id`).
pub fn handle_request(db: &Database, request: &Value) -> Option<Value> {
    let id = request.get("id").cloned();
    let method = request.get("method").and_then(|m| m.as_str()).unwrap_or("");
    let params = request.get("params").cloned().unwrap_or(Value::Null);

    // Notifications carry no id and never get a response.
    let id = id?;

    match method {
        "initialize" => Some(success(
            id,
            json!({
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": { "tools": {} },
                "serverInfo": {
                    "name": "brazilian-soccer-mcp",
                    "version": env!("CARGO_PKG_VERSION")
                },
                "instructions": "Query Brazilian soccer match and player data. Use list_competitions to see coverage, then search_matches / team_stats / head_to_head / search_players / competition_standings / competition_stats."
            }),
        )),
        "ping" => Some(success(id, json!({}))),
        "tools/list" => Some(success(id, json!({ "tools": tools::tool_definitions() }))),
        "tools/call" => Some(handle_tools_call(db, id, &params)),
        other => Some(error(id, -32601, &format!("Method not found: {other}"))),
    }
}

fn handle_tools_call(db: &Database, id: Value, params: &Value) -> Value {
    let name = match params.get("name").and_then(|n| n.as_str()) {
        Some(n) => n,
        None => return error(id, -32602, "Missing tool name"),
    };
    let args = params.get("arguments").cloned().unwrap_or_else(|| json!({}));
    match tools::call_tool(db, name, &args) {
        Ok(text) => success(
            id,
            json!({
                "content": [ { "type": "text", "text": text } ],
                "isError": false
            }),
        ),
        Err(message) => success(
            id,
            json!({
                "content": [ { "type": "text", "text": message } ],
                "isError": true
            }),
        ),
    }
}

fn success(id: Value, result: Value) -> Value {
    json!({ "jsonrpc": "2.0", "id": id, "result": result })
}

fn error(id: Value, code: i64, message: &str) -> Value {
    json!({ "jsonrpc": "2.0", "id": id, "error": { "code": code, "message": message } })
}
