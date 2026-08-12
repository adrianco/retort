use brazilian_soccer_mcp::{DataStore, SoccerService, mcp::McpServer};
use std::{env, path::PathBuf, process::ExitCode};

fn main() -> ExitCode {
    match run() {
        Ok(()) => ExitCode::SUCCESS,
        Err(message) => {
            eprintln!("brazilian-soccer-mcp: {message}");
            ExitCode::FAILURE
        }
    }
}

fn run() -> Result<(), String> {
    let mut data_dir = env::var_os("BRAZILIAN_SOCCER_DATA_DIR")
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from("data/kaggle"));
    let mut check_data = false;
    let mut args = env::args().skip(1);
    while let Some(argument) = args.next() {
        match argument.as_str() {
            "--data-dir" => {
                data_dir = PathBuf::from(args.next().ok_or("--data-dir requires a path")?)
            }
            "--check-data" => check_data = true,
            "-h" | "--help" => {
                println!(
                    "brazilian-soccer-mcp {}\n\nUSAGE:\n  brazilian-soccer-mcp [--data-dir PATH] [--check-data]\n\nBy default the server loads data/kaggle and speaks MCP JSON-RPC over stdio.\nSet BRAZILIAN_SOCCER_DATA_DIR to configure the dataset location.",
                    env!("CARGO_PKG_VERSION")
                );
                return Ok(());
            }
            value => return Err(format!("unknown argument '{value}'")),
        }
    }

    let store = DataStore::load(&data_dir).map_err(|error| error.to_string())?;
    if check_data {
        println!(
            "Loaded {} match records, {} players, and {} normalized teams.",
            store.matches.len(),
            store.players.len(),
            store.teams.len()
        );
        for report in &store.reports {
            println!(
                "{}: {}/{} rows loaded ({} skipped)",
                report.file, report.loaded, report.rows, report.skipped
            );
        }
        return Ok(());
    }
    eprintln!(
        "Loaded {} match records and {} players from {}",
        store.matches.len(),
        store.players.len(),
        data_dir.display()
    );
    McpServer::new(SoccerService::new(store))
        .run_stdio()
        .map_err(|error| error.to_string())
}
