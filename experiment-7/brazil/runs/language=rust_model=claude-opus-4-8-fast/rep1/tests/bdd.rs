// =============================================================================
// Context: Brazilian Soccer MCP Server
// File:    tests/bdd.rs
// Purpose: Behaviour-Driven (Given/When/Then) integration tests that exercise
//          the full stack — real CSV loading, the query layer, the tool layer
//          and the MCP JSON-RPC handler — against the bundled datasets. The
//          scenarios mirror the capabilities and sample questions in the
//          specification (match/team/player/competition/statistical queries).
// =============================================================================

use std::sync::OnceLock;

use brazilian_soccer_mcp::data::Database;
use brazilian_soccer_mcp::mcp;
use brazilian_soccer_mcp::queries::{MatchQuery, PlayerQuery, Venue};
use serde_json::json;

/// GIVEN the bundled datasets, load them once and share across scenarios.
fn db() -> &'static Database {
    static DB: OnceLock<Database> = OnceLock::new();
    DB.get_or_init(|| {
        Database::load_from_dir("data/kaggle").expect("datasets should load")
    })
}

// ----- Feature: Data loading -------------------------------------------------

#[test]
fn scenario_all_datasets_load() {
    // GIVEN the six provided CSV files
    let db = db();
    // THEN a substantial number of matches and players are available
    assert!(db.matches.len() > 10_000, "expected many matches, got {}", db.matches.len());
    assert!(db.players.len() > 18_000, "expected ~18k players, got {}", db.players.len());
}

#[test]
fn scenario_every_competition_is_present() {
    // WHEN we inspect the loaded competitions
    let comps: std::collections::HashSet<_> =
        db().matches.iter().map(|m| m.competition.as_str()).collect();
    // THEN the three headline competitions are represented
    assert!(comps.contains("Brasileirão Série A"));
    assert!(comps.contains("Copa do Brasil"));
    assert!(comps.contains("Copa Libertadores"));
}

// ----- Feature: Match Queries ------------------------------------------------

#[test]
fn scenario_find_matches_between_two_teams() {
    // GIVEN the match data is loaded
    // WHEN I search for matches between Flamengo and Fluminense
    let q = MatchQuery {
        team: Some("Flamengo".into()),
        opponent: Some("Fluminense".into()),
        ..Default::default()
    };
    let matches = db().search_matches(&q);
    // THEN I receive a non-empty list
    assert!(!matches.is_empty(), "expected Fla-Flu derbies");
    // AND every match actually involves both clubs
    for m in matches {
        let teams = format!("{} {}", m.home_team, m.away_team).to_lowercase();
        assert!(teams.contains("flamengo"));
        assert!(teams.contains("fluminense"));
    }
}

#[test]
fn scenario_filter_matches_by_season_and_team() {
    // WHEN I ask what matches Palmeiras played in 2019
    let q = MatchQuery {
        team: Some("Palmeiras".into()),
        season: Some(2019),
        limit: Some(1000),
        ..Default::default()
    };
    let matches = db().search_matches(&q);
    // THEN results exist and are all from 2019
    assert!(!matches.is_empty());
    assert!(matches.iter().all(|m| m.season == 2019));
}

#[test]
fn scenario_matches_sorted_by_date_descending() {
    let q = MatchQuery {
        team: Some("Corinthians".into()),
        limit: Some(50),
        ..Default::default()
    };
    let matches = db().search_matches(&q);
    let dates: Vec<_> = matches.iter().filter_map(|m| m.date.clone()).collect();
    let mut sorted = dates.clone();
    sorted.sort_by(|a, b| b.cmp(a));
    assert_eq!(dates, sorted, "matches should be newest-first");
}

#[test]
fn scenario_handles_team_name_variations() {
    // GIVEN names appear with state suffixes ("Palmeiras-SP")
    // WHEN searching with the bare name
    let q = MatchQuery { team: Some("Palmeiras".into()), ..Default::default() };
    let with_suffix = db()
        .search_matches(&q)
        .iter()
        .any(|m| m.home_team.contains('-') || m.away_team.contains('-'));
    // THEN suffixed records are still matched
    assert!(with_suffix, "normalization should match 'Palmeiras-SP'");
}

