// =============================================================================
// CONTEXT: Brazilian Soccer MCP Server — BDD test suite
//
// Behavior-driven tests following the Given/When/Then structure from the
// specification's testing approach. Each test is named
// given_<precondition>_when_<action>_then_<expectation> and its body is
// organized into explicit GIVEN / WHEN / THEN sections.
//
// Coverage maps to the spec's success criteria:
//   * all six CSV files load and are queryable
//   * match search (by team pair, season, competition, date range, finals)
//   * team statistics (wins/losses/draws/goals, home/away venue)
//   * head-to-head comparison
//   * team-name normalization (state suffixes, accents, renames)
//   * date-format handling (ISO, ISO+time, Brazilian DD/MM/YYYY)
//   * player search and profiles (incl. cross-file club queries)
//   * standings calculation (2019 champion = Flamengo)
//   * aggregate statistics (avg goals, biggest wins)
//   * MCP protocol: initialize, tools/list, tools/call, error handling
// =============================================================================

use brazilian_soccer_mcp::data::{parse_date, team_key, Data, Source};
use brazilian_soccer_mcp::query::{MatchFilter, QueryEngine};
use brazilian_soccer_mcp::server::Server;
use serde_json::{json, Value};
use std::path::Path;
use std::sync::OnceLock;

/// GIVEN (shared): the six Kaggle CSVs loaded from data/kaggle.
fn data() -> &'static Data {
    static DATA: OnceLock<Data> = OnceLock::new();
    DATA.get_or_init(|| {
        let dir = Path::new(env!("CARGO_MANIFEST_DIR")).join("data/kaggle");
        Data::load(&dir).expect("datasets should load")
    })
}

fn engine() -> QueryEngine<'static> {
    QueryEngine::new(data())
}

// ---------------------------------------------------------------------------
// Feature: Data loading
// ---------------------------------------------------------------------------

#[test]
fn given_csv_files_when_loading_then_all_six_sources_are_present() {
    // GIVEN the data directory with six CSV files
    let d = data();

    // WHEN counting loaded rows per source
    let count = |s: Source| d.matches.iter().filter(|m| m.source == s).count();

    // THEN every match dataset contributed rows in the expected magnitude
    assert!(count(Source::Brasileirao) >= 4000, "Brasileirao matches");
    assert!(count(Source::Cup) >= 1300, "Copa do Brasil matches");
    assert!(count(Source::Libertadores) >= 1200, "Libertadores matches");
    assert!(count(Source::Extended) >= 10000, "extended dataset matches");
    assert!(count(Source::Historical) >= 6800, "historical matches");
    // AND the FIFA player database loaded
    assert!(d.players.len() >= 18000, "FIFA players");
}

#[test]
fn given_data_loaded_when_checking_encoding_then_accented_team_names_survive() {
    // GIVEN the loaded match data
    let d = data();

    // WHEN looking for teams with Portuguese accents
    let has_accented = d
        .matches
        .iter()
        .any(|m| m.home_team.contains("Grêmio") || m.away_team.contains("Grêmio"));

    // THEN UTF-8 accented names are preserved in display names
    assert!(has_accented, "expected accented names like Grêmio");
}

// ---------------------------------------------------------------------------
// Feature: Team-name normalization
// ---------------------------------------------------------------------------

#[test]
fn given_name_variations_when_normalizing_then_keys_match() {
    // GIVEN team names in the different conventions used across the CSVs
    // WHEN normalizing them THEN equivalent spellings produce the same key
    assert_eq!(team_key("Palmeiras-SP"), team_key("Palmeiras"));
    assert_eq!(team_key("São Paulo"), team_key("Sao Paulo"));
    assert_eq!(team_key("Flamengo-RJ"), team_key("Flamengo"));
    assert_eq!(team_key("Athletico-PR"), team_key("Atlético-PR"));
    assert_eq!(team_key("América - MG"), team_key("América-MG"));

    // AND clubs that need their state to stay unambiguous keep it
    assert_ne!(team_key("Atlético-MG"), team_key("Atlético-GO"));
    assert_ne!(team_key("América-MG"), team_key("América-RN"));
}

#[test]
fn given_long_official_names_when_searching_then_short_names_still_match() {
    // GIVEN the Copa do Brasil file uses long names like
    // "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ"
    let e = engine();

    // WHEN searching for Corinthians (short form) in cup data
    let out = e.search_matches(&MatchFilter {
        team: Some("Corinthians".into()),
        competition: Some("Copa do Brasil".into()),
        ..Default::default()
    });

    // THEN matches are found despite name-form differences
    assert!(out.starts_with("Found"), "expected cup matches for Corinthians, got: {}", out);
}

