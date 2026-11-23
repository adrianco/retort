mod data;
mod query;

pub use data::Graph;
use serde_json::{Value, json};
use std::io::{self, BufRead, Write};

const PROTOCOL: &str = "2025-11-25";
const SUPPORTED: &[&str] = &[PROTOCOL, "2025-06-18"];

fn error(id: Value, code: i32, message: impl Into<String>) -> Value {
    json!({"jsonrpc":"2.0","id":id,"error":{"code":code,"message":message.into()}})
}

fn request(graph: &Graph, msg: Value, version: &mut Option<String>) -> Option<Value> {
    let id = msg.get("id").cloned();
    let method = msg["method"].as_str();
    if msg["jsonrpc"] != "2.0"
        || method.is_none()
        || id
            .as_ref()
            .is_some_and(|i| !i.is_string() && i.as_i64().is_none() && i.as_u64().is_none())
    {
        return Some(error(Value::Null, -32600, "Invalid Request"));
    }
    let id = id?;
    let params = &msg["params"];
    let result = match method.unwrap() {
        "initialize" => {
            let Some(requested) = params["protocolVersion"].as_str() else {
                return Some(error(id, -32602, "Expected protocolVersion"));
            };
            let negotiated = if SUPPORTED.contains(&requested) {
                requested
            } else {
                PROTOCOL
            };
            *version = Some(negotiated.into());
            json!({"protocolVersion":negotiated,"capabilities":{"tools":{}},
                "serverInfo":{"name":"brazilian-soccer-mcp","version":env!("CARGO_PKG_VERSION")},
                "instructions":"Translate soccer questions into tool arguments. Use search_matches for results, cup_bracket for knockout rounds, team_stats for head-to-head and club links, standings for league tables, and search_players for the FIFA snapshot. Continue with next_offset for additional results."})
        }
        "ping" => json!({}),
        "tools/list" if version.is_some() => json!({"tools":query::tools()}),
        "tools/call" if version.is_some() => {
            let Some(name) = params["name"].as_str() else {
                return Some(error(id, -32602, "Expected a tool name"));
            };
            if !query::tools()
                .as_array()
                .unwrap()
                .iter()
                .any(|tool| tool["name"] == name)
            {
                return Some(error(id, -32602, format!("Unknown tool {name}")));
            }
            let args = params
                .get("arguments")
                .cloned()
                .unwrap_or_else(|| json!({}));
            match graph.call(name, args) {
                Ok(value) => {
                    json!({"content":[{"type":"text","text":value.to_string()}],"structuredContent":value})
                }
                Err(message) => json!({"isError":true,"content":[{"type":"text","text":message}]}),
            }
        }
        "tools/list" | "tools/call" => return Some(error(id, -32002, "Server is not initialized")),
        _ => return Some(error(id, -32601, "Method not found")),
    };
    Some(json!({"jsonrpc":"2.0","id":id,"result":result}))
}

pub fn serve(graph: &Graph, input: impl BufRead, mut output: impl Write) -> io::Result<()> {
    let mut version = None;
    for line in input.lines() {
        let line = line?;
        let reply = match serde_json::from_str(&line) {
            Ok(msg) => request(graph, msg, &mut version),
            Err(_) => Some(error(Value::Null, -32700, "Parse error")),
        };
        if let Some(reply) = reply {
            serde_json::to_writer(&mut output, &reply)?;
            writeln!(output)?;
            output.flush()?;
        }
    }
    Ok(())
}
