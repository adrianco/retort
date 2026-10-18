use brazilian_soccer_mcp::Database;
use serde_json::{json, Value};
use std::io::{self, BufRead, Write};

fn text<'a>(v: &'a Value, key: &str) -> Option<&'a str> {
    v.get(key).and_then(Value::as_str)
}
fn limit(v: &Value) -> usize {
    v.get("limit")
        .and_then(Value::as_u64)
        .unwrap_or(50)
        .min(500) as usize
}
fn schemas() -> Value {
    json!({"tools":[
     {"name":"search_matches","description":"Search every loaded match dataset by team, opponent, competition, season or date range.","inputSchema":{"type":"object","properties":{"team":{"type":"string"},"opponent":{"type":"string"},"competition":{"type":"string"},"season":{"type":"integer"},"from":{"type":"string"},"to":{"type":"string"},"limit":{"type":"integer"}}}},
     {"name":"team_statistics","description":"Calculate a team's wins, draws, losses, goals and win rate.","inputSchema":{"type":"object","properties":{"team":{"type":"string"},"season":{"type":"integer"},"competition":{"type":"string"},"venue":{"type":"string","enum":["home","away"]}},"required":["team"]}},
     {"name":"head_to_head","description":"Return matches and records for two teams.","inputSchema":{"type":"object","properties":{"team":{"type":"string"},"opponent":{"type":"string"},"season":{"type":"integer"},"limit":{"type":"integer"}},"required":["team","opponent"]}},
     {"name":"search_players","description":"Search FIFA players by name, nationality, club or position.","inputSchema":{"type":"object","properties":{"name":{"type":"string"},"nationality":{"type":"string"},"club":{"type":"string"},"position":{"type":"string"},"limit":{"type":"integer"}}}},
     {"name":"standings","description":"Calculate competition standings from results.","inputSchema":{"type":"object","properties":{"season":{"type":"integer"},"competition":{"type":"string"}},"required":["season","competition"]}}
    ]})
}
fn call(db: &Database, name: &str, a: &Value) -> Value {
    match name {
        "search_matches" => json!(db.search_matches(
            text(a, "team"),
            text(a, "opponent"),
            text(a, "competition"),
            a.get("season").and_then(Value::as_i64).map(|x| x as i32),
            text(a, "from"),
            text(a, "to"),
            limit(a)
        )),
        "team_statistics" => json!(db.team_record(
            text(a, "team").unwrap_or(""),
            a.get("season").and_then(Value::as_i64).map(|x| x as i32),
            text(a, "competition"),
            text(a, "venue")
        )),
        "head_to_head" => {
            let season = a.get("season").and_then(Value::as_i64).map(|x| x as i32);
            let (team_record, opponent_record) = db.head_to_head_records(
                text(a, "team").unwrap_or(""),
                text(a, "opponent").unwrap_or(""),
                season,
            );
            json!({"matches":db.search_matches(text(a,"team"),text(a,"opponent"),None,season,None,None,limit(a)),"team_record":team_record,"opponent_record":opponent_record})
        }
        "search_players" => json!(db.search_players(
            text(a, "name"),
            text(a, "nationality"),
            text(a, "club"),
            text(a, "position"),
            limit(a)
        )),
        "standings" => json!(db.standings(
            a.get("season").and_then(Value::as_i64).unwrap_or(0) as i32,
            text(a, "competition").unwrap_or("")
        )),
        _ => json!({"error":"unknown tool"}),
    }
}
fn main() {
    let path = std::env::var("SOCCER_DATA_DIR").unwrap_or_else(|_| "data/kaggle".into());
    let db = match Database::load(path) {
        Ok(x) => x,
        Err(e) => {
            eprintln!("failed to load datasets: {e}");
            return;
        }
    };
    for line in io::stdin().lock().lines().map_while(Result::ok) {
        let req: Value = match serde_json::from_str(&line) {
            Ok(x) => x,
            Err(_) => continue,
        };
        let id = req.get("id").cloned().unwrap_or(Value::Null);
        let params = req.get("params").cloned().unwrap_or(json!({}));
        let result = match text(&req, "method").unwrap_or("") {
            "initialize" => {
                json!({"protocolVersion":"2024-11-05","capabilities":{"tools":{}},"serverInfo":{"name":"brazilian-soccer-mcp","version":"0.1.0"}})
            }
            "tools/list" => schemas(),
            "tools/call" => {
                let value = call(
                    &db,
                    text(&params, "name").unwrap_or(""),
                    &params.get("arguments").cloned().unwrap_or(json!({})),
                );
                json!({"content":[{"type":"text","text":serde_json::to_string_pretty(&value).unwrap()}]})
            }
            _ => json!({}),
        };
        println!("{}", json!({"jsonrpc":"2.0","id":id,"result":result}));
        io::stdout().flush().ok();
    }
}
