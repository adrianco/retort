use super::*;
use std::path::Path;

#[test]
fn given_all_sources_when_an_llm_calls_the_tool_then_it_can_answer_soccer_questions() -> Result<()>
{
    let db = data::load(Path::new("data/kaggle"))?;
    secure(&db);
    let scenarios=&[
 ("How many players are in FIFA?","SELECT count(*) FROM players",json!(18207)),
 ("How many original match records are available?","SELECT count(*) FROM records",json!(23954)),
 ("How many match sources are represented?","SELECT count(DISTINCT source) FROM records",json!(5)),
 ("Who won Serie A in 2019?","SELECT team FROM standings WHERE season=2019 AND competition='Serie A' AND rank=1",json!("flamengo")),
 ("How many points did the champion earn?","SELECT points FROM standings WHERE season=2019 AND competition='Serie A' AND rank=1",json!(90)),
 ("How many games did Flamengo play?","SELECT played FROM standings WHERE team='flamengo' AND season=2019 AND competition='Serie A'",json!(38)),
 ("How many wins?","SELECT wins FROM standings WHERE team='flamengo' AND season=2019 AND competition='Serie A'",json!(28)),
 ("How many draws?","SELECT draws FROM standings WHERE team='flamengo' AND season=2019 AND competition='Serie A'",json!(6)),
 ("How many losses?","SELECT losses FROM standings WHERE team='flamengo' AND season=2019 AND competition='Serie A'",json!(4)),
 ("What was their goal difference?","SELECT goal_difference FROM standings WHERE team='flamengo' AND season=2019 AND competition='Serie A'",json!(49)),
 ("Who is the highest-rated Brazilian?","SELECT name FROM players WHERE nationality='Brazil' ORDER BY overall DESC LIMIT 1",json!("Neymar Jr")),
 ("What is Neymar's dribbling?","SELECT json_extract(attributes,'$.Dribbling') FROM players WHERE name='Neymar Jr'",json!("96")),
 ("Which position does he play?","SELECT position FROM players WHERE name='Neymar Jr'",json!("LW")),
 ("When did historical coverage start?","SELECT min(date) FROM records WHERE source='novo_campeonato_brasileiro.csv'",json!("2003-03-29")),
 ("How many 2018 Libertadores final legs?","SELECT count(*) FROM matches WHERE season=2018 AND competition='Libertadores' AND stage='final'",json!(2)),
 ("How many 2012 Brazilian Cup final legs?","SELECT count(*) FROM matches WHERE season=2012 AND competition='Copa do Brasil' AND stage='final'",json!(2)),
 ("How often did the Fla-Flu teams meet in Serie A 2019?","SELECT count(*) FROM team_results WHERE team=team_key('Flamengo-RJ') AND opponent='fluminense' AND competition='Serie A' AND season=2019",json!(2)),
 ("How many home matches for Corinthians in Serie A 2019?","SELECT count(*) FROM team_results WHERE team=team_key('Sport Club Corinthians Paulista') AND venue='home' AND competition='Serie A' AND season=2019",json!(19)),
 ("Which clubs in a 2019 Libertadores final have FIFA players?","SELECT DISTINCT club_key FROM players JOIN matches ON club_key IN(home,away) WHERE competition='Libertadores' AND season=2019 AND stage='final'",json!("river plate")),
 ("Were there derbies in 2023?","SELECT count(*)>0 FROM matches WHERE derby AND season=2023",json!(1)),
 ("What was the 2023 September 24 cup score?","SELECT home_goal||'-'||away_goal FROM matches WHERE competition='Copa do Brasil' AND date='2023-09-24'",json!("1-1")),
 ];
    for (question, sql, expected) in scenarios {
        let start = Instant::now();
        let response=rpc(&db,json!({"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"query_soccer","arguments":{"sql":sql}}})).unwrap();
        let result: Value =
            serde_json::from_str(response["result"]["content"][0]["text"].as_str().unwrap())?;
        assert_eq!(&result["rows"][0][0], expected, "{question}");
        assert!(start.elapsed() < Duration::from_secs(2), "{question}");
    }
    assert!(query(&db, "DELETE FROM matches").is_err());
    assert_eq!(query(&db, "SELECT id FROM players")?["truncated"], true);
    Ok(())
}

#[test]
fn given_a_client_when_it_connects_then_it_can_discover_the_tool() {
    let db = Connection::open_in_memory().unwrap();
    for method in ["initialize", "ping", "tools/list"] {
        let r = rpc(&db, json!({"jsonrpc":"2.0","id":"abc","method":method})).unwrap();
        assert_eq!(r["id"], "abc");
        assert!(r["result"].is_object());
        if method == "tools/list" {
            assert_eq!(r["result"]["tools"][0]["name"], "query_soccer")
        }
    }
    assert!(rpc(
        &db,
        json!({"jsonrpc":"2.0","method":"notifications/initialized"})
    )
    .is_none());
}
