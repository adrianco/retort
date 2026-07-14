mod data;
mod mcp;
mod tools;

#[cfg(test)]
mod tests;

use std::io::{self, BufRead, Write};

fn main() {
    let data_dir = std::env::var("DATA_DIR").unwrap_or_else(|_| "data/kaggle".to_string());
    eprintln!("INFO: loading data from '{}'", data_dir);

    let store = match data::DataStore::load(&data_dir) {
        Ok(s) => {
            eprintln!(
                "INFO: data loaded ({} matches, {} players)",
                s.matches.len(),
                s.players.len()
            );
            s
        }
        Err(e) => {
            eprintln!("ERROR: failed to load data: {}", e);
            std::process::exit(1);
        }
    };

    let stdin = io::stdin();
    let stdout = io::stdout();
    let mut stdout_lock = stdout.lock();

    for line in stdin.lock().lines() {
        let line = match line {
            Ok(l) => l,
            Err(e) => {
                eprintln!("ERROR: reading stdin: {}", e);
                break;
            }
        };

        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }

        let msg: serde_json::Value = match serde_json::from_str(trimmed) {
            Ok(v) => v,
            Err(e) => {
                eprintln!("WARN: invalid JSON: {} | input: {}", e, &trimmed[..trimmed.len().min(100)]);
                // Return parse error response (id unknown, use null)
                let resp = serde_json::json!({
                    "jsonrpc": "2.0",
                    "id": null,
                    "error": { "code": -32700, "message": "Parse error" }
                });
                let _ = writeln!(stdout_lock, "{}", resp);
                let _ = stdout_lock.flush();
                continue;
            }
        };

        if let Some(response) = mcp::handle_message(&store, &msg) {
            let serialized = match serde_json::to_string(&response) {
                Ok(s) => s,
                Err(e) => {
                    eprintln!("ERROR: serializing response: {}", e);
                    continue;
                }
            };
            if let Err(e) = writeln!(stdout_lock, "{}", serialized) {
                eprintln!("ERROR: writing response: {}", e);
                break;
            }
            if let Err(e) = stdout_lock.flush() {
                eprintln!("ERROR: flushing stdout: {}", e);
                break;
            }
        }
        // Notifications (None response) are silently ignored
    }
}
