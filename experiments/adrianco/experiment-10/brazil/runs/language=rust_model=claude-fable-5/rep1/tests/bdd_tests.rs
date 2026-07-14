//! BDD-style integration tests against the real datasets, following the
//! Gherkin scenarios from the specification.
//!
//! Each test is written as Given / When / Then over the loaded store.

use std::path::Path;
use std::sync::OnceLock;

use brazilian_soccer_mcp::data::{Store, COPA_DO_BRASIL, LIBERTADORES};
use brazilian_soccer_mcp::mcp;
use brazilian_soccer_mcp::query::{self, MatchFilter, PlayerFilter};
use serde_json::json;

fn store() -> &'static Store {
    static STORE: OnceLock<Store> = OnceLock::new();
    STORE.get_or_init(|| {
        Store::load(Path::new(env!("CARGO_MANIFEST_DIR")).join("data/kaggle").as_path())
            .expect("datasets must load")
    })
}

// Feature: Data loading

#[test]
fn scenario_all_six_csv_files_are_loadable() {
    // Given the data directory
    let s = store();
    // Then every source file is loaded with the expected row count
    let counts: std::collections::HashMap<_, _> = s.raw_counts.iter().cloned().collect();
    assert_eq!(counts["Brasileirao_Matches.csv"], 4180);
    assert_eq!(counts["Brazilian_Cup_Matches.csv"], 1337);
    assert_eq!(counts["Libertadores_Matches.csv"], 1255);
    assert_eq!(counts["novo_campeonato_brasileiro.csv"], 6886);
    assert_eq!(counts["BR-Football-Dataset.csv"], 10296);
    assert_eq!(s.players.len(), 18207);
    // And overlapping fixtures are deduplicated
    assert!(s.matches.len() < 4180 + 1337 + 1255 + 6886 + 10296);
    assert!(s.matches.len() > 15_000);
}

#[test]
fn scenario_utf8_team_names_survive_loading() {
    // Given the match data is loaded
    let s = store();
    // Then accented team names are queryable both with and without accents
    for query_name in ["São Paulo", "Sao Paulo", "Grêmio", "Gremio", "Avaí"] {
        let filter = MatchFilter {
            team: Some(query_name.to_string()),
            ..Default::default()
        };
        assert!(
            !query::find_matches(s, &filter).is_empty(),
            "no matches found for {query_name}"
        );
    }
}

// Feature: Match Queries

#[test]
fn scenario_find_matches_between_two_teams() {
    // Given the match data is loaded
    let s = store();
    // When I search for matches between "Flamengo" and "Fluminense"
    let filter = MatchFilter {
        team: Some("Flamengo".into()),
        opponent: Some("Fluminense".into()),
        ..Default::default()
    };
    let matches = query::find_matches(s, &filter);
    // Then I should receive a list of matches
    assert!(matches.len() >= 20, "expected many Fla-Flu derbies, got {}", matches.len());
    // And each match should have date, scores, and competition
    for m in &matches {
        assert!(m.date.is_some(), "match missing date");
        assert!(m.home_goals >= 0 && m.away_goals >= 0);
        assert!(!m.competition.is_empty());
        // And both teams really are Flamengo and Fluminense
        let keys = [m.home_key.as_str(), m.away_key.as_str()];
        assert!(keys.contains(&"flamengo") && keys.contains(&"fluminense"));
    }
}

#[test]
fn scenario_find_matches_by_team_and_season() {
    // Given the match data is loaded
    let s = store();
    // When I search for Palmeiras matches in 2023
    let filter = MatchFilter {
        team: Some("Palmeiras".into()),
        season: Some(2023),
        ..Default::default()
    };
    let matches = query::find_matches(s, &filter);
    // Then I get their 2023 fixtures, all featuring Palmeiras
    assert!(matches.len() >= 38, "expected at least a full league season");
    for m in &matches {
        assert_eq!(m.season, 2023);
        assert!(m.home_key == "palmeiras" || m.away_key == "palmeiras");
    }
}