// ----- Feature: Team Queries -------------------------------------------------

#[test]
fn scenario_team_statistics_for_a_season() {
    // WHEN I request Palmeiras statistics for 2019
    let rec = db().team_record("Palmeiras", Some(2019), None, Venue::All);
    // THEN I receive a coherent W/D/L record
    assert!(rec.matches > 0);
    assert_eq!(rec.matches, rec.wins + rec.draws + rec.losses);
    assert!(rec.win_rate() >= 0.0 && rec.win_rate() <= 100.0);
}

#[test]
fn scenario_home_record_only_counts_home_games() {
    let home = db().team_record("Corinthians", Some(2019), Some("Brasileirão"), Venue::Home);
    let away = db().team_record("Corinthians", Some(2019), Some("Brasileirão"), Venue::Away);
    let all = db().team_record("Corinthians", Some(2019), Some("Brasileirão"), Venue::All);
    // THEN home + away match counts reconcile with the total
    assert_eq!(home.matches + away.matches, all.matches);
}

// ----- Feature: Head-to-head -------------------------------------------------

#[test]
fn scenario_head_to_head_is_symmetric() {
    let (a, _) = db().head_to_head("Palmeiras", "Santos");
    let (b, _) = db().head_to_head("Santos", "Palmeiras");
    // THEN totals agree and wins mirror each other
    assert_eq!(a.total_matches, b.total_matches);
    assert_eq!(a.team1_wins, b.team2_wins);
    assert_eq!(a.team2_wins, b.team1_wins);
    assert_eq!(a.draws, b.draws);
    assert_eq!(a.team1_wins + a.team2_wins + a.draws, a.total_matches);
}

// ----- Feature: Player Queries -----------------------------------------------

#[test]
fn scenario_find_brazilian_players() {
    // WHEN I filter players by nationality Brazil
    let q = PlayerQuery { nationality: Some("Brazil".into()), limit: Some(10000), ..Default::default() };
    let players = db().search_players(&q);
    // THEN there are many, all Brazilian, sorted by rating descending
    assert!(players.len() > 500, "expected many Brazilians, got {}", players.len());
    assert!(players.iter().all(|p| p.nationality.eq_ignore_ascii_case("Brazil")));
    for w in players.windows(2) {
        assert!(w[0].overall >= w[1].overall);
    }
}

#[test]
fn scenario_search_player_by_name() {
    // WHEN I look up a player by (partial) name
    let q = PlayerQuery { name: Some("Neymar".into()), ..Default::default() };
    let players = db().search_players(&q);
    // THEN a matching record is returned
    assert!(players.iter().any(|p| p.name.contains("Neymar")));
}

#[test]
fn scenario_filter_players_by_min_rating() {
    let q = PlayerQuery { min_overall: Some(85), limit: Some(1000), ..Default::default() };
    let players = db().search_players(&q);
    assert!(players.iter().all(|p| p.overall >= 85));
}

// ----- Feature: Competition Queries ------------------------------------------

#[test]
fn scenario_standings_are_ranked_and_consistent() {
    // WHEN I compute the 2019 Brasileirão table
    let rows = db().standings("Brasileirão", 2019);
    // THEN it has the expected size and is correctly ordered
    assert!(rows.len() >= 18, "expected a full league, got {}", rows.len());
    for w in rows.windows(2) {
        assert!(w[0].points >= w[1].points, "table must be sorted by points");
    }
    // AND positions are 1..=n
    assert_eq!(rows[0].position, 1);
    // AND points equal 3*wins + draws
    for r in &rows {
        assert_eq!(r.points, r.record.wins * 3 + r.record.draws);
    }
}

