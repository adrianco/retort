use crate::query::{SoccerService, ToolError};
use serde_json::{json, Value};
use std::io::{self, BufRead, Write};

const PROTOCOL_VERSION: &str = "2025-11-25";
const STATELESS_PROTOCOL_VERSION: &str = "2026-07-28";
const LEGACY_PROTOCOL_VERSIONS: &[&str] =
    &["2024-11-05", "2025-03-26", "2025-06-18", PROTOCOL_VERSION];

pub struct McpServer {
    service: SoccerService,
}

impl McpServer {
    pub fn new(service: SoccerService) -> Self {
        Self { service }
    }

    pub fn serve_stdio(&self) -> io::Result<()> {
        let stdin = io::stdin();
        let mut stdout = io::BufWriter::new(io::stdout().lock());
        let mut initialized = false;
        for line in stdin.lock().lines() {
            let line = line?;
            if line.trim().is_empty() {
                continue;
            }
            if let Some(response) = self.handle_line(&line, &mut initialized) {
                serde_json::to_writer(&mut stdout, &response)?;
                stdout.write_all(b"\n")?;
                stdout.flush()?;
            }
        }
        Ok(())
    }

    pub fn handle_line(&self, line: &str, initialized: &mut bool) -> Option<Value> {
        let request: Value = match serde_json::from_str(line) {
            Ok(v) => v,
            Err(e) => return Some(error(Value::Null, -32700, format!("parse error: {e}"))),
        };
        let Some(obj) = request.as_object() else {
            return Some(error(Value::Null, -32600, "request must be an object"));
        };
        let id = obj.get("id").cloned();
        let method = obj.get("method").and_then(Value::as_str);
        if obj.get("jsonrpc") != Some(&Value::String("2.0".into())) || method.is_none() {
            return id.map(|id| error(id, -32600, "invalid JSON-RPC request"));
        }
        let method = method.unwrap();
        id.as_ref()?;
        let id = id.unwrap();
        if method == "server/discover" {
            return Some(success(
                id,
                json!({
                    "resultType":"complete",
                    "supportedVersions":[STATELESS_PROTOCOL_VERSION],
                    "capabilities":{"tools":{}},
                    "_meta":{"io.modelcontextprotocol/serverInfo":{"name":"brazilian-soccer-mcp","version":env!("CARGO_PKG_VERSION")}},
                    "instructions":"Query the supplied Brazilian soccer match and FIFA player datasets.",
                    "ttlMs":3600000,
                    "cacheScope":"public"
                }),
            ));
        }
        if method == "initialize" {
            if *initialized {
                return Some(error(id, -32600, "server is already initialized"));
            }
            *initialized = true;
            let requested_version = obj
                .get("params")
                .and_then(Value::as_object)
                .and_then(|p| p.get("protocolVersion"))
                .and_then(Value::as_str);
            // Legacy MCP requires echoing a supported client revision. If the
            // revision is unknown, respond with this server's newest legacy
            // revision and let the client decide whether it can continue.
            let negotiated_version = requested_version
                .filter(|v| LEGACY_PROTOCOL_VERSIONS.contains(v))
                .unwrap_or(PROTOCOL_VERSION);
            return Some(success(
                id,
                json!({"protocolVersion":negotiated_version,"capabilities":{"tools":{"listChanged":false}},"serverInfo":{"name":"brazilian-soccer-mcp","version":env!("CARGO_PKG_VERSION")}}),
            ));
        }
        let stateless_request = obj
            .get("params")
            .and_then(Value::as_object)
            .and_then(|p| p.get("_meta"))
            .and_then(Value::as_object)
            .and_then(|m| m.get("io.modelcontextprotocol/protocolVersion"))
            .and_then(Value::as_str)
            == Some(STATELESS_PROTOCOL_VERSION);
        if !*initialized && !stateless_request {
            return Some(error(id, -32002, "server is not initialized"));
        }
        match method {
            "ping" => Some(success(id, json!({}))),
            "tools/list" => Some(success(
                id,
                json!({"resultType":"complete","tools":tool_definitions(),"ttlMs":3600000,"cacheScope":"public"}),
            )),
            "tools/call" => {
                let params = obj.get("params").and_then(Value::as_object);
                let name = params.and_then(|p| p.get("name")).and_then(Value::as_str);
                let Some(name) = name else {
                    return Some(error(id, -32602, "tools/call requires a name"));
                };
                let args = params
                    .and_then(|p| p.get("arguments"))
                    .cloned()
                    .unwrap_or_else(|| json!({}));
                match self.service.call(name, args) {
                    Ok(data) => {
                        let text = format_result(name, &data);
                        Some(success(
                            id,
                            json!({"resultType":"complete","content":[{"type":"text","text":text}],"structuredContent":data,"isError":false}),
                        ))
                    }
                    Err(ToolError::Invalid(message)) => Some(error(id, -32602, message)),
                    Err(ToolError::Unsupported(message)) => Some(success(
                        id,
                        json!({"resultType":"complete","content":[{"type":"text","text":message}],"isError":true}),
                    )),
                }
            }
            _ => Some(error(id, -32601, "method not found")),
        }
    }
}

