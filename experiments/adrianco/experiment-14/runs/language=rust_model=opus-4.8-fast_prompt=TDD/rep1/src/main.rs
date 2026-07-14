// brazilian-soccer-mcp (binary) - stdio entrypoint for the MCP server.
//
// Context: wires the tested `mcp::McpServer` (over `query::Database`) to the
// real MCP stdio transport. It loads the Kaggle CSV datasets once at startup,
// then reads newline-delimited JSON-RPC messages from stdin, dispatches each
// through `handle_message`, and writes any response as one JSON line to stdout.
// Diagnostics go to stderr so the stdout JSON-RPC stream stays clean.
//
// Data directory resolution (first match wins):
//   1. CLI argument:  brazilian-soccer-mcp <data_dir>
//   2. Env var:       BSMCP_DATA_DIR
//   3. ./data/kaggle relative to the current working directory
//   4. <crate>/data/kaggle (the in-repo location)

use std::io::{self, BufRead, Write};
use std::path::PathBuf;

use brazilian_soccer_mcp::mcp::McpServer;
use brazilian_soccer_mcp::query::Database;
use serde_json::Value;

fn resolve_data_dir() -> PathBuf {
    if let Some(arg) = std::env::args().nth(1) {
        return PathBuf::from(arg);
    }
    if let Ok(env) = std::env::var("BSMCP_DATA_DIR") {
        return PathBuf::from(env);
    }
    let cwd = PathBuf::from("data/kaggle");
    if cwd.join("fifa_data.csv").exists() {
        return cwd;
    }
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("data/kaggle")
}

fn main() {
    let data_dir = resolve_data_dir();
    eprintln!(
        "[brazilian-soccer-mcp] loading data from {}",
        data_dir.display()
    );

    let db = match Database::load(&data_dir) {
        Ok(db) => db,
        Err(e) => {
            eprintln!("[brazilian-soccer-mcp] failed to load data: {}", e);
            std::process::exit(1);
        }
    };
    eprintln!(
        "[brazilian-soccer-mcp] ready: {} matches, {} players. Listening on stdio.",
        db.match_count(),
        db.player_count()
    );

    let server = McpServer::new(db);
    let stdin = io::stdin();
    let stdout = io::stdout();
    let mut out = stdout.lock();

    for line in stdin.lock().lines() {
        let line = match line {
            Ok(l) => l,
            Err(e) => {
                eprintln!("[brazilian-soccer-mcp] stdin error: {}", e);
                break;
            }
        };
        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }
        let msg: Value = match serde_json::from_str(trimmed) {
            Ok(v) => v,
            Err(e) => {
                // Parse error per JSON-RPC; no id available, so reply with null id.
                let resp = serde_json::json!({
                    "jsonrpc": "2.0",
                    "id": Value::Null,
                    "error": { "code": -32700, "message": format!("Parse error: {}", e) }
                });
                write_line(&mut out, &resp);
                continue;
            }
        };
        if let Some(resp) = server.handle_message(&msg) {
            write_line(&mut out, &resp);
        }
    }
}

fn write_line<W: Write>(out: &mut W, value: &Value) {
    match serde_json::to_string(value) {
        Ok(s) => {
            let _ = writeln!(out, "{}", s);
            let _ = out.flush();
        }
        Err(e) => eprintln!("[brazilian-soccer-mcp] failed to serialize response: {}", e),
    }
}
