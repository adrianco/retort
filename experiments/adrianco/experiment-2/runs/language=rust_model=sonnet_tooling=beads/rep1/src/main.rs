use brazilian_soccer_mcp::data::DataStore;
use brazilian_soccer_mcp::tools::Tools;
use serde_json::{json, Value};
use std::io::{self, BufRead, Write};
use std::path::PathBuf;

fn make_error(id: &Value, code: i64, message: &str) -> Value {
    json!({
        "jsonrpc": "2.0",
        "id": id,
        "error": {
            "code": code,
            "message": message
        }
    })
}

fn make_result(id: &Value, result: Value) -> Value {
    json!({
        "jsonrpc": "2.0",
        "id": id,
        "result": result
    })
}

fn make_tool_error(id: &Value, text: &str) -> Value {
    make_result(
        id,
        json!({
            "content": [{"type": "text", "text": text}],
            "isError": true
        }),
    )
}

fn make_tool_result(id: &Value, text: String) -> Value {
    make_result(
        id,
        json!({
            "content": [{"type": "text", "text": text}],
            "isError": false
        }),
    )
}

fn tools_list() -> Value {
    json!([
        {
            "name": "search_matches",
            "description": "Search for soccer matches by team, season, or competition",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team1": {"type": "string"},
                    "team2": {"type": "string"},
                    "season": {"type": "integer"},
                    "competition": {"type": "string"},
                    "limit": {"type": "integer"}
                }
            }
        },
        {
            "name": "get_team_stats",
            "description": "Get win/loss/draw statistics for a team",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team": {"type": "string"},
                    "season": {"type": "integer"},
                    "competition": {"type": "string"}
                },
                "required": ["team"]
            }
        },
        {
            "name": "head_to_head",
            "description": "Compare two teams head-to-head",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team1": {"type": "string"},
                    "team2": {"type": "string"},
                    "competition": {"type": "string"}
                },
                "required": ["team1", "team2"]
            }
        },
        {
            "name": "search_players",
            "description": "Search FIFA player database",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "nationality": {"type": "string"},
                    "club": {"type": "string"},
                    "position": {"type": "string"},
                    "min_overall": {"type": "integer"},
                    "limit": {"type": "integer"}
                }
            }
        },
        {
            "name": "get_standings",
            "description": "Calculate league standings for a season",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "season": {"type": "integer"},
                    "competition": {"type": "string"}
                },
                "required": ["season"]
            }
        },
        {
            "name": "get_biggest_wins",
            "description": "Find matches with the largest goal difference",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "competition": {"type": "string"},
                    "season": {"type": "integer"},
                    "limit": {"type": "integer"}
                }
            }
        },
        {
            "name": "competition_stats",
            "description": "Get overall statistics for a competition",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "competition": {"type": "string"},
                    "season": {"type": "integer"}
                }
            }
        }
    ])
}

fn handle_request(request: &Value, tools: &Tools) -> Option<Value> {
    let id = &request["id"];
    let method = request["method"].as_str().unwrap_or("");

    match method {
        "initialize" => {
            let response = make_result(
                id,
                json!({
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "brazilian-soccer-mcp",
                        "version": "0.1.0"
                    }
                }),
            );
            Some(response)
        }
        "notifications/initialized" => {
            // No response for notifications
            None
        }
        "ping" => Some(make_result(id, json!({}))),
        "tools/list" => Some(make_result(id, json!({ "tools": tools_list() }))),
        "tools/call" => {
            let tool_name = request["params"]["name"].as_str().unwrap_or("");
            let args = &request["params"]["arguments"];

            let result_text = match tool_name {
                "search_matches" => tools.search_matches(args),
                "get_team_stats" => tools.get_team_stats(args),
                "head_to_head" => tools.head_to_head(args),
                "search_players" => tools.search_players(args),
                "get_standings" => tools.get_standings(args),
                "get_biggest_wins" => tools.get_biggest_wins(args),
                "competition_stats" => tools.competition_stats(args),
                _ => {
                    return Some(make_tool_error(
                        id,
                        &format!("Error: Unknown tool '{}'", tool_name),
                    ))
                }
            };

            if result_text.starts_with("Error:") {
                Some(make_tool_error(id, &result_text))
            } else {
                Some(make_tool_result(id, result_text))
            }
        }
        _ => Some(make_error(id, -32601, "Method not found")),
    }
}

fn main() {
    // Determine data directory
    let data_dir: PathBuf = std::env::var("DATA_DIR")
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from("./data/kaggle"));

    eprintln!("Loading data from {:?}", data_dir);

    let store = match DataStore::load(&data_dir) {
        Ok(s) => s,
        Err(e) => {
            eprintln!("Failed to load data: {}", e);
            std::process::exit(1);
        }
    };

    let tools = Tools::new(&store);

    let stdin = io::stdin();
    let stdout = io::stdout();
    let mut stdout = stdout.lock();

    for line in stdin.lock().lines() {
        let line = match line {
            Ok(l) => l,
            Err(_) => break,
        };
        let line = line.trim().to_string();
        if line.is_empty() {
            continue;
        }

        let request: Value = match serde_json::from_str(&line) {
            Ok(v) => v,
            Err(e) => {
                eprintln!("JSON parse error: {}", e);
                continue;
            }
        };

        if let Some(response) = handle_request(&request, &tools) {
            let response_str = serde_json::to_string(&response).unwrap_or_default();
            let _ = writeln!(stdout, "{}", response_str);
            let _ = stdout.flush();
        }
    }
}