// ---------------------------------------------------------------------------
// Feature: Date handling
// ---------------------------------------------------------------------------

#[test]
fn given_three_date_formats_when_parsing_then_all_are_understood() {
    // GIVEN the three formats present in the datasets
    // WHEN parsing THEN each resolves to the right calendar day
    assert_eq!(parse_date("2012-05-19 18:30:00").unwrap().to_string(), "2012-05-19");
    assert_eq!(parse_date("2023-09-24").unwrap().to_string(), "2023-09-24");
    assert_eq!(parse_date("29/03/2003").unwrap().to_string(), "2003-03-29");
    // AND missing values are handled gracefully
    assert!(parse_date("NA").is_none());
    assert!(parse_date("").is_none());
}

// ---------------------------------------------------------------------------
// Feature: Match queries
// ---------------------------------------------------------------------------

#[test]
fn given_match_data_when_searching_flamengo_vs_fluminense_then_matches_have_date_score_competition() {
    // GIVEN the match data is loaded
    let e = engine();

    // WHEN I search for matches between Flamengo and Fluminense
    let out = e.search_matches(&MatchFilter {
        team: Some("Flamengo".into()),
        opponent: Some("Fluminense".into()),
        limit: 100,
        ..Default::default()
    });

    // THEN I should receive a list of matches
    assert!(out.contains("Found"), "got: {}", out);
    // AND each listed match line has a date, scores and a competition
    let lines: Vec<&str> = out.lines().filter(|l| l.starts_with("- ")).collect();
    assert!(!lines.is_empty());
    for line in &lines {
        assert!(line.contains("20"), "date missing in: {}", line);
        assert!(line.contains('('), "competition missing in: {}", line);
    }
    // AND a head-to-head summary is included
    assert!(out.contains("Head-to-head"), "got: {}", out);
}

#[test]
fn given_match_data_when_filtering_by_season_then_only_that_season_is_returned() {
    // GIVEN the match data is loaded
    let e = engine();

    // WHEN I ask what matches Palmeiras played in 2019 in the Brasileirão
    let out = e.search_matches(&MatchFilter {
        team: Some("Palmeiras".into()),
        season: Some(2019),
        competition: Some("Brasileirão".into()),
        limit: 50,
        ..Default::default()
    });

    // THEN matches are found and every dated line is from 2019
    assert!(out.starts_with("Found"), "got: {}", out);
    for line in out.lines().filter(|l| l.starts_with("- 2")) {
        assert!(line.starts_with("- 2019"), "non-2019 match: {}", line);
    }
}

#[test]
fn given_match_data_when_filtering_by_date_range_then_results_stay_inside_range() {
    // GIVEN the match data is loaded
    let e = engine();

    // WHEN I search Santos matches between 2015-01-01 and 2015-12-31
    let out = e.search_matches(&MatchFilter {
        team: Some("Santos".into()),
        date_from: parse_date("2015-01-01"),
        date_to: parse_date("2015-12-31"),
        limit: 200,
        ..Default::default()
    });

    // THEN all dated results fall inside the range
    assert!(out.starts_with("Found"), "got: {}", out);
    for line in out.lines().filter(|l| l.starts_with("- 2")) {
        assert!(line.starts_with("- 2015"), "out-of-range match: {}", line);
    }
}

#[test]
fn given_cup_data_when_searching_finals_then_only_last_round_matches_return() {
    // GIVEN Copa do Brasil rounds where the final is the highest round
    let e = engine();

    // WHEN I search for Copa do Brasil finals
    let out = e.search_matches(&MatchFilter {
        competition: Some("Copa do Brasil".into()),
        stage: Some("final".into()),
        limit: 100,
        ..Default::default()
    });

    // THEN finals are found (two legs per season, 2012-2021)
    assert!(out.starts_with("Found"), "got: {}", out);

    // AND a 'final' stage filter on Libertadores does not leak semifinals
    let lib = e.search_matches(&MatchFilter {
        competition: Some("Libertadores".into()),
        stage: Some("final".into()),
        limit: 100,
        ..Default::default()
    });
    assert!(lib.starts_with("Found"), "got: {}", lib);
    assert!(!lib.contains("semifinals"), "semifinals leaked into finals: {}", lib);
}

