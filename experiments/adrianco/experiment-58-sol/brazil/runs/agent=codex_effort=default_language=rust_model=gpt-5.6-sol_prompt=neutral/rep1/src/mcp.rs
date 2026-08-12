use crate::{
    json::{Json, object},
    query::SoccerService,
};
use std::io::{self, BufRead, Write};

const LATEST_PROTOCOL: &str = "2026-07-28";
const LEGACY_PROTOCOL: &str = "2025-11-25";

pub struct McpServer {
    service: SoccerService,
}

impl McpServer {
    pub fn new(service: SoccerService) -> Self {
        Self { service }
    }

    pub fn run_stdio(&self) -> io::Result<()> {
        let stdin = io::stdin();
        let mut stdout = io::stdout().lock();
        for line in stdin.lock().lines() {
            let line = line?;
            if line.trim().is_empty() {
                continue;
            }
            if let Some(response) = self.handle_line(&line) {
                writeln!(stdout, "{response}")?;
                stdout.flush()?;
            }
        }
        Ok(())
    }

    pub fn handle_line(&self, line: &str) -> Option<String> {
        let request = match Json::parse(line) {
            Ok(value) => value,
            Err(message) => {
                return Some(
                    error_response(Json::Null, -32700, &format!("Parse error: {message}"), None)
                        .stringify(),
                );
            }
        };
        self.handle_request(&request).map(|value| value.stringify())
    }

    pub fn handle_request(&self, request: &Json) -> Option<Json> {
        let id = request.get("id").cloned();
        let method = request.get("method").and_then(Json::as_str);
        if request.get("jsonrpc").and_then(Json::as_str) != Some("2.0") || method.is_none() {
            return id.map(|id| error_response(id, -32600, "Invalid Request", None));
        }
        // Notifications never receive a response.
        let id = id?;
        let method = method.unwrap();
        let params = request.get("params").unwrap_or(&Json::Null);
        match method {
            "server/discover" => Some(success(id, discover_result())),
            "initialize" => Some(success(id, initialize_result(params))),
            "ping" => Some(success(id, object([] as [(&str, Json); 0]))),
            "tools/list" => Some(success(
                id,
                object([
                    ("resultType", "complete".into()),
                    ("tools", Json::Array(tool_definitions())),
                ]),
            )),
            "tools/call" => Some(self.call_tool(id, params)),
            _ => Some(error_response(
                id,
                -32601,
                "Method not found",
                Some(object([("method", method.into())])),
            )),
        }
    }

    fn call_tool(&self, id: Json, params: &Json) -> Json {
        let Some(name) = params.get("name").and_then(Json::as_str) else {
            return error_response(id, -32602, "tools/call requires a string name", None);
        };
        if !TOOL_NAMES.contains(&name) {
            return error_response(id, -32602, &format!("Unknown tool: {name}"), None);
        }
        let empty = object([] as [(&str, Json); 0]);
        let args = params.get("arguments").unwrap_or(&empty);
        match self.service.call_tool(name, args) {
            Ok(output) => success(
                id,
                object([
                    ("resultType", "complete".into()),
                    (
                        "content",
                        Json::Array(vec![object([
                            ("type", "text".into()),
                            ("text", output.text.into()),
                        ])]),
                    ),
                    ("structuredContent", output.structured),
                    ("isError", false.into()),
                ]),
            ),
            Err(message) => success(
                id,
                object([
                    ("resultType", "complete".into()),
                    (
                        "content",
                        Json::Array(vec![object([
                            ("type", "text".into()),
                            ("text", message.into()),
                        ])]),
                    ),
                    ("isError", true.into()),
                ]),
            ),
        }
    }
}

const TOOL_NAMES: &[&str] = &[
    "dataset_info",
    "search_matches",
    "team_statistics",
    "team_overview",
    "head_to_head",
    "search_derbies",
    "search_players",
    "standings",
    "competition_statistics",
    "team_rankings",
    "biggest_wins",
];

fn discover_result() -> Json {
    object([
        ("resultType", "complete".into()),
        (
            "supportedVersions",
            Json::Array(vec![
                LATEST_PROTOCOL.into(),
                LEGACY_PROTOCOL.into(),
                "2025-06-18".into(),
                "2024-11-05".into(),
            ]),
        ),
        ("capabilities", capabilities()),
        ("instructions", instructions().into()),
        ("cacheScope", "public".into()),
    ])
}

fn initialize_result(params: &Json) -> Json {
    let requested = params
        .get("protocolVersion")
        .and_then(Json::as_str)
        .unwrap_or(LEGACY_PROTOCOL);
    let protocol = if requested == LATEST_PROTOCOL {
        LEGACY_PROTOCOL
    } else {
        requested
    };
    object([
        ("protocolVersion", protocol.into()), ("capabilities", capabilities()),
        ("serverInfo", object([
            ("name", "brazilian-soccer-mcp".into()), ("title", "Brazilian Soccer Knowledge Graph".into()),
            ("version", env!("CARGO_PKG_VERSION").into()),
            ("description", "Search and analyze the bundled Brazilian soccer match and FIFA player datasets.".into()),
        ])),
        ("instructions", instructions().into()),
    ])
}

