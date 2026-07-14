//! ============================================================================
//! Context
//! ----------------------------------------------------------------------------
//! Module:   mcp
//! Purpose:  Implement the Model Context Protocol (MCP) JSON-RPC 2.0 surface
//!           over which the Brazilian-soccer knowledge graph is exposed.
//!
//! Transport is handled in `main` (newline-delimited JSON over stdio). This
//! module owns:
//!   * the protocol handshake (`initialize`, `notifications/initialized`,
//!     `ping`),
//!   * the tool catalog (`tools/list`),
//!   * tool invocation (`tools/call`) which bridges into the `query` + `format`
//!     layers.
//!
//! `handle_message` is a pure function of (Server, request JSON) -> optional
//! response JSON, which keeps the whole protocol layer unit-testable without
//! any actual stdio.
//! ============================================================================

use serde_json::{json, Value};

use crate::data::Database;
use crate::format;
use crate::query::{self, MatchFilter, PlayerFilter, Venue};

/// MCP protocol version we advertise. Matches the dated revision string used by
/// the reference implementations.
pub const PROTOCOL_VERSION: &str = "2024-11-05";
pub const SERVER_NAME: &str = "brazilian-soccer-mcp";
pub const SERVER_VERSION: &str = env!("CARGO_PKG_VERSION");

/// Holds the loaded data and answers MCP requests.
pub struct Server {
    pub db: Database,
}

impl Server {
    pub fn new(db: Database) -> Self {
        Server { db }
    }

    /// Handle one JSON-RPC message. Returns `Some(response)` for requests and
    /// `None` for notifications (which must not be answered).
    pub fn handle_message(&self, msg: &Value) -> Option<Value> {
        let id = msg.get("id").cloned();
        let method = msg.get("method").and_then(|m| m.as_str()).unwrap_or("");

        // Notifications carry no `id` and expect no reply.
        let is_notification = id.is_none();

        let result = match method {
            "initialize" => Ok(self.initialize()),
            "tools/list" => Ok(self.tools_list()),
            "tools/call" => self.tools_call(msg.get("params")),
            "ping" => Ok(json!({})),
            "notifications/initialized" | "notifications/cancelled" => {
                return None; // acknowledged silently
            }
            other => Err(JsonRpcError::method_not_found(other)),
        };

        if is_notification {
            return None;
        }
        let id = id.unwrap_or(Value::Null);
        Some(match result {
            Ok(value) => json!({"jsonrpc": "2.0", "id": id, "result": value}),
            Err(e) => json!({"jsonrpc": "2.0", "id": id, "error": e.to_json()}),
        })
    }

    fn initialize(&self) -> Value {
        json!({
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": { "tools": {} },
            "serverInfo": { "name": SERVER_NAME, "version": SERVER_VERSION },
            "instructions": "Query a knowledge graph of Brazilian soccer: \
                matches (Brasileirão, Copa do Brasil, Copa Libertadores), team \
                records, calculated league standings, FIFA players and \
                aggregate statistics. Team names are normalized so suffixes \
                like '-SP' and accents are handled automatically."
        })
    }

    fn tools_list(&self) -> Value {
        json!({ "tools": tool_catalog() })
    }

    fn tools_call(&self, params: Option<&Value>) -> Result<Value, JsonRpcError> {
        let params = params.ok_or_else(|| JsonRpcError::invalid_params("missing params"))?;
        let name = params
            .get("name")
            .and_then(|n| n.as_str())
            .ok_or_else(|| JsonRpcError::invalid_params("missing tool name"))?;
        let empty = json!({});
        let args = params.get("arguments").unwrap_or(&empty);

        let text = self
            .dispatch_tool(name, args)
            .map_err(JsonRpcError::invalid_params)?;

        Ok(json!({
            "content": [ { "type": "text", "text": text } ],
            "isError": false
        }))
    }

