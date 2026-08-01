use anyhow::Result;
use brazilian_soccer_mcp::{format_match, Database};
use chrono::NaiveDate;
use serde_json::{json, Value};
use std::io::{self, BufRead, Write};

fn arg<'a>(v: &'a Value, k: &str) -> Option<&'a str> {
    v.get(k).and_then(Value::as_str).filter(|s| !s.is_empty())
}
fn limit(v: &Value) -> usize {
    v.get("limit")
        .and_then(Value::as_u64)
        .unwrap_or(50)
        .min(500) as usize
}
fn result(db: &Database, name: &str, a: &Value) -> Result<Value> {
    Ok(match name {
        "search_matches" => json!(db.matches(
            arg(a, "team"),
            arg(a, "opponent"),
            arg(a, "competition"),
            a.get("season").and_then(Value::as_i64).map(|x| x as i32),
            arg(a, "date_from").and_then(|x| NaiveDate::parse_from_str(x, "%Y-%m-%d").ok()),
            arg(a, "date_to").and_then(|x| NaiveDate::parse_from_str(x, "%Y-%m-%d").ok()),
            limit(a)
        )),
        "team_statistics" => {
            let t = arg(a, "team").ok_or_else(|| anyhow::anyhow!("team is required"))?;
            let r = db.team_record(
                t,
                a.get("season").and_then(Value::as_i64).map(|x| x as i32),
                arg(a, "competition"),
                arg(a, "venue") == Some("home"),
            );
            json!({"team":t,"record":r,"points":r.points(),"win_rate":r.win_rate()})
        }
        "head_to_head" => {
            let ateam = arg(a, "team_a").ok_or_else(|| anyhow::anyhow!("team_a is required"))?;
            let bteam = arg(a, "team_b").ok_or_else(|| anyhow::anyhow!("team_b is required"))?;
            let (x, y) = db.head_to_head(
                ateam,
                bteam,
                a.get("season").and_then(Value::as_i64).map(|x| x as i32),
                arg(a, "competition"),
            );
            json!({"team_a":ateam,"record_a":x,"team_b":bteam,"record_b":y,"matches":db.matches(Some(ateam),Some(bteam),None,None,None,None,limit(a))})
        }
        "search_players" => json!(db.players(
            arg(a, "name"),
            arg(a, "nationality"),
            arg(a, "club"),
            arg(a, "position"),
            limit(a)
        )),
        "standings" => json!(db.standings(
            a.get("season")
                .and_then(Value::as_i64)
                .ok_or_else(|| anyhow::anyhow!("season is required"))? as i32,
            arg(a, "competition")
        )),
        "competition_statistics" => {
            let ms = db.matches(
                None,
                None,
                arg(a, "competition"),
                a.get("season").and_then(Value::as_i64).map(|x| x as i32),
                None,
                None,
                usize::MAX,
            );
            let n = ms.len();
            let total: i32 = ms.iter().map(|m| m.home_goals + m.away_goals).sum();
            json!({"matches":n,"goals":total,"goals_per_match":if n==0{0.0}else{total as f64/n as f64},"home_wins":ms.iter().filter(|m|m.home_goals>m.away_goals).count(),"draws":ms.iter().filter(|m|m.home_goals==m.away_goals).count()})
        }
        "ask" => {
            let q = arg(a, "question").unwrap_or("");
            let lower = q.to_lowercase();
            let team = [
                "flamengo",
                "palmeiras",
                "corinthians",
                "santos",
                "fluminense",
                "são paulo",
                "sao paulo",
                "grêmio",
                "gremio",
                "vasco",
                "botafogo",
                "cruzeiro",
                "atlético mineiro",
            ]
            .into_iter()
            .find(|t| lower.contains(t));
            if lower.contains("player") || lower.contains("jogador") {
                json!({"answer":db.players(team,None,team,None,10)})
            } else {
                let ms = db.matches(team, None, None, None, None, None, 10);
                json!({"answer":ms.iter().map(format_match).collect::<Vec<_>>()})
            }
        }
        _ => return Err(anyhow::anyhow!("unknown tool: {name}")),
    })
}
fn tools() -> Value {
    json!([{"name":"search_matches","description":"Find matches across all supplied CSV files. Team-name accents and state suffixes are normalized.","inputSchema":{"type":"object","properties":{"team":{"type":"string"},"opponent":{"type":"string"},"competition":{"type":"string"},"season":{"type":"integer"},"date_from":{"type":"string"},"date_to":{"type":"string"},"limit":{"type":"integer"}}}}, {"name":"team_statistics","description":"Calculate a team's wins, draws, losses and goals.","inputSchema":{"type":"object","properties":{"team":{"type":"string"},"season":{"type":"integer"},"competition":{"type":"string"},"venue":{"enum":["home","all"]}}}}, {"name":"head_to_head","description":"Compare two teams and return their meetings.","inputSchema":{"type":"object","properties":{"team_a":{"type":"string"},"team_b":{"type":"string"},"season":{"type":"integer"},"competition":{"type":"string"}}}}, {"name":"search_players","description":"Search FIFA players by name, nationality, club, or position, ordered by rating.","inputSchema":{"type":"object","properties":{"name":{"type":"string"},"nationality":{"type":"string"},"club":{"type":"string"},"position":{"type":"string"},"limit":{"type":"integer"}}}}, {"name":"standings","description":"Calculate standings from match results.","inputSchema":{"type":"object","properties":{"season":{"type":"integer"},"competition":{"type":"string"}}}}, {"name":"competition_statistics","description":"Aggregate goals and result rates.","inputSchema":{"type":"object","properties":{"season":{"type":"integer"},"competition":{"type":"string"}}}}, {"name":"ask","description":"Lightweight natural language entry point for common player and match lookups.","inputSchema":{"type":"object","properties":{"question":{"type":"string"}}}}])
}
fn main() -> Result<()> {
    let data = std::env::var("SOCCER_DATA_DIR").unwrap_or_else(|_| "data/kaggle".into());
    let db = Database::load_from_dir(data)?;
    let stdin = io::stdin();
    let mut out = io::stdout();
    for line in stdin.lock().lines() {
        let line = line?;
        if line.trim().is_empty() {
            continue;
        }
        let request: Value = match serde_json::from_str(&line) {
            Ok(x) => x,
            Err(_) => continue,
        };
        let id = request.get("id").cloned().unwrap_or(Value::Null);
        let response = match request.get("method").and_then(Value::as_str) {
            Some("initialize") => {
                json!({"jsonrpc":"2.0","id":id,"result":{"protocolVersion":"2025-03-26","capabilities":{"tools":{}},"serverInfo":{"name":"brazilian-soccer-mcp","version":"0.1.0"}}})
            }
            Some("tools/list") => json!({"jsonrpc":"2.0","id":id,"result":{"tools":tools()}}),
            Some("tools/call") => match result(
                &db,
                request
                    .pointer("/params/name")
                    .and_then(Value::as_str)
                    .unwrap_or(""),
                request.pointer("/params/arguments").unwrap_or(&Value::Null),
            ) {
                Ok(x) => {
                    json!({"jsonrpc":"2.0","id":id,"result":{"content":[{"type":"text","text":serde_json::to_string_pretty(&x)?}],"structuredContent":x}})
                }
                Err(e) => {
                    json!({"jsonrpc":"2.0","id":id,"error":{"code":-32602,"message":e.to_string()}})
                }
            },
            Some("notifications/initialized") => continue,
            _ => {
                json!({"jsonrpc":"2.0","id":id,"error":{"code":-32601,"message":"Method not found"}})
            }
        };
        writeln!(out, "{}", serde_json::to_string(&response)?)?;
        out.flush()?;
    }
    Ok(())
}
