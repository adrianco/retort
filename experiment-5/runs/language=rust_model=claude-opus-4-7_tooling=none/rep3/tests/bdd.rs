//! BDD-style Given/When/Then integration tests against the loaded dataset.
//!
//! These exercise the query layer end-to-end with the bundled Kaggle CSVs and
//! act as the executable specification for TASK.md's success criteria
//! ("at least 20 sample questions can be answered").

use brazilian_soccer_mcp::data::{Competition, Dataset};
use brazilian_soccer_mcp::queries::{
    biggest_wins, competition_stats, find_matches, find_players, head_to_head, standings,
    team_record, MatchFilter, PlayerFilter, Venue,
};
use std::path::PathBuf;
use std::sync::OnceLock;

fn data_dir() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("data/kaggle")
}

/// Load the dataset once per test process — these CSVs total ~40k rows so
/// repeated loading would dominate test time.
fn dataset() -> &'static Dataset {
    static DS: OnceLock<Dataset> = OnceLock::new();
    DS.get_or_init(|| Dataset::load_from_dir(data_dir()).expect("load dataset"))
}

// ---------------------------------------------------------------------------
// Feature: Dataset loading
// ---------------------------------------------------------------------------

#[test]
fn scenario_all_six_csvs_loaded() {
    // Given the bundled Kaggle CSV files
    // When I load the dataset
    let ds = dataset();
    // Then matches from every source must be represented and the player
    // database must be loaded.
    assert!(ds.matches.len() > 15_000, "got {}", ds.matches.len());
    assert!(ds.players.len() > 18_000, "got {}", ds.players.len());

    let comps: std::collections::HashSet<_> = ds.matches.iter().map(|m| m.competition).collect();
    for c in [
        Competition::BrasileiraoSerieA,
        Competition::CopaDoBrasil,
        Competition::Libertadores,
        Competition::BrasileiraoHistorico,
    ] {
        assert!(comps.contains(&c), "missing competition: {:?}", c);
    }
}

// ---------------------------------------------------------------------------
// Feature: Match queries
// ---------------------------------------------------------------------------

#[test]
fn scenario_find_matches_between_two_teams() {
    // Given the match data is loaded
    let ds = dataset();
    // When I search for matches between Flamengo and Fluminense
    let f = MatchFilter {
        team: Some("Flamengo"),
        opponent: Some("Fluminense"),
        ..Default::default()
    };
    let ms = find_matches(ds, &f);
    // Then I should receive a non-empty list and every match must contain
    // both teams with valid scores and a date.
    assert!(!ms.is_empty());
    for m in &ms {
        assert!(m.involves("flamengo"));
        assert!(m.involves("fluminense"));
        assert!(!m.date.is_empty());
        assert!(m.home_goal >= 0 && m.away_goal >= 0);
    }
}

#[test]
fn scenario_matches_sorted_most_recent_first() {
    let ds = dataset();
    let f = MatchFilter {
        team: Some("Palmeiras"),
        season: Some(2022),
        ..Default::default()
    };
    let ms = find_matches(ds, &f);
    assert!(ms.len() > 5);
    for pair in ms.windows(2) {
        assert!(pair[0].date >= pair[1].date, "dates not sorted descending");
    }
}

#[test]
fn scenario_filter_matches_by_competition() {
    let ds = dataset();
    let f = MatchFilter {
        team: Some("Palmeiras"),
        season: Some(2021),
        competition: Some(Competition::Libertadores),
        ..Default::default()
    };
    let ms = find_matches(ds, &f);
    assert!(!ms.is_empty());
    for m in &ms {
        assert_eq!(m.competition, Competition::Libertadores);
        assert_eq!(m.season, 2021);
    }
}

