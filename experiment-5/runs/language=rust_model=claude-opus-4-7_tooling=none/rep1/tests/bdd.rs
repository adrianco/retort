//! BDD-style integration tests (Given/When/Then) over real loaded data.
//!
//! These run the full Store::load against `data/kaggle/` and assert that
//! every required capability in TASK.md is observable in the loaded corpus.

use std::sync::OnceLock;

use brazilian_soccer_mcp::data::Competition;
use brazilian_soccer_mcp::queries::{
    biggest_wins, club_averages_by_nationality, competition_stats, head_to_head, search_matches,
    search_players, season_standings, team_stats, top_players, MatchFilter, PlayerFilter,
};
use brazilian_soccer_mcp::Store;
use serde_json::json;

fn store() -> &'static Store {
    static S: OnceLock<Store> = OnceLock::new();
    S.get_or_init(|| Store::load("data").expect("load data/kaggle"))
}

// --- Feature: Data loading ------------------------------------------------

#[test]
fn given_the_repo_data_dir_when_loading_then_all_six_csvs_are_loaded() {
    // Given the bundled data directory
    let s = store();
    // Then every match dataset contributes rows
    let mut by_comp = std::collections::HashMap::new();
    for m in &s.matches {
        *by_comp.entry(m.competition).or_insert(0u32) += 1;
    }
    // Every CSV contributes its own competition bucket.
    assert!(by_comp.contains_key(&Competition::Brasileirao), "no Brasileirão rows");
    assert!(by_comp.contains_key(&Competition::BrasileiraoHistoric), "no historic rows");
    assert!(by_comp.contains_key(&Competition::CopaDoBrasil), "no Copa do Brasil rows");
    assert!(by_comp.contains_key(&Competition::Libertadores), "no Libertadores rows");
    assert!(by_comp.contains_key(&Competition::BrFootball), "no BR-Football rows");
    // Combined match count should comfortably exceed every individual file.
    assert!(s.matches.len() > 20_000, "expected >20k matches, got {}", s.matches.len());
    // And FIFA players are loaded
    assert!(s.players.len() > 15_000, "expected >15k players, got {}", s.players.len());
}

// --- Feature: Match Queries ----------------------------------------------

#[test]
fn given_match_data_when_searching_flamengo_vs_fluminense_then_returns_matches_with_dates() {
    // Given the match data is loaded
    let s = store();
    // When I search for matches between Flamengo and Fluminense
    let f = MatchFilter {
        team: Some("Flamengo"),
        opponent: Some("Fluminense"),
        ..Default::default()
    };
    let matches = search_matches(s, &f);
    // Then I receive a non-empty list
    assert!(!matches.is_empty(), "expected at least one Fla-Flu match");
    // And every match has date and team labels
    for m in &matches {
        assert!(m.date.is_some(), "match missing date: {:?}", m);
        assert!(!m.home_team.is_empty());
        assert!(!m.away_team.is_empty());
    }
}

#[test]
fn given_match_data_when_filtering_palmeiras_by_season_then_only_that_year_returned() {
    let s = store();
    let f = MatchFilter {
        team: Some("Palmeiras"),
        season: Some(2019),
        ..Default::default()
    };
    let matches = search_matches(s, &f);
    assert!(!matches.is_empty(), "expected Palmeiras 2019 matches");
    for m in &matches {
        assert_eq!(m.season, Some(2019));
    }
}

#[test]
fn given_libertadores_data_when_searching_by_competition_then_only_libertadores_returned() {
    let s = store();
    let f = MatchFilter {
        competition: Some(Competition::Libertadores),
        ..Default::default()
    };
    let matches = search_matches(s, &f);
    assert!(matches.len() >= 1000, "expected >=1000 Libertadores matches");
    assert!(matches.iter().all(|m| m.competition == Competition::Libertadores));
}

// --- Feature: Team Queries ------------------------------------------------

#[test]
fn given_match_data_when_requesting_palmeiras_2019_stats_then_returns_wd_l_and_goals() {
    let s = store();
    let stats = team_stats(
        s,
        "Palmeiras",
        &MatchFilter {
            competition: Some(Competition::Brasileirao),
            season: Some(2019),
            ..Default::default()
        },
    );
    assert!(stats.played > 0, "expected some matches for Palmeiras 2019");
    assert_eq!(
        stats.played,
        stats.wins + stats.draws + stats.losses,
        "W+D+L must equal played"
    );
    assert!(stats.goals_for >= 0 && stats.goals_against >= 0);
}

