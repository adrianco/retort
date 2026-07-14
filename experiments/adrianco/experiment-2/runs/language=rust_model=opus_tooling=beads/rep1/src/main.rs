use brazilian_soccer_mcp::data::Dataset;
use brazilian_soccer_mcp::mcp::{run_stdio, Server};

fn main() -> std::io::Result<()> {
    let data_dir = std::env::var("BR_SOCCER_DATA").unwrap_or_else(|_| "data/kaggle".to_string());
    eprintln!("[brazilian-soccer-mcp] loading data from {}", data_dir);
    let ds = Dataset::load_default(&data_dir)?;
    eprintln!(
        "[brazilian-soccer-mcp] loaded {} matches, {} players",
        ds.matches.len(),
        ds.players.len()
    );
    let server = Server::new(ds);
    run_stdio(server)
}
