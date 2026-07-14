//! ============================================================================
//! Context
//! ----------------------------------------------------------------------------
//! Binary:   brazilian-soccer-mcp
//! Purpose:  Entry point. Loads the datasets once at startup, then runs the MCP
//!           server over the stdio transport: newline-delimited JSON-RPC 2.0
//!           messages on stdin/stdout (the standard MCP stdio framing). All
//!           diagnostics go to stderr so they never corrupt the protocol
//!           stream on stdout.
//!
//! Usage:
//!   brazilian-soccer-mcp                # reads data from ./data/kaggle
//!   SOCCER_DATA_DIR=/path brazilian-soccer-mcp
//!   brazilian-soccer-mcp --self-test    # load data, print a summary, exit
//! ============================================================================

use std::io::{BufRead, Write};

use brazilian_soccer_mcp::{mcp::Server, Database};

fn main() {
    let args: Vec<String> = std::env::args().collect();

    eprintln!("[brazilian-soccer-mcp] loading datasets...");
    let db = match Database::load(None) {
        Ok(db) => db,
        Err(e) => {
            eprintln!("[brazilian-soccer-mcp] FATAL: failed to load data: {}", e);
            std::process::exit(1);
        }
    };
    eprintln!(
        "[brazilian-soccer-mcp] loaded {} matches and {} players.",
        db.matches.len(),
        db.players.len()
    );

    // Optional self-test mode: handy for CI / smoke checks without a client.
    if args.iter().any(|a| a == "--self-test") {
        self_test(&db);
        return;
    }

    let server = Server::new(db);
    run_stdio(&server);
}

/// The stdio JSON-RPC loop. Reads one JSON message per line, dispatches it, and
/// writes any response as a single line.
fn run_stdio(server: &Server) {
    let stdin = std::io::stdin();
    let stdout = std::io::stdout();
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

        let msg: serde_json::Value = match serde_json::from_str(trimmed) {
            Ok(v) => v,
            Err(e) => {
                // Per JSON-RPC, reply with a parse error (no id is known).
                let err = serde_json::json!({
                    "jsonrpc": "2.0",
                    "id": serde_json::Value::Null,
                    "error": { "code": -32700, "message": format!("Parse error: {}", e) }
                });
                write_line(&mut out, &err);
                continue;
            }
        };

        if let Some(response) = server.handle_message(&msg) {
            write_line(&mut out, &response);
        }
    }
}

fn write_line<W: Write>(out: &mut W, value: &serde_json::Value) {
    if let Ok(s) = serde_json::to_string(value) {
        let _ = writeln!(out, "{}", s);
        let _ = out.flush();
    }
}

/// Loads everything and prints a few sample answers to stderr for a smoke test.
fn self_test(db: &Database) {
    let server = Server::new(Database {
        matches: db.matches.clone(),
        players: db.players.clone(),
    });

    let samples: &[(&str, serde_json::Value)] = &[
        (
            "head_to_head",
            serde_json::json!({"team_a": "Flamengo", "team_b": "Fluminense"}),
        ),
        ("standings", serde_json::json!({"season": 2019})),
        (
            "search_players",
            serde_json::json!({"nationality": "Brazil", "limit": 5}),
        ),
        ("competition_stats", serde_json::json!({"competition": "Brasileirão"})),
    ];

    for (tool, args) in samples {
        eprintln!("\n=== {} {} ===", tool, args);
        match server.dispatch_tool(tool, args) {
            Ok(text) => eprintln!("{}", text),
            Err(e) => eprintln!("error: {}", e),
        }
    }
}
