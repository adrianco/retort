use std::path::PathBuf;
use std::sync::Arc;

use anyhow::Context;
use rmcp::{ServiceExt, transport::stdio};

use brazilian_soccer_mcp::server::SoccerServer;
use brazilian_soccer_mcp::store::Store;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt()
        .with_writer(std::io::stderr)
        .init();

    let data_dir = std::env::args()
        .nth(1)
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("data/kaggle"));

    let store = Store::load_from_dir(&data_dir)
        .with_context(|| format!("failed to load datasets from {}", data_dir.display()))?;
    tracing::info!(
        matches = store.matches.len(),
        players = store.players.len(),
        "loaded Brazilian soccer datasets"
    );

    let server = SoccerServer::new(Arc::new(store));
    let service = server.serve(stdio()).await?;
    service.waiting().await?;
    Ok(())
}
