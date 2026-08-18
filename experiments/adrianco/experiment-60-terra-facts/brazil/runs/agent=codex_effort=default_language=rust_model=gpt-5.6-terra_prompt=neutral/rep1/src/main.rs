use brazilian_soccer_mcp::{Database, Result};
use serde_json::{json, Value};
use std::io::{self, BufRead, Write};

fn main() -> Result<()> {
    let data = std::env::var("SOCCER_DATA_DIR").unwrap_or_else(|_| "data/kaggle".into());
    let db = Database::load(data)?;
    let stdin = io::stdin();
    let mut out = io::stdout();
    for line in stdin.lock().lines() {
        let line = line?;
        if line.trim().is_empty() {
            continue;
        }
        let req: Value = match serde_json::from_str(&line) {
            Ok(v) => v,
            Err(e) => {
                write(
                    &mut out,
                    json!({"jsonrpc":"2.0","id":null,"error":{"code":-32700,"message":e.to_string()}}),
                )?;
                continue;
            }
        };
        if let Some(resp) = handle(&db, &req) {
            write(&mut out, resp)?;
        }
    }
    Ok(())
}
fn write(out: &mut impl Write, v: Value) -> Result<()> {
    writeln!(out, "{}", serde_json::to_string(&v)?)?;
    out.flush()?;
    Ok(())
}
fn handle(db: &Database, req: &Value) -> Option<Value> {
    let id = req.get("id").cloned()?;
    let result = match req["method"].as_str()? {
        "initialize" => {
            json!({"protocolVersion":"2024-11-05","capabilities":{"tools":{"listChanged":false}},"serverInfo":{"name":"brazilian-soccer-mcp","version":env!("CARGO_PKG_VERSION")}})
        }
        "notifications/initialized" => return None,
        "tools/list" => json!({"tools":tools()}),
        "tools/call" => call(db, &req["params"]),
        _ => {
            return Some(
                json!({"jsonrpc":"2.0","id":id,"error":{"code":-32601,"message":"Method not found"}}),
            )
        }
    };
    Some(json!({"jsonrpc":"2.0","id":id,"result":result}))
}
fn tools() -> Vec<Value> {
    vec![
        tool(
            "search_matches",
            "Find matches by team, opponent, competition, season, or ISO date range",
            json!({
                "team":{"type":"string"}, "opponent":{"type":"string"},
                "competition":{"type":"string"}, "season":{"type":"integer"},
                "from":{"type":"string","format":"date"}, "to":{"type":"string","format":"date"},
                "limit":{"type":"integer","minimum":1,"maximum":500}
            }),
        ),
        tool(
            "team_record",
            "Calculate a team's win/loss/draw record and goals",
            json!({"team":{"type":"string"}, "season":{"type":"integer"}, "competition":{"type":"string"}, "venue":{"type":"string","enum":["home","away"]}}),
        ),
        tool(
            "head_to_head",
            "Compare two teams' head-to-head results",
            json!({"team_a":{"type":"string"}, "team_b":{"type":"string"}, "season":{"type":"integer"}}),
        ),
        tool(
            "search_players",
            "Search FIFA players by name, nationality, club, or position",
            json!({"name":{"type":"string"}, "nationality":{"type":"string"}, "club":{"type":"string"}, "position":{"type":"string"}, "limit":{"type":"integer","minimum":1,"maximum":500}}),
        ),
        tool(
            "standings",
            "Calculate league standings from results",
            json!({"season":{"type":"integer"}, "competition":{"type":"string"}}),
        ),
        tool(
            "statistics",
            "Calculate goals-per-match and biggest win",
            json!({"competition":{"type":"string"}, "season":{"type":"integer"}}),
        ),
    ]
}
fn tool(name: &str, description: &str, properties: Value) -> Value {
    json!({"name":name,"description":description,"inputSchema":{"type":"object","properties":properties}})
}
fn s<'a>(a: &'a Value, k: &str) -> Option<&'a str> {
    a.get(k).and_then(Value::as_str)
}
fn n(a: &Value, k: &str) -> Option<i32> {
    a.get(k).and_then(Value::as_i64).map(|v| v as i32)
}
fn limit(a: &Value) -> usize {
    a.get("limit")
        .and_then(Value::as_u64)
        .unwrap_or(50)
        .min(500) as usize
}
fn call(db: &Database, p: &Value) -> Value {
    let a = &p["arguments"];
    let v = match p["name"].as_str() {
        Some("search_matches") => json!(db.find_matches(
            s(a, "team"),
            s(a, "opponent"),
            s(a, "competition"),
            n(a, "season"),
            s(a, "from"),
            s(a, "to"),
            limit(a)
        )),
        Some("team_record") => json!(db.team_record(
            s(a, "team").unwrap_or(""),
            n(a, "season"),
            s(a, "competition"),
            s(a, "venue")
        )),
        Some("head_to_head") => db.head_to_head(
            s(a, "team_a").unwrap_or(""),
            s(a, "team_b").unwrap_or(""),
            n(a, "season"),
        ),
        Some("search_players") => json!(db.search_players(
            s(a, "name"),
            s(a, "nationality"),
            s(a, "club"),
            s(a, "position"),
            limit(a)
        )),
        Some("standings") => db.standings(
            n(a, "season").unwrap_or(0),
            s(a, "competition").unwrap_or("Brasileirão"),
        ),
        Some("statistics") => db.statistics(s(a, "competition"), n(a, "season")),
        _ => return json!({"content":[{"type":"text","text":"Unknown tool"}],"isError":true}),
    };
    json!({"content":[{"type":"text","text":serde_json::to_string_pretty(&v).unwrap()}],"structuredContent":v})
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn declares_six_tools() {
        assert_eq!(tools().len(), 6)
    }
    #[test]
    fn initializes_protocol() {
        let r = handle(&Database::default(), &json!({"id":1,"method":"initialize"})).unwrap();
        assert_eq!(r["result"]["serverInfo"]["name"], "brazilian-soccer-mcp");
    }
}
