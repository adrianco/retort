//! ============================================================================
//! Integration tests
//!
//! Context
//! -------
//! Exercises the full stack — CSV loading, the query engine, and the MCP
//! JSON-RPC protocol — against the real datasets in `data/kaggle`. These tests
//! double as the executable proof that the success criteria in the spec are met:
//! every CSV is loadable, the documented sample questions return sensible
//! answers, and known historical facts (e.g. the 2019 Brasileirão champion) come
//! out correctly from the calculated standings.
//!
//! If the dataset directory is absent the data-dependent tests skip gracefully,
//! so the suite still builds and the pure-logic tests still run anywhere.
//! ============================================================================

use std::path::Path;
use std::sync::OnceLock;

use brazilian_soccer_mcp::db::{MatchFilter, PlayerFilter};
use brazilian_soccer_mcp::{Database, Server};
use serde_json::json;

fn data_dir() -> &'static Path {
    Path::new("data/kaggle")
}

fn have_data() -> bool {
    data_dir().join("Brasileirao_Matches.csv").exists()
}

/// Load the database once and share it across all tests.
fn db() -> &'static Database {
    static DB: OnceLock<Database> = OnceLock::new();
    DB.get_or_init(|| Database::load_from_dir(data_dir()))
}

fn server() -> &'static Server {
    static SRV: OnceLock<Server> = OnceLock::new();
    // Build a fresh Database for the server (Server owns its Database).
    SRV.get_or_init(|| Server::new(Database::load_from_dir(data_dir())))
}

// ---------------------------------------------------------------------------
// Data coverage
// ---------------------------------------------------------------------------

#[test]
fn all_six_files_load() {
    if !have_data() {
        eprintln!("skipping: data/kaggle not present");
        return;
    }
    let report = db().report();
    assert!(report.files_missing.is_empty(), "missing files: {:?}", report.files_missing);
    // 5 match files + fifa = 6 datasets.
    assert_eq!(report.files_loaded.len(), 6);
    assert!(db().match_count() > 15_000, "matches: {}", db().match_count());
    assert!(db().player_count() > 18_000, "players: {}", db().player_count());
}

// ---------------------------------------------------------------------------
// Competition queries: standings calculated from match results
// ---------------------------------------------------------------------------

#[test]
fn flamengo_won_2019_brasileirao() {
    if !have_data() {
        return;
    }
    let rows = db().standings("Brasileirão Série A", 2019);
    assert!(!rows.is_empty());
    // The 2019 Série A had 20 teams playing 38 rounds.
    assert_eq!(rows.len(), 20, "expected 20 teams");
    let champ = &rows[0];
    assert_eq!(champ.team, "Flamengo");
    // Flamengo's historical 2019 tally: 90 points, 38 games.
    assert_eq!(champ.record.points(), 90, "Flamengo should have 90 pts");
    let games = champ.record.matches;
    assert_eq!(games, 38, "each team plays 38 games");
}

#[test]
fn standings_are_sorted_by_points() {
    if !have_data() {
        return;
    }
    let rows = db().standings("Brasileirão Série A", 2018);
    for w in rows.windows(2) {
        assert!(w[0].record.points() >= w[1].record.points());
    }
}

// ---------------------------------------------------------------------------
// Match + team queries
// ---------------------------------------------------------------------------

#[test]
fn fla_flu_derby_is_found() {
    if !have_data() {
        return;
    }
    let (fla, _) = db().resolve_team("Flamengo").unwrap();
    let (flu, _) = db().resolve_team("Fluminense").unwrap();
    let h = db().head_to_head(&fla, &flu);
    assert!(h.total > 20, "expected many Fla-Flu meetings, got {}", h.total);
    assert_eq!(h.total, h.a_wins + h.b_wins + h.draws);
}

#[test]
fn team_name_variations_resolve_to_same_club() {
    if !have_data() {
        return;
    }
    // Different spellings of São Paulo FC should resolve identically.
    let a = db().resolve_team("Sao Paulo").map(|(k, _)| k);
    let b = db().resolve_team("São Paulo-SP").map(|(k, _)| k);
    assert_eq!(a, b);
    assert!(a.is_some());
}

#[test]
fn distinct_atleticos_are_not_merged() {
    if !have_data() {
        return;
    }
    let mg = db().resolve_team("Atletico-MG").map(|(k, _)| k);
    let go = db().resolve_team("Atletico-GO").map(|(k, _)| k);
    assert!(mg.is_some() && go.is_some());
    assert_ne!(mg, go, "Atlético-MG and Atlético-GO must stay distinct");
}

#[test]
fn team_record_respects_season_and_venue() {
    if !have_data() {
        return;
    }
    let (corinthians, _) = db().resolve_team("Corinthians").unwrap();
    let filter = MatchFilter {
        team: Some(corinthians),
        season: Some(2022),
        venue: Some("home".to_string()),
        ..Default::default()
    };
    let rec = db().team_record(&filter);
    // A home season is ~19 matches; allow a small tolerance for cup/extra games.
    assert!(rec.matches >= 18 && rec.matches <= 22, "home matches: {}", rec.matches);
    assert_eq!(rec.matches, rec.wins + rec.draws + rec.losses);
}

