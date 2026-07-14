//! ============================================================================
//! Binary: brazilian-soccer-mcp
//!
//! Context
//! -------
//! Entry point and stdio transport for the Brazilian Soccer MCP server. It loads
//! the CSV datasets once at startup, then runs a line-delimited JSON-RPC 2.0
//! loop over stdin/stdout — the standard MCP stdio transport an LLM host speaks.
//!
//! Usage:
//!   brazilian-soccer-mcp [DATA_DIR]      # serve MCP over stdio (default ./data/kaggle)
//!   brazilian-soccer-mcp --selftest      # load data, print a summary, exit
//!
//! Diagnostics go to stderr so they never corrupt the JSON-RPC stream on stdout.
//! ============================================================================

use std::io::{self, BufRead, Write};
use std::path::PathBuf;

use brazilian_soccer_mcp::{Database, Server};

fn data_dir_from_args(args: &[String]) -> PathBuf {
    args.iter()
        .find(|a| !a.starts_with("--"))
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from("data/kaggle"))
}

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let data_dir = data_dir_from_args(&args);

    eprintln!("[brazilian-soccer-mcp] loading data from {}", data_dir.display());
    let db = Database::load_from_dir(&data_dir);
    let report = db.report();
    eprintln!(
        "[brazilian-soccer-mcp] loaded {} matches, {} players (files: {}; missing: {})",
        db.match_count(),
        db.player_count(),
        report.files_loaded.join(", "),
        if report.files_missing.is_empty() {
            "none".to_string()
        } else {
            report.files_missing.join(", ")
        }
    );

    if args.iter().any(|a| a == "--selftest") {
        let server = Server::new(db);
        println!("{}", server.call_tool("list_competitions", &serde_json::json!({})).unwrap_or_default());
        return;
    }

    let server = Server::new(db);
    if let Err(e) = serve_stdio(&server) {
        eprintln!("[brazilian-soccer-mcp] fatal: {}", e);
        std::process::exit(1);
    }
}

/// Run the JSON-RPC 2.0 loop: one request object per input line, one response
/// object per output line.
fn serve_stdio(server: &Server) -> io::Result<()> {
    let stdin = io::stdin();
    let stdout = io::stdout();
    let mut out = stdout.lock();

    for line in stdin.lock().lines() {
        let line = line?;
        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }
        let request: serde_json::Value = match serde_json::from_str(trimmed) {
            Ok(v) => v,
            Err(e) => {
                let resp = serde_json::json!({
                    "jsonrpc": "2.0",
                    "id": null,
                    "error": { "code": -32700, "message": format!("Parse error: {}", e) }
                });
                writeln!(out, "{}", resp)?;
                out.flush()?;
                continue;
            }
        };

        if let Some(response) = server.handle(&request) {
            writeln!(out, "{}", serde_json::to_string(&response)?)?;
            out.flush()?;
        }
    }
    Ok(())
}
