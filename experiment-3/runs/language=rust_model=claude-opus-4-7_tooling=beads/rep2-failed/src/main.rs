//! Brazilian Soccer MCP Server — binary entry point.
//!
//! Loads the Kaggle datasets and serves the Model Context Protocol over stdio:
//! it reads newline-delimited JSON-RPC 2.0 messages from stdin and writes each
//! response as a single JSON line to stdout. Diagnostics go to stderr so they
//! never corrupt the protocol stream.
//!
//! The data directory is resolved from the `SOCCER_DATA_DIR` environment
//! variable, falling back to `data/kaggle` relative to the working directory.
//!
//! Run `brazilian-soccer-mcp --help` for usage, or `--selftest` to load the
//! data and print a summary without starting the protocol loop.

use std::io::{self, BufRead, Write};

use brazilian_soccer_mcp::{mcp, Database};
use serde_json::Value;

fn data_dir() -> String {
    std::env::var("SOCCER_DATA_DIR").unwrap_or_else(|_| "data/kaggle".to_string())
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.iter().any(|a| a == "--help" || a == "-h") {
        print_help();
        return;
    }

    let dir = data_dir();
    let db = match Database::load(&dir) {
        Ok(db) => db,
        Err(e) => {
            eprintln!("error: could not load data from '{dir}': {e}");
            eprintln!("hint: set SOCCER_DATA_DIR to the directory containing the Kaggle CSVs.");
            std::process::exit(1);
        }
    };
    eprintln!(
        "brazilian-soccer-mcp: loaded {} matches and {} players from '{dir}'",
        db.matches.len(),
        db.players.len()
    );

    if args.iter().any(|a| a == "--selftest") {
        selftest(&db);
        return;
    }

    serve(&db);
}

/// The MCP stdio serve loop: one JSON-RPC message per input line.
fn serve(db: &Database) {
    let stdin = io::stdin();
    let stdout = io::stdout();
    let mut out = stdout.lock();

    for line in stdin.lock().lines() {
        let line = match line {
            Ok(l) => l,
            Err(e) => {
                eprintln!("brazilian-soccer-mcp: stdin error: {e}");
                break;
            }
        };
        if line.trim().is_empty() {
            continue;
        }
        let request: Value = match serde_json::from_str(&line) {
            Ok(v) => v,
            Err(e) => {
                // Malformed JSON: emit a JSON-RPC parse error with null id.
                let err = serde_json::json!({
                    "jsonrpc": "2.0",
                    "id": Value::Null,
                    "error": {"code": -32700, "message": format!("Parse error: {e}")}
                });
                write_line(&mut out, &err);
                continue;
            }
        };
        if let Some(response) = mcp::handle(db, &request) {
            write_line(&mut out, &response);
        }
    }
}

fn write_line(out: &mut impl Write, value: &Value) {
    if let Ok(s) = serde_json::to_string(value) {
        let _ = writeln!(out, "{s}");
        let _ = out.flush();
    }
}

/// Load-and-summarize mode: useful for verifying the data loads correctly.
fn selftest(db: &Database) {
    println!("Self-test: data loaded successfully.");
    println!("  Matches: {}", db.matches.len());
    println!("  Players: {}", db.players.len());
    for c in brazilian_soccer_mcp::queries::list_competitions(db) {
        println!(
            "  {} — {} matches ({}-{})",
            c.name, c.matches, c.first_season, c.last_season
        );
    }
}

fn print_help() {
    println!(
        "brazilian-soccer-mcp — MCP server for Brazilian soccer data\n\
         \n\
         USAGE:\n    \
         brazilian-soccer-mcp [OPTIONS]\n\
         \n\
         OPTIONS:\n    \
         -h, --help     Show this help.\n    \
         --selftest     Load the data, print a summary, and exit.\n\
         \n\
         By default the server speaks MCP (JSON-RPC 2.0) over stdio.\n\
         Set SOCCER_DATA_DIR to point at the directory holding the Kaggle CSVs\n\
         (defaults to ./data/kaggle)."
    );
}