fn capabilities() -> Json {
    object([("tools", object([("listChanged", false.into())]))])
}

fn instructions() -> &'static str {
    "Use search_matches for games and schedules, team_statistics or head_to_head for club performance, team_overview to combine a club's match competitions with its FIFA players, search_derbies for traditional rivalries, search_players for FIFA player records, standings for a season table, competition_statistics for aggregate rates, team_rankings for best home/away records, and biggest_wins for score margins. Team matching ignores accents, common full-name forms, and Brazilian state suffixes. Results come only from the bundled historical datasets, not live feeds."
}

fn tool_definitions() -> Vec<Json> {
    vec![
        tool(
            "dataset_info",
            "Report loaded files, record counts, coverage, and available query capabilities.",
            schema(&[], &[]),
        ),
        tool(
            "search_matches",
            "Find historical match results. Supports one team, an optional opponent, home/away venue, date range, competition, season, stage/round, and source file. Use for 'last played', schedules/results, finals, derbies, and competitions a team played in.",
            schema(
                &[],
                &[
                    ("team", "string"),
                    ("opponent", "string"),
                    ("competition", "string"),
                    ("season", "integer"),
                    ("date_from", "string"),
                    ("date_to", "string"),
                    ("stage", "string"),
                    ("venue", "string"),
                    ("source", "string"),
                    ("limit", "integer"),
                    ("offset", "integer"),
                ],
            ),
        ),
        tool(
            "team_statistics",
            "Calculate a team's wins, draws, losses, goals for/against, goal difference, points, and win rate. Filter by season, competition, date range, source, and home or away venue.",
            schema(
                &["team"],
                &[
                    ("team", "string"),
                    ("competition", "string"),
                    ("season", "integer"),
                    ("date_from", "string"),
                    ("date_to", "string"),
                    ("venue", "string"),
                    ("source", "string"),
                ],
            ),
        ),
        tool(
            "team_overview",
            "Combine a club's match history, competitions, aggregate record, and players from the separate FIFA dataset in one cross-file answer. The optional season filters matches; FIFA is a fixed historical snapshot.",
            schema(
                &["team"],
                &[
                    ("team", "string"),
                    ("season", "integer"),
                    ("player_limit", "integer"),
                ],
            ),
        ),
        tool(
            "head_to_head",
            "Compare two teams and return wins, draws, and their recent meetings. Team order does not affect which matches are found.",
            schema(
                &["team_a", "team_b"],
                &[
                    ("team_a", "string"),
                    ("team_b", "string"),
                    ("competition", "string"),
                    ("season", "integer"),
                    ("date_from", "string"),
                    ("date_to", "string"),
                    ("source", "string"),
                    ("limit", "integer"),
                ],
            ),
        ),
        tool(
            "search_derbies",
            "Find matches between a curated set of traditional Brazilian rivals (including Fla-Flu, Grenal, Derby Paulista, Majestoso, Choque-Rei, Clássico Mineiro, Ba-Vi, Re-Pa, and Atletiba). Filter by season, competition, or one participating team.",
            schema(
                &[],
                &[
                    ("season", "integer"),
                    ("competition", "string"),
                    ("team", "string"),
                    ("limit", "integer"),
                ],
            ),
        ),
        tool(
            "search_players",
            "Search the FIFA player database by partial name, nationality, normalized club, position group (forward/midfielder/defender/goalkeeper), and rating range. Sorted by overall rating.",
            schema(
                &[],
                &[
                    ("name", "string"),
                    ("nationality", "string"),
                    ("club", "string"),
                    ("position", "string"),
                    ("min_overall", "integer"),
                    ("max_overall", "integer"),
                    ("limit", "integer"),
                    ("offset", "integer"),
                ],
            ),
        ),
        tool(
            "standings",
            "Calculate a season's competition table using 3 points per win, then wins, goal difference, and goals scored as tie-breakers. Uses the dedicated competition dataset to avoid overlap.",
            schema(
                &["season"],
                &[
                    ("season", "integer"),
                    ("competition", "string"),
                    ("limit", "integer"),
                ],
            ),
        ),
        tool(
            "competition_statistics",
            "Calculate match count, total and average goals, home wins, away wins, and draws for a competition, optionally in one season.",
            schema(
                &["competition"],
                &[
                    ("competition", "string"),
                    ("season", "integer"),
                    ("source", "string"),
                ],
            ),
        ),
        tool(
            "team_rankings",
            "Rank teams by win rate for home, away, or all matches, with optional season and competition filters. Use for 'best home/away record' questions.",
            schema(
                &[],
                &[
                    ("venue", "string"),
                    ("season", "integer"),
                    ("competition", "string"),
                    ("minimum_matches", "integer"),
                    ("limit", "integer"),
                ],
            ),
        ),
        tool(
            "biggest_wins",
            "Return matches with the largest absolute goal margin, optionally filtered by team, season, competition, or source.",
            schema(
                &[],
                &[
                    ("team", "string"),
                    ("season", "integer"),
                    ("competition", "string"),
                    ("source", "string"),
                    ("limit", "integer"),
                ],
            ),
        ),
    ]
}

