use std::path::PathBuf;

use anyhow::Result;
use brazilian_soccer_mcp::mcp::Server;
use brazilian_soccer_mcp::Store;

fn main() -> Result<()> {
    let data_dir = std::env::var("BSMCP_DATA_DIR")
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from("data"));

    eprintln!(
        "brazilian-soccer-mcp: loading data from {}",
        data_dir.display()
    );
    let store = Store::load(&data_dir)?;
    eprintln!(
        "brazilian-soccer-mcp: loaded {} matches, {} players",
        store.matches.len(),
        store.players.len()
    );

    let server = Server::new(store);
    server.run_stdio()?;
    Ok(())
}
