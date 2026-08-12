use brazilian_soccer_mcp::{DataStore, McpServer, SoccerService};
use std::{env, path::PathBuf};

fn main() {
    if let Err(error) = run() {
        eprintln!("brazilian-soccer-mcp: {error}");
        std::process::exit(1);
    }
}

fn run() -> Result<(), Box<dyn std::error::Error>> {
    let data_dir = env::var_os("BRAZILIAN_SOCCER_DATA_DIR")
        .map(PathBuf::from)
        // MCP clients commonly launch a configured executable with their own
        // working directory. Resolve bundled data from the crate location so
        // the documented absolute-binary entrypoint works from anywhere.
        .unwrap_or_else(|| PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("data/kaggle"));
    let (store, report) = DataStore::load(&data_dir)?;
    eprintln!(
        "loaded {} matches and {} players from {} files ({} duplicate match rows merged)",
        store.matches.len(),
        store.players.len(),
        report.files_loaded,
        report.duplicate_matches_merged
    );
    McpServer::new(SoccerService::new(store)).serve_stdio()?;
    Ok(())
}
