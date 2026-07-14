//! Brazilian Soccer MCP server binary.
//!
//! Usage:
//!   brazilian-soccer-mcp                 Run the MCP server on stdio (default).
//!   brazilian-soccer-mcp selftest        Print answers to sample questions.
//!   brazilian-soccer-mcp call <tool> '<json-args>'   Run one tool and print.

use std::io::{self, Write};

use brazilian_soccer_mcp::{data::Dataset, mcp};
use serde_json::{json, Value};

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();

    let ds = match Dataset::load_default() {
        Ok(ds) => ds,
        Err(e) => {
            eprintln!("Error loading data: {e}");
            eprintln!(
                "Set SOCCER_DATA_DIR to the directory containing the CSV files (default: {}).",
                brazilian_soccer_mcp::data::DEFAULT_DATA_DIR
            );
            std::process::exit(1);
        }
    };

    match args.first().map(String::as_str) {
        None | Some("serve") => {
            eprintln!(
                "brazilian-soccer-mcp: loaded {} matches and {} players. Listening on stdio.",
                ds.matches.len(),
                ds.players.len()
            );
            let stdin = io::stdin();
            let stdout = io::stdout();
            if let Err(e) = mcp::serve(&ds, stdin.lock(), stdout.lock()) {
                eprintln!("server error: {e}");
                std::process::exit(1);
            }
        }
        Some("selftest") => run_selftest(&ds),
        Some("call") => {
            let tool = args.get(1).map(String::as_str).unwrap_or("");
            let json_args: Value = args
                .get(2)
                .map(|s| serde_json::from_str(s).unwrap_or_else(|_| json!({})))
                .unwrap_or_else(|| json!({}));
            match mcp::dispatch_tool(&ds, tool, &json_args) {
                Ok(text) => println!("{text}"),
                Err(e) => {
                    eprintln!("{e}");
                    std::process::exit(1);
                }
            }
        }
        Some(other) => {
            eprintln!("Unknown command: {other}");
            eprintln!("Commands: serve (default), selftest, call <tool> '<json>'");
            std::process::exit(2);
        }
    }
}

fn run_selftest(ds: &Dataset) {
    let cases: &[(&str, Value)] = &[
        ("list_datasets", json!({})),
        ("search_matches", json!({ "team": "Flamengo", "team2": "Fluminense", "limit": 5 })),
        ("team_stats", json!({ "team": "Corinthians", "season": 2022, "venue": "home" })),
        ("standings", json!({ "season": 2019 })),
        ("competition_stats", json!({ "competition": "Brasileirão" })),
        ("search_players", json!({ "name": "Neymar" })),
        ("top_players", json!({ "nationality": "Brazil", "limit": 5 })),
        ("head_to_head", json!({ "team1": "Palmeiras", "team2": "Santos" })),
    ];
    let out = io::stdout();
    let mut w = out.lock();
    for (tool, args) in cases {
        let _ = writeln!(w, "\n========== {tool} {args} ==========");
        match mcp::dispatch_tool(ds, tool, args) {
            Ok(text) => {
                let _ = writeln!(w, "{text}");
            }
            Err(e) => {
                let _ = writeln!(w, "ERROR: {e}");
            }
        }
    }
}