    /// Run a named tool and return its rendered text. `Err` means bad input.
    pub fn dispatch_tool(&self, name: &str, args: &Value) -> Result<String, String> {
        match name {
            "search_matches" => Ok(self.tool_search_matches(args)),
            "head_to_head" => self.tool_head_to_head(args),
            "team_record" => self.tool_team_record(args),
            "standings" => self.tool_standings(args),
            "search_players" => Ok(self.tool_search_players(args)),
            "player_profile" => self.tool_player_profile(args),
            "competition_stats" => Ok(self.tool_competition_stats(args)),
            "players_by_club" => Ok(self.tool_players_by_club(args)),
            other => Err(format!("unknown tool: {}", other)),
        }
    }

    // ---- individual tool implementations ---------------------------------

    fn tool_search_matches(&self, args: &Value) -> String {
        let filter = MatchFilter {
            team: opt_str(args, "team"),
            opponent: opt_str(args, "opponent"),
            competition: opt_str(args, "competition"),
            season: opt_i32(args, "season"),
            venue: Venue::parse(&opt_str(args, "venue").unwrap_or_default()),
            date_from: opt_str(args, "date_from")
                .and_then(|s| crate::normalize::parse_date(&s)),
            date_to: opt_str(args, "date_to").and_then(|s| crate::normalize::parse_date(&s)),
            include_extended: args
                .get("include_extended")
                .and_then(|v| v.as_bool())
                .unwrap_or(false),
        };
        let mut matches = query::search_matches(&self.db, &filter);
        if let Some(limit) = opt_usize(args, "limit") {
            matches.truncate(limit);
        }
        let title = describe_match_query(&filter);
        format::format_matches(&title, &matches)
    }

    fn tool_head_to_head(&self, args: &Value) -> Result<String, String> {
        let a = req_str(args, "team_a")?;
        let b = req_str(args, "team_b")?;
        let h = query::head_to_head(&self.db, &a, &b);
        Ok(format::format_head_to_head(&h))
    }

    fn tool_team_record(&self, args: &Value) -> Result<String, String> {
        let team = req_str(args, "team")?;
        let season = opt_i32(args, "season");
        let competition = opt_str(args, "competition");
        let venue = Venue::parse(&opt_str(args, "venue").unwrap_or_default());
        let rec = query::team_record(&self.db, &team, season, competition.as_deref(), venue);

        let mut scope = Vec::new();
        if let Some(s) = season {
            scope.push(s.to_string());
        }
        if let Some(c) = &competition {
            scope.push(crate::normalize::canonical_competition(c));
        }
        match venue {
            Venue::Home => scope.push("home".into()),
            Venue::Away => scope.push("away".into()),
            Venue::Any => {}
        }
        let scope = if scope.is_empty() {
            "(all competitions, all seasons)".to_string()
        } else {
            format!("({})", scope.join(" "))
        };
        Ok(format::format_team_record(&rec, &scope))
    }

    fn tool_standings(&self, args: &Value) -> Result<String, String> {
        let season = opt_i32(args, "season")
            .ok_or_else(|| "standings requires a 'season' (year)".to_string())?;
        let competition = opt_str(args, "competition").unwrap_or_else(|| "Brasileirão".into());
        let comp_label = crate::normalize::canonical_competition(&competition);
        let rows = query::standings(&self.db, &competition, season);
        Ok(format::format_standings(&rows, &comp_label, season))
    }

    fn tool_search_players(&self, args: &Value) -> String {
        let filter = PlayerFilter {
            name: opt_str(args, "name"),
            nationality: opt_str(args, "nationality"),
            club: opt_str(args, "club"),
            position: opt_str(args, "position"),
            min_overall: opt_i32(args, "min_overall").map(|n| n.max(0) as u32),
            limit: opt_usize(args, "limit").or(Some(25)),
        };
        let players = query::search_players(&self.db, &filter);
        let title = describe_player_query(&filter);
        format::format_players(&title, &players)
    }

