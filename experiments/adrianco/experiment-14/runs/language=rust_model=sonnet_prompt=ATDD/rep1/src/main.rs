mod data;
mod normalize;
mod tools;

use data::AppData;
use std::io::{BufRead, BufReader, Write};

fn tools_list() -> serde_json::Value {
    serde_json::json!([
        {
            "name": "find_matches",
            "description": "Find Brazilian soccer matches. Filter by team, team2 (for H2H), competition (brasileirao/copa_brasil/libertadores), season, limit.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team": {"type": "string", "description": "Team name (partial match OK, state suffix not required)"},
                    "team2": {"type": "string", "description": "Second team for head-to-head search"},
                    "competition": {"type": "string", "description": "brasileirao, copa_brasil, libertadores"},
                    "season": {"type": "integer", "description": "Season year"},
                    "limit": {"type": "integer", "description": "Max results (default 20)"}
                }
            }
        },
        {
            "name": "get_team_stats",
            "description": "Get win/loss/draw statistics for a team. Optionally filter by competition and season.",
            "inputSchema": {
                "type": "object",
                "required": ["team"],
                "properties": {
                    "team": {"type": "string", "description": "Team name"},
                    "competition": {"type": "string", "description": "brasileirao, copa_brasil, libertadores"},
                    "season": {"type": "integer", "description": "Season year"}
                }
            }
        },
        {
            "name": "find_players",
            "description": "Find FIFA-rated Brazilian soccer players. Filter by name, nationality, club, position, min_rating, max_age.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Player name (partial match)"},
                    "nationality": {"type": "string", "description": "Nationality (e.g. Brazil)"},
                    "club": {"type": "string", "description": "Club name (partial match)"},
                    "position": {"type": "string", "description": "Position (e.g. ST, GK)"},
                    "min_rating": {"type": "integer", "description": "Minimum overall rating"},
                    "max_age": {"type": "integer", "description": "Maximum age"},
                    "limit": {"type": "integer", "description": "Max results (default 20)"}
                }
            }
        },
        {
            "name": "get_head_to_head",
            "description": "Get head-to-head record between two teams with summary stats and recent matches.",
            "inputSchema": {
                "type": "object",
                "required": ["team1", "team2"],
                "properties": {
                    "team1": {"type": "string", "description": "First team name"},
                    "team2": {"type": "string", "description": "Second team name"},
                    "competition": {"type": "string", "description": "Filter by competition"},
                    "season": {"type": "integer", "description": "Filter by season"},
                    "limit": {"type": "integer", "description": "Max recent matches to show (default 10)"}
                }
            }
        },
        {
            "name": "get_standings",
            "description": "Get league standings (points table) for a competition and season.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "competition": {"type": "string", "description": "brasileirao, copa_brasil, libertadores (default: brasileirao)"},
                    "season": {"type": "integer", "description": "Season year"},
                    "limit": {"type": "integer", "description": "Max teams to show (default 20)"}
                }
            }
        },
        {
            "name": "get_statistical_summary",
            "description": "Get overall statistical summary: total matches, goals, win rates, scoring records for a competition.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "competition": {"type": "string", "description": "brasileirao, copa_brasil, libertadores, or empty for all"},
                    "season": {"type": "integer", "description": "Filter by season year"}
                }
            }
        }
    ])
}

fn call_tool(data: &AppData, name: &str, args: &serde_json::Value) -> String {
    match name {
        "find_matches" => tools::find_matches(data, args),
        "get_team_stats" => tools::get_team_stats(data, args),
        "find_players" => tools::find_players(data, args),
        "get_head_to_head" => tools::get_head_to_head(data, args),
        "get_standings" => tools::get_standings(data, args),
        "get_statistical_summary" => tools::get_statistical_summary(data, args),
        _ => format!("Unknown tool: {}", name),
    }
}

fn main() {
    let data_dir = std::env::var("SOCCER_DATA_DIR").unwrap_or_else(|_| {
        // Find data relative to binary location or use cwd
        let exe = std::env::current_exe().unwrap_or_default();
        let dir = exe.parent().unwrap_or(std::path::Path::new("."));
        // Try several locations
        for candidate in &[
            "data/kaggle",
            "../data/kaggle",
            "../../data/kaggle",
            "../../../data/kaggle",
        ] {
            let path = dir.join(candidate);
            if path.exists() {
                return path.to_string_lossy().to_string();
            }
        }
        // Also try from current working directory
        for candidate in &["data/kaggle", "../data/kaggle"] {
            let path = std::path::Path::new(candidate);
            if path.exists() {
                return path.to_string_lossy().to_string();
            }
        }
        "data/kaggle".to_string()
    });

    eprintln!("Loading data from {}", data_dir);
    let data = AppData::load(&data_dir);
    eprintln!(
        "Loaded {} matches, {} players",
        data.matches.len(),
        data.players.len()
    );

    let stdin = std::io::stdin();
    let stdout = std::io::stdout();
    let mut out = stdout.lock();

    for line in BufReader::new(stdin.lock()).lines() {
        let line = match line {
            Ok(l) => l,
            Err(e) => {
                eprintln!("Read error: {}", e);
                break;
            }
        };
        let line = line.trim().to_string();
        if line.is_empty() {
            continue;
        }

        let msg: serde_json::Value = match serde_json::from_str(&line) {
            Ok(v) => v,
            Err(e) => {
                eprintln!("JSON parse error: {} for line: {}", e, line);
                continue;
            }
        };

        let method = msg["method"].as_str().unwrap_or("");
        let id = &msg["id"];

        match method {
            "initialize" => {
                let resp = serde_json::json!({
                    "jsonrpc": "2.0",
                    "id": id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "brazilian-soccer", "version": "1.0.0"}
                    }
                });
                writeln!(out, "{}", resp).unwrap();
                out.flush().unwrap();
            }
            "notifications/initialized" => {
                // No response needed for notifications
            }
            "tools/list" => {
                let resp = serde_json::json!({
                    "jsonrpc": "2.0",
                    "id": id,
                    "result": {
                        "tools": tools_list()
                    }
                });
                writeln!(out, "{}", resp).unwrap();
                out.flush().unwrap();
            }
            "tools/call" => {
                let name = msg["params"]["name"].as_str().unwrap_or("");
                let args = &msg["params"]["arguments"];
                let result_text = call_tool(&data, name, args);
                let resp = serde_json::json!({
                    "jsonrpc": "2.0",
                    "id": id,
                    "result": {
                        "content": [{"type": "text", "text": result_text}]
                    }
                });
                writeln!(out, "{}", resp).unwrap();
                out.flush().unwrap();
            }
            _ => {
                if !id.is_null() {
                    let resp = serde_json::json!({
                        "jsonrpc": "2.0",
                        "id": id,
                        "error": {
                            "code": -32601,
                            "message": format!("Method not found: {}", method)
                        }
                    });
                    writeln!(out, "{}", resp).unwrap();
                    out.flush().unwrap();
                }
            }
        }
    }
}
