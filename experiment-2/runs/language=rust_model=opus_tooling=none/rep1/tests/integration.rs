use brazilian_soccer_mcp::data::{normalize_team, Competition, Dataset};
use brazilian_soccer_mcp::queries::Query;

fn load() -> Dataset {
    Dataset::load_from_dir("data/kaggle").expect("load dataset")
}

#[test]
fn normalizes_team_names_across_variants() {
    assert_eq!(normalize_team("Palmeiras-SP"), normalize_team("Palmeiras"));
    assert_eq!(normalize_team("Flamengo-RJ"), normalize_team("Flamengo"));
    assert_eq!(normalize_team("São Paulo"), normalize_team("Sao Paulo"));
    assert_eq!(normalize_team("Grêmio-RS"), normalize_team("Gremio"));
}

#[test]
fn dataset_loads_all_files() {
    let ds = load();
    assert!(ds.matches.len() > 20_000, "matches: {}", ds.matches.len());
    assert!(ds.players.len() > 15_000, "players: {}", ds.players.len());
}

// BDD: Scenario: Find matches between two teams
#[test]
fn bdd_find_matches_between_two_teams() {
    let ds = load();
    let q = Query::new(&ds);
    let ms = q.matches_between("Flamengo", "Fluminense");
    assert!(!ms.is_empty(), "should find Fla-Flu matches");
    for m in &ms {
        assert!(!m.date.is_empty());
    }
}

// BDD: Scenario: Get team statistics
#[test]
fn bdd_team_statistics_for_season() {
    let ds = load();
    let q = Query::new(&ds);
    let stats = q.team_stats("Palmeiras", Some(2019), false, false);
    assert!(stats.matches > 0);
    assert_eq!(stats.matches, stats.wins + stats.draws + stats.losses);
}

#[test]
fn head_to_head_totals_are_consistent() {
    let ds = load();
    let q = Query::new(&ds);
    let h = q.head_to_head("Palmeiras", "Santos");
    assert_eq!(h.total, h.a_wins + h.b_wins + h.draws);
    assert!(h.total > 0);
}

#[test]
fn standings_produce_20ish_teams_for_brasileirao() {
    let ds = load();
    let q = Query::new(&ds);
    let table = q.standings(Competition::Brasileirao, 2019);
    assert!(table.len() >= 18 && table.len() <= 22, "teams: {}", table.len());
    // Winner should be first
    assert!(table[0].points >= table[1].points);
}

#[test]
fn player_search_finds_brazilian_star() {
    let ds = load();
    let q = Query::new(&ds);
    let neymar = q.search_players("Neymar");
    assert!(!neymar.is_empty());
    assert!(neymar.iter().any(|p| p.nationality.to_lowercase().contains("brazil")));
}

#[test]
fn players_by_nationality_brazil_is_ranked() {
    let ds = load();
    let q = Query::new(&ds);
    let top = q.players_by_nationality("Brazil", 10);
    assert_eq!(top.len(), 10);
    for w in top.windows(2) {
        assert!(w[0].overall >= w[1].overall);
    }
}

#[test]
fn average_goals_and_home_win_rate_are_sensible() {
    let ds = load();
    let q = Query::new(&ds);
    let avg = q.average_goals_per_match(Some(Competition::Brasileirao));
    assert!(avg > 1.5 && avg < 4.0, "avg: {}", avg);
    let hwr = q.home_win_rate(Some(Competition::Brasileirao));
    assert!(hwr > 0.3 && hwr < 0.7, "hwr: {}", hwr);
}

#[test]
fn biggest_wins_returns_limit() {
    let ds = load();
    let q = Query::new(&ds);
    let top = q.biggest_wins(5);
    assert_eq!(top.len(), 5);
    let diff0 = (top[0].home_goal - top[0].away_goal).abs();
    let diff1 = (top[1].home_goal - top[1].away_goal).abs();
    assert!(diff0 >= diff1);
}

#[test]
fn mcp_tools_list_and_call_work() {
    use brazilian_soccer_mcp::mcp;
    use serde_json::json;
    let ds = load();
    let req = json!({"jsonrpc":"2.0","id":1,"method":"tools/list"});
    let resp = mcp::handle_request(&ds, &req);
    assert!(resp["result"]["tools"].as_array().unwrap().len() >= 10);

    let req = json!({
        "jsonrpc":"2.0","id":2,"method":"tools/call",
        "params": {"name": "team_stats", "arguments": {"team": "Corinthians", "season": 2022, "home_only": true}}
    });
    let resp = mcp::handle_request(&ds, &req);
    let text = resp["result"]["content"][0]["text"].as_str().unwrap();
    assert!(text.contains("Corinthians"));
}