fn tool(name: &str, description: &str, input_schema: Json) -> Json {
    object([
        ("name", name.into()),
        ("title", title(name).into()),
        ("description", description.into()),
        ("inputSchema", input_schema),
        ("outputSchema", object([("type", "object".into())])),
        (
            "annotations",
            object([
                ("readOnlyHint", true.into()),
                ("destructiveHint", false.into()),
                ("idempotentHint", true.into()),
                ("openWorldHint", false.into()),
            ]),
        ),
    ])
}

fn title(name: &str) -> String {
    name.split('_')
        .map(|word| {
            let mut chars = word.chars();
            chars
                .next()
                .map(|ch| ch.to_uppercase().collect::<String>() + chars.as_str())
                .unwrap_or_default()
        })
        .collect::<Vec<_>>()
        .join(" ")
}

fn schema(required: &[&str], properties: &[(&str, &str)]) -> Json {
    let mut props = std::collections::BTreeMap::new();
    for (name, kind) in properties {
        props.insert((*name).into(), object([("type", (*kind).into())]));
    }
    object([
        (
            "$schema",
            "https://json-schema.org/draft/2020-12/schema".into(),
        ),
        ("type", "object".into()),
        ("properties", Json::Object(props)),
        (
            "required",
            Json::Array(required.iter().map(|value| (*value).into()).collect()),
        ),
        ("additionalProperties", false.into()),
    ])
}

fn success(id: Json, result: Json) -> Json {
    object([("jsonrpc", "2.0".into()), ("id", id), ("result", result)])
}

fn error_response(id: Json, code: i32, message: &str, data: Option<Json>) -> Json {
    let mut error = object([("code", code.into()), ("message", message.into())]);
    if let (Json::Object(map), Some(data)) = (&mut error, data) {
        map.insert("data".into(), data);
    }
    object([("jsonrpc", "2.0".into()), ("id", id), ("error", error)])
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::data::{DataStore, DatasetReport};
    use std::path::PathBuf;

    fn server() -> McpServer {
        McpServer::new(SoccerService::new(DataStore {
            matches: vec![],
            players: vec![],
            teams: Default::default(),
            reports: Vec::<DatasetReport>::new(),
            data_dir: PathBuf::new(),
        }))
    }

    #[test]
    fn supports_discovery_and_legacy_initialization() {
        let discover = server()
            .handle_line(r#"{"jsonrpc":"2.0","id":1,"method":"server/discover","params":{}}"#)
            .unwrap();
        let json = Json::parse(&discover).unwrap();
        assert_eq!(
            json.get("result")
                .and_then(|r| r.get("resultType"))
                .and_then(Json::as_str),
            Some("complete")
        );
        let initialize = server().handle_line(r#"{"jsonrpc":"2.0","id":"a","method":"initialize","params":{"protocolVersion":"2025-11-25"}}"#).unwrap();
        assert_eq!(
            Json::parse(&initialize)
                .unwrap()
                .get("result")
                .and_then(|r| r.get("protocolVersion"))
                .and_then(Json::as_str),
            Some("2025-11-25")
        );
    }

    #[test]
    fn lists_eleven_read_only_tools() {
        let response = server()
            .handle_line(r#"{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}"#)
            .unwrap();
        let parsed = Json::parse(&response).unwrap();
        let Json::Array(tools) = parsed.get("result").and_then(|r| r.get("tools")).unwrap() else {
            panic!()
        };
        assert_eq!(tools.len(), 11);
        assert!(tools.iter().all(|tool| {
            tool.get("annotations")
                .and_then(|a| a.get("readOnlyHint"))
                .and_then(Json::as_bool)
                == Some(true)
        }));
    }

    #[test]
    fn parse_errors_and_notifications_follow_json_rpc() {
        let bad = server().handle_line("{").unwrap();
        assert_eq!(
            Json::parse(&bad)
                .unwrap()
                .get("error")
                .and_then(|e| e.get("code"))
                .and_then(Json::as_i64),
            Some(-32700)
        );
        assert!(
            server()
                .handle_line(r#"{"jsonrpc":"2.0","method":"notifications/initialized"}"#)
                .is_none()
        );
    }
}
