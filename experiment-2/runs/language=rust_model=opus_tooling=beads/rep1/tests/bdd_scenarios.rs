// BDD-style scenarios for the Brazilian Soccer MCP server.
// These are written as "Given/When/Then" inside plain Rust tests to keep
// dependencies light. Each test maps to a Gherkin scenario in the spec.

use brazilian_soccer_mcp::data::{Competition, Dataset};
use brazilian_soccer_mcp::mcp::Server;
use brazilian_soccer_mcp::query::{
    aggregate_stats, find_matches, find_players, head_to_head, standings, team_stats,
    MatchFilter, PlayerFilter,
};
use serde_json::json;

fn given_dataset() -> Dataset {
    Dataset::load_default("data/kaggle").expect("dataset loads")
}

// Feature: Match Queries
// Scenario: Find matches between two teams
#[test]
fn scenario_matches_between_two_teams() {
    let ds = given_dataset();
    let ms = find_matches(&ds, &MatchFilter {
        team: Some("Flamengo"), opponent: Some("Fluminense"), ..Default::default()
    });
    assert!(ms.len() >= 15);
    for m in &ms {
        assert!(!m.date.is_empty());
        assert!(!m.home_team.is_empty() && !m.away_team.is_empty());
    }
}

// Feature: Team Queries
// Scenario: Get team statistics for a season
#[test]
fn scenario_team_stats_for_season() {
    let ds = given_dataset();
    let ms = find_matches(&ds, &MatchFilter {
        team: Some("Palmeiras"), season: Some(2023),
        competition: Some(Competition::Brasileirao), ..Default::default()
    });
    let s = team_stats(&ms, "Palmeiras");
    assert!(s.matches > 0);
    assert_eq!(s.matches, s.wins + s.draws + s.losses);
    assert_eq!(s.matches, s.home_matches + s.away_matches);
}

// Feature: Team Queries
// Scenario: Head-to-head record between rivals
#[test]
fn scenario_head_to_head_rivals() {
    let ds = given_dataset();
    let h = head_to_head(&ds, "Palmeiras", "Santos");
    assert!(h.matches > 0);
    assert_eq!(h.matches, h.a_wins + h.b_wins + h.draws);
}

// Feature: Player Queries
// Scenario: Top Brazilian players sorted by rating
#[test]
fn scenario_top_brazilian_players() {
    let ds = given_dataset();
    let ps = find_players(&ds, &PlayerFilter {
        nationality: Some("Brazil"), sort_by_overall_desc: true, limit: Some(10), ..Default::default()
    });
    assert_eq!(ps.len(), 10);
    for p in &ps { assert_eq!(p.nationality, "Brazil"); }
    // monotonically non-increasing overall rating
    for w in ps.windows(2) {
        assert!(w[0].overall.unwrap_or(0) >= w[1].overall.unwrap_or(0));
    }
}

// Feature: Player Queries
// Scenario: Search by name
#[test]
fn scenario_search_player_by_name() {
    let ds = given_dataset();
    let ps = find_players(&ds, &PlayerFilter {
        name_contains: Some("Neymar"), limit: Some(5), ..Default::default()
    });
    assert!(!ps.is_empty());
    assert!(ps[0].name.to_lowercase().contains("neymar"));
}

// Feature: Competition Queries
// Scenario: 2019 Brasileirão champion is Flamengo
#[test]
fn scenario_2019_brasileirao_champion() {
    let ds = given_dataset();
    let rows = standings(&ds, Competition::Brasileirao, 2019);
    assert!(rows[0].team.to_lowercase().contains("flamengo"));
    assert!(rows[0].points >= rows[1].points);
}

// Feature: Statistical Analysis
// Scenario: Average goals per match is plausible
#[test]
fn scenario_average_goals_plausible() {
    let ds = given_dataset();
    let s = aggregate_stats(&ds, &MatchFilter {
        competition: Some(Competition::Brasileirao), ..Default::default()
    });
    assert!(s.total_matches > 1000);
    assert!(s.avg_goals_per_match > 1.5 && s.avg_goals_per_match < 4.0,
            "avg={}", s.avg_goals_per_match);
    assert!(s.home_win_rate > 0.35 && s.home_win_rate < 0.65,
            "home_win_rate={}", s.home_win_rate);
}

// Feature: MCP protocol
// Scenario: initialize -> tools/list -> tools/call happy path
#[test]
fn scenario_mcp_round_trip() {
    let server = Server::new(given_dataset());

    let init = server.handle_request(&json!({
        "jsonrpc":"2.0","id":1,"method":"initialize","params":{}
    })).unwrap();
    assert_eq!(init["result"]["protocolVersion"], "2024-11-05");

    let list = server.handle_request(&json!({
        "jsonrpc":"2.0","id":2,"method":"tools/list"
    })).unwrap();
    let names: Vec<&str> = list["result"]["tools"].as_array().unwrap()
        .iter().map(|t| t["name"].as_str().unwrap()).collect();
    for expected in ["find_matches", "team_stats", "head_to_head", "standings",
                     "find_players", "biggest_wins", "aggregate_stats"] {
        assert!(names.contains(&expected), "missing tool {}", expected);
    }

    let call = server.handle_request(&json!({
        "jsonrpc":"2.0","id":3,"method":"tools/call",
        "params": {
            "name": "team_stats",
            "arguments": {"team":"Corinthians","season":2022,"competition":"brasileirao"}
        }
    })).unwrap();
    let text = call["result"]["content"][0]["text"].as_str().unwrap();
    assert!(text.contains("Corinthians"));
    assert!(text.contains("Win rate"));
}

// Feature: Data quality
// Scenario: team name variations match the same record
#[test]
fn scenario_team_name_variations_unify() {
    let ds = given_dataset();
    let a = find_matches(&ds, &MatchFilter { team: Some("Palmeiras"), season: Some(2019), ..Default::default() }).len();
    let b = find_matches(&ds, &MatchFilter { team: Some("Palmeiras-SP"), season: Some(2019), ..Default::default() }).len();
    assert_eq!(a, b);
    assert!(a > 0);

    let sp_a = find_matches(&ds, &MatchFilter { team: Some("São Paulo"), season: Some(2019), ..Default::default() }).len();
    let sp_b = find_matches(&ds, &MatchFilter { team: Some("Sao Paulo"), season: Some(2019), ..Default::default() }).len();
    assert_eq!(sp_a, sp_b);
}
