use anyhow::Result;
use std::io::{self, BufRead, Write};
use std::path::Path;

use brazilian_soccer_mcp::data::Database;
use brazilian_soccer_mcp::mcp::process_message;

#[tokio::main]
async fn main() -> Result<()> {
    let data_dir = find_data_dir();

    eprintln!("Loading Brazilian soccer database from {:?}...", data_dir);
    let db = Database::load_from_dir(&data_dir)?;
    eprintln!(
        "Loaded {} matches and {} players.",
        db.matches.len(),
        db.players.len()
    );

    let stdin = io::stdin();
    let stdout = io::stdout();
    let mut out = stdout.lock();

    for line in stdin.lock().lines() {
        let line = line?;
        if line.trim().is_empty() {
            continue;
        }
        if let Some(response) = process_message(&db, &line) {
            writeln!(out, "{}", response)?;
            out.flush()?;
        }
    }

    Ok(())
}

fn find_data_dir() -> std::path::PathBuf {
    let cwd_data = Path::new("data");
    if cwd_data.exists() {
        return cwd_data.to_path_buf();
    }
    if let Ok(exe) = std::env::current_exe() {
        if let Some(parent) = exe.parent() {
            let exe_data = parent.join("data");
            if exe_data.exists() {
                return exe_data;
            }
            if let Some(grandparent) = parent.parent() {
                let gp_data = grandparent.join("data");
                if gp_data.exists() {
                    return gp_data;
                }
            }
        }
    }
    Path::new("data").to_path_buf()
}