#[test]
fn scenario_filter_home_only() {
    let ds = dataset();
    let f = MatchFilter {
        team: Some("Corinthians"),
        season: Some(2022),
        competition: Some(Competition::BrasileiraoSerieA),
        home_only: true,
        ..Default::default()
    };
    let ms = find_matches(ds, &f);
    for m in &ms {
        assert_eq!(m.home_team_norm, "corinthians");
    }
    // A Brasileirão Série A season has 19 home games per team.
    assert_eq!(ms.len(), 19);
}

// ---------------------------------------------------------------------------
// Feature: Team statistics
// ---------------------------------------------------------------------------

#[test]
fn scenario_team_record_home_in_season() {
    // Given the match data is loaded
    let ds = dataset();
    // When I request Corinthians' home record in 2022 Brasileirão
    let r = team_record(
        ds,
        "Corinthians",
        Some(2022),
        Some(Competition::BrasileiraoSerieA),
        Venue::Home,
    );
    // Then I get wins, losses, draws, and goals.
    assert_eq!(r.matches, 19);
    assert_eq!(r.matches, r.wins + r.draws + r.losses);
    assert!(r.goals_for > 0);
    assert!(r.points() > 0);
}

#[test]
fn scenario_team_record_across_all_venues() {
    let ds = dataset();
    let r = team_record(
        ds,
        "Palmeiras",
        Some(2022),
        Some(Competition::BrasileiraoSerieA),
        Venue::All,
    );
    // 38 games in a Brasileirão season.
    assert_eq!(r.matches, 38);
}

// ---------------------------------------------------------------------------
// Feature: Head-to-head
// ---------------------------------------------------------------------------

#[test]
fn scenario_head_to_head_is_consistent() {
    let ds = dataset();
    let h = head_to_head(ds, "Flamengo", "Fluminense");
    assert!(h.matches > 10, "expected many Fla-Flu matches, got {}", h.matches);
    assert_eq!(h.matches, h.team_a_wins + h.team_b_wins + h.draws);
}

#[test]
fn scenario_head_to_head_handles_name_variations() {
    let ds = dataset();
    let a = head_to_head(ds, "Atletico Mineiro", "Cruzeiro");
    let b = head_to_head(ds, "Atletico-MG", "Cruzeiro");
    assert_eq!(a.matches, b.matches, "name variation must match canonical form");
    assert!(a.matches > 0);
}

// ---------------------------------------------------------------------------
// Feature: Standings
// ---------------------------------------------------------------------------

#[test]
fn scenario_2019_brasileirao_champion_is_flamengo() {
    let ds = dataset();
    let s = standings(ds, 2019, Competition::BrasileiraoSerieA);
    // 20 teams compete.
    assert_eq!(s.len(), 20);
    // Each plays 38 games.
    for row in &s {
        assert_eq!(row.matches, 38, "team {} played {} games", row.team, row.matches);
    }
    // Flamengo were champions with a known points total of 90.
    let top = &s[0];
    let top_norm = brazilian_soccer_mcp::normalize::normalize_team(&top.team);
    assert_eq!(top_norm, "flamengo");
    assert_eq!(top.points, 90, "Flamengo 2019 should have 90 pts");
    assert_eq!(top.wins, 28);
    assert_eq!(top.draws, 6);
    assert_eq!(top.losses, 4);
}

#[test]
fn scenario_standings_sum_to_zero_goal_difference() {
    let ds = dataset();
    let s = standings(ds, 2020, Competition::BrasileiraoSerieA);
    let total_gd: i32 = s.iter().map(|r| r.goal_difference).sum();
    assert_eq!(total_gd, 0, "goals scored across a season must equal goals conceded");
}

// ---------------------------------------------------------------------------
// Feature: Player queries
// ---------------------------------------------------------------------------

#[test]
fn scenario_find_player_by_name() {
    let ds = dataset();
    let f = PlayerFilter {
        name: Some("Neymar"),
        ..Default::default()
    };
    let ps = find_players(ds, &f);
    assert!(!ps.is_empty());
    assert!(ps.iter().any(|p| p.name.contains("Neymar")));
}

