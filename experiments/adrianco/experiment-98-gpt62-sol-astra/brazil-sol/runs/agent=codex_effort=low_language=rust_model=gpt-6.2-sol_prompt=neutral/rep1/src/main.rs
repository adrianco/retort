use brazilian_soccer_mcp::{Graph, serve};
use std::{error::Error, io, path::PathBuf};

fn main() -> Result<(), Box<dyn Error>> {
    let path = std::env::args_os()
        .nth(1)
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("data/kaggle"));
    let graph = Graph::load(&path)?;
    serve(&graph, io::stdin().lock(), io::stdout().lock())?;
    Ok(())
}
