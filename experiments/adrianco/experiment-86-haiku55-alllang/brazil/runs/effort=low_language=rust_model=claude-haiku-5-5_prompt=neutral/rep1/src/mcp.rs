//! JSON-RPC 2.0 handling for the Model Context Protocol over stdio.
//!
//! Each request is one line of JSON. Notifications (no `id`) get no response.

use serde_json::{json, Value};

use crate::data::Dataset;
use crate::tools;

/// MCP protocol revision this server speaks.
pub const PROTOCOL_VERSION: &str = "2024-11-05";
pub const SERVER_NAME: &str = "brazilian-soccer-mcp";
pub const SERVER_VERSION: &str = env!("CARGO_PKG_VERSION");

const PARSE_ERROR: i64 = -32700;
const INVALID_REQUEST: i64 = -32600;
const METHOD_NOT_FOUND: i64 = -32601;
const INVALID_PARAMS: i64 = -32602;

/// Handles one incoming line. Returns the response line to send, if any.
pub fn handle_line(ds: &Dataset, line: &str) -> Option<Value> {
    let message: Value = match serde_json::from_str(line) {
        Ok(value) => value,
        Err(err) => return Some(error_response(Value::Null, PARSE_ERROR, &format!("parse error: {err}"))),
    };
    let Some(object) = message.as_object() else {
        return Some(error_response(Value::Null, INVALID_REQUEST, "request must be a JSON object"));
    };
    let id = object.get("id").cloned();
    let Some(method) = object.get("method").and_then(Value::as_str) else {
        return id.map(|id| error_response(id, INVALID_REQUEST, "missing method"));
    };
    let id = id?; // notifications carry no id and need no reply
    let params = object.get("params").cloned().unwrap_or(Value::Null);

    Some(match method {
        "initialize" => ok_response(id, initialize_result()),
        "ping" => ok_response(id, json!({})),
        "tools/list" => ok_response(id, json!({ "tools": tools::definitions() })),
        "tools/call" => match tool_call(ds, &params) {
            Ok(result) => ok_response(id, result),
            Err(message) => error_response(id, INVALID_PARAMS, &message),
        },
        other => error_response(id, METHOD_NOT_FOUND, &format!("method not found: {other}")),
    })
}

fn initialize_result() -> Value {
    json!({
        "protocolVersion": PROTOCOL_VERSION,
        "capabilities": { "tools": {} },
        "serverInfo": { "name": SERVER_NAME, "version": SERVER_VERSION },
        "instructions": "Answers questions about Brazilian football (Brasileirão, Copa do Brasil, Libertadores, Série B/C matches from 2003 onward, and FIFA player ratings). Use team names as written in Portuguese or English; state suffixes such as -SP are optional."
    })
}

/// Runs `tools/call`. Unknown tools and bad arguments become a tool result
/// with `isError: true`, so the model can see and correct them.
fn tool_call(ds: &Dataset, params: &Value) -> Result<Value, String> {
    let name = params
        .get("name")
        .and_then(Value::as_str)
        .ok_or("tools/call requires a 'name' string")?;
    let args = params.get("arguments").cloned().unwrap_or(Value::Null);
    Ok(match tools::call(ds, name, &args) {
        Ok(text) => json!({ "content": [{ "type": "text", "text": text }], "isError": false }),
        Err(text) => json!({ "content": [{ "type": "text", "text": text }], "isError": true }),
    })
}

fn ok_response(id: Value, result: Value) -> Value {
    json!({ "jsonrpc": "2.0", "id": id, "result": result })
}

fn error_response(id: Value, code: i64, message: &str) -> Value {
    json!({ "jsonrpc": "2.0", "id": id, "error": { "code": code, "message": message } })
}