    fn tool_player_profile(&self, args: &Value) -> Result<String, String> {
        let name = req_str(args, "name")?;
        let filter = PlayerFilter {
            name: Some(name.clone()),
            limit: Some(1),
            ..Default::default()
        };
        let players = query::search_players(&self.db, &filter);
        match players.first() {
            Some(p) => Ok(format::format_player_detail(p)),
            None => Ok(format!("No player matching \"{}\" found in the dataset.", name)),
        }
    }

    fn tool_competition_stats(&self, args: &Value) -> String {
        let competition = opt_str(args, "competition");
        let season = opt_i32(args, "season");
        let stats = query::competition_stats(&self.db, competition.as_deref(), season);
        let biggest = query::biggest_wins(&self.db, competition.as_deref(), season, 5);

        let mut scope = Vec::new();
        if let Some(c) = &competition {
            scope.push(crate::normalize::canonical_competition(c));
        }
        if let Some(s) = season {
            scope.push(s.to_string());
        }
        let scope = if scope.is_empty() {
            "(all competitions)".to_string()
        } else {
            format!("({})", scope.join(" "))
        };
        format::format_stats(&stats, &scope, &biggest)
    }

    fn tool_players_by_club(&self, args: &Value) -> String {
        let nationality = opt_str(args, "nationality").unwrap_or_else(|| "Brazil".into());
        let filter = PlayerFilter {
            nationality: Some(nationality.clone()),
            min_overall: opt_i32(args, "min_overall").map(|n| n.max(0) as u32),
            ..Default::default()
        };
        let players = query::search_players(&self.db, &filter);
        let aggs = query::group_by_club(&players);
        let title = format!("{} players grouped by club", nationality);
        format::format_club_aggregates(&title, &aggs)
    }
}

// ---- argument helpers ----------------------------------------------------

fn opt_str(args: &Value, key: &str) -> Option<String> {
    args.get(key).and_then(|v| match v {
        Value::String(s) if !s.trim().is_empty() => Some(s.trim().to_string()),
        Value::Number(n) => Some(n.to_string()),
        _ => None,
    })
}

fn req_str(args: &Value, key: &str) -> Result<String, String> {
    opt_str(args, key).ok_or_else(|| format!("missing required argument '{}'", key))
}

fn opt_i32(args: &Value, key: &str) -> Option<i32> {
    match args.get(key) {
        Some(Value::Number(n)) => n.as_i64().map(|v| v as i32),
        Some(Value::String(s)) => s.trim().parse().ok(),
        _ => None,
    }
}

fn opt_usize(args: &Value, key: &str) -> Option<usize> {
    opt_i32(args, key).and_then(|n| if n >= 0 { Some(n as usize) } else { None })
}

fn describe_match_query(f: &MatchFilter) -> String {
    let mut parts = Vec::new();
    if let (Some(t), Some(o)) = (&f.team, &f.opponent) {
        parts.push(format!("{} vs {}", t, o));
    } else if let Some(t) = &f.team {
        let v = match f.venue {
            Venue::Home => " (home)",
            Venue::Away => " (away)",
            Venue::Any => "",
        };
        parts.push(format!("{}{}", t, v));
    } else if let Some(o) = &f.opponent {
        parts.push(format!("matches involving {}", o));
    }
    if let Some(c) = &f.competition {
        parts.push(crate::normalize::canonical_competition(c));
    }
    if let Some(s) = f.season {
        parts.push(s.to_string());
    }
    if parts.is_empty() {
        "Matches".to_string()
    } else {
        format!("Matches: {}", parts.join(", "))
    }
}

fn describe_player_query(f: &PlayerFilter) -> String {
    let mut parts = Vec::new();
    if let Some(n) = &f.name {
        parts.push(format!("name~\"{}\"", n));
    }
    if let Some(n) = &f.nationality {
        parts.push(n.clone());
    }
    if let Some(c) = &f.club {
        parts.push(format!("at {}", c));
    }
    if let Some(p) = &f.position {
        parts.push(p.clone());
    }
    if let Some(m) = f.min_overall {
        parts.push(format!("overall>={}", m));
    }
    if parts.is_empty() {
        "Players".to_string()
    } else {
        format!("Players: {}", parts.join(", "))
    }
}

