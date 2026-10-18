//! Context: entry point. Loads the datasets then serves MCP over stdin/stdout.
//!
//! Usage: `brazilian-soccer-mcp [DATA_DIR]`. DATA_DIR defaults to the
//! `BRAZIL_SOCCER_DATA` environment variable, then `data/kaggle`.

use std::io::{self, BufReader};
use std::path::PathBuf;
use std::process::ExitCode;

use brazilian_soccer_mcp::data::Dataset;
use brazilian_soccer_mcp::mcp;

fn data_dir() -> PathBuf {
    std::env::args_os()
        .nth(1)
        .map(PathBuf::from)
        .or_else(|| std::env::var_os("BRAZIL_SOCCER_DATA").map(PathBuf::from))
        .unwrap_or_else(|| PathBuf::from("data/kaggle"))
}

fn main() -> ExitCode {
    let dir = data_dir();
    let dataset = match Dataset::load_from_dir(&dir) {
        Ok(ds) => ds,
        Err(e) => {
            // Logs go to stderr; stdout is reserved for protocol messages.
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
    let stdout = io::stdout();
    match mcp::serve(&dataset, BufReader::new(stdin.lock()), stdout.lock()) {
        Ok(()) => ExitCode::SUCCESS,
        Err(e) => {
            eprintln!("transport error: {e}");
            ExitCode::FAILURE
        }
    }
}
