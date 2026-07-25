//! Model Context Protocol server: JSON-RPC 2.0 over newline-delimited stdio.
//!
//! Implements the methods an MCP host needs to drive the tool set:
//! `initialize`, `ping`, `tools/list`, `tools/call`, `resources/list`,
//! `resources/read` and `prompts/list`. Tool failures are returned as
//! successful results with `isError: true` (per the MCP spec) so the model can
//! read and recover from them; protocol failures use JSON-RPC error objects.

use std::io::{BufRead, Write};

use serde_json::{json, Value};

use crate::graph::KnowledgeGraph;
use crate::model::{Competition, Source};
use crate::tools::{self, TOOLS};

/// Protocol revisions this server understands, newest first.
pub const SUPPORTED_PROTOCOL_VERSIONS: [&str; 3] = ["2025-06-18", "2025-03-26", "2024-11-05"];
pub const SERVER_NAME: &str = "brazilian-soccer-mcp";
pub const SERVER_VERSION: &str = env!("CARGO_PKG_VERSION");

const PARSE_ERROR: i64 = -32700;
const INVALID_REQUEST: i64 = -32600;
const METHOD_NOT_FOUND: i64 = -32601;
const INVALID_PARAMS: i64 = -32602;

/// An MCP server bound to a loaded knowledge graph.
pub struct Server {
    graph: KnowledgeGraph,
    initialized: bool,
}

impl Server {
    pub fn new(graph: KnowledgeGraph) -> Server {
        Server {
            graph,
            initialized: false,
        }
    }

    pub fn graph(&self) -> &KnowledgeGraph {
        &self.graph
    }

    /// True once the client has sent `initialize`.
    pub fn is_initialized(&self) -> bool {
        self.initialized
    }

    /// Reads newline-delimited JSON-RPC messages until EOF.
    pub fn serve(&mut self, input: impl BufRead, mut output: impl Write) -> std::io::Result<()> {
        for line in input.lines() {
            let line = line?;
            if line.trim().is_empty() {
                continue;
            }
            if let Some(response) = self.handle_line(&line) {
                writeln!(output, "{response}")?;
                output.flush()?;
            }
        }
        Ok(())
    }

    /// Handles one raw message, returning the serialized response (if any).
    pub fn handle_line(&mut self, line: &str) -> Option<String> {
        let request: Value = match serde_json::from_str(line) {
            Ok(value) => value,
            Err(error) => {
                return Some(
                    error_response(Value::Null, PARSE_ERROR, &format!("parse error: {error}"))
                        .to_string(),
                )
            }
        };
        // JSON-RPC batches (used by MCP 2024-11-05 clients).
        if let Value::Array(items) = request {
            let responses: Vec<Value> = items
                .into_iter()
                .filter_map(|item| self.handle(item))
                .collect();
            if responses.is_empty() {
                return None;
            }
            return Some(Value::Array(responses).to_string());
        }
        self.handle(request).map(|value| value.to_string())
    }

    /// Handles one parsed JSON-RPC message. Returns `None` for notifications.
    pub fn handle(&mut self, request: Value) -> Option<Value> {
        let id = request.get("id").cloned().unwrap_or(Value::Null);
        let is_notification = request.get("id").is_none();
        let Some(method) = request.get("method").and_then(Value::as_str) else {
            if is_notification {
                return None;
            }
            return Some(error_response(id, INVALID_REQUEST, "missing 'method'"));
        };
        let params = request.get("params").cloned().unwrap_or(Value::Null);

        let result = match method {
            "initialize" => Ok(self.initialize(&params)),
            "notifications/initialized" | "initialized" => {
                self.initialized = true;
                return None;
            }
            "notifications/cancelled" | "notifications/progress" => return None,
            "ping" => Ok(json!({})),
            "tools/list" => Ok(tools_list()),
            "tools/call" => self.tools_call(&params),
            "resources/list" => Ok(self.resources_list()),
            "resources/templates/list" => Ok(json!({ "resourceTemplates": [] })),
            "resources/read" => self.resources_read(&params),
            "prompts/list" => Ok(json!({ "prompts": prompts() })),
            "prompts/get" => self.prompts_get(&params),
            other => {
                if is_notification {
                    return None;
                }
                return Some(error_response(
                    id,
                    METHOD_NOT_FOUND,
                    &format!("unknown method '{other}'"),
                ));
            }
        };

        if is_notification {
            return None;
        }
        Some(match result {
            Ok(value) => json!({ "jsonrpc": "2.0", "id": id, "result": value }),
            Err(message) => error_response(id, INVALID_PARAMS, &message),
        })
    }

