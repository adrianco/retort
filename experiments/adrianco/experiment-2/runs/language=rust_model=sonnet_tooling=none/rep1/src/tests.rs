#[cfg(test)]
mod tests {
    use crate::data::{DataStore, normalize_team_name};
    use crate::tools::{
        get_head_to_head, get_standings, get_team_stats, search_matches, search_players,
        GlobalStatsArgs, HeadToHeadArgs, SearchMatchesArgs, SearchPlayersArgs, StandingsArgs,
        TeamStatsArgs,
    };

    fn load_store() -> DataStore {
        // Try env var first, then relative path for `cargo test` run from project root
        let data_dir = std::env::var("DATA_DIR").unwrap_or_else(|_| "data/kaggle".to_string());
        DataStore::load(&data_dir).expect("Failed to load DataStore")
    }

    // -----------------------------------------------------------------------
    // Data loading
    // -----------------------------------------------------------------------

    #[test]
    fn test_data_loads() {
        let store = load_store();
        assert!(
            store.matches.len() > 1000,
            "Expected > 1000 matches, got {}",
            store.matches.len()
        );
        assert!(
            store.players.len() > 100,
            "Expected > 100 players, got {}",
            store.players.len()
        );
    }

    // -----------------------------------------------------------------------
    // search_matches
    // -----------------------------------------------------------------------

    #[test]
    fn test_search_matches_flamengo() {
        let store = load_store();
        let args = SearchMatchesArgs {
            team: Some("Flamengo".to_string()),
            opponent: None,
            competition: None,
            season: None,
            date_from: None,
            date_to: None,
            limit: 50,
        };
        let result = search_matches(&store, &args);
        assert!(
            !result.contains("No matches found"),
            "Expected Flamengo matches, got: {}",
            &result[..result.len().min(200)]
        );
        assert!(
            result.to_lowercase().contains("flamengo"),
            "Result should mention Flamengo: {}",
            &result[..result.len().min(200)]
        );
    }

    #[test]
    fn test_search_matches_by_season() {
        let store = load_store();
        let args = SearchMatchesArgs {
            team: Some("Palmeiras".to_string()),
            opponent: None,
            competition: None,
            season: Some(2019),
            date_from: None,
            date_to: None,
            limit: 50,
        };
        let result = search_matches(&store, &args);
        assert!(
            !result.contains("No matches found"),
            "Expected Palmeiras 2019 matches: {}",
            &result[..result.len().min(200)]
        );
    }

    #[test]
    fn test_search_matches_competition_filter() {
        let store = load_store();
        let args = SearchMatchesArgs {
            team: None,
            opponent: None,
            competition: Some("brasileirao".to_string()),
            season: Some(2022),
            date_from: None,
            date_to: None,
            limit: 10,
        };
        let result = search_matches(&store, &args);
        assert!(
            !result.contains("No matches found"),
            "Expected brasileirao 2022 matches: {}",
            &result[..result.len().min(200)]
        );
        assert!(
            result.contains("Brasileirao"),
            "Result should mention Brasileirao: {}",
            &result[..result.len().min(300)]
        );
    }

    // -----------------------------------------------------------------------
    // get_team_stats
    // -----------------------------------------------------------------------

    #[test]
    fn test_get_team_stats_palmeiras() {
        let store = load_store();
        let args = TeamStatsArgs {
            team: "Palmeiras".to_string(),
            competition: None,
            season: None,
        };
        let result = get_team_stats(&store, &args);
        assert!(
            result.contains("Wins:"),
            "Expected stats with Wins field: {}",
            &result[..result.len().min(400)]
        );
        assert!(
            result.contains("Losses:"),
            "Expected stats with Losses field: {}",
            &result[..result.len().min(400)]
        );
        assert!(
            result.contains("Draws:"),
            "Expected stats with Draws field: {}",
            &result[..result.len().min(400)]
        );
        // Palmeiras should have played many matches
        let played_line = result
            .lines()
            .find(|l| l.contains("Played:"))
            .expect("Should have a Played line");
        // Extract the number after "Played: "
        let played: i32 = played_line
            .split("Played:")
            .nth(1)
            .and_then(|s| s.trim().split(',').next())
            .and_then(|s| s.trim().parse().ok())
            .unwrap_or(0);
        assert!(
            played > 10,
            "Palmeiras should have played > 10 matches, got {}",
            played
        );
    }

    // -----------------------------------------------------------------------
    // search_players
    // -----------------------------------------------------------------------

    #[test]
    fn test_search_players_brazil() {
        let store = load_store();
        let args = SearchPlayersArgs {
            name: None,
            nationality: Some("Brazil".to_string()),
            club: None,
            position: None,
            min_overall: None,
            max_results: 30,
        };
        let result = search_players(&store, &args);
        assert!(
            !result.contains("No players found"),
            "Expected Brazilian players: {}",
            &result[..result.len().min(400)]
        );
        assert!(
            result.contains("Brazil"),
            "Result should mention Brazil: {}",
            &result[..result.len().min(400)]
        );
    }

    #[test]
    fn test_search_players_by_name() {
        let store = load_store();
        let args = SearchPlayersArgs {
            name: Some("Neymar".to_string()),
            nationality: None,
            club: None,
            position: None,
            min_overall: None,
            max_results: 5,
        };
        let result = search_players(&store, &args);
        assert!(
            !result.contains("No players found"),
            "Expected Neymar in FIFA data: {}",
            &result[..result.len().min(400)]
        );
    }