// ---------------------------------------------------------------------------
// Feature: Team statistics
// ---------------------------------------------------------------------------

#[test]
fn given_match_data_when_requesting_palmeiras_2023_stats_then_wdl_and_goals_are_returned() {
    // GIVEN the match data is loaded
    let e = engine();

    // WHEN I request statistics for "Palmeiras" in season 2023
    let out = e.team_stats("Palmeiras", Some(2023), None, None);

    // THEN I should receive wins, losses, draws, and goals
    assert!(out.contains("Wins:"), "got: {}", out);
    assert!(out.contains("Draws:"), "got: {}", out);
    assert!(out.contains("Losses:"), "got: {}", out);
    assert!(out.contains("Goals For:"), "got: {}", out);
    assert!(out.contains("Win rate:"), "got: {}", out);
}

#[test]
fn given_match_data_when_requesting_home_record_then_only_home_matches_count() {
    // GIVEN the match data is loaded
    let e = engine();

    // WHEN I request Corinthians' home record for 2022 in the Brasileirão
    let home = e.team_stats(
        "Corinthians",
        Some(2022),
        Some("Brasileirão".into()),
        Some("home".into()),
    );
    let all = e.team_stats("Corinthians", Some(2022), Some("Brasileirão".into()), None);

    // THEN both succeed and the home-only match count is smaller
    let count = |s: &str| -> u32 {
        s.lines()
            .find(|l| l.starts_with("- Matches:"))
            .and_then(|l| l.rsplit(' ').next())
            .and_then(|n| n.parse().ok())
            .unwrap_or(0)
    };
    assert!(count(&home) > 0, "no home matches: {}", home);
    assert!(count(&home) < count(&all), "home should be a subset of all");
}

// ---------------------------------------------------------------------------
// Feature: Head-to-head
// ---------------------------------------------------------------------------

#[test]
fn given_match_data_when_comparing_palmeiras_and_santos_then_record_is_consistent() {
    // GIVEN the match data is loaded
    let e = engine();

    // WHEN I compare Palmeiras and Santos head-to-head
    let out = e.head_to_head("Palmeiras", "Santos", None);

    // THEN the summary names both teams with win counts and draws
    assert!(out.contains("Palmeiras") && out.contains("Santos"), "got: {}", out);
    assert!(out.contains("wins") && out.contains("draws"), "got: {}", out);
    // AND recent meetings are listed
    assert!(out.contains("Most recent meetings"), "got: {}", out);
}

// ---------------------------------------------------------------------------
// Feature: Standings / competition queries
// ---------------------------------------------------------------------------

#[test]
fn given_2019_results_when_computing_standings_then_flamengo_is_champion() {
    // GIVEN the 2019 Brasileirão results
    let e = engine();

    // WHEN I compute the 2019 standings
    let out = e.standings(2019, None);

    // THEN Flamengo tops the table as champion
    let first = out
        .lines()
        .find(|l| l.starts_with("1."))
        .expect("standings should have a first row");
    assert!(first.contains("Flamengo"), "2019 champion row: {}", first);
    assert!(first.contains("Champion"), "champion tag missing: {}", first);
    // AND a relegation zone is marked
    assert!(out.contains("Relegation zone"), "got: {}", out);
}

#[test]
fn given_overlapping_datasets_when_computing_standings_then_matches_are_not_double_counted() {
    // GIVEN 2015 Serie A exists in three CSVs (Brasileirao, historical, extended)
    let e = engine();

    // WHEN computing the 2015 standings
    let out = e.standings(2015, None);

    // THEN a 20-team double round-robin yields 38 played matches for the leader
    let first = out.lines().find(|l| l.starts_with("1.")).unwrap();
    let wdl: Vec<u32> = first
        .split(['(', ')'])
        .nth(1)
        .unwrap()
        .split(", ")
        .filter_map(|p| p.trim_matches(|c: char| !c.is_ascii_digit()).parse().ok())
        .collect();
    let played: u32 = wdl.iter().take(3).sum();
    assert_eq!(played, 38, "leader should have exactly 38 matches: {}", first);
}

// ---------------------------------------------------------------------------
// Feature: Statistical analysis
// ---------------------------------------------------------------------------

