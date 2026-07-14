use brazilian_soccer_mcp::{mcp, Dataset};
use std::io::{self, BufRead, Write};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let data_dir = std::env::var("DATA_DIR").unwrap_or_else(|_| "data/kaggle".to_string());
    let ds = Dataset::load_from_dir(&data_dir)?;
    eprintln!(
        "Loaded {} matches, {} players from {}",
        ds.matches.len(),
        ds.players.len(),
        data_dir
    );

    let stdin = io::stdin();
    let stdout = io::stdout();
    let mut out = stdout.lock();
    for line in stdin.lock().lines() {
        let line = line?;
        if line.trim().is_empty() {
            continue;
        }
        let req: serde_json::Value = match serde_json::from_str(&line) {
            Ok(v) => v,
            Err(e) => {
                writeln!(out, "{{\"error\":\"parse: {}\"}}", e)?;
                continue;
            }
        };
        let resp = mcp::handle_request(&ds, &req);
        writeln!(out, "{}", resp.to_string())?;
        out.flush()?;
    }
    Ok(())
}