#[test]
fn given_h2h_query_when_comparing_palmeiras_and_santos_then_totals_are_consistent() {
    let s = store();
    let h = head_to_head(s, "Palmeiras", "Santos");
    let total = h.team1_wins + h.team2_wins + h.draws;
    assert!(total > 0, "expected at least one Palmeiras vs Santos match");
    // Symmetry: swapping arguments should swap the records and goal columns.
    let rev = head_to_head(s, "Santos", "Palmeiras");
    assert_eq!(h.team1_wins, rev.team2_wins);
    assert_eq!(h.team2_wins, rev.team1_wins);
    assert_eq!(h.draws, rev.draws);
    assert_eq!(h.team1_goals, rev.team2_goals);
    assert_eq!(h.team2_goals, rev.team1_goals);
}

#[test]
fn given_a_home_only_filter_when_computing_corinthians_2022_stats_then_no_away_legs_counted() {
    let s = store();
    let all = team_stats(
        s,
        "Corinthians",
        &MatchFilter {
            competition: Some(Competition::Brasileirao),
            season: Some(2022),
            ..Default::default()
        },
    );
    let home = team_stats(
        s,
        "Corinthians",
        &MatchFilter {
            competition: Some(Competition::Brasileirao),
            season: Some(2022),
            home_only: true,
            ..Default::default()
        },
    );
    assert!(home.played <= all.played, "home subset must not exceed total");
    assert!(home.played > 0, "expected some home games");
}

// --- Feature: Competition Queries ----------------------------------------

#[test]
fn given_2019_brasileirao_when_computing_standings_then_flamengo_is_champion() {
    let s = store();
    let rows = season_standings(s, 2019, Competition::Brasileirao);
    assert!(!rows.is_empty(), "expected 2019 Brasileirão standings");
    let champ = &rows[0];
    let champ_norm =
        brazilian_soccer_mcp::normalize::normalize_team(&champ.team);
    assert!(
        champ_norm.contains("flamengo"),
        "expected Flamengo on top of 2019 Brasileirão, got {}",
        champ.team
    );
}

#[test]
fn given_a_season_when_computing_standings_then_points_equal_3w_plus_d() {
    let s = store();
    let rows = season_standings(s, 2018, Competition::Brasileirao);
    for r in rows {
        assert_eq!(
            r.stats.points(),
            (r.stats.wins as i32) * 3 + r.stats.draws as i32
        );
    }
}

// --- Feature: Player Queries ---------------------------------------------

#[test]
fn given_fifa_data_when_searching_for_neymar_then_returns_a_neymar_record() {
    let s = store();
    let players = search_players(
        s,
        &PlayerFilter {
            name: Some("Neymar"),
            ..Default::default()
        },
    );
    assert!(!players.is_empty(), "expected at least one Neymar");
    assert!(players.iter().any(|p| p.name.to_lowercase().contains("neymar")));
}

#[test]
fn given_fifa_data_when_filtering_brazilians_then_all_results_are_brazilian() {
    let s = store();
    let players = search_players(
        s,
        &PlayerFilter {
            nationality: Some("Brazil"),
            ..Default::default()
        },
    );
    assert!(players.len() > 100, "expected many Brazilian players");
    for p in &players {
        assert!(
            p.nationality.to_lowercase().contains("brazil"),
            "non-Brazilian leaked through filter: {} ({})",
            p.name,
            p.nationality
        );
    }
}

#[test]
fn given_fifa_data_when_asking_top_brazilians_then_ratings_are_descending() {
    let s = store();
    let top = top_players(s, Some("Brazil"), None, 10);
    assert_eq!(top.len(), 10);
    let ratings: Vec<i32> = top.iter().map(|p| p.overall.unwrap_or(0)).collect();
    let mut sorted = ratings.clone();
    sorted.sort_by(|a, b| b.cmp(a));
    assert_eq!(ratings, sorted, "top players must be sorted by Overall desc");
}

#[test]
fn given_fifa_data_when_summarising_brazilian_clubs_then_each_entry_has_players() {
    let s = store();
    let groups = club_averages_by_nationality(s, "Brazil");
    assert!(!groups.is_empty(), "expected at least one Brazilian club");
    for (club, n, avg) in groups.iter().take(5) {
        assert!(n > &0, "club {} has zero players", club);
        assert!(*avg >= 0.0);
    }
}

// --- Feature: Statistical Analysis ---------------------------------------