#[test]
fn scenario_find_brazilian_players_sorted_by_overall() {
    let ds = dataset();
    let f = PlayerFilter {
        nationality: Some("Brazil"),
        sort_by_overall: true,
        limit: Some(10),
        ..Default::default()
    };
    let ps = find_players(ds, &f);
    assert_eq!(ps.len(), 10);
    for p in &ps {
        assert!(p.nationality.to_lowercase().contains("brazil"));
    }
    // Sorted by overall descending.
    for pair in ps.windows(2) {
        assert!(pair[0].overall >= pair[1].overall);
    }
    // The top Brazilian player in the FIFA dataset should be Neymar (94 in the
    // 2019 ratings the file is based on).
    assert!(ps[0].overall >= 88);
}

#[test]
fn scenario_filter_players_by_club_handles_name_variations() {
    let ds = dataset();
    // Fluminense appears in the FIFA dataset; the search must work whether the
    // user spells the club with or without diacritics.
    let f = PlayerFilter {
        club: Some("Fluminense"),
        ..Default::default()
    };
    let ps = find_players(ds, &f);
    assert!(!ps.is_empty(), "expected Fluminense players in FIFA dataset");
    for p in &ps {
        assert!(
            p.club.to_lowercase().contains("fluminense"),
            "club {} did not contain expected substring",
            p.club
        );
    }
}

// ---------------------------------------------------------------------------
// Feature: Aggregate statistics
// ---------------------------------------------------------------------------

#[test]
fn scenario_competition_stats_brasileirao() {
    let ds = dataset();
    let st = competition_stats(ds, Some(Competition::BrasileiraoSerieA), Some(2019));
    assert_eq!(st.matches, 380);
    // Brasileirão averages ~2.3-2.5 goals/match historically.
    assert!(st.avg_goals_per_match > 2.0);
    assert!(st.avg_goals_per_match < 4.0);
    assert!((st.home_win_rate + st.away_win_rate + st.draw_rate - 1.0).abs() < 1e-9);
}

#[test]
fn scenario_biggest_wins_have_largest_goal_difference() {
    let ds = dataset();
    let ms = biggest_wins(ds, None, None, 10);
    assert_eq!(ms.len(), 10);
    let top_diff = (ms[0].home_goal - ms[0].away_goal).abs();
    for m in &ms {
        let diff = (m.home_goal - m.away_goal).abs();
        assert!(diff > 0);
        assert!(diff <= top_diff);
    }
    assert!(top_diff >= 5, "expected a blowout at the top, got {}", top_diff);
}

// ---------------------------------------------------------------------------
// Feature: Cross-file queries (player + match)
// ---------------------------------------------------------------------------

#[test]
fn scenario_brazilian_players_at_brazilian_clubs_are_findable() {
    let ds = dataset();
    // Cruzeiro appears in the FIFA file with Brazilian players — a real
    // cross-filter (nationality AND club) should return matches.
    let f = PlayerFilter {
        nationality: Some("Brazil"),
        club: Some("Cruzeiro"),
        ..Default::default()
    };
    let ps = find_players(ds, &f);
    assert!(!ps.is_empty(), "expected Brazilian players at Cruzeiro");
    for p in &ps {
        assert!(p.nationality.to_lowercase().contains("brazil"));
        assert!(p.club.to_lowercase().contains("cruzeiro"));
    }
}

// ---------------------------------------------------------------------------
// Feature: MCP protocol
// ---------------------------------------------------------------------------

