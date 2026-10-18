//! Context: minimal Model Context Protocol server over stdio. Messages are
//! newline-delimited JSON-RPC 2.0. Only the tools capability is implemented.

use std::io::{self, BufRead, Write};

use serde_json::{json, Value};

use crate::data::Dataset;
use crate::tools::{call_tool, tool_definitions};

pub const PROTOCOL_VERSION: &str = "2024-11-05";
pub const SERVER_NAME: &str = "brazilian-soccer-mcp";
pub const SERVER_VERSION: &str = env!("CARGO_PKG_VERSION");

const PARSE_ERROR: i64 = -32700;
const INVALID_REQUEST: i64 = -32600;
const METHOD_NOT_FOUND: i64 = -32601;
const INVALID_PARAMS: i64 = -32602;

fn error_response(id: Value, code: i64, message: &str) -> Value {
    json!({
        "jsonrpc": "2.0",
        "id": id,
        "error": {"code": code, "message": message}
    })
}

fn success_response(id: Value, result: Value) -> Value {
    json!({"jsonrpc": "2.0", "id": id, "result": result})
}

/// Handle one parsed JSON-RPC message. Returns `None` for notifications.
pub fn handle_message(ds: &Dataset, msg: &Value) -> Option<Value> {
    let Some(method) = msg.get("method").and_then(Value::as_str) else {
        // A response from the client or a malformed request; reply only when it had an id.
        return msg
            .get("id")
            .map(|id| error_response(id.clone(), INVALID_REQUEST, "missing method"));
    };
    // Notifications carry no id and get no response.
    let id = msg.get("id")?.clone();
    let params = msg.get("params").cloned().unwrap_or_else(|| json!({}));

    Some(match method {
        "initialize" => success_response(
            id,
            json!({
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                "instructions": "Query Brazilian soccer match results (2003-2023), standings, team records and FIFA player data."
            }),
        ),
        "ping" => success_response(id, json!({})),
        "tools/list" => success_response(id, json!({"tools": tool_definitions()})),
        "tools/call" => call_tool_message(ds, id, &params),
        _ => error_response(id, METHOD_NOT_FOUND, &format!("method not found: {method}")),
    })
}

fn call_tool_message(ds: &Dataset, id: Value, params: &Value) -> Value {
    let Some(name) = params.get("name").and_then(Value::as_str) else {
        return error_response(id, INVALID_PARAMS, "tools/call requires a 'name'");
    };
    let args = params
        .get("arguments")
        .cloned()
        .unwrap_or_else(|| json!({}));
    if !args.is_object() {
        return error_response(id, INVALID_PARAMS, "'arguments' must be an object");
    }
    let (text, is_error) = match call_tool(ds, name, &args) {
        Ok(text) => (text, false),
        Err(message) => (message, true),
    };
    success_response(
        id,
        json!({
            "content": [{"type": "text", "text": text}],
            "isError": is_error
        }),
    )
}

/// Serve requests from `input` until EOF, writing one response line per request.
pub fn serve<R: BufRead, W: Write>(ds: &Dataset, input: R, mut output: W) -> io::Result<()> {
    for line in input.lines() {
        let line = line?;
        if line.trim().is_empty() {
            continue;
        }
        let response = match serde_json::from_str::<Value>(&line) {
            Ok(msg) => handle_message(ds, &msg),
            Err(e) => Some(error_response(
                Value::Null,
                PARSE_ERROR,
                &format!("parse error: {e}"),
            )),
        };
        if let Some(resp) = response {
            writeln!(output, "{resp}")?;
            output.flush()?;
        }
    }
    Ok(())
}