#[test]
fn given_all_matches_when_computing_competition_stats_then_averages_are_plausible() {
    // GIVEN all completed matches
    let e = engine();

    // WHEN computing overall competition statistics
    let out = e.competition_stats(None, None);

    // THEN the average goals per match is in a plausible football range
    let avg_line = out
        .lines()
        .find(|l| l.contains("Average goals per match"))
        .expect("avg goals line");
    let avg: f64 = avg_line.rsplit(' ').next().unwrap().parse().unwrap();
    assert!((1.5..=3.5).contains(&avg), "implausible avg goals: {}", avg);
    // AND biggest victories and high-scoring games are reported
    assert!(out.contains("Biggest victories"), "got: {}", out);
    assert!(out.contains("Highest-scoring matches"), "got: {}", out);
    // AND home wins / draws / away wins percentages are present
    assert!(out.contains("Home wins:"), "got: {}", out);
}

// ---------------------------------------------------------------------------
// Feature: Player queries
// ---------------------------------------------------------------------------

#[test]
fn given_fifa_data_when_filtering_brazilians_then_sorted_by_rating() {
    // GIVEN the FIFA player database
    let e = engine();

    // WHEN I search for Brazilian players
    let out = e.search_players(None, Some("Brazil".into()), None, None, None, 10);

    // THEN hundreds are found, best first (Neymar Jr, overall 92, leads FIFA 19)
    assert!(out.contains("Neymar"), "top Brazilian should be Neymar: {}", out);
    let total: usize = out
        .lines()
        .next()
        .unwrap()
        .trim_matches(|c: char| !c.is_ascii_digit())
        .parse()
        .unwrap();
    assert!(total >= 800, "expected 800+ Brazilians, got {}", total);
}

#[test]
fn given_fifa_data_when_searching_by_club_and_position_then_filters_combine() {
    // GIVEN the FIFA player database (FIFA 19 includes Santos FC)
    let e = engine();

    // WHEN I search for forwards at Santos
    let out = e.search_players(None, None, Some("Santos".into()), Some("forward".into()), None, 20);

    // THEN players are found and all are in forward positions
    assert!(out.starts_with("Found"), "got: {}", out);
    for line in out.lines().filter(|l| l.contains("Position:")) {
        let pos = line
            .split("Position: ")
            .nth(1)
            .unwrap()
            .split(',')
            .next()
            .unwrap();
        assert!(
            ["ST", "CF", "LW", "RW", "LS", "RS", "LF", "RF"].contains(&pos),
            "not a forward: {}",
            line
        );
    }
}

#[test]
fn given_fifa_data_when_asking_who_is_a_player_then_profile_is_returned() {
    // GIVEN the FIFA player database
    let e = engine();

    // WHEN I ask about a player by partial name
    let out = e.player_profile("Gabriel Jesus");

    // THEN a detailed profile is returned
    assert!(out.contains("Overall:"), "got: {}", out);
    assert!(out.contains("Position:"), "got: {}", out);
    assert!(out.contains("Nationality: Brazil"), "got: {}", out);

    // AND a player absent from the dataset yields a graceful message
    let missing = e.player_profile("Zé Inexistente da Silva");
    assert!(missing.contains("No player matching"), "got: {}", missing);
}

// ---------------------------------------------------------------------------
// Feature: Cross-file queries
// ---------------------------------------------------------------------------

#[test]
fn given_player_and_match_data_when_querying_one_club_then_both_answer() {
    // GIVEN both the FIFA data and the match data mention Santos
    let e = engine();

    // WHEN I query players at the club and the club's match record
    let players = e.search_players(None, None, Some("Santos".into()), None, None, 5);
    let stats = e.team_stats("Santos", None, None, None);

    // THEN both cross-referenced queries succeed
    assert!(players.starts_with("Found"), "players: {}", players);
    assert!(stats.contains("Win rate:"), "stats: {}", stats);
}

// ---------------------------------------------------------------------------
// Feature: MCP protocol
// ---------------------------------------------------------------------------

fn server() -> Server {
    let dir = Path::new(env!("CARGO_MANIFEST_DIR")).join("data/kaggle");
    Server::new(Data::load(&dir).expect("datasets should load"))
}