#[test]
fn scenario_find_copa_do_brasil_finals() {
    // Given the match data is loaded
    let s = store();
    // When I search Copa do Brasil matches at the "final" stage
    let filter = MatchFilter {
        competition: Some("Copa do Brasil".into()),
        stage: Some("final".into()),
        ..Default::default()
    };
    let matches = query::find_matches(s, &filter);
    // Then the last round of each cup season is returned
    assert!(!matches.is_empty());
    for m in &matches {
        assert_eq!(m.competition, COPA_DO_BRASIL);
        assert_eq!(m.stage.as_deref(), Some("Final"));
    }
}

#[test]
fn scenario_find_matches_by_date_range() {
    // Given the match data is loaded
    let s = store();
    // When I search for matches in May 2019
    let filter = MatchFilter {
        date_from: chrono::NaiveDate::from_ymd_opt(2019, 5, 1),
        date_to: chrono::NaiveDate::from_ymd_opt(2019, 5, 31),
        ..Default::default()
    };
    let matches = query::find_matches(s, &filter);
    // Then every match falls inside the range
    assert!(!matches.is_empty());
    for m in &matches {
        let d = m.date.unwrap();
        assert!(d >= filter.date_from.unwrap() && d <= filter.date_to.unwrap());
    }
}

#[test]
fn scenario_libertadores_stages_are_preserved() {
    // Given the match data is loaded
    let s = store();
    // When I search for Libertadores finals
    let filter = MatchFilter {
        competition: Some("Libertadores".into()),
        stage: Some("final".into()),
        ..Default::default()
    };
    let matches = query::find_matches(s, &filter);
    // Then knockout finals are present
    assert!(!matches.is_empty());
    assert!(matches.iter().all(|m| m.competition == LIBERTADORES));
}

// Feature: Team statistics

#[test]
fn scenario_get_team_statistics() {
    // Given the match data is loaded
    let s = store();
    // When I request statistics for "Palmeiras" in season "2023"
    let filter = MatchFilter {
        team: Some("Palmeiras".into()),
        season: Some(2023),
        competition: Some("Serie A".into()),
        ..Default::default()
    };
    let matches = query::find_matches(s, &filter);
    let rec = query::team_record(&matches, "palmeiras", "all");
    // Then I should receive wins, losses, draws, and goals
    // (the 2023 source file is missing the last 3 fixtures of the season,
    // so 37 of Palmeiras' 38 matches are present)
    assert!(rec.played >= 37, "got {} matches", rec.played);
    assert_eq!(rec.wins + rec.draws + rec.losses, rec.played);
    assert!(rec.goals_for > 0 && rec.goals_against > 0);
    assert!(rec.points() >= 67);
}

#[test]
fn scenario_full_season_team_statistics_2022() {
    // Given the match data is loaded
    let s = store();
    // When I request Palmeiras' record for the complete 2022 Série A season
    let filter = MatchFilter {
        team: Some("Palmeiras".into()),
        season: Some(2022),
        competition: Some("Serie A".into()),
        ..Default::default()
    };
    let matches = query::find_matches(s, &filter);
    let rec = query::team_record(&matches, "palmeiras", "all");
    // Then the championship-winning record matches the real table:
    // 81 points from 23 wins, 12 draws, 3 losses
    assert_eq!(rec.played, 38);
    assert_eq!(rec.points(), 81);
    assert_eq!((rec.wins, rec.draws, rec.losses), (23, 12, 3));
    // And the calculated standings crown Palmeiras champions
    let rows = query::standings(s, 2022);
    assert_eq!(rows[0].team, "Palmeiras");
    assert!(rows.iter().all(|r| r.rec.played == 38));
}

#[test]
fn scenario_home_record_counts_only_home_matches() {
    // Given the match data is loaded
    let s = store();
    // When I request Corinthians' home record for the 2022 Série A
    let filter = MatchFilter {
        team: Some("Corinthians".into()),
        season: Some(2022),
        competition: Some("Serie A".into()),
        ..Default::default()
    };
    let matches = query::find_matches(s, &filter);
    let home = query::team_record(&matches, "corinthians", "home");
    let away = query::team_record(&matches, "corinthians", "away");
    // Then home and away each cover half of a 38-game season
    assert_eq!(home.played, 19);
    assert_eq!(away.played, 19);
}

#[test]
fn scenario_head_to_head_summary() {
    // Given the match data is loaded
    let s = store();
    // When I compare Palmeiras and Santos head-to-head
    let text = query::head_to_head(s, "Palmeiras", "Santos", None);
    // Then I get a win/draw summary plus recent matches
    assert!(text.contains("wins"), "summary missing win counts: {text}");
    assert!(text.contains("draws"));
    assert!(text.contains("Most recent matches:"));
}

