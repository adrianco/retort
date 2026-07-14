use std::path::Path;

use brazilian_soccer_mcp::loaders;
use brazilian_soccer_mcp::player_loader;

fn data_path(name: &str) -> std::path::PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("data/kaggle").join(name)
}

#[test]
fn loads_all_match_csv_files_with_expected_row_counts() {
    let brasileirao =
        loaders::load_brasileirao_matches(&data_path("Brasileirao_Matches.csv")).unwrap();
    assert_eq!(brasileirao.len(), 4180);

    let cup = loaders::load_brazilian_cup_matches(&data_path("Brazilian_Cup_Matches.csv")).unwrap();
    assert_eq!(cup.len(), 1337);

    // One row in the raw file is an unplayed-fixture placeholder (season="NA", goals="-")
    // and is intentionally skipped by the loader; see loaders::deserialize_optional_season.
    let libertadores =
        loaders::load_libertadores_matches(&data_path("Libertadores_Matches.csv")).unwrap();
    assert_eq!(libertadores.len(), 1254);

    let br_football =
        loaders::load_br_football_dataset(&data_path("BR-Football-Dataset.csv")).unwrap();
    assert_eq!(br_football.len(), 10296);

    let novo_campeonato =
        loaders::load_novo_campeonato(&data_path("novo_campeonato_brasileiro.csv")).unwrap();
    assert_eq!(novo_campeonato.len(), 6886);
}

#[test]
fn loads_fifa_players_with_expected_row_count() {
    let players = player_loader::load_fifa_players(&data_path("fifa_data.csv")).unwrap();
    assert_eq!(players.len(), 18207);
    let brazilians = players
        .iter()
        .filter(|p| p.nationality == "Brazil")
        .count();
    assert!(brazilians > 500);
}
