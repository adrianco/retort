//! ============================================================================
//! Context
//! ----------------------------------------------------------------------------
//! Test suite: BDD (Behaviour-Driven Development) scenarios
//! Purpose:    Exercise the Brazilian-soccer knowledge graph end-to-end against
//!             the real bundled datasets, following the Given/When/Then style
//!             requested by the specification's "Testing Approach" section.
//!
//! Each test reads as a Gherkin scenario:
//!   Given <some loaded data / context>
//!   When  <a query is issued>
//!   Then  <assertions on the result>
//!
//! The datasets are loaded once and shared across all scenarios (loading parses
//! ~42k CSV rows, so we avoid repeating it per test).
//! ============================================================================

use std::sync::OnceLock;

use brazilian_soccer_mcp::data::Database;
use brazilian_soccer_mcp::mcp::Server;
use brazilian_soccer_mcp::query::{
    self, MatchFilter, PlayerFilter, Venue,
};
use serde_json::json;

/// Given: the full match + player datasets are loaded (once, shared).
fn db() -> &'static Database {
    static DB: OnceLock<Database> = OnceLock::new();
    DB.get_or_init(|| Database::load(None).expect("datasets should load from data/kaggle"))
}

// ===========================================================================
// Feature: Data loading
// ===========================================================================

#[test]
fn scenario_all_datasets_load() {
    // Given the bundled data directory
    // When the database is loaded
    let db = db();
    // Then matches and players are present in large numbers
    assert!(
        db.matches.len() > 15_000,
        "expected many matches, got {}",
        db.matches.len()
    );
    assert!(
        db.players.len() > 18_000,
        "expected ~18k players, got {}",
        db.players.len()
    );

    // And every competition bucket is represented
    let has = |c: &str| db.matches.iter().any(|m| m.competition == c);
    assert!(has("Brasileirão"));
    assert!(has("Copa do Brasil"));
    assert!(has("Copa Libertadores"));

    // And the extended dataset is loaded too (queryable, but flagged)
    assert!(db.matches.iter().any(|m| m.is_extended()));
}

// ===========================================================================
// Feature: Match Queries
// ===========================================================================

#[test]
fn scenario_find_matches_between_two_teams() {
    // Given the match data is loaded
    let db = db();
    // When I search for matches between "Flamengo" and "Fluminense"
    let matches = query::search_matches(
        db,
        &MatchFilter {
            team: Some("Flamengo".into()),
            opponent: Some("Fluminense".into()),
            ..Default::default()
        },
    );
    // Then I receive a non-empty list of matches
    assert!(!matches.is_empty(), "Fla-Flu should have matches");
    // And each match really involves both teams
    for m in &matches {
        assert!(m.involves("flamengo"), "{} should involve Flamengo", m.summary());
        assert!(m.involves("fluminense"));
    }
    // And each match has a date and scores
    assert!(matches.iter().all(|m| m.date.is_some() && m.has_score()));
}

#[test]
fn scenario_matches_by_team_and_season() {
    // Given the match data is loaded
    let db = db();
    // When I ask what matches Palmeiras played in 2022
    let matches = query::search_matches(
        db,
        &MatchFilter {
            team: Some("Palmeiras".into()),
            season: Some(2022),
            ..Default::default()
        },
    );
    // Then there are matches and they are all from 2022 involving Palmeiras
    assert!(!matches.is_empty());
    assert!(matches.iter().all(|m| m.season == Some(2022)));
    assert!(matches.iter().all(|m| m.involves("palmeiras")));
}

#[test]
fn scenario_matches_filtered_by_competition() {
    // Given the match data is loaded
    let db = db();
    // When I search Libertadores matches
    let matches = query::search_matches(
        db,
        &MatchFilter {
            competition: Some("libertadores".into()),
            ..Default::default()
        },
    );
    // Then all results belong to the Copa Libertadores
    assert!(!matches.is_empty());
    assert!(matches.iter().all(|m| m.competition == "Copa Libertadores"));
}

