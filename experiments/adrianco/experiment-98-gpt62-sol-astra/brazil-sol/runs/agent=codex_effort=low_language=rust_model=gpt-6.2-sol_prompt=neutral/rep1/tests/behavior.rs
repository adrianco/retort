use brazilian_soccer_mcp::Graph;
use serde_json::{Value, json};
use std::{
    io::{BufRead, BufReader, Write},
    path::Path,
    process::{Command, Stdio},
    sync::OnceLock,
    time::{Duration, Instant},
};

fn given_the_datasets_are_loaded() -> &'static Graph {
    static GRAPH: OnceLock<Graph> = OnceLock::new();
    GRAPH.get_or_init(|| {
        Graph::load(
            Path::new(env!("CARGO_MANIFEST_DIR"))
                .join("data/kaggle")
                .as_path(),
        )
        .unwrap()
    })
}

fn query(tool: &str, args: Value) -> Value {
    given_the_datasets_are_loaded().call(tool, args).unwrap()
}

fn rows<'a>(result: &'a Value, key: &str) -> &'a [Value] {
    result[key].as_array().unwrap()
}

#[test]
fn finds_fla_flu_in_both_orientations_and_returns_scores() {
    let result = query(
        "search_matches",
        json!({"team":"Flamengo-RJ","opponent":"Fluminense",
        "competition":"Série A","start_date":"01/01/2023","end_date":"2023-12-31"}),
    );
    let matches = rows(&result, "matches");
    assert_eq!(matches.len(), 2);
    assert_ne!(matches[0]["home_team"], matches[1]["home_team"]);
    for m in matches {
        assert!(m["date"].as_str().unwrap().starts_with("2023"));
        assert_eq!(m["competition"], "Brasileirão");
        assert!(m["home_goal"].is_u64() && m["away_goal"].is_u64());
    }
}

#[test]
fn most_recent_meeting_includes_a_score_and_supports_pagination() {
    let first = query(
        "search_matches",
        json!({"team":"Flamengo","opponent":"Sport Club Corinthians Paulista","limit":1}),
    );
    assert_eq!(first["next_offset"], 1);
    assert_eq!(first["matches"][0]["date"], "2023-10-08");
    assert_eq!(first["matches"][0]["home_goal"], 1);
    assert_eq!(first["matches"][0]["away_goal"], 1);
    let second = query(
        "search_matches",
        json!({"team":"Flamengo","opponent":"Corinthians-SP","limit":1,"offset":1}),
    );
    assert_eq!(first["total"], second["total"]);
    assert!(first["matches"][0]["date"].as_str() > second["matches"][0]["date"].as_str());
}

#[test]
fn supports_each_match_source_and_its_fields() {
    for (source, count, field) in [
        ("novo_campeonato_brasileiro.csv", 6886, "stadium"),
        ("Brasileirao_Matches.csv", 4180, "round"),
        ("Brazilian_Cup_Matches.csv", 1337, "round"),
        ("Libertadores_Matches.csv", 1255, "stage"),
        ("BR-Football-Dataset.csv", 10296, "extra"),
    ] {
        let result = query("search_matches", json!({"source":source,"limit":1}));
        assert_eq!(result["total"], count);
        assert_eq!(result["matches"][0]["sources"], json!([source]));
        assert!(!result["matches"][0][field].is_null());
    }
    let fifa = query("search_players", json!({"limit":0}));
    assert_eq!(fifa["total"], 18207);
    assert_eq!(
        query("dataset_info", json!({}))["sources"]
            .as_object()
            .unwrap()
            .len(),
        6
    );
}

#[test]
fn normalizes_team_names_and_counts_wins_draws_losses_and_goals() {
    let result = query(
        "team_stats",
        json!({"team":"Sociedade Esportiva Palmeiras","season":2023,"competition":"Brasileirao"}),
    );
    let record = &result["record"];
    assert_eq!(record["played"], 37);
    assert_eq!(record["wins"], 19);
    assert_eq!(record["draws"], 10);
    assert_eq!(record["losses"], 8);
    assert_eq!(record["goals_for"], 61);
    assert_eq!(record["goals_against"], 32);
    let club = query("team_stats", json!({"team":"Palmeiras-SP","limit":0}));
    assert!(club["by_competition"].get("Copa Libertadores").is_some());
    assert!(club["by_competition"].get("Copa do Brasil").is_some());
}