#[test]
fn given_all_matches_when_listing_biggest_wins_then_first_margin_is_largest() {
    let s = store();
    let wins = biggest_wins(s, None, 5);
    assert_eq!(wins.len(), 5);
    let margins: Vec<i32> = wins.iter().map(|m| (m.home_goal - m.away_goal).abs()).collect();
    let mut sorted = margins.clone();
    sorted.sort_by(|a, b| b.cmp(a));
    assert_eq!(margins, sorted, "biggest_wins must be sorted by margin desc");
    assert!(margins[0] >= 5, "expected a thumping margin in the dataset");
}

#[test]
fn given_brasileirao_when_computing_competition_stats_then_average_goals_is_reasonable() {
    let s = store();
    let stats = competition_stats(s, Some(Competition::Brasileirao), None);
    assert!(stats.matches > 0);
    let avg = stats.average_goals();
    assert!(
        (1.5..=4.0).contains(&avg),
        "average goals per match should be in [1.5, 4.0], got {}",
        avg
    );
    let hwr = stats.home_win_rate();
    assert!(
        (0.3..=0.7).contains(&hwr),
        "home win rate should be in [0.3, 0.7], got {}",
        hwr
    );
}

// --- Feature: MCP protocol surface ---------------------------------------

#[test]
fn given_a_jsonrpc_initialize_when_dispatched_then_returns_server_info() {
    let server = brazilian_soccer_mcp::mcp::Server::new(
        Store::load("data").expect("load"),
    );
    let req = json!({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name":"test","version":"1"}}
    });
    let line = serde_json::to_string(&req).unwrap();
    let resp = server.dispatch_line(&line).expect("response expected");
    let v: serde_json::Value = serde_json::from_str(&resp).unwrap();
    assert_eq!(v["jsonrpc"], "2.0");
    assert_eq!(v["id"], 1);
    assert_eq!(v["result"]["serverInfo"]["name"], "brazilian-soccer-mcp");
    assert!(v["result"]["capabilities"]["tools"].is_object());
}

#[test]
fn given_a_tools_list_when_dispatched_then_returns_at_least_ten_tools() {
    let server = brazilian_soccer_mcp::mcp::Server::new(
        Store::load("data").expect("load"),
    );
    let req = json!({"jsonrpc":"2.0","id":2,"method":"tools/list"});
    let resp = server
        .dispatch_line(&serde_json::to_string(&req).unwrap())
        .unwrap();
    let v: serde_json::Value = serde_json::from_str(&resp).unwrap();
    let tools = v["result"]["tools"].as_array().expect("tools array");
    assert!(tools.len() >= 10, "expected >=10 tools, got {}", tools.len());
    for t in tools {
        assert!(t["name"].is_string());
        assert!(t["description"].is_string());
        assert!(t["inputSchema"].is_object());
    }
}

#[test]
fn given_search_matches_tool_call_when_dispatched_then_response_contains_text_block() {
    let server = brazilian_soccer_mcp::mcp::Server::new(
        Store::load("data").expect("load"),
    );
    let req = json!({
        "jsonrpc":"2.0","id":3,"method":"tools/call",
        "params":{"name":"search_matches","arguments":{"team":"Flamengo","opponent":"Fluminense","limit":3}}
    });
    let resp = server
        .dispatch_line(&serde_json::to_string(&req).unwrap())
        .unwrap();
    let v: serde_json::Value = serde_json::from_str(&resp).unwrap();
    let content = v["result"]["content"][0]["text"]
        .as_str()
        .expect("text block");
    assert!(content.contains("Matches found"));
    assert!(content.contains("Head-to-head"));
}

#[test]
fn given_a_notification_when_dispatched_then_no_response_is_emitted() {
    let server = brazilian_soccer_mcp::mcp::Server::new(
        Store::load("data").expect("load"),
    );
    let notif = json!({"jsonrpc":"2.0","method":"notifications/initialized"});
    let resp = server.dispatch_line(&serde_json::to_string(&notif).unwrap());
    assert!(resp.is_none(), "notifications must not produce a response");
}

#[test]
fn given_an_unknown_method_when_dispatched_then_returns_method_not_found_error() {
    let server = brazilian_soccer_mcp::mcp::Server::new(
        Store::load("data").expect("load"),
    );
    let req = json!({"jsonrpc":"2.0","id":42,"method":"does/not/exist"});
    let resp = server
        .dispatch_line(&serde_json::to_string(&req).unwrap())
        .unwrap();
    let v: serde_json::Value = serde_json::from_str(&resp).unwrap();
    assert_eq!(v["error"]["code"], -32601);
}