#[test]
fn scenario_matches_sorted_newest_first() {
    // Given the match data is loaded
    let db = db();
    // When I list Corinthians matches
    let matches = query::search_matches(
        db,
        &MatchFilter {
            team: Some("Corinthians".into()),
            ..Default::default()
        },
    );
    // Then they are ordered from most recent to oldest
    let dates: Vec<_> = matches.iter().filter_map(|m| m.date).collect();
    let mut sorted = dates.clone();
    sorted.sort_by(|a, b| b.cmp(a));
    assert_eq!(dates, sorted, "matches should be newest-first");
}

// ===========================================================================
// Feature: Team Queries
// ===========================================================================

#[test]
fn scenario_team_statistics_for_a_season() {
    // Given the match data is loaded
    let db = db();
    // When I request statistics for Palmeiras in season 2022 (Brasileirão)
    let rec = query::team_record(db, "Palmeiras", Some(2022), Some("Brasileirão"), Venue::Any);
    // Then I receive wins, draws, losses and goals that add up coherently
    assert!(rec.matches > 0);
    assert_eq!(rec.matches, rec.wins + rec.draws + rec.losses);
    assert!(rec.goals_for > 0);
    // And the win rate is a sane percentage
    assert!(rec.win_rate() >= 0.0 && rec.win_rate() <= 100.0);
}

#[test]
fn scenario_team_home_record() {
    // Given the match data is loaded
    let db = db();
    // When I ask for Corinthians' home record in 2022
    let home = query::team_record(db, "Corinthians", Some(2022), Some("Brasileirão"), Venue::Home);
    let all = query::team_record(db, "Corinthians", Some(2022), Some("Brasileirão"), Venue::Any);
    // Then the home games are a subset of all games
    assert!(home.matches > 0);
    assert!(home.matches < all.matches);
    // And there are at most 19 home games (a 20-team league), counting only
    // those with recorded scores — a few 2022 fixtures carry "NA" results.
    assert!(
        (15..=19).contains(&home.matches),
        "expected ~19 home games, got {}",
        home.matches
    );
}

#[test]
fn scenario_head_to_head_record_is_consistent() {
    // Given the match data is loaded
    let db = db();
    // When I compare Palmeiras and Santos head-to-head
    let h = query::head_to_head(db, "Palmeiras", "Santos");
    // Then the wins + draws total the scored matches between them
    let scored = h.matches.iter().filter(|m| m.has_score()).count() as u32;
    assert_eq!(h.a_wins + h.b_wins + h.draws, scored);
    assert!(scored > 0, "Palmeiras-Santos should have played");
}

// ===========================================================================
// Feature: Player Queries
// ===========================================================================

#[test]
fn scenario_lookup_player_by_name() {
    // Given the player data is loaded
    let db = db();
    // When I look up "Neymar"
    let players = query::search_players(
        db,
        &PlayerFilter {
            name: Some("Neymar".into()),
            ..Default::default()
        },
    );
    // Then at least one player is found and is Brazilian
    assert!(!players.is_empty());
    assert!(players.iter().any(|p| p.nationality == "Brazil"));
}

#[test]
fn scenario_filter_brazilian_players_sorted_by_rating() {
    // Given the player data is loaded
    let db = db();
    // When I ask for the top Brazilian players
    let players = query::search_players(
        db,
        &PlayerFilter {
            nationality: Some("Brazil".into()),
            limit: Some(10),
            ..Default::default()
        },
    );
    // Then I get 10 Brazilians, sorted by Overall descending
    assert_eq!(players.len(), 10);
    assert!(players.iter().all(|p| p.nationality == "Brazil"));
    let ratings: Vec<u32> = players.iter().map(|p| p.overall.unwrap_or(0)).collect();
    let mut sorted = ratings.clone();
    sorted.sort_by(|a, b| b.cmp(a));
    assert_eq!(ratings, sorted);
}

#[test]
fn scenario_filter_players_by_position() {
    // Given the player data is loaded
    let db = db();
    // When I ask for goalkeepers only
    let players = query::search_players(
        db,
        &PlayerFilter {
            position: Some("GK".into()),
            limit: Some(20),
            ..Default::default()
        },
    );
    // Then every returned player is a goalkeeper
    assert!(!players.is_empty());
    assert!(players.iter().all(|p| p.position == "GK"));
}

