// =============================================================================
// Context
// -----------------------------------------------------------------------------
// Binary:  brazilian-soccer-mcp
// Purpose: Entry point for the Brazilian Soccer MCP server. Loads the six
//          Kaggle CSV datasets into memory once at startup, then serves the
//          Model Context Protocol over stdio (JSON-RPC 2.0, newline-delimited).
//
// Usage:
//   brazilian-soccer-mcp [DATA_DIR]
//     DATA_DIR defaults to ./data/kaggle. Override via arg or the
//     BR_SOCCER_DATA_DIR environment variable.
//
//   Diagnostic mode (no stdio server, prints a load summary and exits):
//     brazilian-soccer-mcp --check [DATA_DIR]
//
// Wiring:  data.rs (load) -> mcp.rs (serve) over the query engine in queries.rs.
// =============================================================================

use brazilian_soccer_mcp::data::Dataset;
use brazilian_soccer_mcp::mcp;
use std::io::{self, Write};
use std::path::PathBuf;
use std::process::ExitCode;

fn resolve_data_dir(args: &[String]) -> PathBuf {
    // First non-flag argument wins, then env var, then default.
    if let Some(arg) = args.iter().find(|a| !a.starts_with("--")) {
        return PathBuf::from(arg);
    }
    if let Ok(env) = std::env::var("BR_SOCCER_DATA_DIR") {
        return PathBuf::from(env);
    }
    PathBuf::from("data/kaggle")
}

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let check_only = args.iter().any(|a| a == "--check");
    let data_dir = resolve_data_dir(&args);

    eprintln!("[info] loading datasets from {}", data_dir.display());
    let dataset = match Dataset::load_from_dir(&data_dir) {
        Ok(ds) => ds,
        Err(e) => {
            eprintln!("[error] {e}");
            return ExitCode::FAILURE;
        }
    };
    eprintln!(
        "[info] loaded {} matches and {} players",
        dataset.matches.len(),
        dataset.players.len()
    );

    if check_only {
        let mut out = io::stdout();
        let _ = writeln!(out, "{}", dataset.list_competitions());
        let _ = writeln!(
            out,
            "Players: {} | Matches: {}",
            dataset.players.len(),
            dataset.matches.len()
        );
        return ExitCode::SUCCESS;
    }

    eprintln!("[info] brazilian-soccer-mcp ready on stdio");
    let stdin = io::stdin();
    let stdout = io::stdout();
    if let Err(e) = mcp::serve_stdio(&dataset, stdin.lock(), stdout.lock()) {
        eprintln!("[error] server loop failed: {e}");
        return ExitCode::FAILURE;
    }
    ExitCode::SUCCESS
}
