// =============================================================================
// Context: Brazilian Soccer MCP Server
// File:    src/main.rs
// Purpose: Binary entry point. Loads the datasets once at startup, then runs a
//          newline-delimited JSON-RPC loop over stdin/stdout implementing the
//          Model Context Protocol. Each line is one request; each response is
//          written as one line. Diagnostics go to stderr so they never corrupt
//          the protocol stream on stdout.
//
//          The data directory defaults to "data/kaggle" and can be overridden
//          with the SOCCER_DATA_DIR environment variable or a single CLI arg.
// =============================================================================

use std::io::{self, BufRead, Write};

use brazilian_soccer_mcp::data::Database;
use brazilian_soccer_mcp::mcp;

fn main() {
    let data_dir = std::env::args()
        .nth(1)
        .or_else(|| std::env::var("SOCCER_DATA_DIR").ok())
        .unwrap_or_else(|| "data/kaggle".to_string());

    eprintln!("[brazilian-soccer-mcp] loading data from {data_dir} ...");
    let db = match Database::load_from_dir(&data_dir) {
        Ok(db) => db,
        Err(e) => {
            eprintln!("[brazilian-soccer-mcp] failed to load data: {e}");
            std::process::exit(1);
        }
    };
    eprintln!(
        "[brazilian-soccer-mcp] loaded {} matches and {} players. Ready.",
        db.matches.len(),
        db.players.len()
    );

    let stdin = io::stdin();
    let stdout = io::stdout();
    let mut out = stdout.lock();

    for line in stdin.lock().lines() {
        let line = match line {
            Ok(l) => l,
            Err(e) => {
                eprintln!("[brazilian-soccer-mcp] stdin error: {e}");
                break;
            }
        };
        if line.trim().is_empty() {
            continue;
        }
        let request: serde_json::Value = match serde_json::from_str(&line) {
            Ok(v) => v,
            Err(e) => {
                eprintln!("[brazilian-soccer-mcp] invalid JSON: {e}");
                let resp = serde_json::json!({
                    "jsonrpc": "2.0",
                    "id": null,
                    "error": { "code": -32700, "message": "Parse error" }
                });
                writeln!(out, "{resp}").ok();
                out.flush().ok();
                continue;
            }
        };

        if let Some(response) = mcp::handle_request(&db, &request) {
            if let Err(e) = writeln!(out, "{response}") {
                eprintln!("[brazilian-soccer-mcp] stdout error: {e}");
                break;
            }
            out.flush().ok();
        }
    }
}
