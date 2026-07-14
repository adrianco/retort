//! Acceptance-test harness.
//!
//! Drives the Brazilian Soccer MCP server purely as an external client would:
//! it spawns the compiled server binary as a child process and speaks the MCP
//! protocol (newline-delimited JSON-RPC 2.0) over the child's stdin/stdout.
//!
//! There is deliberately NO back-door access to the server's internals — tests
//! see only what a real MCP client (an LLM host) would see: the tool list and
//! the results of `tools/call`. Each test constructs its own `McpClient`, so
//! every scenario starts from a fresh, independent server process.

use std::io::{BufRead, BufReader, Write};
use std::process::{Child, ChildStdin, ChildStdout, Command, Stdio};

use serde_json::{json, Value};

pub struct McpClient {
    child: Child,
    stdin: ChildStdin,
    stdout: BufReader<ChildStdout>,
    next_id: i64,
}

impl McpClient {
    /// Start a fresh server process and complete the MCP initialize handshake.
    pub fn start() -> Self {
        let exe = env!("CARGO_BIN_EXE_brazilian-soccer-mcp");
        let mut child = Command::new(exe)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::inherit())
            .spawn()
            .expect("failed to spawn MCP server binary");

        let stdin = child.stdin.take().expect("child stdin");
        let stdout = BufReader::new(child.stdout.take().expect("child stdout"));

        let mut client = McpClient {
            child,
            stdin,
            stdout,
            next_id: 0,
        };

        // Handshake: initialize -> response, then the initialized notification.
        let init = client.request(
            "initialize",
            json!({
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": { "name": "acceptance-test", "version": "1.0" }
            }),
        );
        assert!(
            init.get("result").is_some(),
            "initialize must return a result, got: {init}"
        );

        client.notify("notifications/initialized", json!({}));
        client
    }

    fn send(&mut self, msg: &Value) {
        let line = serde_json::to_string(msg).unwrap();
        self.stdin.write_all(line.as_bytes()).unwrap();
        self.stdin.write_all(b"\n").unwrap();
        self.stdin.flush().unwrap();
    }

    fn read_message(&mut self) -> Value {
        let mut line = String::new();
        let n = self
            .stdout
            .read_line(&mut line)
            .expect("failed reading from server");
        assert!(n > 0, "server closed stdout unexpectedly");
        serde_json::from_str(&line)
            .unwrap_or_else(|e| panic!("server emitted invalid JSON {line:?}: {e}"))
    }

    /// Send a request and return the full JSON-RPC response object.
    pub fn request(&mut self, method: &str, params: Value) -> Value {
        self.next_id += 1;
        let id = self.next_id;
        self.send(&json!({
            "jsonrpc": "2.0",
            "id": id,
            "method": method,
            "params": params,
        }));
        // Skip any notifications the server might emit; match on our id.
        loop {
            let msg = self.read_message();
            if msg.get("id").and_then(|v| v.as_i64()) == Some(id) {
                return msg;
            }
        }
    }

    pub fn notify(&mut self, method: &str, params: Value) {
        self.send(&json!({
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
        }));
    }

    /// List the available tools (their names).
    pub fn tool_names(&mut self) -> Vec<String> {
        let resp = self.request("tools/list", json!({}));
        resp["result"]["tools"]
            .as_array()
            .expect("tools array")
            .iter()
            .map(|t| t["name"].as_str().unwrap().to_string())
            .collect()
    }

    /// Call a tool and return its structured result object.
    ///
    /// Asserts the call did not error and returns the `structuredContent`
    /// payload — the machine-readable result an MCP client consumes.
    pub fn call(&mut self, name: &str, args: Value) -> Value {
        let resp = self.request(
            "tools/call",
            json!({ "name": name, "arguments": args }),
        );
        let result = resp
            .get("result")
            .unwrap_or_else(|| panic!("tool '{name}' returned no result: {resp}"));
        let is_error = result
            .get("isError")
            .and_then(|v| v.as_bool())
            .unwrap_or(false);
        assert!(
            !is_error,
            "tool '{name}' reported an error: {}",
            result["content"]
        );
        result
            .get("structuredContent")
            .cloned()
            .unwrap_or_else(|| panic!("tool '{name}' returned no structuredContent: {result}"))
    }

    /// Call a tool expecting it to fail; returns the human-readable error text.
    pub fn call_expecting_error(&mut self, name: &str, args: Value) -> String {
        let resp = self.request(
            "tools/call",
            json!({ "name": name, "arguments": args }),
        );
        let result = &resp["result"];
        let is_error = result
            .get("isError")
            .and_then(|v| v.as_bool())
            .unwrap_or(false);
        assert!(is_error, "expected tool '{name}' to error, got: {resp}");
        result["content"][0]["text"]
            .as_str()
            .unwrap_or("")
            .to_string()
    }
}

impl Drop for McpClient {
    fn drop(&mut self) {
        let _ = self.child.kill();
        let _ = self.child.wait();
    }
}