    fn initialize(&mut self, params: &Value) -> Value {
        let requested = params
            .get("protocolVersion")
            .and_then(Value::as_str)
            .unwrap_or(SUPPORTED_PROTOCOL_VERSIONS[0]);
        let version = if SUPPORTED_PROTOCOL_VERSIONS.contains(&requested) {
            requested
        } else {
            SUPPORTED_PROTOCOL_VERSIONS[0]
        };
        let stats = self.graph.stats();
        json!({
            "protocolVersion": version,
            "capabilities": {
                "tools": { "listChanged": false },
                "resources": { "listChanged": false, "subscribe": false },
                "prompts": { "listChanged": false },
            },
            "serverInfo": { "name": SERVER_NAME, "version": SERVER_VERSION },
            "instructions": format!(
                "Knowledge graph over six Brazilian soccer datasets: {} teams, {} matches ({} after de-duplicating overlapping files) and {} FIFA players. \
                 Use search_matches/head_to_head for fixtures, team_stats/team_rankings/standings for performance, search_players/club_players for squads, \
                 find_team when a club name is ambiguous and dataset_overview for coverage and caveats.",
                stats.teams, stats.matches, stats.canonical_matches, stats.players
            ),
        })
    }

    fn tools_call(&self, params: &Value) -> Result<Value, String> {
        let name = params
            .get("name")
            .and_then(Value::as_str)
            .ok_or("tools/call requires a 'name'")?;
        let arguments = params.get("arguments").cloned().unwrap_or(Value::Null);
        match tools::call(&self.graph, name, &arguments) {
            Ok(output) => Ok(json!({
                "content": [{ "type": "text", "text": output.text }],
                "structuredContent": output.data,
                "isError": false,
            })),
            // Tool-level failures are results, not protocol errors, so the model
            // sees the message and can retry with different arguments.
            Err(message) => Ok(json!({
                "content": [{ "type": "text", "text": message }],
                "isError": true,
            })),
        }
    }

    fn resources_list(&self) -> Value {
        let mut resources = vec![
            json!({
                "uri": "soccer://overview",
                "name": "dataset-overview",
                "title": "Dataset overview",
                "description": "Files, licenses, coverage, graph size and data caveats",
                "mimeType": "text/markdown",
            }),
            json!({
                "uri": "soccer://teams",
                "name": "teams",
                "title": "Canonical clubs",
                "description": "Every club in the graph with its name variants",
                "mimeType": "application/json",
            }),
            json!({
                "uri": "soccer://competitions",
                "name": "competitions",
                "title": "Competitions and seasons",
                "description": "Competitions with the seasons available for each",
                "mimeType": "application/json",
            }),
        ];
        for report in &self.graph.reports {
            resources.push(json!({
                "uri": format!("soccer://source/{}", report.source.file_name()),
                "name": report.source.file_name(),
                "title": report.source.label(),
                "description": format!("{} rows, license {}", report.rows_used, report.source.license()),
                "mimeType": "application/json",
            }));
        }
        json!({ "resources": resources })
    }

