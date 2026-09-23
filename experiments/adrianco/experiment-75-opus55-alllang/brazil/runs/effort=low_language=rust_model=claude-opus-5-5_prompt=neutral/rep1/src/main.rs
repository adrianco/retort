use brazilian_soccer_mcp::{mcp, query::Engine};
use std::io::{BufRead, Write};

fn main() {
    let dir = std::env::args()
        .nth(1)
        .or_else(|| std::env::var("SOCCER_DATA_DIR").ok())
        .unwrap_or_else(|| "data/kaggle".into());
    let engine = match Engine::load(&dir) {
        Ok(e) => e,
        Err(err) => {
            eprintln!("failed to load data from {dir}: {err}");
            std::process::exit(1);
        }
    };
    eprintln!("{}", engine.dataset_summary());
    let stdin = std::io::stdin();
    let mut out = std::io::stdout().lock();
    for line in stdin.lock().lines() {
        let Ok(line) = line else { break };
        if line.trim().is_empty() {
            continue;
        }
        let resp = match serde_json::from_str::<serde_json::Value>(&line) {
            Ok(req) => mcp::handle(&engine, &req),
            Err(e) => Some(serde_json::json!({"jsonrpc": "2.0", "id": null,
                "error": {"code": -32700, "message": format!("Parse error: {e}")}})),
        };
        if let Some(r) = resp {
            let _ = writeln!(out, "{r}");
            let _ = out.flush();
        }
    }
}
