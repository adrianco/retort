// ============================================================================
// CONTEXT: Brazilian Soccer MCP Server - binary entry point
//
// Purpose:  Runs the MCP server over stdio: newline-delimited JSON-RPC 2.0
//           requests on stdin, one JSON response per line on stdout.
//           Diagnostics go to stderr so they never corrupt the protocol
//           stream.
//
// Startup:  Loads all six CSVs into memory once (~31k matches, ~18k players,
//           well under a second), then serves queries with no further I/O -
//           comfortably inside the <2s simple / <5s aggregate latency budget.
//
// Config:   Data directory resolution order:
//             1. first CLI argument
//             2. BRAZIL_SOCCER_DATA environment variable
//             3. ./data/kaggle (relative to the working directory)
//
// Usage:    cargo run --release
//           Register in an MCP client config as:
//             {"command": "/path/to/brazilian-soccer-mcp", "args": []}
// ============================================================================

use brazilian_soccer_mcp::{data::Dataset, server};
use std::io::{BufRead, Write};
use std::path::PathBuf;

fn data_dir() -> PathBuf {
    if let Some(arg) = std::env::args().nth(1) {
        return PathBuf::from(arg);
    }
    if let Ok(env) = std::env::var("BRAZIL_SOCCER_DATA") {
        return PathBuf::from(env);
    }
    PathBuf::from("data/kaggle")
}

fn main() {
    let dir = data_dir();
    let ds = match Dataset::load(&dir) {
        Ok(ds) => ds,
        Err(e) => {
            eprintln!("[brazilian-soccer-mcp] failed to load data from {}: {}", dir.display(), e);
            std::process::exit(1);
        }
    };
    eprintln!(
        "[brazilian-soccer-mcp] v{} ready: {} match records, {} players loaded from {}",
        server::SERVER_VERSION,
        ds.matches.len(),
        ds.players.len(),
        dir.display()
    );

    let stdin = std::io::stdin();
    let stdout = std::io::stdout();
    let mut out = stdout.lock();
    for line in stdin.lock().lines() {
        let line = match line {
            Ok(l) => l,
            Err(_) => break,
        };
        if line.trim().is_empty() {
            continue;
        }
        let req: serde_json::Value = match serde_json::from_str(&line) {
            Ok(v) => v,
            Err(e) => {
                let err = serde_json::json!({
                    "jsonrpc": "2.0", "id": null,
                    "error": {"code": -32700, "message": format!("Parse error: {}", e)}
                });
                let _ = writeln!(out, "{}", err);
                let _ = out.flush();
                continue;
            }
        };
        if let Some(resp) = server::handle_request(&ds, &req) {
            let _ = writeln!(out, "{}", resp);
            let _ = out.flush();
        }
    }
}
