//! End-to-end test: spawn the compiled MCP server binary, drive it via stdio,
//! and verify the JSON-RPC handshake plus a representative tool call.

use std::io::{BufRead, BufReader, Write};
use std::process::{Command, Stdio};

use serde_json::{json, Value};

fn bin_path() -> std::path::PathBuf {
    // CARGO_BIN_EXE_<name> is set by cargo for integration tests.
    std::path::PathBuf::from(env!("CARGO_BIN_EXE_brazilian-soccer-mcp"))
}

#[test]
fn handshake_and_tool_call() {
    let mut child = Command::new(bin_path())
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .env(
            "BR_SOCCER_DATA_DIR",
            std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("data/kaggle"),
        )
        .spawn()
        .expect("spawn server");

    let mut stdin = child.stdin.take().unwrap();
    let stdout = child.stdout.take().unwrap();
    let mut reader = BufReader::new(stdout);

    let send = |stdin: &mut std::process::ChildStdin, v: Value| {
        let s = serde_json::to_string(&v).unwrap();
        writeln!(stdin, "{}", s).unwrap();
        stdin.flush().unwrap();
    };

    let recv = |reader: &mut BufReader<std::process::ChildStdout>| -> Value {
        let mut buf = String::new();
        reader.read_line(&mut buf).unwrap();
        serde_json::from_str(buf.trim()).unwrap()
    };

    // initialize
    send(
        &mut stdin,
        json!({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "0.0"}
            }
        }),
    );
    let init = recv(&mut reader);
    assert_eq!(init["jsonrpc"], "2.0");
    assert_eq!(init["id"], json!(1));
    assert_eq!(init["result"]["protocolVersion"], "2024-11-05");
    assert_eq!(init["result"]["serverInfo"]["name"], "brazilian-soccer-mcp");

    // initialized notification (no response)
    send(
        &mut stdin,
        json!({
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }),
    );

    // tools/list
    send(
        &mut stdin,
        json!({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}),
    );
    let list = recv(&mut reader);
    let tools = list["result"]["tools"].as_array().unwrap();
    assert!(tools.iter().any(|t| t["name"] == "search_matches"));

    // tools/call head_to_head
    send(
        &mut stdin,
        json!({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "head_to_head",
                "arguments": {"team_a": "Flamengo", "team_b": "Fluminense"}
            }
        }),
    );
    let call = recv(&mut reader);
    assert!(call["error"].is_null());
    let text = call["result"]["content"][0]["text"].as_str().unwrap();
    assert!(text.contains("Flamengo"));
    assert!(text.contains("matches"));

    drop(stdin);
    let _ = child.wait();
}
