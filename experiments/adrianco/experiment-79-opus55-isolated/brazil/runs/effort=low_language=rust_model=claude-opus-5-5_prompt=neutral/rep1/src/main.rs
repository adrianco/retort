//! Entry point.
//!
//!   brazilian-soccer-mcp [--data-dir DIR]                 run the MCP server on stdio
//!   brazilian-soccer-mcp [--data-dir DIR] call TOOL JSON   run one tool and print the answer
//!   brazilian-soccer-mcp tools                             list the available tools

use brazilian_soccer_mcp::data::{find_data_dir, Database};
use brazilian_soccer_mcp::mcp;
use std::process::ExitCode;

fn run() -> Result<(), String> {
    let mut args: Vec<String> = std::env::args().skip(1).collect();
    let mut data_dir = None;
    if let Some(i) = args.iter().position(|a| a == "--data-dir") {
        if i + 1 >= args.len() {
            return Err("--data-dir requires a path".into());
        }
        data_dir = Some(args.remove(i + 1));
        args.remove(i);
    }
    if args.first().map(String::as_str) == Some("tools") {
        for t in mcp::tool_definitions().as_array().into_iter().flatten() {
            println!("{} - {}", t["name"].as_str().unwrap_or(""), t["description"].as_str().unwrap_or(""));
        }
        return Ok(());
    }
    let db = Database::load(&find_data_dir(data_dir.as_deref())?)?;
    match args.first().map(String::as_str) {
        None => {
            eprintln!(
                "brazilian-soccer-mcp: loaded {} matches and {} players; serving MCP on stdio",
                db.matches.len(),
                db.players.len()
            );
            mcp::serve(&db, std::io::stdin().lock(), std::io::stdout().lock()).map_err(|e| e.to_string())
        }
        Some("call") => {
            let tool = args.get(1).ok_or("usage: call TOOL [JSON_ARGS]")?;
            let json = args.get(2).map(String::as_str).unwrap_or("{}");
            let value = serde_json::from_str(json).map_err(|e| format!("invalid JSON arguments: {e}"))?;
            println!("{}", mcp::call_tool(&db, tool, &value)?);
            Ok(())
        }
        Some(other) => Err(format!("unknown command '{other}' (expected: call, tools, or no command to serve)")),
    }
}

fn main() -> ExitCode {
    match run() {
        Ok(()) => ExitCode::SUCCESS,
        Err(e) => {
            eprintln!("error: {e}");
            ExitCode::FAILURE
        }
    }
}
