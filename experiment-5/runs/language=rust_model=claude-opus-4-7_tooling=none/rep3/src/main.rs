//! Binary entry point — runs the MCP server over stdio.
//!
//! Run with no args to start the JSON-RPC stdio server.  CSVs are loaded from
//! `data/kaggle/` relative to the current working directory (override with
//! the `BSMCP_DATA_DIR` env var).

use std::env;
use std::io::{self, BufReader};
use std::path::PathBuf;

use anyhow::Result;
use brazilian_soccer_mcp::data::Dataset;
use brazilian_soccer_mcp::mcp;

fn main() -> Result<()> {
    let data_dir = env::var("BSMCP_DATA_DIR")
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from("data/kaggle"));

    eprintln!("brazilian-soccer-mcp: loading datasets from {}", data_dir.display());
    let ds = Dataset::load_from_dir(&data_dir)?;
    eprintln!(
        "brazilian-soccer-mcp: loaded {} matches, {} players — ready",
        ds.matches.len(),
        ds.players.len()
    );

    let stdin = io::stdin();
    let stdout = io::stdout();
    mcp::serve(&ds, BufReader::new(stdin.lock()), stdout.lock())?;
    Ok(())
}
