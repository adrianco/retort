//! Entry point: `brazilian-soccer-mcp [--data-dir DIR] [--call TOOL [JSON_ARGS]]`.
//! Without `--call` it runs as an MCP stdio server.
use brazilian_soccer_mcp::{data::Db, mcp};
use std::path::PathBuf;

fn data_dir(cli: Option<String>) -> PathBuf {
    if let Some(d) = cli.or_else(|| std::env::var("BRAZILIAN_SOCCER_DATA_DIR").ok()) {
        return PathBuf::from(d);
    }
    let local = PathBuf::from("data/kaggle");
    if local.is_dir() {
        return local;
    }
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("data/kaggle")
}

fn main() {
    let mut args = std::env::args().skip(1);
    let (mut dir, mut call) = (None, None);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--data-dir" => dir = args.next(),
            "--call" => {
                let tool = args.next().unwrap_or_default();
                call = Some((tool, args.next().unwrap_or_else(|| "{}".into())));
            }
            "-h" | "--help" => {
                println!("usage: brazilian-soccer-mcp [--data-dir DIR] [--call TOOL [JSON_ARGS]]\nRuns an MCP server on stdio; --call runs a single tool and prints the answer.");
                return;
            }
            o => {
                eprintln!("unknown argument: {o}");
                std::process::exit(2);
            }
        }
    }
    let dir = data_dir(dir);
    let db = match Db::load(&dir) {
        Ok(db) => db,
        Err(e) => {
            eprintln!("failed to load data from {}: {e}", dir.display());
            std::process::exit(1);
        }
    };
    eprintln!("brazilian-soccer-mcp: loaded {} matches and {} players from {}", db.matches.len(), db.players.len(), dir.display());
    if let Some((tool, json)) = call {
        let parsed = serde_json::from_str(&json).map_err(|e| format!("invalid JSON arguments: {e}"));
        match parsed.and_then(|a| mcp::call_tool(&db, &tool, &a)) {
            Ok(t) => println!("{t}"),
            Err(e) => {
                eprintln!("Error: {e}");
                std::process::exit(1);
            }
        }
        return;
    }
    let stdin = std::io::stdin();
    if let Err(e) = mcp::serve(&db, stdin.lock(), std::io::stdout().lock()) {
        eprintln!("I/O error: {e}");
        std::process::exit(1);
    }
}
