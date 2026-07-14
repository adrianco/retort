//! Minimal MCP (Model Context Protocol) server over a stdio JSON-RPC 2.0
//! transport using newline-delimited messages.
//!
//! Implements the handshake (`initialize` / `notifications/initialized`),
//! `tools/list`, and `tools/call`. Each tool returns both `content` (text the
//! LLM reads) and `structuredContent` (machine-readable result).

use serde_json::{json, Value};

use crate::data::DataStore;
use crate::tools::{self, ToolOutput};

pub const PROTOCOL_VERSION: &str = "2024-11-05";
pub const SERVER_NAME: &str = "brazilian-soccer-mcp";
pub const SERVER_VERSION: &str = "0.1.0";

type ToolFn = fn(&DataStore, &Value) -> Result<ToolOutput, String>;

struct ToolDef {
    name: &'static str,
    description: &'static str,
    input_schema: Value,
    func: ToolFn,
}

fn string_prop(desc: &str) -> Value {
    json!({ "type": "string", "description": desc })
}
fn int_prop(desc: &str) -> Value {
    json!({ "type": "integer", "description": desc })
}

fn tool_defs() -> Vec<ToolDef> {
    vec![
        ToolDef {
            name: "search_matches",
            description: "Find matches by team, opponent, competition, season, or date range. \
                          When both 'team' and 'opponent' are given, a head-to-head summary is included.",
            input_schema: json!({
                "type": "object",
                "properties": {
                    "team": string_prop("A team to find matches for (home or away). Name variants like 'Palmeiras' or 'Palmeiras-SP' both work."),
                    "opponent": string_prop("Restrict to matches against this opponent."),
                    "home_team": string_prop("Restrict to matches where this team played at home."),
                    "away_team": string_prop("Restrict to matches where this team played away."),
                    "competition": string_prop("Brasileirão, Copa do Brasil, or Copa Libertadores."),
                    "season": int_prop("Season year, e.g. 2019."),
                    "start_date": string_prop("Inclusive ISO start date (YYYY-MM-DD)."),
                    "end_date": string_prop("Inclusive ISO end date (YYYY-MM-DD)."),
                    "limit": int_prop("Maximum matches to return (default 50).")
                }
            }),
            func: tools::search_matches,
        },
        ToolDef {
            name: "team_record",
            description: "Get a team's win/draw/loss record, goals, points and win rate, \
                          optionally filtered by competition, season, and venue (home/away/all).",
            input_schema: json!({
                "type": "object",
                "properties": {
                    "team": string_prop("Team name (required)."),
                    "competition": string_prop("Optional competition filter."),
                    "season": int_prop("Optional season year filter."),
                    "venue": json!({ "type": "string", "enum": ["home", "away", "all"], "description": "Restrict to home or away games (default all)." })
                },
                "required": ["team"]
            }),
            func: tools::team_record,
        },
        ToolDef {
            name: "head_to_head",
            description: "Compare two teams head-to-head: total meetings, each side's wins, draws, goals, and the match list.",
            input_schema: json!({
                "type": "object",
                "properties": {
                    "team_a": string_prop("First team (required)."),
                    "team_b": string_prop("Second team (required)."),
                    "competition": string_prop("Optional competition filter.")
                },
                "required": ["team_a", "team_b"]
            }),
            func: tools::head_to_head,
        },
        ToolDef {
            name: "search_players",
            description: "Search FIFA players by name, nationality, club, position and minimum overall rating; \
                          sortable by overall, potential or age.",
            input_schema: json!({
                "type": "object",
                "properties": {
                    "name": string_prop("Full or partial player name."),
                    "nationality": string_prop("Nationality, e.g. 'Brazil'."),
                    "club": string_prop("Club name (partial match)."),
                    "position": string_prop("Playing position, e.g. 'ST', 'GK'."),
                    "min_overall": int_prop("Minimum FIFA overall rating."),
                    "sort_by": json!({ "type": "string", "enum": ["overall", "potential", "age"], "description": "Sort key (default overall, descending)." }),
                    "limit": int_prop("Maximum players to return (default 25).")
                }
            }),
            func: tools::search_players,
        },
        ToolDef {
            name: "league_standings",
            description: "Compute the final league table for a competition and season from match results \
                          (rank, points, played, W/D/L, goals for/against, goal difference).",
            input_schema: json!({
                "type": "object",
                "properties": {
                    "competition": string_prop("Competition (default Brasileirão)."),
                    "season": int_prop("Season year (required), e.g. 2019.")
                },
                "required": ["season"]
            }),
            func: tools::league_standings,
        },
        ToolDef {
            name: "competition_stats",
            description: "Aggregate statistics for a competition/season: match count, average goals per match, \
                          home/away/draw split, home win rate, and the biggest wins.",
            input_schema: json!({
                "type": "object",
                "properties": {
                    "competition": string_prop("Optional competition filter."),
                    "season": int_prop("Optional season year filter.")
                }
            }),
            func: tools::competition_stats,
        },
        ToolDef {
            name: "list_competitions",
            description: "List all competitions available in the loaded data with match counts and season ranges.",
            input_schema: json!({ "type": "object", "properties": {} }),
            func: tools::list_competitions,
        },
    ]
}