#[test]
fn calculates_home_away_head_to_head_and_cross_file_club_links() {
    let home = query(
        "team_stats",
        json!({"team":"Corinthians","season":2022,"competition":"Serie A","venue":"home"}),
    );
    assert_eq!(home["record"]["played"], 19);
    assert_eq!(home["by_venue"]["away"]["played"], 0);
    let away = query(
        "team_stats",
        json!({"team":"Corinthians","season":2022,"competition":"Serie A","venue":"away"}),
    );
    assert_eq!(away["record"]["played"], 19);
    let h2h = query(
        "team_stats",
        json!({"team":"Palmeiras","opponent":"Santos FC","season":2019}),
    );
    let reverse = query(
        "team_stats",
        json!({"team":"Santos","opponent":"Palmeiras","season":2019}),
    );
    assert_eq!(h2h["opponent_wins"], reverse["record"]["wins"]);
    assert_eq!(
        h2h["record"]["goals_for"],
        reverse["record"]["goals_against"]
    );
    let santos = query(
        "team_stats",
        json!({"team":"Santos Futebol Clube", "limit":1}),
    );
    assert_eq!(santos["fifa_players"]["total"], 20);
    assert_eq!(santos["fifa_players"]["players"][0]["club"], "Santos");
    assert!(!rows(&santos, "matches").is_empty());
}

#[test]
fn returns_fifa_players_by_name_country_club_and_position() {
    let neymar = query("search_players", json!({"name":"Neymar"}));
    assert_eq!(neymar["players"][0]["overall"], 92);
    assert!(neymar["players"][0]["attributes"]["Dribbling"].is_string());
    let brazil = query(
        "search_players",
        json!({"nationality":"Brazilian","limit":3}),
    );
    assert_eq!(brazil["players"][0]["name"], "Neymar Jr");
    assert!(
        rows(&brazil, "players")
            .iter()
            .all(|p| p["nationality"] == "Brazil")
    );
    let forwards = query(
        "search_players",
        json!({"club":"Santos FC","position":"forward"}),
    );
    assert!(!rows(&forwards, "players").is_empty());
    assert!(
        rows(&forwards, "players")
            .iter()
            .all(|p| p["club"] == "Santos")
    );
    assert_eq!(
        query("search_players", json!({"club":"Flamengo"}))["total"],
        0
    );
    assert_eq!(
        query("search_players", json!({"name":"Gabriel Barbosa"}))["total"],
        0
    );
}

#[test]
fn calculates_standings_relegation_and_reports_incomplete_seasons() {
    let league = |season| {
        query(
            "standings",
            json!({"competition":"Brasileirão","season":season}),
        )
    };
    let table = league(2019);
    assert_eq!(table["champion"], "Flamengo");
    assert_eq!(table["matches_played"], 380);
    assert_eq!(table["standings"][0]["points"], 90);
    assert_eq!(table["top_scorers_available"], false);
    assert_eq!(
        league(2020)["relegated"],
        json!(["Vasco", "Goiás", "Coritiba", "Botafogo-RJ"])
    );
    let incomplete = league(2023);
    assert_eq!(incomplete["matches_played"], 377);
    assert!(incomplete["champion"].is_null());
    assert_eq!(incomplete["complete_double_round_robin"], false);
}

#[test]
fn finds_cup_finals_bracket_and_traditional_derbies() {
    let finals = query(
        "search_matches",
        json!({"competition":"Copa do Brasil","stage":"finals","limit":100}),
    );
    assert_eq!(finals["total"], 24);
    assert!(
        rows(&finals, "matches")
            .iter()
            .all(|m| m["stage"] == "final")
    );
    let bracket = query(
        "cup_bracket",
        json!({"competition":"Libertadores","season":2018}),
    );
    let rounds = rows(&bracket, "rounds");
    assert_eq!(rounds.len(), 4);
    assert_eq!(rounds[0]["stage"], "round of 16");
    assert_eq!(rounds[3]["stage"], "final");
    assert_eq!(rows(&rounds[3], "matches").len(), 2);
    let derbies = query(
        "search_matches",
        json!({"team":"Flamengo","derbies":true,"season":2023}),
    );
    assert!(
        rows(&derbies, "matches")
            .iter()
            .any(|m| m["home_team"] == "Fluminense" || m["away_team"] == "Fluminense")
    );
    assert!(
        rows(&derbies, "matches")
            .iter()
            .all(|m| ![&m["home_team"], &m["away_team"]].contains(&&json!("Palmeiras")))
    );
}

