use serde::{Deserialize, Serialize};
use serde_json::{json, Value};

#[derive(Debug, Deserialize)]
pub struct JsonRpcRequest {
    pub jsonrpc: String,
    pub method: String,
    pub params: Option<Value>,
    pub id: Option<Value>,
}

#[derive(Debug, Serialize)]
pub struct JsonRpcResponse {
    pub jsonrpc: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub result: Option<Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<JsonRpcError>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub id: Option<Value>,
}

#[derive(Debug, Serialize)]
pub struct JsonRpcError {
    pub code: i32,
    pub message: String,
}

impl JsonRpcResponse {
    pub fn success(id: Option<Value>, result: Value) -> Self {
        Self {
            jsonrpc: "2.0".to_string(),
            result: Some(result),
            error: None,
            id,
        }
    }

    pub fn error(id: Option<Value>, code: i32, message: impl Into<String>) -> Self {
        Self {
            jsonrpc: "2.0".to_string(),
            result: None,
            error: Some(JsonRpcError {
                code,
                message: message.into(),
            }),
            id,
        }
    }
}

pub fn tool_definitions() -> Value {
    json!([
        {
            "name": "search_matches",
            "description": "Search matches from all competitions (Brasileirão Serie A, Copa do Brasil, Copa Libertadores, and historical data). Filter by team name(s), competition, season, and date range. Returns match results with scores.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team": {
                        "type": "string",
                        "description": "Team name to search for (partial match, case-insensitive). Handles state suffixes like 'Palmeiras-SP' → matches 'Palmeiras'."
                    },
                    "team2": {
                        "type": "string",
                        "description": "Second team name for head-to-head search. When provided with 'team', finds matches where both teams played."
                    },
                    "competition": {
                        "type": "string",
                        "description": "Competition name filter (e.g., 'Brasileirão', 'Copa do Brasil', 'Libertadores'). Case-insensitive partial match."
                    },
                    "season": {
                        "type": "integer",
                        "description": "Season year (e.g., 2019, 2022, 2023)."
                    },
                    "date_from": {
                        "type": "string",
                        "description": "Start date filter in ISO format (YYYY-MM-DD)."
                    },
                    "date_to": {
                        "type": "string",
                        "description": "End date filter in ISO format (YYYY-MM-DD)."
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of matches to return (default: 20, max recommended: 50).",
                        "default": 20
                    }
                },
                "additionalProperties": false
            }
        },
        {
            "name": "team_stats",
            "description": "Get comprehensive statistics for a team: total matches, wins, draws, losses, goals scored/conceded, goal difference, points, and win rate. Broken down by home and away performance.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team": {
                        "type": "string",
                        "description": "Team name (partial match, case-insensitive)."
                    },
                    "competition": {
                        "type": "string",
                        "description": "Filter by competition (e.g., 'Brasileirão', 'Copa do Brasil'). Optional."
                    },
                    "season": {
                        "type": "integer",
                        "description": "Filter by season year. Optional."
                    }
                },
                "required": ["team"],
                "additionalProperties": false
            }
        },
        {
            "name": "head_to_head",
            "description": "Compare two teams head-to-head: total matches, wins for each team, draws, goals, and list of recent meetings.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team1": {
                        "type": "string",
                        "description": "First team name."
                    },
                    "team2": {
                        "type": "string",
                        "description": "Second team name."
                    },
                    "competition": {
                        "type": "string",
                        "description": "Filter by competition. Optional."
                    },
                    "season": {
                        "type": "integer",
                        "description": "Filter by season year. Optional."
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of recent matches to show (default: 10).",
                        "default": 10
                    }
                },
                "required": ["team1", "team2"],
                "additionalProperties": false
            }
        },
        {
            "name": "search_players",
            "description": "Search FIFA player database. Find players by name, nationality, club, or position. Results sorted by overall rating.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Player name (partial match, case-insensitive)."
                    },
                    "nationality": {
                        "type": "string",
                        "description": "Player nationality (e.g., 'Brazil', 'Argentina')."
                    },
                    "club": {
                        "type": "string",
                        "description": "Club name (partial match, e.g., 'Flamengo', 'Palmeiras', 'Santos')."
                    },
                    "position": {
                        "type": "string",
                        "description": "Playing position (e.g., 'GK', 'ST', 'LW', 'CDM')."
                    },
                    "min_overall": {
                        "type": "integer",
                        "description": "Minimum FIFA overall rating (0-99)."
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 20).",
                        "default": 20
                    }
                },
                "additionalProperties": false
            }
        },
        {
            "name": "season_standings",
            "description": "Calculate league table standings for a competition and season from match results. Shows points, matches played, wins, draws, losses, and goal difference.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "competition": {
                        "type": "string",
                        "description": "Competition name (e.g., 'Brasileirão', 'brasileirão serie a')."
                    },
                    "season": {
                        "type": "integer",
                        "description": "Season year (e.g., 2019)."
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of teams to show in standings (default: 20).",
                        "default": 20
                    }
                },
                "required": ["competition", "season"],
                "additionalProperties": false
            }
        },
        {
            "name": "biggest_wins",
            "description": "Find matches with the largest goal margin (biggest victories). Optionally filter by competition and season.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "competition": {
                        "type": "string",
                        "description": "Competition filter. Optional."
                    },
                    "season": {
                        "type": "integer",
                        "description": "Season year filter. Optional."
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of results to return (default: 10).",
                        "default": 10
                    }
                },
                "additionalProperties": false
            }
        },
        {
            "name": "competition_stats",
            "description": "Get aggregate statistics for a competition: total matches, goals, average goals per match, home/away win rates.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "competition": {
                        "type": "string",
                        "description": "Competition name. Optional (omit for all competitions)."
                    },
                    "season": {
                        "type": "integer",
                        "description": "Season year. Optional (omit for all seasons)."
                    }
                },
                "additionalProperties": false
            }
        },
        {
            "name": "top_scoring_teams",
            "description": "Find the teams that scored the most goals in a competition/season.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "competition": {
                        "type": "string",
                        "description": "Competition name. Optional."
                    },
                    "season": {
                        "type": "integer",
                        "description": "Season year. Optional."
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of teams to show (default: 10).",
                        "default": 10
                    }
                },
                "additionalProperties": false
            }
        }
    ])
}

pub fn server_info() -> Value {
    json!({
        "protocolVersion": "2024-11-05",
        "capabilities": {
            "tools": {}
        },
        "serverInfo": {
            "name": "brazilian-soccer-mcp",
            "version": "0.1.0"
        }
    })
}
