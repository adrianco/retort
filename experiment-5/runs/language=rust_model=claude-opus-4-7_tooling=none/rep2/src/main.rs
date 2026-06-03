use anyhow::{Context, Result};

use brazilian_soccer_mcp::data::{default_data_dir, Dataset};
use brazilian_soccer_mcp::mcp::Server;

fn main() -> Result<()> {
    let dir = default_data_dir();
    eprintln!("brazilian-soccer-mcp: loading data from {}", dir.display());
    let dataset = Dataset::load_from_dir(&dir)
        .with_context(|| format!("loading dataset from {}", dir.display()))?;
    eprintln!(
        "brazilian-soccer-mcp: loaded {} matches, {} players. Ready on stdio.",
        dataset.matches.len(),
        dataset.players.len()
    );

    Server::new(dataset).serve_stdio()
}