// ===========================================================================
// Feature: Competition Queries (calculated standings)
// ===========================================================================

#[test]
fn scenario_calculated_standings_match_reality_2019() {
    // Given the match data is loaded
    let db = db();
    // When I calculate the 2019 Brasileirão final standings
    let table = query::standings(db, "Brasileirão", 2019);
    // Then there are 20 teams
    assert_eq!(table.len(), 20, "2019 Brasileirão had 20 clubs");
    // And the champion is Flamengo with 90 points (historically accurate)
    let champ = &table[0];
    assert!(
        champ.team.to_lowercase().contains("flamengo"),
        "champion was {}",
        champ.team
    );
    assert_eq!(champ.points(), 90, "Flamengo finished 2019 on 90 points");
    // And every club played 38 games
    assert!(table.iter().all(|r| r.played == 38));
    // And the table is sorted by points descending
    let pts: Vec<u32> = table.iter().map(|r| r.points()).collect();
    let mut sorted = pts.clone();
    sorted.sort_by(|a, b| b.cmp(a));
    assert_eq!(pts, sorted);
}

// ===========================================================================
// Feature: Statistical Analysis
// ===========================================================================

#[test]
fn scenario_aggregate_competition_statistics() {
    // Given the match data is loaded
    let db = db();
    // When I compute Brasileirão statistics
    let stats = query::competition_stats(db, Some("Brasileirão"), None);
    // Then the averages are in believable football ranges
    assert!(stats.matches_with_score > 1000);
    let avg = stats.avg_goals_per_match();
    assert!((2.0..3.5).contains(&avg), "avg goals/match was {}", avg);
    // And home advantage is real (home win rate beats away win rate)
    assert!(stats.home_win_rate() > stats.away_win_rate());
    // And the rates are a partition of 100%
    let total = stats.home_win_rate() + stats.away_win_rate() + stats.draw_rate();
    assert!((total - 100.0).abs() < 0.01);
}

#[test]
fn scenario_biggest_wins_are_lopsided() {
    // Given the match data is loaded
    let db = db();
    // When I ask for the biggest victories
    let wins = query::biggest_wins(db, None, None, 5);
    // Then I get five blowouts, ordered by margin descending
    assert_eq!(wins.len(), 5);
    let margin = |m: &&brazilian_soccer_mcp::models::Match| {
        (m.home_goal.unwrap() as i64 - m.away_goal.unwrap() as i64).abs()
    };
    let margins: Vec<i64> = wins.iter().map(margin).collect();
    let mut sorted = margins.clone();
    sorted.sort_by(|a, b| b.cmp(a));
    assert_eq!(margins, sorted);
    assert!(margins[0] >= 6, "the biggest win should be a rout");
}

// ===========================================================================
// Feature: Data Quality (normalization)
// ===========================================================================

#[test]
fn scenario_team_name_variations_are_handled() {
    // Given the match data is loaded
    let db = db();
    // When I query the same club with and without its state suffix
    let plain = query::search_matches(
        db,
        &MatchFilter { team: Some("Palmeiras".into()), season: Some(2019), ..Default::default() },
    );
    let suffixed = query::search_matches(
        db,
        &MatchFilter { team: Some("Palmeiras-SP".into()), season: Some(2019), ..Default::default() },
    );
    // Then both forms find the same matches
    assert!(!plain.is_empty());
    assert_eq!(plain.len(), suffixed.len());
}

#[test]
fn scenario_accented_names_are_matched() {
    // Given the match data is loaded
    let db = db();
    // When I search "Sao Paulo" without the accent
    let matches = query::search_matches(
        db,
        &MatchFilter { team: Some("Sao Paulo".into()), season: Some(2019), ..Default::default() },
    );
    // Then accented "São Paulo" matches are still found
    assert!(!matches.is_empty());
    assert!(matches.iter().all(|m| m.involves("sao paulo")));
}

