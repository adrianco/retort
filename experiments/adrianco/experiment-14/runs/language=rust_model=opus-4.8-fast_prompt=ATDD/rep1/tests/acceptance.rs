//! Executable acceptance specification for the Brazilian Soccer MCP server.
//!
//! Each test is an external user story phrased in the language of the problem
//! domain (find matches, get a team's record, look up a player, build the
//! league table, compute competition statistics). Every test drives the system
//! ONLY through the MCP protocol via a fresh server process — there is no
//! access to the server's internals and no shared state between scenarios.

mod common;
use common::McpClient;
use serde_json::json;

// ---------------------------------------------------------------------------
// Protocol surface
// ---------------------------------------------------------------------------

#[test]
fn server_advertises_the_expected_query_tools() {
    let mut mcp = McpClient::start();
    let tools = mcp.tool_names();
    for expected in [
        "search_matches",
        "team_record",
        "head_to_head",
        "search_players",
        "league_standings",
        "competition_stats",
        "list_competitions",
    ] {
        assert!(
            tools.contains(&expected.to_string()),
            "expected tool '{expected}' to be advertised, got {tools:?}"
        );
    }
}

// ---------------------------------------------------------------------------
// 1. Match queries
// ---------------------------------------------------------------------------

#[test]
fn find_matches_between_two_specific_teams() {
    let mut mcp = McpClient::start();
    let out = mcp.call(
        "search_matches",
        json!({ "team": "Flamengo", "opponent": "Fluminense" }),
    );

    let matches = out["matches"].as_array().expect("matches array");
    assert!(
        !matches.is_empty(),
        "expected at least one Flamengo vs Fluminense match"
    );
    // Every returned fixture must actually involve both clubs.
    for m in matches {
        let home = m["home_team"].as_str().unwrap().to_lowercase();
        let away = m["away_team"].as_str().unwrap().to_lowercase();
        let pair = format!("{home} {away}");
        assert!(
            pair.contains("flamengo") && pair.contains("fluminense"),
            "fixture did not involve both teams: {m}"
        );
    }
    // A head-to-head summary is provided when two teams are named.
    let h2h = &out["head_to_head"];
    let total = h2h["team_a_wins"].as_i64().unwrap()
        + h2h["team_b_wins"].as_i64().unwrap()
        + h2h["draws"].as_i64().unwrap();
    assert_eq!(
        total as usize,
        matches.len(),
        "head-to-head tally must account for every match"
    );
}

#[test]
fn find_matches_a_team_played_in_a_given_season() {
    let mut mcp = McpClient::start();
    let out = mcp.call(
        "search_matches",
        json!({ "team": "Palmeiras", "season": 2018, "competition": "Brasileirão" }),
    );
    let matches = out["matches"].as_array().unwrap();
    assert!(!matches.is_empty(), "Palmeiras played in 2018");
    for m in matches {
        assert_eq!(m["season"].as_i64().unwrap(), 2018);
        let pair = format!(
            "{} {}",
            m["home_team"].as_str().unwrap().to_lowercase(),
            m["away_team"].as_str().unwrap().to_lowercase()
        );
        assert!(pair.contains("palmeiras"), "fixture not for Palmeiras: {m}");
    }
}

#[test]
fn find_matches_by_competition_only() {
    let mut mcp = McpClient::start();
    let out = mcp.call(
        "search_matches",
        json!({ "competition": "Copa do Brasil", "limit": 30 }),
    );
    let matches = out["matches"].as_array().unwrap();
    assert!(!matches.is_empty());
    for m in matches {
        assert_eq!(
            m["competition"].as_str().unwrap(),
            "Copa do Brasil",
            "match was not from the requested competition"
        );
    }
}

#[test]
fn find_matches_within_a_date_range() {
    let mut mcp = McpClient::start();
    let out = mcp.call(
        "search_matches",
        json!({
            "team": "Corinthians",
            "start_date": "2019-01-01",
            "end_date": "2019-12-31"
        }),
    );
    let matches = out["matches"].as_array().unwrap();
    assert!(!matches.is_empty(), "Corinthians played during 2019");
    for m in matches {
        let date = m["date"].as_str().unwrap();
        assert!(
            ("2019-01-01"..="2019-12-31").contains(&date),
            "match {date} outside requested range"
        );
    }
}

// ---------------------------------------------------------------------------
// 2. Team queries
// ---------------------------------------------------------------------------