#[test]
fn aggregates_goals_rankings_season_trends_and_biggest_wins_within_budget() {
    given_the_datasets_are_loaded();
    let start = Instant::now();
    let results = query(
        "analyze_matches",
        json!({"competition":"Serie A","seasons":[2018,2019],"venue":"away","min_matches":15}),
    );
    assert!(start.elapsed() < Duration::from_secs(5));
    assert_eq!(results["matches_played"], 760);
    assert_eq!(results["by_season"][0]["season"], 2018);
    assert_eq!(results["by_season"][1]["matches_played"], 380);
    assert!(results["average_goals"].as_f64().unwrap() > 2.0);
    let best_home = query(
        "analyze_matches",
        json!({"competition":"Serie A","season":2019,"venue":"home","limit":1}),
    );
    assert_eq!(best_home["team_rankings"][0]["team"], "Flamengo");
    let scoring = query(
        "analyze_matches",
        json!({"competition":"Serie A","season":2023,"rank_by":"goals","limit":1}),
    );
    assert_eq!(scoring["team_rankings"][0]["goals_for"], 63);
    let start = Instant::now();
    let wins = query("search_matches", json!({"order":"biggest_win","limit":10}));
    assert!(start.elapsed() < Duration::from_secs(2));
    let margin = |m: &Value| {
        m["home_goal"]
            .as_u64()
            .unwrap()
            .abs_diff(m["away_goal"].as_u64().unwrap())
    };
    assert!(
        rows(&wins, "matches")
            .windows(2)
            .all(|w| margin(&w[0]) >= margin(&w[1]))
    );
}

#[test]
fn handles_mcp_stdio_handshake_discovery_results_notifications_and_errors() {
    let mut child = Command::new(env!("CARGO_BIN_EXE_brazilian-soccer-mcp"))
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .spawn()
        .unwrap();
    let mut input = child.stdin.take().unwrap();
    let output = BufReader::new(child.stdout.take().unwrap());
    let request = |id: u32, method: &str, params: Value| json!({"jsonrpc":"2.0","id":id,"method":method,"params":params});
    writeln!(input, "{{").unwrap();
    for message in [
        request(
            1,
            "initialize",
            json!({"protocolVersion":"2025-11-25","clientInfo":{"name":"test","version":"1"},"capabilities":{}}),
        ),
        json!({"jsonrpc":"2.0","method":"notifications/initialized"}),
        request(2, "tools/list", json!({})),
        request(3, "ping", json!({})),
        request(
            4,
            "tools/call",
            json!({"name":"search_matches","arguments":{"team":"Grêmio","limit":1}}),
        ),
        request(
            5,
            "tools/call",
            json!({"name":"search_matches","arguments":{"start_date":"2023-02-29"}}),
        ),
        request(6, "tools/call", json!({"name":"unknown"})),
    ] {
        writeln!(input, "{message}").unwrap();
    }
    drop(input);
    let replies: Vec<Value> = output
        .lines()
        .map(|line| serde_json::from_str(&line.unwrap()).unwrap())
        .collect();
    assert!(child.wait().unwrap().success());
    assert_eq!(replies.len(), 7);
    assert_eq!(replies[0]["error"]["code"], -32700);
    assert_eq!(replies[1]["result"]["protocolVersion"], "2025-11-25");
    let listed = rows(&replies[2]["result"], "tools");
    assert_eq!(listed.len(), 7);
    assert!(listed.iter().any(|t| t["name"] == "cup_bracket"));
    assert_eq!(replies[3]["result"], json!({}));
    let result = &replies[4]["result"];
    let text: Value = serde_json::from_str(result["content"][0]["text"].as_str().unwrap()).unwrap();
    assert_eq!(result["structuredContent"], text);
    assert_eq!(rows(&text, "matches").len(), 1);
    assert_eq!(replies[5]["result"]["isError"], true);
    assert_eq!(replies[6]["error"]["code"], -32602);
}
