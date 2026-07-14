//! Brazilian Soccer MCP server binary.
//!
//! Loads the bundled Kaggle datasets into an in-memory knowledge base and
//! serves Model Context Protocol requests over stdio. The dataset directory
//! defaults to `data/kaggle` and can be overridden with the first CLI argument
//! or the `SOCCER_DATA_DIR` environment variable.

use brazilian_soccer_mcp::data::Database;
use brazilian_soccer_mcp::mcp::McpServer;
use std::process::ExitCode;

fn main() -> ExitCode {
    let dir = std::env::args()
        .nth(1)
        .or_else(|| std::env::var("SOCCER_DATA_DIR").ok())
        .unwrap_or_else(|| "data/kaggle".to_string());

    eprintln!("[brazilian-soccer-mcp] loading datasets from {dir} ...");
    let db = match Database::load_from_dir(&dir) {
        Ok(db) => db,
        Err(e) => {
            eprintln!("[brazilian-soccer-mcp] failed to load datasets from {dir}: {e}");
            return ExitCode::FAILURE;
        }
    };
    eprintln!(
        "[brazilian-soccer-mcp] loaded {} matches and {} players; ready on stdio.",
        db.matches.len(),
        db.players.len()
    );

    let server = McpServer::new(db);
    if let Err(e) = server.run() {
        eprintln!("[brazilian-soccer-mcp] server error: {e}");
        return ExitCode::FAILURE;
    }
    ExitCode::SUCCESS
}