#[test]
fn scenario_2019_brasileirao_champion_is_flamengo() {
    // Known historical fact: Flamengo won the 2019 Brasileirão with 90 points
    // from a 38-game season (28W 6D 4L). This also guards against the
    // cross-dataset double-counting that an earlier merge strategy produced.
    let rows = db().standings("Brasileirão", 2019);
    assert_eq!(rows.len(), 20, "Série A is a 20-team league");
    let champion = &rows[0];
    assert!(
        champion.team.to_lowercase().contains("flamengo"),
        "expected Flamengo as 2019 champion, got {}",
        champion.team
    );
    assert_eq!(champion.points, 90, "Flamengo finished on 90 points");
    let games = champion.record.wins + champion.record.draws + champion.record.losses;
    assert_eq!(games, 38, "each club plays 38 games — no double counting");
}

// ----- Feature: Statistical Analysis -----------------------------------------

#[test]
fn scenario_average_goals_per_match_is_reasonable() {
    let stats = db().competition_stats(Some("Brasileirão"), None);
    assert!(stats.matches > 0);
    // Football scoring sanity bounds.
    assert!(stats.avg_goals_per_match > 1.5 && stats.avg_goals_per_match < 4.0);
    assert!(stats.home_win_rate > 30.0 && stats.home_win_rate < 70.0);
}

#[test]
fn scenario_biggest_wins_are_ordered_by_margin() {
    let wins = db().biggest_wins(None, None, 10);
    assert!(!wins.is_empty());
    for w in wins.windows(2) {
        let a = (w[0].home_goal - w[0].away_goal).abs();
        let b = (w[1].home_goal - w[1].away_goal).abs();
        assert!(a >= b, "biggest wins must be sorted by margin");
    }
}

// ----- Feature: MCP protocol layer -------------------------------------------

#[test]
fn scenario_initialize_handshake() {
    let req = json!({"jsonrpc":"2.0","id":1,"method":"initialize","params":{}});
    let resp = mcp::handle_request(db(), &req).expect("response");
    assert_eq!(resp["result"]["protocolVersion"], mcp::PROTOCOL_VERSION);
    assert_eq!(resp["result"]["serverInfo"]["name"], "brazilian-soccer-mcp");
}

#[test]
fn scenario_notifications_get_no_response() {
    let note = json!({"jsonrpc":"2.0","method":"notifications/initialized"});
    assert!(mcp::handle_request(db(), &note).is_none());
}

#[test]
fn scenario_tools_list_advertises_all_tools() {
    let req = json!({"jsonrpc":"2.0","id":2,"method":"tools/list"});
    let resp = mcp::handle_request(db(), &req).expect("response");
    let names: Vec<String> = resp["result"]["tools"]
        .as_array()
        .unwrap()
        .iter()
        .map(|t| t["name"].as_str().unwrap().to_string())
        .collect();
    for expected in [
        "search_matches",
        "team_stats",
        "head_to_head",
        "search_players",
        "competition_standings",
        "competition_stats",
        "list_competitions",
    ] {
        assert!(names.contains(&expected.to_string()), "missing tool {expected}");
    }
}

#[test]
fn scenario_tools_call_search_matches_returns_text() {
    let req = json!({
        "jsonrpc":"2.0","id":3,"method":"tools/call",
        "params": {"name":"search_matches","arguments":{"team":"Flamengo","opponent":"Fluminense"}}
    });
    let resp = mcp::handle_request(db(), &req).expect("response");
    assert_eq!(resp["result"]["isError"], false);
    let text = resp["result"]["content"][0]["text"].as_str().unwrap();
    assert!(text.contains("Head-to-head"), "expected a head-to-head summary");
}

#[test]
fn scenario_tools_call_unknown_tool_is_error() {
    let req = json!({
        "jsonrpc":"2.0","id":4,"method":"tools/call",
        "params": {"name":"does_not_exist","arguments":{}}
    });
    let resp = mcp::handle_request(db(), &req).expect("response");
    assert_eq!(resp["result"]["isError"], true);
}

#[test]
fn scenario_unknown_method_returns_jsonrpc_error() {
    let req = json!({"jsonrpc":"2.0","id":5,"method":"frobnicate"});
    let resp = mcp::handle_request(db(), &req).expect("response");
    assert_eq!(resp["error"]["code"], -32601);
}