pub struct Server {
    store: DataStore,
    tools: Vec<ToolDef>,
}

impl Server {
    pub fn new(store: DataStore) -> Self {
        Server { store, tools: tool_defs() }
    }

    /// Handle one JSON-RPC message. Returns `Some(response)` for requests and
    /// `None` for notifications (which receive no reply).
    pub fn handle(&self, msg: &Value) -> Option<Value> {
        let id = msg.get("id").cloned();
        let method = msg.get("method").and_then(|m| m.as_str()).unwrap_or("");
        let params = msg.get("params").cloned().unwrap_or(json!({}));

        // Notifications carry no id and expect no response.
        if id.is_none() {
            return None;
        }
        let id = id.unwrap();

        let result = match method {
            "initialize" => Ok(json!({
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": { "tools": {} },
                "serverInfo": { "name": SERVER_NAME, "version": SERVER_VERSION }
            })),
            "ping" => Ok(json!({})),
            "tools/list" => Ok(self.list_tools()),
            "tools/call" => self.call_tool(&params),
            other => Err((-32601, format!("method not found: {other}"))),
        };

        Some(match result {
            Ok(value) => json!({ "jsonrpc": "2.0", "id": id, "result": value }),
            Err((code, message)) => json!({
                "jsonrpc": "2.0",
                "id": id,
                "error": { "code": code, "message": message }
            }),
        })
    }

    fn list_tools(&self) -> Value {
        let tools: Vec<Value> = self
            .tools
            .iter()
            .map(|t| {
                json!({
                    "name": t.name,
                    "description": t.description,
                    "inputSchema": t.input_schema,
                })
            })
            .collect();
        json!({ "tools": tools })
    }

    fn call_tool(&self, params: &Value) -> Result<Value, (i64, String)> {
        let name = params
            .get("name")
            .and_then(|n| n.as_str())
            .ok_or((-32602, "missing tool name".to_string()))?;
        let args = params.get("arguments").cloned().unwrap_or(json!({}));

        let tool = self
            .tools
            .iter()
            .find(|t| t.name == name)
            .ok_or((-32602, format!("unknown tool: {name}")))?;

        // Tool-level failures are reported as a successful JSON-RPC result with
        // isError=true, per the MCP convention, so the LLM can read the message.
        match (tool.func)(&self.store, &args) {
            Ok(out) => Ok(json!({
                "content": [{ "type": "text", "text": out.text }],
                "structuredContent": out.structured,
                "isError": false
            })),
            Err(message) => Ok(json!({
                "content": [{ "type": "text", "text": format!("Error: {message}") }],
                "isError": true
            })),
        }
    }
}
