//! Binary entry point: loads the datasets and serves the MCP server over
//! stdio, the transport used by MCP clients that launch this as a
//! subprocess (e.g. Claude Desktop, Claude Code).

use std::path::PathBuf;

use anyhow::{Context, Result};
use brazilian_soccer_mcp::server::BrazilianSoccerServer;
use rmcp::ServiceExt;

/// Resolve the data directory: `--data-dir` / first CLI arg, then the
/// `BRAZIL_SOCCER_DATA_DIR` env var, then `data/kaggle` next to the
/// executable's cargo manifest (the checked-in dataset location).
fn resolve_data_dir() -> PathBuf {
    if let Some(arg) = std::env::args().nth(1) {
        return PathBuf::from(arg);
    }
    if let Ok(env_dir) = std::env::var("BRAZIL_SOCCER_DATA_DIR") {
        return PathBuf::from(env_dir);
    }
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("data/kaggle")
}

#[tokio::main]
async fn main() -> Result<()> {
    let data_dir = resolve_data_dir();
    eprintln!(
        "brazilian-soccer-mcp: loading datasets from {}",
        data_dir.display()
    );

    let kb = brazilian_soccer_mcp::load_from_dir(&data_dir)
        .with_context(|| format!("loading datasets from {}", data_dir.display()))?;
    eprintln!(
        "brazilian-soccer-mcp: loaded {} matches and {} players",
        kb.matches.len(),
        kb.players.len()
    );

    let server = BrazilianSoccerServer::new(kb);
    let service = server
        .serve(rmcp::transport::stdio())
        .await
        .context("starting MCP server on stdio")?;
    service.waiting().await.context("MCP server loop")?;
    Ok(())
}
