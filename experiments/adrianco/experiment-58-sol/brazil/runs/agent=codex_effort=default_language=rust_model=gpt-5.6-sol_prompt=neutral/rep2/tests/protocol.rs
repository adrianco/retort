use serde_json::{json, Value};
use std::{
    io::{BufRead, BufReader, Write},
    process::{Command, Stdio},
};

#[test]
fn binary_speaks_stdio_mcp_without_stdout_noise() {
    let mut child = Command::new(env!("CARGO_BIN_EXE_brazilian-soccer-mcp"))
        // A real MCP host does not promise to launch in the crate directory.
        .current_dir(std::env::temp_dir())
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();
    let mut stdin = child.stdin.take().unwrap();
    let mut stdout = BufReader::new(child.stdout.take().unwrap());

    writeln!(stdin, "{}", json!({"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"test","version":"1"}}})).unwrap();
    writeln!(
        stdin,
        "{}",
        json!({"jsonrpc":"2.0","method":"notifications/initialized"})
    )
    .unwrap();
    writeln!(
        stdin,
        "{}",
        json!({"jsonrpc":"2.0","id":"tools","method":"tools/list"})
    )
    .unwrap();
    writeln!(stdin, "{}", json!({"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"get_standings","arguments":{"season":2019,"limit":4}}})).unwrap();
    drop(stdin);

    let mut lines = Vec::new();
    let mut line = String::new();
    while stdout.read_line(&mut line).unwrap() > 0 {
        lines.push(serde_json::from_str::<Value>(line.trim()).expect("stdout line is JSON"));
        line.clear();
    }
    let status = child.wait().unwrap();
    assert!(status.success());
    assert_eq!(lines.len(), 3, "notification produces no response");
    assert_eq!(lines[0]["result"]["protocolVersion"], "2025-06-18");
    assert_eq!(lines[1]["result"]["tools"].as_array().unwrap().len(), 7);
    assert_eq!(lines[2]["result"]["isError"], false);
    assert_eq!(
        lines[2]["result"]["structuredContent"]["data"][0]["team"],
        "Flamengo-RJ"
    );
    assert!(lines[2]["result"]["content"][0]["text"]
        .as_str()
        .unwrap()
        .contains("Flamengo-RJ"));
}
