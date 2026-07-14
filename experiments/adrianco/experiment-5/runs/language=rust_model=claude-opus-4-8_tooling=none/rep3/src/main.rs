//! ============================================================================
//! Binary: brazilian-soccer-mcp
//! Project: Brazilian Soccer MCP Server (Rust)
//!
//! Context:
//!   Executable entry point. It loads all datasets from the data directory and
//!   then runs the MCP server over stdio so an MCP-capable LLM client can call
//!   the soccer query tools. The data directory defaults to `data/kaggle`
//!   (relative to the working directory) but can be overridden with the first
//!   CLI argument or the `SOCCER_DATA_DIR` environment variable.
//!
//!   A `--selftest` flag is provided to load the data, print a summary and run
//!   a few representative queries without entering the stdio loop — handy for
//!   verifying the build against the real CSVs from a shell.
//!
//!   Startup diagnostics are written to stderr so they never corrupt the
//!   JSON-RPC stream on stdout.
//! ============================================================================

use brazilian_soccer_mcp::mcp;
use brazilian_soccer_mcp::{format, Store};
use std::path::PathBuf;

fn resolve_data_dir() -> PathBuf {
    // Priority: explicit CLI arg (non-flag) > env var > default.
    if let Some(arg) = std::env::args().nth(1) {
        if !arg.starts_with("--") {
            return PathBuf::from(arg);
        }
    }
    if let Ok(env) = std::env::var("SOCCER_DATA_DIR") {
        if !env.is_empty() {
            return PathBuf::from(env);
        }
    }
    PathBuf::from("data/kaggle")
}

fn main() {
    let data_dir = resolve_data_dir();
    eprintln!("[brazilian-soccer-mcp] loading data from {}", data_dir.display());

    let store = match Store::load_from_dir(&data_dir) {
        Ok(s) => s,
        Err(e) => {
            eprintln!("[brazilian-soccer-mcp] fatal: could not load data: {e}");
            std::process::exit(1);
        }
    };

    eprintln!("[brazilian-soccer-mcp] {}", format::store_banner(&store));

    if std::env::args().any(|a| a == "--selftest") {
        run_selftest(&store);
        return;
    }

    eprintln!("[brazilian-soccer-mcp] ready; serving MCP over stdio.");
    if let Err(e) = mcp::serve_stdio(&store) {
        eprintln!("[brazilian-soccer-mcp] I/O error: {e}");
        std::process::exit(1);
    }
}

/// Run a handful of representative queries and print the formatted answers.
fn run_selftest(store: &Store) {
    use serde_json::json;
    let cases: &[(&str, serde_json::Value)] = &[
        ("data_summary", json!({})),
        ("head_to_head", json!({"team_a": "Flamengo", "team_b": "Fluminense"})),
        ("team_stats", json!({"team": "Corinthians", "season": 2022, "venue": "home"})),
        ("search_players", json!({"nationality": "Brazil", "limit": 5})),
        ("standings", json!({"season": 2019})),
        ("average_goals", json!({"competition": "Brasileirão"})),
        ("biggest_wins", json!({"limit": 5})),
    ];
    for (tool, args) in cases {
        println!("\n===== {tool} =====");
        match mcp::dispatch_tool(store, tool, args) {
            Ok(text) => println!("{text}"),
            Err(e) => println!("error: {e}"),
        }
    }
}