// Feature: Competition queries

#[test]
fn scenario_2019_standings_match_the_real_table() {
    // Given the match data is loaded
    let s = store();
    // When I calculate the 2019 Brasileirão standings
    let rows = query::standings(s, 2019);
    // Then there are 20 teams playing 38 matches each
    assert_eq!(rows.len(), 20);
    assert!(rows.iter().all(|r| r.rec.played == 38));
    // And Flamengo are champions with 90 points (28W 6D 4L)
    assert_eq!(rows[0].team, "Flamengo");
    assert_eq!(rows[0].rec.points(), 90);
    assert_eq!(rows[0].rec.wins, 28);
    assert_eq!(rows[0].rec.draws, 6);
    assert_eq!(rows[0].rec.losses, 4);
}

#[test]
fn scenario_historical_standings_from_pre_2012_file() {
    // Given seasons only covered by novo_campeonato_brasileiro.csv
    let s = store();
    // When I calculate the 2009 standings
    let rows = query::standings(s, 2009);
    // Then Flamengo are champions of a 20-team league
    assert_eq!(rows.len(), 20);
    assert_eq!(rows[0].team, "Flamengo");
    assert_eq!(rows[0].rec.points(), 67);
}

// Feature: Player Queries

#[test]
fn scenario_search_players_by_name() {
    // Given the player data is loaded
    let s = store();
    // When I search for "Neymar"
    let filter = PlayerFilter {
        name: Some("Neymar".into()),
        ..Default::default()
    };
    let players = query::find_players(s, &filter, "overall");
    // Then Neymar Jr is found with his FIFA profile
    assert!(!players.is_empty());
    assert_eq!(players[0].name, "Neymar Jr");
    assert_eq!(players[0].nationality, "Brazil");
    assert!(players[0].overall >= 90);
}

#[test]
fn scenario_filter_brazilian_players() {
    // Given the player data is loaded
    let s = store();
    // When I filter players by nationality Brazil
    let filter = PlayerFilter {
        nationality: Some("Brazil".into()),
        ..Default::default()
    };
    let players = query::find_players(s, &filter, "overall");
    // Then hundreds of Brazilians are returned, best-rated first
    assert_eq!(players.len(), 827);
    assert!(players.windows(2).all(|w| w[0].overall >= w[1].overall));
    assert!(players.iter().all(|p| p.nationality == "Brazil"));
}

#[test]
fn scenario_filter_players_by_club_with_accents() {
    // Given the player data is loaded
    let s = store();
    // When I search clubs by an unaccented name
    let filter = PlayerFilter {
        club: Some("Gremio".into()),
        ..Default::default()
    };
    let players = query::find_players(s, &filter, "overall");
    // Then the accented club "Grêmio" is still matched
    assert!(!players.is_empty());
    assert!(players.iter().all(|p| p.club.contains("Grêmio")));
}

#[test]
fn scenario_filter_forwards_by_position_group() {
    // Given the player data is loaded
    let s = store();
    // When I ask for "forward" as a position group
    let filter = PlayerFilter {
        position: Some("forward".into()),
        nationality: Some("Brazil".into()),
        ..Default::default()
    };
    let players = query::find_players(s, &filter, "overall");
    // Then only attacking positions are returned
    assert!(!players.is_empty());
    let fw = ["ST", "CF", "LF", "RF", "LW", "RW", "LS", "RS"];
    assert!(players.iter().all(|p| fw.contains(&p.position.as_str())));
}

// Feature: MCP protocol

#[test]
fn scenario_initialize_handshake() {
    // Given a running server
    let s = store();
    // When the client sends initialize
    let resp = mcp::handle_message(
        s,
        &json!({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}),
    )
    .unwrap();
    // Then the server reports protocol version and tool capability
    assert_eq!(resp["result"]["protocolVersion"], mcp::PROTOCOL_VERSION);
    assert_eq!(resp["result"]["serverInfo"]["name"], mcp::SERVER_NAME);
    assert!(resp["result"]["capabilities"]["tools"].is_object());
}

