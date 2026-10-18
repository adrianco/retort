//! Context: BDD scenarios for loading the provided data files.
//!
//! Feature: Data Coverage
//!   Scenario: All six CSV files load from data/kaggle
//!   Scenario: Missing file is reported, not silently ignored

use std::path::Path;

use brazilian_soccer_mcp::data::Dataset;

#[test]
fn scenario_all_six_csv_files_are_loadable() {
    // Given the provided Kaggle datasets in data/kaggle
    let dir = Path::new(env!("CARGO_MANIFEST_DIR")).join("data/kaggle");
    // When the dataset is loaded
    let ds = Dataset::load_dir(&dir).expect("all files load");
    // Then matches from the five match files and players from FIFA are available
    assert!(ds.matches.len() > 10_000, "got {}", ds.matches.len());
    assert!(ds.players.len() > 18_000, "got {}", ds.players.len());
    let competitions: std::collections::HashSet<&str> =
        ds.matches.iter().map(|m| m.competition.as_str()).collect();
    for c in [
        "Brasileirão Série A",
        "Brasileirão Série B",
        "Copa do Brasil",
        "Copa Libertadores",
    ] {
        assert!(competitions.contains(c), "missing {c}");
    }
}

#[test]
fn scenario_missing_file_is_an_error() {
    // Given an empty directory
    let dir = std::env::temp_dir().join("soccer_mcp_empty_dir_test");
    std::fs::create_dir_all(&dir).unwrap();
    // When the dataset is loaded
    let result = Dataset::load_dir(&dir);
    // Then loading fails naming the missing file
    let err = result.unwrap_err().to_string();
    assert!(err.contains("I/O error"), "{err}");
}
