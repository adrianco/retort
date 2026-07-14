use brazilian_soccer_mcp::data::{DataStore, normalize_team, normalize_date};
use brazilian_soccer_mcp::tools::Tools;
use serde_json::json;
use std::path::PathBuf;

fn get_data_dir() -> PathBuf {
    PathBuf::from("/tmp/retort-local-3kfsv5xb/retort-73fa38125972/data/kaggle")
}

fn load_store() -> DataStore {
    DataStore::load(&get_data_dir()).expect("Failed to load DataStore")
}

#[test]
fn test_load_datastore() {
    let store = load_store();
    assert!(!store.matches.is_empty(), "Should have matches loaded");
    assert!(!store.players.is_empty(), "Should have players loaded");
}

#[test]
fn test_search_matches_flamengo() {
    let store = load_store();
    let tools = Tools::new(&store);
    let args = json!({"team1": "Flamengo", "limit": 10});
    let result = tools.search_matches(&args);
    assert!(
        result.contains("Flamengo") || result.contains("flamengo"),
        "Should find Flamengo matches, got: {}",
        &result[..result.len().min(200)]
    );
    assert!(!result.starts_with("Error:"), "Should not return error");
}

#[test]
fn test_head_to_head_flamengo_fluminense() {
    let store = load_store();
    let tools = Tools::new(&store);
    let args = json!({"team1": "Flamengo", "team2": "Fluminense"});
    let result = tools.head_to_head(&args);
    assert!(
        result.contains("Flamengo") || result.contains("flamengo"),
        "Should contain Flamengo, got: {}",
        &result[..result.len().min(300)]
    );
    assert!(!result.starts_with("Error:"), "Should not return error");
}

#[test]
fn test_search_players_brazil() {
    let store = load_store();
    let tools = Tools::new(&store);
    let args = json!({"nationality": "Brazil", "limit": 10});
    let result = tools.search_players(&args);
    assert!(
        result.contains("Brazil"),
        "Should find Brazilian players, got: {}",
        &result[..result.len().min(300)]
    );
    assert!(!result.starts_with("Error:"), "Should not return error");
}

#[test]
fn test_get_standings_2019() {
    let store = load_store();
    let tools = Tools::new(&store);
    let args = json!({"season": 2019});
    let result = tools.get_standings(&args);
    assert!(!result.starts_with("Error:"), "Should not return error");
    assert!(
        result.contains("2019"),
        "Should contain 2019 season info, got: {}",
        &result[..result.len().min(300)]
    );
}

#[test]
fn test_get_team_stats_palmeiras_2023() {
    let store = load_store();
    let tools = Tools::new(&store);
    let args = json!({"team": "Palmeiras", "season": 2023});
    let result = tools.get_team_stats(&args);
    assert!(!result.starts_with("Error:"), "Should not return error");
    assert!(
        result.contains("Palmeiras") || result.contains("palmeiras"),
        "Should contain team stats, got: {}",
        &result[..result.len().min(300)]
    );
}

#[test]
fn test_normalize_team_palmeiras_sp() {
    assert_eq!(normalize_team("Palmeiras-SP"), "palmeiras");
}

#[test]
fn test_normalize_team_flamengo_rj() {
    assert_eq!(normalize_team("Flamengo-RJ"), "flamengo");
}

#[test]
fn test_normalize_date() {
    assert_eq!(normalize_date("29/03/2003"), "2003-03-29");
}
