//! Brazilian Soccer MCP server — binary entry point.
//!
//! Context: thin wrapper that resolves the dataset directory, loads every
//! provided Kaggle CSV into an in-memory `Database`, and then serves MCP
//! JSON-RPC requests on stdin/stdout. All diagnostic output goes to stderr so
//! it never corrupts the protocol stream on stdout.
//!
//! Usage:
//!   brazilian-soccer-mcp [DATA_DIR]
//! `DATA_DIR` defaults to the `SOCCER_DATA_DIR` env var, then `data/kaggle`.

use brazilian_soccer_mcp::{data::Database, mcp};

fn main() {
    let data_dir = std::env::args()
        .nth(1)
        .or_else(|| std::env::var("SOCCER_DATA_DIR").ok())
        .unwrap_or_else(|| "data/kaggle".to_string());

    eprintln!("[brazilian-soccer-mcp] loading datasets from '{data_dir}'...");
    let db = Database::load(&data_dir);
    eprintln!(
        "[brazilian-soccer-mcp] loaded {} matches and {} players across {} competitions",
        db.matches.len(),
        db.players.len(),
        db.competitions().len()
    );

    if let Err(e) = mcp::serve(&db) {
        eprintln!("[brazilian-soccer-mcp] fatal: {e}");
        std::process::exit(1);
    }
}