#[test]
fn scenario_tools_list_returns_all_tools() {
    // Given a running server
    let s = store();
    // When the client lists tools
    let resp = mcp::handle_message(
        s,
        &json!({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}),
    )
    .unwrap();
    // Then all nine tools are advertised with schemas
    let tools = resp["result"]["tools"].as_array().unwrap();
    assert_eq!(tools.len(), 9);
    for t in tools {
        assert!(t["name"].is_string());
        assert!(t["description"].is_string());
        assert_eq!(t["inputSchema"]["type"], "object");
    }
}

#[test]
fn scenario_tools_call_returns_text_content() {
    // Given a running server
    let s = store();
    // When the client calls search_matches over the wire format
    let resp = mcp::handle_message(
        s,
        &json!({
            "jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {"name": "search_matches",
                        "arguments": {"team": "Flamengo", "opponent": "Fluminense"}}
        }),
    )
    .unwrap();
    // Then the result is MCP text content
    assert_eq!(resp["result"]["isError"], false);
    let text = resp["result"]["content"][0]["text"].as_str().unwrap();
    assert!(text.contains("Flamengo"));
    assert!(text.contains("Fluminense"));
}

#[test]
fn scenario_unknown_tool_is_a_tool_error() {
    // Given a running server
    let s = store();
    // When the client calls a tool that does not exist
    let resp = mcp::handle_message(
        s,
        &json!({
            "jsonrpc": "2.0", "id": 4, "method": "tools/call",
            "params": {"name": "no_such_tool", "arguments": {}}
        }),
    )
    .unwrap();
    // Then the call returns an in-band tool error, not a protocol error
    assert_eq!(resp["result"]["isError"], true);
}

#[test]
fn scenario_unknown_method_is_method_not_found() {
    let s = store();
    let resp = mcp::handle_message(
        s,
        &json!({"jsonrpc": "2.0", "id": 5, "method": "bogus/method"}),
    )
    .unwrap();
    assert_eq!(resp["error"]["code"], -32601);
}

#[test]
fn scenario_notifications_get_no_response() {
    let s = store();
    let resp = mcp::handle_message(
        s,
        &json!({"jsonrpc": "2.0", "method": "notifications/initialized"}),
    );
    assert!(resp.is_none());
}

// Feature: Performance

#[test]
fn scenario_aggregate_queries_are_fast() {
    // Given the data is loaded (loading time excluded; the server loads once)
    let s = store();
    let start = std::time::Instant::now();
    // When I run a simple lookup and several aggregate queries
    let _ = query::find_matches(
        s,
        &MatchFilter {
            team: Some("Flamengo".into()),
            opponent: Some("Corinthians".into()),
            ..Default::default()
        },
    );
    let _ = query::standings(s, 2019);
    let _ = query::competition_overview(s, Some("Brasileirão"), None);
    let _ = query::biggest_wins(s, None, None, 10);
    // Then they all complete well within the 5 second budget
    assert!(
        start.elapsed() < std::time::Duration::from_secs(5),
        "aggregate queries took {:?}",
        start.elapsed()
    );
}

// Feature: Cross-file queries

#[test]
fn scenario_cross_file_player_and_match_data() {
    // Given both player and match data are loaded
    let s = store();
    // When I look up a club in the FIFA data and in the match data
    let players = query::find_players(
        s,
        &PlayerFilter {
            club: Some("Santos".into()),
            ..Default::default()
        },
        "overall",
    );
    let santos_players: Vec<_> = players.iter().filter(|p| p.club == "Santos").collect();
    let matches = query::find_matches(
        s,
        &MatchFilter {
            team: Some("Santos".into()),
            season: Some(2019),
            competition: Some("Serie A".into()),
            ..Default::default()
        },
    );
    // Then both sides of the join return data
    assert!(!santos_players.is_empty(), "FIFA data has Santos players");
    assert_eq!(matches.len(), 38, "match data has Santos' 2019 season");
}

#[test]
fn scenario_serie_a_history_spans_2003_to_2023() {
    // Given the merged Série A data
    let s = store();
    // Then every season from 2003 to 2023 is queryable
    for season in 2003..=2023 {
        let rows = query::standings(s, season);
        assert!(
            rows.len() >= 20,
            "season {} has only {} teams",
            season,
            rows.len()
        );
    }
}