/// The static catalog returned by `tools/list`.
pub fn tool_catalog() -> Value {
    json!([
        {
            "name": "search_matches",
            "description": "Search matches by team, opponent, competition (Brasileirão / Copa do Brasil / Copa Libertadores), season (year), venue (home/away/any) and/or date range. Returns matches newest first.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team": {"type": "string", "description": "Team name; suffixes like '-SP' and accents are handled."},
                    "opponent": {"type": "string", "description": "Restrict to matches against this team."},
                    "competition": {"type": "string", "description": "Brasileirão, Copa do Brasil, or Copa Libertadores (aliases like 'Serie A' accepted)."},
                    "season": {"type": "integer", "description": "Season year, e.g. 2019."},
                    "venue": {"type": "string", "enum": ["home", "away", "any"], "description": "Side the 'team' played on."},
                    "date_from": {"type": "string", "description": "Inclusive start date (YYYY-MM-DD)."},
                    "date_to": {"type": "string", "description": "Inclusive end date (YYYY-MM-DD)."},
                    "include_extended": {"type": "boolean", "description": "Also search the extended BR-Football dataset (off by default; it overlaps the curated files with divergent dates/scores)."},
                    "limit": {"type": "integer", "description": "Maximum matches to return."}
                }
            }
        },
        {
            "name": "head_to_head",
            "description": "Head-to-head record and match list between two teams across all competitions in the dataset.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_a": {"type": "string"},
                    "team_b": {"type": "string"}
                },
                "required": ["team_a", "team_b"]
            }
        },
        {
            "name": "team_record",
            "description": "Win/draw/loss record, goals for/against, points and win rate for a team, optionally scoped by season, competition and venue.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team": {"type": "string"},
                    "season": {"type": "integer"},
                    "competition": {"type": "string"},
                    "venue": {"type": "string", "enum": ["home", "away", "any"]}
                },
                "required": ["team"]
            }
        },
        {
            "name": "standings",
            "description": "Calculate the final league table for a competition and season from match results (3 pts win, 1 draw). Defaults to Brasileirão.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "competition": {"type": "string"},
                    "season": {"type": "integer"}
                },
                "required": ["season"]
            }
        },
        {
            "name": "search_players",
            "description": "Search the FIFA player database by name, nationality, club, position and/or minimum overall rating. Sorted by Overall rating descending.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "nationality": {"type": "string", "description": "e.g. Brazil"},
                    "club": {"type": "string"},
                    "position": {"type": "string", "description": "e.g. ST, GK, CB"},
                    "min_overall": {"type": "integer"},
                    "limit": {"type": "integer"}
                }
            }
        },
        {
            "name": "player_profile",
            "description": "Detailed profile (nationality, club, position, age, ratings) for the best name match in the FIFA database. Answers 'Who is X?'.",
            "inputSchema": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"]
            }
        },
        {
            "name": "competition_stats",
            "description": "Aggregate statistics (total matches, average goals per match, home/away/draw rates, biggest victories) for an optional competition and/or season.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "competition": {"type": "string"},
                    "season": {"type": "integer"}
                }
            }
        },
        {
            "name": "players_by_club",
            "description": "Group players of a given nationality (default Brazil) by club, with player counts and average rating. Useful for 'Brazilian players at Brazilian clubs'.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "nationality": {"type": "string"},
                    "min_overall": {"type": "integer"}
                }
            }
        }
    ])
}

// ---- JSON-RPC error helper ----------------------------------------------

#[derive(Debug)]
pub struct JsonRpcError {
    pub code: i64,
    pub message: String,
}

impl JsonRpcError {
    pub fn method_not_found(method: &str) -> Self {
        JsonRpcError {
            code: -32601,
            message: format!("Method not found: {}", method),
        }
    }
    pub fn invalid_params(msg: impl Into<String>) -> Self {
        JsonRpcError {
            code: -32602,
            message: msg.into(),
        }
    }
    pub fn to_json(&self) -> Value {
        json!({ "code": self.code, "message": self.message })
    }
}
