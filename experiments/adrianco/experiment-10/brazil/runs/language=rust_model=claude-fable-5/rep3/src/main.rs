// =============================================================================
// CONTEXT: Brazilian Soccer MCP Server — binary entry point
//
// Starts the MCP server on stdio. The data directory containing the six
// Kaggle CSVs is resolved in order from:
//   1. first CLI argument
//   2. BRAZILIAN_SOCCER_DATA environment variable
//   3. ./data/kaggle (relative to the current working directory)
//
// All diagnostics go to stderr; stdout carries only JSON-RPC messages, as the
// MCP stdio transport requires.
// =============================================================================

use anyhow::{Context, Result};
use brazilian_soccer_mcp::data::Data;
use brazilian_soccer_mcp::server::Server;
use std::io::{stdin, stdout};
use std::path::PathBuf;

fn data_dir() -> PathBuf {
    if let Some(arg) = std::env::args().nth(1) {
        return PathBuf::from(arg);
    }
    if let Ok(env) = std::env::var("BRAZILIAN_SOCCER_DATA") {
        return PathBuf::from(env);
    }
    PathBuf::from("data/kaggle")
}

fn main() -> Result<()> {
    let dir = data_dir();
    let started = std::time::Instant::now();
    let data = Data::load(&dir)
        .with_context(|| format!("loading datasets from {}", dir.display()))?;
    eprintln!(
        "[brazilian-soccer-mcp] loaded {} matches and {} players from {} in {:?}",
        data.matches.len(),
        data.players.len(),
        dir.display(),
        started.elapsed()
    );
    let server = Server::new(data);
    server.run(stdin().lock(), stdout().lock())?;
    Ok(())
}