#[test]
fn team_record_reports_a_consistent_win_loss_draw_breakdown() {
    let mut mcp = McpClient::start();
    let out = mcp.call(
        "team_record",
        json!({ "team": "Flamengo", "season": 2019, "competition": "Brasileirão" }),
    );

    // Flamengo were the 2019 Brasileirão champions: 38 games, 28-6-4, 90 pts.
    assert_eq!(out["matches"].as_i64().unwrap(), 38);
    assert_eq!(out["wins"].as_i64().unwrap(), 28);
    assert_eq!(out["draws"].as_i64().unwrap(), 6);
    assert_eq!(out["losses"].as_i64().unwrap(), 4);
    assert_eq!(out["goals_for"].as_i64().unwrap(), 86);
    assert_eq!(out["goals_against"].as_i64().unwrap(), 37);
    assert_eq!(out["points"].as_i64().unwrap(), 90);

    // Internal consistency the domain demands.
    let w = out["wins"].as_i64().unwrap();
    let d = out["draws"].as_i64().unwrap();
    let l = out["losses"].as_i64().unwrap();
    assert_eq!(w + d + l, out["matches"].as_i64().unwrap());
    assert_eq!(w * 3 + d, out["points"].as_i64().unwrap());
}

#[test]
fn team_record_can_be_restricted_to_home_matches() {
    let mut mcp = McpClient::start();
    let all = mcp.call(
        "team_record",
        json!({ "team": "Corinthians", "season": 2019, "competition": "Brasileirão" }),
    );
    let home = mcp.call(
        "team_record",
        json!({ "team": "Corinthians", "season": 2019, "competition": "Brasileirão", "venue": "home" }),
    );
    // A home-only record is a strict subset of the full season record.
    assert!(home["matches"].as_i64().unwrap() < all["matches"].as_i64().unwrap());
    assert_eq!(home["matches"].as_i64().unwrap(), 19, "half of a 38-game season at home");
}

#[test]
fn unknown_team_record_is_reported_as_an_error() {
    let mut mcp = McpClient::start();
    let msg = mcp.call_expecting_error(
        "team_record",
        json!({ "team": "Nonexistent United FC" }),
    );
    assert!(
        msg.to_lowercase().contains("no matches"),
        "error should explain that no matches were found: {msg}"
    );
}

// ---------------------------------------------------------------------------
// 3. Head-to-head
// ---------------------------------------------------------------------------

#[test]
fn head_to_head_tally_is_internally_consistent() {
    let mut mcp = McpClient::start();
    let out = mcp.call(
        "head_to_head",
        json!({ "team_a": "Palmeiras", "team_b": "Santos" }),
    );
    let total = out["total_matches"].as_i64().unwrap();
    assert!(total > 0, "Palmeiras and Santos have met");
    let a = out["team_a_wins"].as_i64().unwrap();
    let b = out["team_b_wins"].as_i64().unwrap();
    let d = out["draws"].as_i64().unwrap();
    assert_eq!(a + b + d, total, "every meeting is a win, loss or draw");
    assert_eq!(out["matches"].as_array().unwrap().len() as i64, total);
}

// ---------------------------------------------------------------------------
// 4. Player queries
// ---------------------------------------------------------------------------

#[test]
fn look_up_a_player_by_name() {
    let mut mcp = McpClient::start();
    let out = mcp.call("search_players", json!({ "name": "Messi" }));
    let players = out["players"].as_array().unwrap();
    let messi = players
        .iter()
        .find(|p| p["name"].as_str().unwrap().contains("Messi"))
        .expect("Messi should be found");
    assert_eq!(messi["nationality"].as_str().unwrap(), "Argentina");
    assert_eq!(messi["overall"].as_i64().unwrap(), 94);
}

#[test]
fn find_brazilian_players() {
    let mut mcp = McpClient::start();
    let out = mcp.call(
        "search_players",
        json!({ "nationality": "Brazil", "limit": 500 }),
    );
    let players = out["players"].as_array().unwrap();
    assert!(
        players.len() > 100,
        "the dataset has hundreds of Brazilian players, got {}",
        players.len()
    );
    for p in players {
        assert_eq!(p["nationality"].as_str().unwrap(), "Brazil");
    }
}

#[test]
fn highest_rated_players_are_returned_in_descending_order() {
    let mut mcp = McpClient::start();
    let out = mcp.call(
        "search_players",
        json!({ "nationality": "Brazil", "sort_by": "overall", "limit": 10 }),
    );
    let players = out["players"].as_array().unwrap();
    assert_eq!(players.len(), 10);
    let mut prev = i64::MAX;
    for p in players {
        let ovr = p["overall"].as_i64().unwrap();
        assert!(ovr <= prev, "players must be sorted by descending overall");
        prev = ovr;
    }
    // The best Brazilian in this dataset is Neymar (overall 92).
    assert_eq!(players[0]["overall"].as_i64().unwrap(), 92);
}

