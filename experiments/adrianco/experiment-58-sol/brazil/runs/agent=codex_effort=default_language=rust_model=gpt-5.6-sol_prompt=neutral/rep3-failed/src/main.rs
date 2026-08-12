use anyhow::{Context, Result};
use brasileirao_mcp::{McpServer, SoccerStore};
use serde_json::Value;
use std::env;
use std::io::{self, BufRead, Write};
use std::path::PathBuf;

fn main() -> Result<()> {
    let (data_dir, check_only) = arguments()?;
    let store = SoccerStore::load(&data_dir)?;
    if check_only {
        println!("{}", serde_json::to_string_pretty(store.counts())?);
        return Ok(());
    }
    eprintln!(
        "brasileirao-mcp loaded {} unique matches and {} players",
        store.counts().unique_matches,
        store.counts().total_players
    );
    let server = McpServer::new(store);
    let stdin = io::stdin();
    let mut stdout = io::stdout().lock();
    for line in stdin.lock().lines() {
        let line = line?;
        if line.trim().is_empty() {
            continue;
        }
        let response = match serde_json::from_str::<Value>(&line) {
            Ok(request) => server.handle(request),
            Err(error) => Some(
                serde_json::json!({"jsonrpc":"2.0","id":null,"error":{"code":-32700,"message":format!("parse error: {error}")}}),
            ),
        };
        if let Some(response) = response {
            serde_json::to_writer(&mut stdout, &response)?;
            stdout.write_all(b"\n")?;
            stdout.flush()?;
        }
    }
    Ok(())
}

fn arguments() -> Result<(PathBuf, bool)> {
    let mut args = env::args().skip(1);
    let mut data_dir = env::var_os("BRAZILIAN_SOCCER_DATA_DIR")
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from("data/kaggle"));
    let mut check = false;
    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--data-dir" => {
                data_dir = PathBuf::from(args.next().context("--data-dir requires a path")?)
            }
            "--check" => check = true,
            "--help" | "-h" => {
                println!("Usage: brasileirao-mcp [--data-dir PATH] [--check]\n\nRuns an MCP stdio server. Set BRAZILIAN_SOCCER_DATA_DIR to configure the six CSV files.");
                std::process::exit(0);
            }
            _ => anyhow::bail!("unknown argument: {arg}"),
        }
    }
    Ok((data_dir, check))
}
