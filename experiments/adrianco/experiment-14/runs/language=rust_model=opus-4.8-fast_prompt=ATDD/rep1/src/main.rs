//! Brazilian Soccer MCP Server.
//!
//! An MCP server exposing a knowledge interface over the provided Brazilian
//! soccer datasets (matches across the Brasileirão, Copa do Brasil and Copa
//! Libertadores, plus the FIFA player database). It speaks JSON-RPC 2.0 over
//! stdio so an LLM host can answer natural-language questions about players,
//! teams, matches and competitions by calling the exposed tools.
//!
//! Data directory: `$SOCCER_DATA_DIR` if set, otherwise `data/kaggle`.

mod data;
mod mcp;
mod model;
mod normalize;
mod teams;
mod tools;

use std::io::{self, BufRead, Write};
use std::path::PathBuf;

use data::DataStore;
use mcp::Server;

fn main() {
    let dir = std::env::var("SOCCER_DATA_DIR")
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from("data/kaggle"));

    let store = match DataStore::load(&dir) {
        Ok(s) => s,
        Err(e) => {
            eprintln!("brazilian-soccer-mcp: failed to load data from {}: {e}", dir.display());
            std::process::exit(1);
        }
    };
    eprintln!(
        "brazilian-soccer-mcp: loaded {} matches and {} players from {}",
        store.matches.len(),
        store.players.len(),
        dir.display()
    );

    let server = Server::new(store);
    let stdin = io::stdin();
    let stdout = io::stdout();
    let mut out = stdout.lock();

    for line in stdin.lock().lines() {
        let line = match line {
            Ok(l) => l,
            Err(_) => break,
        };
        if line.trim().is_empty() {
            continue;
        }
        let msg: serde_json::Value = match serde_json::from_str(&line) {
            Ok(v) => v,
            Err(e) => {
                // Parse error: reply with a JSON-RPC error (null id).
                let resp = serde_json::json!({
                    "jsonrpc": "2.0",
                    "id": null,
                    "error": { "code": -32700, "message": format!("parse error: {e}") }
                });
                writeln!(out, "{resp}").ok();
                out.flush().ok();
                continue;
            }
        };

        if let Some(response) = server.handle(&msg) {
            writeln!(out, "{response}").expect("failed writing response");
            out.flush().expect("failed flushing stdout");
        }
    }
}