#[test]
fn find_players_by_club_and_minimum_rating() {
    let mut mcp = McpClient::start();
    let out = mcp.call(
        "search_players",
        json!({ "club": "Real Madrid", "min_overall": 85 }),
    );
    let players = out["players"].as_array().unwrap();
    assert!(!players.is_empty());
    for p in players {
        assert!(p["club"].as_str().unwrap().contains("Real Madrid"));
        assert!(p["overall"].as_i64().unwrap() >= 85);
    }
}

// ---------------------------------------------------------------------------
// 5. Competition queries
// ---------------------------------------------------------------------------

#[test]
fn build_the_final_league_table_for_a_season() {
    let mut mcp = McpClient::start();
    let out = mcp.call(
        "league_standings",
        json!({ "competition": "Brasileirão", "season": 2019 }),
    );
    let table = out["standings"].as_array().unwrap();
    assert_eq!(table.len(), 20, "the Brasileirão is a 20-team league");

    let champion = &table[0];
    assert_eq!(champion["rank"].as_i64().unwrap(), 1);
    assert!(
        champion["team"].as_str().unwrap().contains("Flamengo"),
        "Flamengo won the 2019 Brasileirão, got {}",
        champion["team"]
    );
    assert_eq!(champion["points"].as_i64().unwrap(), 90);
    assert_eq!(champion["played"].as_i64().unwrap(), 38);

    // The table must be sorted by points (descending) and every side plays 38.
    let mut prev = i64::MAX;
    for row in table {
        let pts = row["points"].as_i64().unwrap();
        assert!(pts <= prev, "standings must be ordered by points");
        prev = pts;
        assert_eq!(row["played"].as_i64().unwrap(), 38);
    }
}

#[test]
fn list_competitions_covers_the_major_tournaments() {
    let mut mcp = McpClient::start();
    let out = mcp.call("list_competitions", json!({}));
    let names: Vec<String> = out["competitions"]
        .as_array()
        .unwrap()
        .iter()
        .map(|c| c["name"].as_str().unwrap().to_string())
        .collect();
    for expected in ["Brasileirão", "Copa do Brasil", "Copa Libertadores"] {
        assert!(
            names.iter().any(|n| n == expected),
            "expected competition '{expected}' in {names:?}"
        );
    }
}

// ---------------------------------------------------------------------------
// 6. Statistical analysis
// ---------------------------------------------------------------------------

#[test]
fn competition_statistics_are_plausible_and_well_formed() {
    let mut mcp = McpClient::start();
    let out = mcp.call(
        "competition_stats",
        json!({ "competition": "Brasileirão", "season": 2019 }),
    );

    assert_eq!(out["matches"].as_i64().unwrap(), 380, "20-team double round robin");

    let avg = out["avg_goals_per_match"].as_f64().unwrap();
    assert!(
        (1.5..4.0).contains(&avg),
        "average goals per match should be football-plausible, got {avg}"
    );

    let rate = out["home_win_rate"].as_f64().unwrap();
    assert!((0.0..=1.0).contains(&rate), "home win rate is a proportion");

    // Biggest wins, ordered by goal margin (largest first).
    let biggest = out["biggest_wins"].as_array().unwrap();
    assert!(!biggest.is_empty());
    let mut prev = i64::MAX;
    for w in biggest {
        let margin = w["margin"].as_i64().unwrap();
        assert!(margin <= prev, "biggest wins must be ordered by margin");
        assert!(margin > 0);
        prev = margin;
    }
}

// ---------------------------------------------------------------------------
// Cross-file query: players + matches together
// ---------------------------------------------------------------------------

#[test]
fn match_data_and_player_data_are_queryable_from_one_server() {
    let mut mcp = McpClient::start();

    // Match side: Brazilian clubs have fixtures in the match datasets.
    let matches = mcp.call("search_matches", json!({ "team": "Flamengo", "limit": 5 }));
    assert!(!matches["matches"].as_array().unwrap().is_empty());

    // Player side: Brazilian footballers are present in the FIFA player dataset.
    // Both knowledge bases answer within the same session, joined by nationality.
    let players = mcp.call("search_players", json!({ "nationality": "Brazil", "limit": 5 }));
    assert!(
        !players["players"].as_array().unwrap().is_empty(),
        "Brazilian players should be present in the FIFA dataset"
    );
}