    fn resources_read(&self, params: &Value) -> Result<Value, String> {
        let uri = params
            .get("uri")
            .and_then(Value::as_str)
            .ok_or("resources/read requires a 'uri'")?;
        let (mime, text) = match uri {
            "soccer://overview" => (
                "text/markdown",
                tools::call(&self.graph, "dataset_overview", &Value::Null)
                    .map_err(|e| e.to_string())?
                    .text,
            ),
            "soccer://teams" => (
                "application/json",
                serde_json::to_string_pretty(&json!({
                    "teams": self.graph.teams.iter().map(|team| json!({
                        "key": team.key,
                        "name": team.name,
                        "state": team.state,
                        "country": team.country,
                        "matches": self.graph.team_matches(team.id).len(),
                        "aliases": team.aliases,
                    })).collect::<Vec<_>>()
                }))
                .unwrap(),
            ),
            "soccer://competitions" => (
                "application/json",
                serde_json::to_string_pretty(&json!({
                    "competitions": self.graph.competitions().iter().map(|competition| json!({
                        "id": competition.slug(),
                        "name": competition.name(),
                        "seasons": self.graph.seasons(*competition),
                        "matches": self.graph.competition_matches(*competition).len(),
                        "source_priority": Source::priority_for(*competition)
                            .iter().map(|s| s.file_name()).collect::<Vec<_>>(),
                    })).collect::<Vec<_>>()
                }))
                .unwrap(),
            ),
            other if other.starts_with("soccer://source/") => {
                let file = other.trim_start_matches("soccer://source/");
                let report = self
                    .graph
                    .reports
                    .iter()
                    .find(|report| report.source.file_name() == file)
                    .ok_or_else(|| format!("unknown source file '{file}'"))?;
                (
                    "application/json",
                    serde_json::to_string_pretty(&json!({
                        "file": report.source.file_name(),
                        "description": report.source.label(),
                        "license": report.source.license(),
                        "rows_read": report.rows_read,
                        "rows_used": report.rows_used,
                        "rows_skipped": report.rows_skipped,
                    }))
                    .unwrap(),
                )
            }
            other => return Err(format!("unknown resource '{other}'")),
        };
        Ok(json!({
            "contents": [{ "uri": uri, "mimeType": mime, "text": text }],
        }))
    }

    fn prompts_get(&self, params: &Value) -> Result<Value, String> {
        let name = params
            .get("name")
            .and_then(Value::as_str)
            .ok_or("prompts/get requires a 'name'")?;
        let arguments = params.get("arguments").cloned().unwrap_or(Value::Null);
        let text = match name {
            "club_report" => {
                let club = arguments
                    .get("club")
                    .and_then(Value::as_str)
                    .ok_or("'club' argument is required")?;
                format!(
                    "Produce a report on {club}: call team_profile for its competitions, team_stats for its overall record, \
                     team_rankings to place it among its peers and club_players for its FIFA squad. Mention data caveats where relevant."
                )
            }
            "season_review" => {
                let season = arguments
                    .get("season")
                    .and_then(|value| value.as_i64().or_else(|| value.as_str()?.parse().ok()))
                    .ok_or("'season' argument is required")?;
                format!(
                    "Review the {season} Brasileirão: call standings for the final table, competition_stats for scoring trends \
                     and biggest_wins for the standout results. Name the champion and the relegated clubs."
                )
            }
            other => return Err(format!("unknown prompt '{other}'")),
        };
        Ok(json!({
            "messages": [{
                "role": "user",
                "content": { "type": "text", "text": text },
            }],
        }))
    }
}

fn prompts() -> Value {
    json!([
        {
            "name": "club_report",
            "title": "Club report",
            "description": "Summarise a club's history, record and squad",
            "arguments": [{ "name": "club", "description": "Club name", "required": true }],
        },
        {
            "name": "season_review",
            "title": "Season review",
            "description": "Review a Brasileirão season: table, champion, relegation, scoring trends",
            "arguments": [{ "name": "season", "description": "Season year", "required": true }],
        },
    ])
}

fn tools_list() -> Value {
    json!({
        "tools": TOOLS.iter().map(|tool| json!({
            "name": tool.name,
            "description": tool.description,
            "inputSchema": (tool.schema)(),
        })).collect::<Vec<_>>(),
    })
}

fn error_response(id: Value, code: i64, message: &str) -> Value {
    json!({
        "jsonrpc": "2.0",
        "id": id,
        "error": { "code": code, "message": message },
    })
}

/// Competitions advertised in the server instructions; kept here so the
/// protocol layer has no dependency on query internals.
pub fn competition_names() -> Vec<&'static str> {
    Competition::ALL.iter().map(|c| c.name()).collect()
}
