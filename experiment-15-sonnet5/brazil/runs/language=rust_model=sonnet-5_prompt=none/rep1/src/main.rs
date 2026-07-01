use std::path::PathBuf;
use std::sync::Arc;

use anyhow::{Context, Result};
use rmcp::ServiceExt;
use rmcp::transport::stdio;

use brazilian_soccer_mcp::server::SoccerServer;
use brazilian_soccer_mcp::store::Store;

/// Resolve the directory containing the Kaggle CSVs: an explicit CLI
/// argument, then `SOCCER_DATA_DIR`, then `./data/kaggle` relative to the
/// current working directory, falling back to the directory baked in at
/// compile time so the server also works when launched from elsewhere.
fn resolve_data_dir() -> PathBuf {
    if let Some(arg) = std::env::args().nth(1) {
        return PathBuf::from(arg);
    }
    if let Ok(env_dir) = std::env::var("SOCCER_DATA_DIR") {
        return PathBuf::from(env_dir);
    }
    let cwd_candidate = PathBuf::from("data/kaggle");
    if cwd_candidate.exists() {
        return cwd_candidate;
    }
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("data/kaggle")
}

#[tokio::main]
async fn main() -> Result<()> {
    // All logging must go to stderr: stdout is reserved for the MCP
    // JSON-RPC stream when using the stdio transport.
    tracing_subscriber::fmt().with_writer(std::io::stderr).init();

    let data_dir = resolve_data_dir();
    tracing::info!("loading Brazilian soccer datasets from {}", data_dir.display());
    let store = Arc::new(
        Store::load(&data_dir).with_context(|| format!("loading datasets from {}", data_dir.display()))?,
    );
    tracing::info!(
        "loaded {} matches and {} players",
        store.matches.len(),
        store.players.len()
    );

    let server = SoccerServer::new(store);
    let service = server.serve(stdio()).await?;
    service.waiting().await?;
    Ok(())
}
