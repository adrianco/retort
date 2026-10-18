//! Context: entry point. Loads the Kaggle CSVs once, then serves MCP
//! JSON-RPC messages over stdin/stdout (one JSON object per line).
//!
//! Usage: `brazilian_soccer_mcp [DATA_DIR]`. DATA_DIR defaults to the
//! `SOCCER_DATA_DIR` environment variable, then `data/kaggle`.

use std::io::{self, BufRead, Write};
use std::path::PathBuf;
use std::process::ExitCode;

use brazilian_soccer_mcp::data::Dataset;
use brazilian_soccer_mcp::mcp;

fn data_dir() -> PathBuf {
    std::env::args_os()
        .nth(1)
        .map(PathBuf::from)
        .or_else(|| std::env::var_os("SOCCER_DATA_DIR").map(PathBuf::from))
        .unwrap_or_else(|| PathBuf::from("data/kaggle"))
}

fn main() -> ExitCode {
    let dir = data_dir();
    let dataset = match Dataset::load_dir(&dir) {
        Ok(ds) => ds,
        Err(e) => {
            eprintln!("failed to load data from {}: {e}", dir.display());
            return ExitCode::FAILURE;
        }
    };
    eprintln!(
        "loaded {} matches and {} players from {}",
        dataset.matches.len(),
        dataset.players.len(),
        dir.display()
    );

    let stdin = io::stdin();
    let mut stdout = io::stdout().lock();
    for line in stdin.lock().lines() {
        let Ok(line) = line else { break };
        if line.trim().is_empty() {
            continue;
        }
        if let Some(response) = mcp::handle_message(&dataset, &line)
            && writeln!(stdout, "{response}")
                .and_then(|_| stdout.flush())
                .is_err()
        {
            break;
        }
    }
    ExitCode::SUCCESS
}