    #[test]
    fn test_search_players_min_overall() {
        let store = load_store();
        let args = SearchPlayersArgs {
            name: None,
            nationality: None,
            club: None,
            position: None,
            min_overall: Some(90),
            max_results: 10,
        };
        let result = search_players(&store, &args);
        assert!(
            !result.contains("No players found"),
            "Expected players with overall >= 90"
        );
        // All returned players should have overall >= 90
        // (check at least one line has a high overall)
        assert!(
            result.contains("Overall: 9"),
            "Expected high overall ratings: {}",
            &result[..result.len().min(500)]
        );
    }

    // -----------------------------------------------------------------------
    // get_standings
    // -----------------------------------------------------------------------

    #[test]
    fn test_get_standings_2019() {
        let store = load_store();
        let args = StandingsArgs {
            season: 2019,
            competition: Some("brasileirao".to_string()),
        };
        let result = get_standings(&store, &args);
        assert!(
            result.contains("2019"),
            "Result should mention 2019: {}",
            &result[..result.len().min(400)]
        );
        // Flamengo won 2019 Brasileirao – should appear in standings
        assert!(
            result.contains("Flamengo"),
            "Flamengo should be in standings: {}",
            &result[..result.len().min(600)]
        );
        // Flamengo should have 90 points (28W 6D 4L) in 2019
        // Find the Flamengo row and verify it has a high point total
        let flamengo_line = result
            .lines()
            .find(|l| l.contains("Flamengo"))
            .expect("Flamengo should have a standings row");
        // The points column (last column) should be >= 88 (Flamengo won with 90 pts)
        let pts: i32 = flamengo_line
            .split_whitespace()
            .last()
            .and_then(|s| s.parse().ok())
            .unwrap_or(0);
        assert!(
            pts >= 88,
            "Flamengo should have >= 88 pts in 2019 standings, got {}: {}",
            pts,
            flamengo_line
        );
    }

    #[test]
    fn test_get_standings_requires_season() {
        let store = load_store();
        let args = StandingsArgs {
            season: 2023,
            competition: None,
        };
        let result = get_standings(&store, &args);
        assert!(
            !result.contains("No data found") || result.contains("2023"),
            "Standings result unexpected: {}",
            &result[..result.len().min(200)]
        );
    }

    // -----------------------------------------------------------------------
    // get_head_to_head
    // -----------------------------------------------------------------------

    #[test]
    fn test_head_to_head_flamengo_fluminense() {
        let store = load_store();
        let args = HeadToHeadArgs {
            team1: "Flamengo".to_string(),
            team2: "Fluminense".to_string(),
            competition: None,
            season: None,
        };
        let result = get_head_to_head(&store, &args);
        assert!(
            !result.contains("No head-to-head matches found"),
            "Expected Fla-Flu matches: {}",
            &result[..result.len().min(400)]
        );
        assert!(
            result.contains("Flamengo") && result.contains("Fluminense"),
            "Result should mention both teams: {}",
            &result[..result.len().min(400)]
        );
        assert!(
            result.contains("wins:"),
            "Result should have win summary: {}",
            &result[..result.len().min(400)]
        );
    }

    #[test]
    fn test_head_to_head_no_results() {
        let store = load_store();
        let args = HeadToHeadArgs {
            team1: "Flamengo".to_string(),
            team2: "ZZZ_NONEXISTENT_TEAM".to_string(),
            competition: None,
            season: None,
        };
        let result = get_head_to_head(&store, &args);
        assert!(
            result.contains("No head-to-head matches found"),
            "Expected no results: {}",
            &result[..result.len().min(200)]
        );
    }

    // -----------------------------------------------------------------------
    // Team name normalization
    // -----------------------------------------------------------------------

    #[test]
    fn test_normalize_team_name() {
        assert_eq!(normalize_team_name("Palmeiras-SP"), "Palmeiras");
        assert_eq!(normalize_team_name("Flamengo-RJ"), "Flamengo");
        assert_eq!(normalize_team_name("Sport-PE"), "Sport");
        assert_eq!(normalize_team_name("Corinthians"), "Corinthians");
        assert_eq!(normalize_team_name("América - MG"), "América");
        assert_eq!(normalize_team_name("  Grêmio-RS  "), "Grêmio");
        assert_eq!(normalize_team_name("São Paulo-SP"), "São Paulo");
        // Names without state should be unchanged
        assert_eq!(normalize_team_name("Vasco"), "Vasco");
        assert_eq!(normalize_team_name("Fluminense"), "Fluminense");
    }

    // -----------------------------------------------------------------------
    // get_global_stats
    // -----------------------------------------------------------------------

    #[test]
    fn test_global_stats_brasileirao() {
        let store = load_store();
        let args = GlobalStatsArgs {
            competition: Some("brasileirao".to_string()),
            season: None,
        };
        let result = crate::tools::get_global_stats(&store, &args);
        assert!(
            result.contains("Average goals"),
            "Expected average goals stat: {}",
            &result[..result.len().min(400)]
        );
        assert!(
            result.contains("Home win rate"),
            "Expected home win rate: {}",
            &result[..result.len().min(400)]
        );
    }
}
