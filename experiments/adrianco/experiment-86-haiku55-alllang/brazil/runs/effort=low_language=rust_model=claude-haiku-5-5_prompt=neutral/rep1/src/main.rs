//! Entry point: loads the datasets, then serves MCP over stdin/stdout.
//!
//! Usage: `brazilian-soccer-mcp [DATA_DIR]`. `DATA_DIR` defaults to the
//! `BRAZIL_SOCCER_DATA_DIR` environment variable, then `data/kaggle`.
//! Logs go to stderr so they never corrupt the protocol stream.

use std::io::{self, BufRead, Write};
use std::path::PathBuf;
use std::process::ExitCode;
use std::time::Instant;

use brazilian_soccer_mcp::data::Dataset;
use brazilian_soccer_mcp::mcp;

fn main() -> ExitCode {
    let dir = std::env::args_os()
        .nth(1)
        .map(PathBuf::from)
        .or_else(|| std::env::var_os("BRAZIL_SOCCER_DATA_DIR").map(PathBuf::from))
        .unwrap_or_else(|| PathBuf::from("data/kaggle"));

    let started = Instant::now();
    let dataset = match Dataset::load(&dir) {
        Ok(dataset) => dataset,
        Err(err) => {
            eprintln!("failed to load datasets from {}: {err}", dir.display());
            return ExitCode::FAILURE;
        }
    };
    eprintln!(
        "loaded {} matches and {} players from {} in {:?}",
        dataset.matches.len(),
        dataset.players.len(),
        dir.display(),
        started.elapsed()
    );

    if let Err(err) = serve(&dataset) {
        eprintln!("transport error: {err}");
        return ExitCode::FAILURE;
    }
    ExitCode::SUCCESS
}

fn serve(dataset: &Dataset) -> io::Result<()> {
    let stdin = io::stdin();
    let mut stdout = io::stdout().lock();
    for line in stdin.lock().lines() {
        let line = line?;
        if line.trim().is_empty() {
            continue;
        }
        if let Some(response) = mcp::handle_line(dataset, &line) {
            writeln!(stdout, "{response}")?;
            stdout.flush()?;
        }
    }
    Ok(())
}
