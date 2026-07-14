use serde_json::{json, Value};
use crate::data::DataStore;
use crate::tools::{
    search_matches, SearchMatchesArgs,
    get_team_stats, TeamStatsArgs,
    search_players, SearchPlayersArgs,
    get_standings, StandingsArgs,
    get_head_to_head, HeadToHeadArgs,
    get_global_stats, GlobalStatsArgs,
};

pub fn handle_message(store: &DataStore, msg: &Value) -> Option<Value> {
    let method = msg.get("method")?.as_str()?;
    let id = msg.get("id").cloned();

    match method {
        "initialize" => {
            Some(json_response(id, json!({
                "protocolVersion": "2024-11-05",
                "capabilities": { "tools": {} },
                "serverInfo": { "name": "brazilian-soccer-mcp", "version": "0.1.0" }
            })))
        }
        "notifications/initialized" => {
            // Notification – no response needed
            None
        }
        "tools/list" => {
            Some(json_response(id, json!({
                "tools": tools_schema()
            })))
        }
        "tools/call" => {
            let params = msg.get("params").cloned().unwrap_or(json!({}));
            let tool_name = params.get("name").and_then(|n| n.as_str()).unwrap_or("");
            let args = params.get("arguments").cloned().unwrap_or(json!({}));

            let result_text = dispatch_tool(store, tool_name, &args);
            Some(json_response(id, json!({
                "content": [{ "type": "text", "text": result_text }]
            })))
        }
        _ => {
            // Unknown method – return an error response if it has an id
            if id.is_some() {
                Some(json!({
                    "jsonrpc": "2.0",
                    "id": id,
                    "error": {
                        "code": -32601,
                        "message": format!("Method not found: {}", method)
                    }
                }))
            } else {
                None
            }
        }
    }
}

fn json_response(id: Option<Value>, result: Value) -> Value {
    json!({
        "jsonrpc": "2.0",
        "id": id,
        "result": result
    })
}

fn dispatch_tool(store: &DataStore, tool_name: &str, args: &Value) -> String {
    match tool_name {
        "search_matches" => {
            let a = SearchMatchesArgs::from_json(args);
            search_matches(store, &a)
        }
        "get_team_stats" => {
            match TeamStatsArgs::from_json(args) {
                Some(a) => get_team_stats(store, &a),
                None => "Missing required field: team".to_string(),
            }
        }
        "search_players" => {
            let a = SearchPlayersArgs::from_json(args);
            search_players(store, &a)
        }
        "get_standings" => {
            match StandingsArgs::from_json(args) {
                Some(a) => get_standings(store, &a),
                None => "Missing required field: season".to_string(),
            }
        }
        "get_head_to_head" => {
            match HeadToHeadArgs::from_json(args) {
                Some(a) => get_head_to_head(store, &a),
                None => "Missing required fields: team1, team2".to_string(),
            }
        }
        "get_global_stats" => {
            let a = GlobalStatsArgs::from_json(args);
            get_global_stats(store, &a)
        }
        _ => format!("Unknown tool: {}", tool_name),
    }
}

fn tools_schema() -> Value {
    json!([
        {
            "name": "search_matches",
            "description": "Search matches across all datasets (Brasileirao, Copa do Brasil, Libertadores, BR Football, Historico). Returns formatted list of matches.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team": {
                        "type": "string",
                        "description": "Team name to search for (home or away)"
                    },
                    "opponent": {
                        "type": "string",
                        "description": "Opponent team name (use with team for head-to-head)"
                    },
                    "competition": {
                        "type": "string",
                        "enum": ["brasileirao", "copa_brasil", "libertadores", "br_football", "historico"],
                        "description": "Competition to filter by"
                    },
                    "season": {
                        "type": "integer",
                        "description": "Season year (e.g. 2023)"
                    },
                    "date_from": {
                        "type": "string",
                        "description": "Start date YYYY-MM-DD"
                    },
                    "date_to": {
                        "type": "string",
                        "description": "End date YYYY-MM-DD"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results (default 20)"
                    }
                }
            }
        },
        {
            "name": "get_team_stats",
            "description": "Get statistics for a team including wins, losses, draws, goals, win rate, home/away records.",
            "inputSchema": {
                "type": "object",
                "required": ["team"],
                "properties": {
                    "team": {
                        "type": "string",
                        "description": "Team name"
                    },
                    "competition": {
                        "type": "string",
                        "enum": ["brasileirao", "copa_brasil", "libertadores", "br_football", "historico"],
                        "description": "Filter by competition"
                    },
                    "season": {
                        "type": "integer",
                        "description": "Filter by season year"
                    }
                }
            }
        },
        {
            "name": "search_players",
            "description": "Search FIFA player database by name, nationality, club, or position.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Player name (partial match)"
                    },
                    "nationality": {
                        "type": "string",
                        "description": "Player nationality (e.g. 'Brazil')"
                    },
                    "club": {
                        "type": "string",
                        "description": "Club name (partial match)"
                    },
                    "position": {
                        "type": "string",
                        "description": "Playing position (e.g. 'ST', 'GK')"
                    },
                    "min_overall": {
                        "type": "integer",
                        "description": "Minimum FIFA overall rating"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Max results to return (default 20)"
                    }
                }
            }
        },
        {
            "name": "get_standings",
            "description": "Calculate league standings from match results for a given season.",
            "inputSchema": {
                "type": "object",
                "required": ["season"],
                "properties": {
                    "season": {
                        "type": "integer",
                        "description": "Season year"
                    },
                    "competition": {
                        "type": "string",
                        "enum": ["brasileirao", "copa_brasil", "libertadores", "br_football", "historico"],
                        "description": "Competition (defaults to all)"
                    }
                }
            }
        },
        {
            "name": "get_head_to_head",
            "description": "Get head-to-head record between two teams including all matches and summary.",
            "inputSchema": {
                "type": "object",
                "required": ["team1", "team2"],
                "properties": {
                    "team1": {
                        "type": "string",
                        "description": "First team name"
                    },
                    "team2": {
                        "type": "string",
                        "description": "Second team name"
                    },
                    "competition": {
                        "type": "string",
                        "enum": ["brasileirao", "copa_brasil", "libertadores", "br_football", "historico"],
                        "description": "Filter by competition"
                    },
                    "season": {
                        "type": "integer",
                        "description": "Filter by season"
                    }
                }
            }
        },
        {
            "name": "get_global_stats",
            "description": "Get global statistics: avg goals/match, win rates, top scoring teams, biggest wins.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "competition": {
                        "type": "string",
                        "enum": ["brasileirao", "copa_brasil", "libertadores", "br_football", "historico"],
                        "description": "Filter by competition"
                    },
                    "season": {
                        "type": "integer",
                        "description": "Filter by season year"
                    }
                }
            }
        }
    ])
}