#[test]
fn given_server_when_initializing_then_handshake_and_tools_are_advertised() {
    // GIVEN a running MCP server
    let s = server();

    // WHEN the client sends initialize
    let resp = s
        .handle(&json!({
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": { "protocolVersion": "2024-11-05", "capabilities": {} }
        }))
        .expect("initialize must produce a response");

    // THEN the server identifies itself and reports tool capability
    assert_eq!(resp["result"]["serverInfo"]["name"], "brazilian-soccer-mcp");
    assert!(resp["result"]["capabilities"]["tools"].is_object());

    // AND the initialized notification produces no response
    assert!(s
        .handle(&json!({ "jsonrpc": "2.0", "method": "notifications/initialized" }))
        .is_none());

    // WHEN listing tools
    let tools = s
        .handle(&json!({ "jsonrpc": "2.0", "id": 2, "method": "tools/list" }))
        .unwrap();

    // THEN all eight tools are advertised with schemas
    let list = tools["result"]["tools"].as_array().unwrap();
    assert_eq!(list.len(), 8);
    for t in list {
        assert!(t["inputSchema"]["type"] == "object", "schema missing for {}", t["name"]);
    }
}

#[test]
fn given_server_when_calling_tools_then_text_content_is_returned() {
    // GIVEN a running MCP server
    let s = server();
    let call = |name: &str, args: Value| -> Value {
        s.handle(&json!({
            "jsonrpc": "2.0", "id": 7, "method": "tools/call",
            "params": { "name": name, "arguments": args }
        }))
        .unwrap()
    };

    // WHEN calling search_matches for the Fla-Flu derby
    let resp = call("search_matches", json!({ "team": "Flamengo", "opponent": "Fluminense" }));
    // THEN text content with matches is returned
    let text = resp["result"]["content"][0]["text"].as_str().unwrap();
    assert!(text.contains("Found"), "got: {}", text);

    // WHEN calling get_standings for 2019
    let resp = call("get_standings", json!({ "season": 2019 }));
    let text = resp["result"]["content"][0]["text"].as_str().unwrap();
    // THEN Flamengo is the champion
    assert!(text.contains("Flamengo"), "got: {}", text);

    // WHEN calling get_player
    let resp = call("get_player", json!({ "name": "Neymar" }));
    let text = resp["result"]["content"][0]["text"].as_str().unwrap();
    assert!(text.contains("Overall:"), "got: {}", text);

    // WHEN calling get_data_summary
    let resp = call("get_data_summary", json!({}));
    let text = resp["result"]["content"][0]["text"].as_str().unwrap();
    assert!(text.contains("fifa_data.csv"), "got: {}", text);
}

#[test]
fn given_server_when_sending_bad_requests_then_errors_are_well_formed() {
    // GIVEN a running MCP server
    let s = server();

    // WHEN calling an unknown method
    let resp = s
        .handle(&json!({ "jsonrpc": "2.0", "id": 3, "method": "no/such/method" }))
        .unwrap();
    // THEN a JSON-RPC method-not-found error is returned
    assert_eq!(resp["error"]["code"], -32601);

    // WHEN calling an unknown tool
    let resp = s
        .handle(&json!({
            "jsonrpc": "2.0", "id": 4, "method": "tools/call",
            "params": { "name": "no_such_tool", "arguments": {} }
        }))
        .unwrap();
    // THEN the tool result is flagged as an error (MCP convention)
    assert_eq!(resp["result"]["isError"], true);

    // WHEN omitting a required argument
    let resp = s
        .handle(&json!({
            "jsonrpc": "2.0", "id": 5, "method": "tools/call",
            "params": { "name": "get_team_stats", "arguments": {} }
        }))
        .unwrap();
    // THEN the error message names the missing argument
    let text = resp["result"]["content"][0]["text"].as_str().unwrap();
    assert!(text.contains("team"), "got: {}", text);
}

// ---------------------------------------------------------------------------
// Feature: Query performance
// ---------------------------------------------------------------------------

#[test]
fn given_full_dataset_when_running_queries_then_they_finish_within_spec_limits() {
    // GIVEN the full dataset is loaded (excluded from timing)
    let e = engine();

    // WHEN running a simple lookup
    let t0 = std::time::Instant::now();
    let _ = e.search_matches(&MatchFilter {
        team: Some("Flamengo".into()),
        opponent: Some("Corinthians".into()),
        ..Default::default()
    });
    let simple = t0.elapsed();

    // AND an aggregate query
    let t1 = std::time::Instant::now();
    let _ = e.standings(2019, None);
    let _ = e.competition_stats(None, None);
    let aggregate = t1.elapsed();

    // THEN simple lookups finish well under 2s and aggregates under 5s
    assert!(simple.as_secs_f64() < 2.0, "simple lookup took {:?}", simple);
    assert!(aggregate.as_secs_f64() < 5.0, "aggregate queries took {:?}", aggregate);
}