#[test]
fn find_matches_filters_by_competition_and_season() {
    if !have_data() {
        return;
    }
    let (palmeiras, _) = db().resolve_team("Palmeiras").unwrap();
    let filter = MatchFilter {
        team: Some(palmeiras),
        season: Some(2018),
        competition: Some("Brasileirão".to_string()),
        ..Default::default()
    };
    let matches = db().find_matches(&filter);
    assert!(!matches.is_empty());
    assert!(matches.iter().all(|m| m.season == 2018));
    assert!(matches.iter().all(|m| m.competition.contains("Brasileirão")));
    // Returned newest-first.
    for w in matches.windows(2) {
        assert!(w[0].date >= w[1].date);
    }
}

// ---------------------------------------------------------------------------
// Player queries
// ---------------------------------------------------------------------------

#[test]
fn brazilian_players_are_searchable_and_sorted() {
    if !have_data() {
        return;
    }
    let players = db().search_players(&PlayerFilter {
        nationality: Some("Brazil".to_string()),
        ..Default::default()
    });
    assert!(players.len() > 500, "found {} Brazilians", players.len());
    // Sorted by overall descending; Neymar tops the FIFA Brazilian list.
    assert_eq!(players[0].name, "Neymar Jr");
    for w in players.windows(2) {
        assert!(w[0].overall.unwrap_or(0) >= w[1].overall.unwrap_or(0));
    }
}

#[test]
fn player_search_by_name_is_accent_insensitive() {
    if !have_data() {
        return;
    }
    // Searching without accents should still match accented names.
    let players = db().search_players(&PlayerFilter {
        name: Some("coutinho".to_string()),
        ..Default::default()
    });
    assert!(players.iter().any(|p| p.name_key.contains("coutinho")));
}

#[test]
fn players_filter_by_position_and_rating() {
    if !have_data() {
        return;
    }
    let players = db().search_players(&PlayerFilter {
        nationality: Some("Brazil".to_string()),
        position: Some("GK".to_string()),
        min_overall: Some(85),
        ..Default::default()
    });
    assert!(!players.is_empty());
    assert!(players.iter().all(|p| p.position == "GK"));
    assert!(players.iter().all(|p| p.overall.unwrap_or(0) >= 85));
}

// ---------------------------------------------------------------------------
// Statistical analysis
// ---------------------------------------------------------------------------

#[test]
fn average_goals_per_match_is_realistic() {
    if !have_data() {
        return;
    }
    let stats = db().league_stats(&MatchFilter {
        competition: Some("Brasileirão Série A".to_string()),
        ..Default::default()
    });
    assert!(stats.matches > 1000);
    // Real-world football sits roughly between 2 and 3 goals per game.
    assert!(stats.avg_goals_per_match > 2.0 && stats.avg_goals_per_match < 3.2);
    assert!(stats.home_win_rate > 40.0 && stats.home_win_rate < 60.0);
}

#[test]
fn biggest_wins_are_ordered_by_margin() {
    if !have_data() {
        return;
    }
    let matches = db().biggest_wins(&MatchFilter::default(), 5);
    assert_eq!(matches.len(), 5);
    for w in matches.windows(2) {
        assert!(w[0].margin() >= w[1].margin());
    }
    assert!(matches[0].margin() >= 5);
}

// ---------------------------------------------------------------------------
// MCP protocol layer
// ---------------------------------------------------------------------------

#[test]
fn mcp_initialize_and_list_tools() {
    if !have_data() {
        return;
    }
    let init = server().handle(&json!({
        "jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}
    }));
    let init = init.expect("initialize returns a response");
    assert_eq!(init["result"]["protocolVersion"], "2024-11-05");

    let list = server()
        .handle(&json!({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}))
        .unwrap();
    let tools = list["result"]["tools"].as_array().unwrap();
    assert_eq!(tools.len(), 9);
    let names: Vec<&str> = tools.iter().map(|t| t["name"].as_str().unwrap()).collect();
    for expected in ["find_matches", "standings", "search_players", "head_to_head"] {
        assert!(names.contains(&expected), "missing tool {}", expected);
    }
}

#[test]
fn mcp_notifications_get_no_response() {
    let resp = server().handle(&json!({
        "jsonrpc": "2.0", "method": "notifications/initialized"
    }));
    assert!(resp.is_none(), "notifications must not produce a response");
}

#[test]
fn mcp_tool_call_returns_text_content() {
    if !have_data() {
        return;
    }
    let resp = server()
        .handle(&json!({
            "jsonrpc": "2.0", "id": 7, "method": "tools/call",
            "params": { "name": "standings", "arguments": { "season": 2019, "limit": 1 } }
        }))
        .unwrap();
    let text = resp["result"]["content"][0]["text"].as_str().unwrap();
    assert!(text.contains("Flamengo"), "standings text: {}", text);
    assert!(text.contains("90 pts"));
}

#[test]
fn mcp_unknown_method_is_an_error() {
    let resp = server()
        .handle(&json!({"jsonrpc": "2.0", "id": 9, "method": "does/not/exist"}))
        .unwrap();
    assert_eq!(resp["error"]["code"], -32601);
}

#[test]
fn mcp_unknown_tool_reports_error_content() {
    let resp = server()
        .handle(&json!({
            "jsonrpc": "2.0", "id": 10, "method": "tools/call",
            "params": { "name": "no_such_tool", "arguments": {} }
        }))
        .unwrap();
    assert_eq!(resp["result"]["isError"], true);
}
