mod data;
use data::Result;
use rusqlite::{
    hooks::{AuthAction, AuthContext, Authorization},
    types::ValueRef,
    Connection,
};
use serde_json::{json, Value};
use std::{
    io::{self, BufRead, Write},
    path::PathBuf,
    time::{Duration, Instant},
};

const DESCRIPTION:&str="Answer soccer questions with a single read-only SQLite SELECT. matches(id,competition,date,season,round,stage,home,away,home_goal,away_goal,derby) contains reconciled fixtures. Dates are ISO, unknown scores are NULL. Competitions: Serie A (Brasileirão), Serie B, Serie C, Copa do Brasil, Libertadores. derby=1 marks selected traditional rivalries. team_results(id,competition,season,date,team,opponent,venue,gf,ga,win,draw,loss,points) has two perspectives per completed fixture; venue is home or away. standings(competition,season,team,played,wins,draws,losses,goals_for,goals_against,goal_difference,points,rank) ranks observed results; filter competition and season. Cup brackets use matches.stage/round ordered by date. players(id,name,age,nationality,overall,potential,club,club_key,position,attributes) is a FIFA snapshot; use nationality='Brazil', sort overall DESC. Join club_key to team. Use team_key('São Paulo FC') to match canonical team names and fold(name) LIKE '%neymar%' for accent-insensitive searches. records(id,source,competition,date,season,round,stage,home,away,home_goal,away_goal,fixture,attributes) preserves each match CSV row and links fixture to matches.id. Use json_extract(attributes,'$.Dribbling') or similar for original player/match fields. No individual match scorer data. Explain incomplete seasons and tied ranks. Results contain columns and rows; use ORDER BY, LIMIT and OFFSET for paging.";
fn secure(db: &Connection) {
    db.authorizer(Some(|ctx: AuthContext| match ctx.action {
        AuthAction::Select | AuthAction::Read { .. } => Authorization::Allow,
        AuthAction::Function { function_name }
            if !matches!(function_name, "load_extension" | "writefile" | "readfile") =>
        {
            Authorization::Allow
        }
        _ => Authorization::Deny,
    }));
    db.set_limit(rusqlite::limits::Limit::SQLITE_LIMIT_LENGTH, 4_000_000);
}
fn query(db: &Connection, sql: &str) -> Result<Value> {
    let deadline = Instant::now() + Duration::from_secs(4);
    db.progress_handler(10000, Some(move || Instant::now() > deadline));
    let mut stmt = db.prepare(sql)?;
    if !stmt.readonly() || stmt.column_count() == 0 {
        return Err("Expected a SELECT query".into());
    }
    let cols: Vec<String> = stmt.column_names().into_iter().map(String::from).collect();
    let mut rows = stmt.query([])?;
    let mut output = Vec::new();
    let mut truncated = false;
    while let Some(r) = rows.next()? {
        if output.len() == 100 {
            truncated = true;
            break;
        }
        let mut values = Vec::new();
        for i in 0..cols.len() {
            values.push(match r.get_ref(i)? {
                ValueRef::Null => Value::Null,
                ValueRef::Integer(v) => json!(v),
                ValueRef::Real(v) => json!(v),
                ValueRef::Text(v) => json!(std::str::from_utf8(v)?),
                ValueRef::Blob(_) => return Err("Binary results are unsupported".into()),
            })
        }
        output.push(values)
    }
    Ok(json!({"columns":cols,"rows":output,"truncated":truncated}))
}
fn rpc(db: &Connection, request: Value) -> Option<Value> {
    let id = &request["id"];
    let error =
        |code, msg| Some(json!({"jsonrpc":"2.0","id":id,"error":{"code":code,"message":msg}}));
    if request["jsonrpc"] != "2.0" || !request["method"].is_string() {
        return error(-32600, "Invalid request");
    }
    request.get("id")?;
    let params = &request["params"];
    let result = match request["method"].as_str()? {
        "initialize" => {
            let version = params["protocolVersion"]
                .as_str()
                .filter(|v| ["2024-11-05", "2025-03-26", "2025-06-18", "2025-11-25"].contains(v))
                .unwrap_or("2025-06-18");
            json!({"protocolVersion":version,"capabilities":{"tools":{}},"serverInfo":{"name":"brazilian-soccer","version":env!("CARGO_PKG_VERSION")}})
        }
        "ping" => json!({}),
        "tools/list" => {
            json!({"tools":[{"name":"query_soccer","description":DESCRIPTION,"inputSchema":{"type":"object","properties":{"sql":{"type":"string"}},"required":["sql"],"additionalProperties":false}}]})
        }
        "tools/call" => {
            if params["name"] != "query_soccer" {
                return error(-32602, "Unknown tool");
            }
            let Some(sql) = params["arguments"]["sql"].as_str() else {
                return error(-32602, "Expected sql string");
            };
            let (message, failed) = match query(db, sql) {
                Ok(v) => (v.to_string(), false),
                Err(e) => (e.to_string(), true),
            };
            json!({"content":[{"type":"text","text":message}],"isError":failed})
        }
        _ => return error(-32601, "Method not found"),
    };
    Some(json!({"jsonrpc":"2.0","id":id,"result":result}))
}
fn main() -> Result<()> {
    let dir = std::env::args_os()
        .nth(1)
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("data/kaggle"));
    let db = data::load(&dir)?;
    secure(&db);
    let mut out = io::stdout().lock();
    for line in io::stdin().lock().lines() {
        let line = line?;
        let reply = match serde_json::from_str(&line) {
            Ok(v) => rpc(&db, v),
            Err(_) => Some(
                json!({"jsonrpc":"2.0","id":null,"error":{"code":-32700,"message":"Parse error"}}),
            ),
        };
        if let Some(v) = reply {
            writeln!(out, "{v}")?;
            out.flush()?
        }
    }
    Ok(())
}
#[cfg(test)]
mod tests;
