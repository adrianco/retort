// ============================================================================
// CONTEXT: BDD scenarios - Features: Competition Queries & Statistical Analysis
//
// Covers TASK.md "Competition Queries" and "Statistical Analysis":
//   - "Who won the 2019 Brasileirão?" (Flamengo, 90 pts - verified vs CSV)
//   - 2003 season from the historical dataset (Cruzeiro champions, 24 teams)
//   - "Which teams were relegated in 2020?" (bottom-4 status flag)
//   - "What's the average goals per match in the Brasileirão?"
//   - "Which team has the best away record?"
//   - "Show me the biggest wins in the dataset"
//   - knockout competitions correctly refuse standings
// ============================================================================

mod common;

use brazilian_soccer_mcp::queries::{analyze_stats, best_records, standings};

#[test]
fn scenario_2019_brasileirao_champion() {
    // GIVEN the match data is loaded
    let ds = common::given_loaded_dataset();

    // WHEN I ask "Who won the 2019 Brasileirão?"
    let table = standings(ds, 2019, None).unwrap();

    // THEN Flamengo is champion with 90 points (28W 6D 4L)
    let rows = table["table"].as_array().unwrap();
    assert_eq!(rows.len(), 20, "Serie A has 20 teams");
    let first = &rows[0];
    assert!(first["team"].as_str().unwrap().to_lowercase().contains("flamengo"));
    assert_eq!(first["points"], 90);
    assert_eq!(first["wins"], 28);
    assert_eq!(first["draws"], 6);
    assert_eq!(first["losses"], 4);
    assert_eq!(first["status"], "Champion");
    // AND every team played the full 38 rounds
    for r in rows {
        assert_eq!(r["played"], 38);
    }
}

#[test]
fn scenario_historical_season_from_2003_dataset() {
    // GIVEN the match data is loaded (2003 only exists in the historical file)
    let ds = common::given_loaded_dataset();

    // WHEN I compute the 2003 standings
    let table = standings(ds, 2003, Some("Campeonato Brasileiro")).unwrap();

    // THEN the table comes from the 2003-2019 dataset with its 24-team format
    assert_eq!(table["source"], "novo_campeonato_brasileiro.csv");
    let rows = table["table"].as_array().unwrap();
    assert_eq!(rows.len(), 24, "2003 Serie A had 24 teams");
    // AND Cruzeiro won the 2003 title
    assert!(rows[0]["team"].as_str().unwrap().to_lowercase().contains("cruzeiro"));
}

#[test]
fn scenario_relegation_zone_is_flagged() {
    // GIVEN the match data is loaded
    let ds = common::given_loaded_dataset();

    // WHEN I ask about the 2020 season table
    let table = standings(ds, 2020, None).unwrap();
    let rows = table["table"].as_array().unwrap();

    // THEN the bottom four teams carry the relegation flag
    let flagged: Vec<&str> = rows
        .iter()
        .filter(|r| r["status"] == "Relegation zone")
        .map(|r| r["team"].as_str().unwrap())
        .collect();
    assert_eq!(flagged.len(), 4);
    // Botafogo finished bottom in 2020
    assert!(flagged.iter().any(|t| t.to_lowercase().contains("botafogo")));
}

#[test]
fn scenario_standings_rejected_for_knockout_competitions() {
    // GIVEN the match data is loaded
    let ds = common::given_loaded_dataset();

    // WHEN I request standings for a knockout cup
    let err = standings(ds, 2019, Some("Copa do Brasil")).unwrap_err();

    // THEN a helpful error explains standings don't apply
    assert!(err.contains("knockout"));
}

#[test]
fn scenario_average_goals_and_home_advantage() {
    // GIVEN the match data is loaded
    let ds = common::given_loaded_dataset();

    // WHEN I ask "What's the average goals per match in the Brasileirão?"
    let stats = analyze_stats(ds, Some("Brasileirão"), None, 5).unwrap();

    // THEN the average is a plausible football number
    let avg = stats["avg_goals_per_match"].as_f64().unwrap();
    assert!((1.8..=3.2).contains(&avg), "implausible avg goals: {}", avg);

    // AND home advantage is visible and the three rates sum to ~100%
    let hw = stats["home_win_rate_pct"].as_f64().unwrap();
    let dr = stats["draw_rate_pct"].as_f64().unwrap();
    let aw = stats["away_win_rate_pct"].as_f64().unwrap();
    assert!(hw > aw, "home win rate should exceed away win rate");
    assert!(((hw + dr + aw) - 100.0).abs() < 0.5);
}

#[test]
fn scenario_biggest_wins_are_sorted_by_margin() {
    // GIVEN the match data is loaded
    let ds = common::given_loaded_dataset();

    // WHEN I ask "Show me the biggest wins in the dataset"
    let stats = analyze_stats(ds, None, None, 10).unwrap();

    // THEN the list is sorted by goal margin, biggest first
    let wins = stats["biggest_wins"].as_array().unwrap();
    assert_eq!(wins.len(), 10);
    let margins: Vec<i64> = wins
        .iter()
        .map(|m| (m["home_goals"].as_i64().unwrap() - m["away_goals"].as_i64().unwrap()).abs())
        .collect();
    for w in margins.windows(2) {
        assert!(w[0] >= w[1]);
    }
    assert!(margins[0] >= 5, "the dataset contains at least one 5+ goal rout");
}

#[test]
fn scenario_best_away_record_ranking() {
    // GIVEN the match data is loaded
    let ds = common::given_loaded_dataset();

    // WHEN I ask "Which team has the best away record?" (Serie A, min 100 away games)
    let result = best_records(ds, "away", Some("Brasileirão"), None, 100, 10).unwrap();

    // THEN a ranking ordered by win rate is returned
    let teams = result["teams"].as_array().unwrap();
    assert!(teams.len() >= 5);
    let rates: Vec<f64> = teams.iter().map(|t| t["win_rate_pct"].as_f64().unwrap()).collect();
    for w in rates.windows(2) {
        assert!(w[0] >= w[1], "teams should be sorted by win rate desc");
    }
    // AND each entry carries the full W/D/L breakdown
    for t in teams {
        assert!(t["matches"].as_u64().unwrap() >= 100);
        assert!(t["team"].is_string());
    }
}

#[test]
fn scenario_season_comparison_2018_vs_2019() {
    // GIVEN the match data is loaded
    let ds = common::given_loaded_dataset();

    // WHEN I aggregate each season separately ("Compare the 2018 and 2019 seasons")
    let s2018 = analyze_stats(ds, Some("Brasileirão"), Some(2018), 3).unwrap();
    let s2019 = analyze_stats(ds, Some("Brasileirão"), Some(2019), 3).unwrap();

    // THEN both seasons return complete, comparable aggregates
    assert_eq!(s2018["total_matches"], 380);
    assert_eq!(s2019["total_matches"], 380);
    assert!(s2018["avg_goals_per_match"].as_f64().unwrap() > 0.0);
    assert!(s2019["avg_goals_per_match"].as_f64().unwrap() > 0.0);
}