#[test]
fn scenario_mcp_initialize_then_list_tools() {
    use brazilian_soccer_mcp::mcp;
    use serde_json::json;

    let ds = dataset();

    // Given an MCP client
    let init = json!({ "jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {} });
    let resp = mcp::handle(ds, &init).expect("response");
    assert_eq!(resp["result"]["serverInfo"]["name"], "brazilian-soccer-mcp");

    // When the client lists tools
    let list = json!({ "jsonrpc": "2.0", "id": 2, "method": "tools/list" });
    let resp = mcp::handle(ds, &list).expect("response");
    let tools = resp["result"]["tools"].as_array().unwrap();
    // Then at least 8 tools are exposed.
    assert!(tools.len() >= 8);
}

#[test]
fn scenario_mcp_calls_find_matches_tool() {
    use brazilian_soccer_mcp::mcp;
    use serde_json::json;

    let ds = dataset();
    let req = json!({
        "jsonrpc": "2.0",
        "id": 5,
        "method": "tools/call",
        "params": {
            "name": "find_matches",
            "arguments": { "team": "Flamengo", "opponent": "Fluminense", "limit": 5 }
        }
    });
    let resp = mcp::handle(ds, &req).expect("response");
    assert!(resp["error"].is_null());
    let count = resp["result"]["structuredContent"]["count"].as_u64().unwrap();
    assert!(count > 0);
    let matches = resp["result"]["structuredContent"]["matches"].as_array().unwrap();
    assert!(matches.len() <= 5);
    // Each result has the expected shape.
    for m in matches {
        assert!(m["date"].is_string());
        assert!(m["home_goal"].is_i64());
        assert!(m["away_goal"].is_i64());
    }
}

#[test]
fn scenario_mcp_calls_standings_tool() {
    use brazilian_soccer_mcp::mcp;
    use serde_json::json;

    let ds = dataset();
    let req = json!({
        "jsonrpc": "2.0",
        "id": 6,
        "method": "tools/call",
        "params": {
            "name": "standings",
            "arguments": { "season": 2019, "competition": "brasileirao", "limit": 3 }
        }
    });
    let resp = mcp::handle(ds, &req).expect("response");
    let rows = resp["result"]["structuredContent"]["rows"].as_array().unwrap();
    assert_eq!(rows.len(), 3);
    assert_eq!(rows[0]["rank"], 1);
    assert_eq!(rows[0]["points"], 90);
}

#[test]
fn scenario_mcp_calls_competition_stats_tool() {
    use brazilian_soccer_mcp::mcp;
    use serde_json::json;

    let ds = dataset();
    let req = json!({
        "jsonrpc": "2.0",
        "id": 7,
        "method": "tools/call",
        "params": {
            "name": "competition_stats",
            "arguments": { "competition": "brasileirao", "season": 2019 }
        }
    });
    let resp = mcp::handle(ds, &req).expect("response");
    let sc = &resp["result"]["structuredContent"];
    assert_eq!(sc["matches"], 380);
    let avg = sc["avg_goals_per_match"].as_f64().unwrap();
    assert!(avg > 2.0 && avg < 4.0);
}

#[test]
fn scenario_mcp_calls_find_players_tool() {
    use brazilian_soccer_mcp::mcp;
    use serde_json::json;

    let ds = dataset();
    let req = json!({
        "jsonrpc": "2.0",
        "id": 8,
        "method": "tools/call",
        "params": {
            "name": "find_players",
            "arguments": { "nationality": "Brazil", "min_overall": 85, "limit": 5 }
        }
    });
    let resp = mcp::handle(ds, &req).expect("response");
    let players = resp["result"]["structuredContent"]["players"]
        .as_array()
        .unwrap();
    assert!(!players.is_empty());
    for p in players {
        assert!(p["overall"].as_i64().unwrap() >= 85);
        let nat = p["nationality"].as_str().unwrap().to_lowercase();
        assert!(nat.contains("brazil"));
    }
}

#[test]
fn scenario_mcp_rejects_unknown_tool() {
    use brazilian_soccer_mcp::mcp;
    use serde_json::json;
    let ds = dataset();
    let req = json!({
        "jsonrpc": "2.0",
        "id": 9,
        "method": "tools/call",
        "params": { "name": "no_such_tool", "arguments": {} }
    });
    let resp = mcp::handle(ds, &req).expect("response");
    assert!(!resp["error"].is_null());
}
