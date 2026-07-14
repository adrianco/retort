use std::path::PathBuf;
use std::process::ExitCode;

use brazilian_soccer_mcp::{data::Store, mcp};

fn data_dir() -> PathBuf {
    // --data-dir <path> argument, BRAZILIAN_SOCCER_DATA env var, or the
    // default location relative to the working directory.
    let mut args = std::env::args().skip(1);
    while let Some(arg) = args.next() {
        if arg == "--data-dir" {
            if let Some(path) = args.next() {
                return PathBuf::from(path);
            }
        }
    }
    if let Ok(path) = std::env::var("BRAZILIAN_SOCCER_DATA") {
        return PathBuf::from(path);
    }
    PathBuf::from("data/kaggle")
}

fn main() -> ExitCode {
    let dir = data_dir();
    let store = match Store::load(&dir) {
        Ok(store) => store,
        Err(e) => {
            eprintln!("brazilian-soccer-mcp: failed to load data from {}: {}", dir.display(), e);
            eprintln!("hint: pass --data-dir <path> or set BRAZILIAN_SOCCER_DATA");
            return ExitCode::FAILURE;
        }
    };
    eprintln!(
        "brazilian-soccer-mcp: loaded {} matches and {} players from {}",
        store.matches.len(),
        store.players.len(),
        dir.display()
    );
    if let Err(e) = mcp::serve(&store) {
        eprintln!("brazilian-soccer-mcp: io error: {}", e);
        return ExitCode::FAILURE;
    }
    ExitCode::SUCCESS
}