fn success(id: Value, result: Value) -> Value {
    json!({"jsonrpc":"2.0","id":id,"result":result})
}
fn error(id: Value, code: i32, message: impl Into<String>) -> Value {
    json!({"jsonrpc":"2.0","id":id,"error":{"code":code,"message":message.into()}})
}
fn format_result(name: &str, data: &Value) -> String {
    // Text content is the interoperable MCP result surface. Keep the concise
    // lead-in, but include the actual data so clients that ignore the optional
    // structuredContent field can still answer accurately.
    let summary = match name {
        "search_matches" => format!("Found {} matching matches.", data["total"]),
        "search_players" => format!("Found {} matching players.", data["total"]),
        "get_team_record" | "get_head_to_head" => {
            format!("Team record covers {} matches.", data["record"]["matches"])
        }
        "analyze_competition" | "get_standings" => {
            format!("Competition analysis covers {} matches.", data["matches"])
        }
        _ => "Brazilian soccer query completed.".into(),
    };
    let body = serde_json::to_string_pretty(data).unwrap_or_else(|_| data.to_string());
    format!("{summary}\n{body}")
}

fn tool_definitions() -> Value {
    json!([
     {"name":"search_matches","description":"Find completed matches by team, opponent, venue, competition, season, date range, stage, or round.","annotations":{"title":"Search Brazilian soccer matches","readOnlyHint":true,"openWorldHint":false},"inputSchema":object_schema(json!({"team":{"type":"string"},"opponent":{"type":"string"},"venue":{"type":"string","enum":["any","home","away"]},"competition":{"type":"string"},"season":{"type":"integer"},"date_from":{"type":"string","format":"date"},"date_to":{"type":"string","format":"date"},"stage":{"type":"string"},"round":{"type":"string"},"sort":{"type":"string","enum":["newest","oldest","largest_margin"]},"limit":{"type":"integer","minimum":1,"maximum":200},"offset":{"type":"integer","minimum":0}}),json!([]))},
     {"name":"get_team_record","description":"Calculate wins, draws, losses, points, goals and win rate for a team, optionally head-to-head or by venue.","annotations":{"title":"Calculate team record","readOnlyHint":true,"openWorldHint":false},"inputSchema":object_schema(json!({"team":{"type":"string"},"opponent":{"type":"string"},"venue":{"type":"string","enum":["any","home","away"]},"competition":{"type":"string"},"season":{"type":"integer"},"date_from":{"type":"string","format":"date"},"date_to":{"type":"string","format":"date"}}),json!(["team"]))},
     {"name":"get_head_to_head","description":"Calculate the head-to-head wins, draws, losses, points, and goals between two teams from supplied match data.","annotations":{"title":"Compare two teams head-to-head","readOnlyHint":true,"openWorldHint":false},"inputSchema":object_schema(json!({"team_a":{"type":"string"},"team_b":{"type":"string"},"competition":{"type":"string"},"season":{"type":"integer"},"date_from":{"type":"string","format":"date"},"date_to":{"type":"string","format":"date"}}),json!(["team_a","team_b"]))},
     {"name":"search_players","description":"Search the FIFA snapshot by name, nationality, club, position, rating, or age.","annotations":{"title":"Search soccer players","readOnlyHint":true,"openWorldHint":false},"inputSchema":object_schema(json!({"name":{"type":"string"},"nationality":{"type":"string"},"club":{"type":"string"},"position":{"type":"string"},"min_overall":{"type":"integer","minimum":0,"maximum":100},"max_age":{"type":"integer","minimum":1},"sort":{"type":"string","enum":["overall_desc","potential_desc","name"]},"limit":{"type":"integer","minimum":1,"maximum":200},"offset":{"type":"integer","minimum":0}}),json!([]))},
     {"name":"analyze_competition","description":"Calculate league standings, competition summaries, team rankings, or biggest wins.","annotations":{"title":"Analyze a competition","readOnlyHint":true,"openWorldHint":false},"inputSchema":object_schema(json!({"competition":{"type":"string"},"season":{"type":"integer"},"analysis":{"type":"string","enum":["standings","summary","team_ranking","biggest_wins"]},"metric":{"type":"string","enum":["points","goals_for","win_rate"]},"limit":{"type":"integer","minimum":1,"maximum":200}}),json!(["competition","analysis"]))},
     {"name":"get_standings","description":"Calculate a season league table from match results. Defaults to Brasileirão and returns positions, points, W/D/L, and goals.","annotations":{"title":"Get season standings","readOnlyHint":true,"openWorldHint":false},"inputSchema":object_schema(json!({"season":{"type":"integer"},"competition":{"type":"string","default":"Brasileirão"},"limit":{"type":"integer","minimum":1,"maximum":200}}),json!(["season"]))},
     {"name":"ask_soccer","description":"Map a common natural-language Brazilian soccer question to the structured dataset operations.","annotations":{"title":"Ask about Brazilian soccer","readOnlyHint":true,"openWorldHint":false},"inputSchema":object_schema(json!({"question":{"type":"string","minLength":1},"limit":{"type":"integer","minimum":1,"maximum":200}}),json!(["question"]))}
    ])
}
fn object_schema(properties: Value, required: Value) -> Value {
    json!({"type":"object","properties":properties,"required":required,"additionalProperties":false})
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::data::DataStore;
    #[test]
    fn protocol_lifecycle_and_errors() {
        let s = McpServer::new(SoccerService::new(DataStore::default()));
        let mut init = false;
        assert_eq!(
            s.handle_line("not json", &mut init).unwrap()["error"]["code"],
            -32700
        );
        let r = s
            .handle_line(
                r#"{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}"#,
                &mut init,
            )
            .unwrap();
        assert_eq!(r["result"]["protocolVersion"], PROTOCOL_VERSION);
        let r = s
            .handle_line(
                r#"{"jsonrpc":"2.0","id":"x","method":"tools/list"}"#,
                &mut init,
            )
            .unwrap();
        assert_eq!(r["result"]["tools"].as_array().unwrap().len(), 7);
        assert_eq!(r["id"], "x")
    }
    #[test]
    fn notifications_have_no_response() {
        let s = McpServer::new(SoccerService::new(DataStore::default()));
        let mut init = true;
        assert!(s
            .handle_line(
                r#"{"jsonrpc":"2.0","method":"notifications/initialized"}"#,
                &mut init
            )
            .is_none())
    }

    #[test]
    fn supports_legacy_negotiation_and_stateless_discovery() {
        let s = McpServer::new(SoccerService::new(DataStore::default()));
        let mut initialized = false;
        let old = s
            .handle_line(
                r#"{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05"}}"#,
                &mut initialized,
            )
            .unwrap();
        assert_eq!(old["result"]["protocolVersion"], "2024-11-05");

        let mut stateless = false;
        let discovery = s
            .handle_line(
                r#"{"jsonrpc":"2.0","id":2,"method":"server/discover","params":{"_meta":{"io.modelcontextprotocol/protocolVersion":"2026-07-28"}}}"#,
                &mut stateless,
            )
            .unwrap();
        assert_eq!(
            discovery["result"]["supportedVersions"][0],
            STATELESS_PROTOCOL_VERSION
        );
        let tools = s
            .handle_line(
                r#"{"jsonrpc":"2.0","id":3,"method":"tools/list","params":{"_meta":{"io.modelcontextprotocol/protocolVersion":"2026-07-28"}}}"#,
                &mut stateless,
            )
            .unwrap();
        assert_eq!(tools["result"]["tools"].as_array().unwrap().len(), 7);
    }
}