#[test]
fn scenario_same_named_clubs_stay_distinct() {
    // Given the match data is loaded
    let db = db();
    // When I build the 2019 standings (which contains several Atléticos)
    let table = query::standings(db, "Brasileirão", 2019);
    // Then Atlético-MG and Athletico-PR appear as separate clubs
    let mineiro = table.iter().any(|r| r.team.contains("Atletico-MG"));
    let paranaense = table
        .iter()
        .any(|r| r.team.contains("Atletico-PR") || r.team.contains("Athletico"));
    assert!(mineiro, "Atlético-MG should be in the table");
    assert!(paranaense, "Athletico-PR should be in the table");
}

// ===========================================================================
// Feature: MCP protocol surface
// ===========================================================================

#[test]
fn scenario_mcp_initialize_handshake() {
    // Given an MCP server over the loaded data
    let server = Server::new(Database::load(None).unwrap());
    // When the client sends `initialize`
    let req = json!({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}});
    let resp = server.handle_message(&req).expect("initialize must reply");
    // Then the server advertises a protocol version and its name
    assert_eq!(resp["result"]["protocolVersion"], "2024-11-05");
    assert_eq!(resp["result"]["serverInfo"]["name"], "brazilian-soccer-mcp");
    assert!(resp["result"]["capabilities"]["tools"].is_object());
}

#[test]
fn scenario_mcp_notifications_get_no_reply() {
    // Given an MCP server
    let server = Server::new(Database::default());
    // When an `initialized` notification (no id) arrives
    let note = json!({"jsonrpc": "2.0", "method": "notifications/initialized"});
    // Then there is no response
    assert!(server.handle_message(&note).is_none());
}

#[test]
fn scenario_mcp_tools_list_exposes_capabilities() {
    // Given an MCP server
    let server = Server::new(Database::default());
    // When the client lists tools
    let req = json!({"jsonrpc": "2.0", "id": 2, "method": "tools/list"});
    let resp = server.handle_message(&req).unwrap();
    // Then the catalog covers all five capability areas
    let tools = resp["result"]["tools"].as_array().unwrap();
    let names: Vec<&str> = tools.iter().filter_map(|t| t["name"].as_str()).collect();
    for expected in [
        "search_matches",
        "head_to_head",
        "team_record",
        "standings",
        "search_players",
        "competition_stats",
    ] {
        assert!(names.contains(&expected), "missing tool {}", expected);
    }
    // And each tool has an input schema
    assert!(tools.iter().all(|t| t["inputSchema"].is_object()));
}

#[test]
fn scenario_mcp_tool_call_returns_text_content() {
    // Given an MCP server over the loaded data
    let server = Server::new(Database::load(None).unwrap());
    // When the client calls `standings` for 2019 via tools/call
    let req = json!({
        "jsonrpc": "2.0", "id": 3, "method": "tools/call",
        "params": { "name": "standings", "arguments": { "season": 2019 } }
    });
    let resp = server.handle_message(&req).unwrap();
    // Then it returns text content mentioning the champion
    let text = resp["result"]["content"][0]["text"].as_str().unwrap();
    assert!(text.contains("Flamengo"));
    assert!(text.contains("Champion"));
    assert_eq!(resp["result"]["isError"], false);
}

#[test]
fn scenario_mcp_unknown_method_is_an_error() {
    // Given an MCP server
    let server = Server::new(Database::default());
    // When an unsupported method is called
    let req = json!({"jsonrpc": "2.0", "id": 4, "method": "does/not/exist"});
    let resp = server.handle_message(&req).unwrap();
    // Then a JSON-RPC "method not found" error is returned
    assert_eq!(resp["error"]["code"], -32601);
}

#[test]
fn scenario_mcp_player_profile_answers_who_is() {
    // Given an MCP server over the loaded data
    let server = Server::new(Database::load(None).unwrap());
    // When asked "Who is Gabriel Barbosa?" via player_profile
    let text = server
        .dispatch_tool("player_profile", &json!({"name": "Gabriel Barbosa"}))
        .unwrap();
    // Then a profile (or a clear not-found) is returned, never a panic
    assert!(text.contains("Nationality") || text.contains("No player"));
}
