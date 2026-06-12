use std::io::{BufRead, BufReader, Write};
use std::process::{Child, ChildStdin, Command, Stdio};

struct McpTestServer {
    process: Child,
    stdin: ChildStdin,
    reader: BufReader<std::process::ChildStdout>,
}

impl McpTestServer {
    fn start() -> Self {
        let data_dir = format!(
            "{}/data/kaggle",
            env!("CARGO_MANIFEST_DIR")
        );
        let mut process = Command::new(env!("CARGO_BIN_EXE_brazilian-soccer-mcp"))
            .env("SOCCER_DATA_DIR", &data_dir)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::inherit())
            .spawn()
            .expect("Failed to start binary");
        let stdin = process.stdin.take().unwrap();
        let stdout = process.stdout.take().unwrap();
        let reader = BufReader::new(stdout);
        let mut server = McpTestServer {
            process,
            stdin,
            reader,
        };
        // MCP handshake
        server.send(serde_json::json!({
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0"}
            }
        }));
        let _init_resp = server.recv(); // read initialize response
        server.send(serde_json::json!({"jsonrpc": "2.0", "method": "notifications/initialized"}));
        server
    }

    fn send(&mut self, msg: serde_json::Value) {
        let line = msg.to_string() + "\n";
        self.stdin.write_all(line.as_bytes()).unwrap();
        self.stdin.flush().unwrap();
    }

    fn recv(&mut self) -> serde_json::Value {
        loop {
            let mut line = String::new();
            self.reader.read_line(&mut line).expect("Failed to read");
            let line = line.trim();
            if line.is_empty() {
                continue;
            }
            match serde_json::from_str(line) {
                Ok(v) => return v,
                Err(_) => continue, // skip non-JSON lines
            }
        }
    }

    fn call_tool(&mut self, id: u64, name: &str, args: serde_json::Value) -> String {
        self.send(serde_json::json!({
            "jsonrpc": "2.0", "id": id, "method": "tools/call",
            "params": {"name": name, "arguments": args}
        }));
        let resp = self.recv();
        resp["result"]["content"][0]["text"]
            .as_str()
            .unwrap_or("")
            .to_string()
    }
}

impl Drop for McpTestServer {
    fn drop(&mut self) {
        let _ = self.process.kill();
    }
}

#[test]
fn tools_list_exposes_all_required_tools() {
    let mut server = McpTestServer::start();
    server.send(serde_json::json!({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}));
    let resp = server.recv();
    let tools = resp["result"]["tools"].as_array().unwrap();
    let names: Vec<&str> = tools
        .iter()
        .map(|t| t["name"].as_str().unwrap())
        .collect();
    assert!(names.contains(&"find_matches"), "Missing find_matches");
    assert!(names.contains(&"get_team_stats"), "Missing get_team_stats");
    assert!(names.contains(&"find_players"), "Missing find_players");
    assert!(
        names.contains(&"get_head_to_head"),
        "Missing get_head_to_head"
    );
    assert!(names.contains(&"get_standings"), "Missing get_standings");
    assert!(
        names.contains(&"get_statistical_summary"),
        "Missing get_statistical_summary"
    );
}

#[test]
fn find_matches_between_flamengo_and_fluminense() {
    let mut server = McpTestServer::start();
    let text = server.call_tool(
        3,
        "find_matches",
        serde_json::json!({"team": "Flamengo", "team2": "Fluminense"}),
    );
    assert!(!text.is_empty(), "Response should not be empty");
    assert!(
        text.contains("Flamengo") || text.contains("flamengo"),
        "Should contain Flamengo: {}",
        text
    );
    assert!(
        text.contains("Fluminense") || text.contains("fluminense"),
        "Should contain Fluminense: {}",
        text
    );
}

#[test]
fn get_team_stats_returns_win_loss_draw() {
    let mut server = McpTestServer::start();
    let text = server.call_tool(
        4,
        "get_team_stats",
        serde_json::json!({"team": "Palmeiras", "competition": "brasileirao", "season": 2019}),
    );
    assert!(!text.is_empty(), "Response should not be empty");
    let lower = text.to_lowercase();
    assert!(
        lower.contains("win")
            || lower.contains("draw")
            || lower.contains("loss")
            || lower.contains("pts")
            || lower.contains("points"),
        "Should contain stats: {}",
        text
    );
}

#[test]
fn find_players_by_nationality_brazil() {
    let mut server = McpTestServer::start();
    let text = server.call_tool(
        5,
        "find_players",
        serde_json::json!({"nationality": "Brazil", "min_rating": 88}),
    );
    assert!(!text.is_empty(), "Response should not be empty");
    assert!(text.contains("Neymar"), "Should contain Neymar: {}", text);
}

#[test]
fn get_head_to_head_corinthians_palmeiras() {
    let mut server = McpTestServer::start();
    let text = server.call_tool(
        6,
        "get_head_to_head",
        serde_json::json!({"team1": "Corinthians", "team2": "Palmeiras"}),
    );
    assert!(!text.is_empty(), "Response should not be empty");
    // Should have numeric stats
    assert!(
        text.chars().any(|c| c.is_ascii_digit()),
        "Should contain numeric stats: {}",
        text
    );
}

#[test]
fn get_standings_brasileirao_2019() {
    let mut server = McpTestServer::start();
    let text = server.call_tool(
        7,
        "get_standings",
        serde_json::json!({"competition": "brasileirao", "season": 2019}),
    );
    assert!(!text.is_empty(), "Response should not be empty");
    assert!(
        text.contains("Flamengo"),
        "Flamengo should be in 2019 standings: {}",
        text
    );
    assert!(
        text.chars().any(|c| c.is_ascii_digit()),
        "Should contain point values: {}",
        text
    );
}

#[test]
fn get_statistical_summary_brasileirao() {
    let mut server = McpTestServer::start();
    let text = server.call_tool(
        8,
        "get_statistical_summary",
        serde_json::json!({"competition": "brasileirao"}),
    );
    assert!(!text.is_empty(), "Response should not be empty");
    let lower = text.to_lowercase();
    assert!(
        lower.contains("goal") || lower.contains("average") || lower.contains("match"),
        "Should contain statistics: {}",
        text
    );
}

#[test]
fn team_name_normalization() {
    let mut server = McpTestServer::start();
    let text = server.call_tool(
        9,
        "find_matches",
        serde_json::json!({"team": "Flamengo", "competition": "brasileirao", "limit": 5}),
    );
    assert!(
        !text.is_empty(),
        "Response should not be empty - Flamengo matches should be found even without -RJ suffix"
    );
    assert!(
        text.contains("Flamengo"),
        "Should contain Flamengo matches: {}",
        text
    );
}

#[test]
fn find_matches_by_season() {
    let mut server = McpTestServer::start();
    // BR-Football-Dataset has Serie A (brasileirao) through 2023
    let text = server.call_tool(
        10,
        "find_matches",
        serde_json::json!({"competition": "brasileirao", "season": 2023, "limit": 5}),
    );
    assert!(!text.is_empty(), "Response should not be empty");
    assert!(
        text.contains("2023"),
        "Should contain 2023 season matches: {}",
        text
    );
}

#[test]
fn find_players_by_club() {
    let mut server = McpTestServer::start();
    let text = server.call_tool(
        11,
        "find_players",
        serde_json::json!({"club": "Flamengo", "limit": 10}),
    );
    // FIFA dataset may or may not have Flamengo players, but response should be non-empty
    assert!(!text.is_empty(), "Response should not be empty");
}
