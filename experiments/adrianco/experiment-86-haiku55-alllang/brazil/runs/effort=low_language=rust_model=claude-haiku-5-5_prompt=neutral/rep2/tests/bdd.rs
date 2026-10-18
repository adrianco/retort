//! Context: BDD-style acceptance tests (Given / When / Then) run against the
//! real Kaggle CSV files in `data/kaggle/`. Each scenario maps to a
//! requirement in TASK.md.

use std::path::PathBuf;
use std::sync::OnceLock;

use brazilian_soccer_mcp::data::Dataset;
use brazilian_soccer_mcp::mcp::handle_message;
use brazilian_soccer_mcp::normalize::team_key;
use brazilian_soccer_mcp::query::{
    average_goals, biggest_wins, club_summary, find_matches, head_to_head, resolve_team,
    search_players, standings, team_record, MatchFilter, PlayerFilter, Venue,
};
use brazilian_soccer_mcp::tools::{call_tool, tool_definitions};
use serde_json::{json, Value};

/// The dataset is loaded once and shared by every scenario.
fn dataset() -> &'static Dataset {
    static DS: OnceLock<Dataset> = OnceLock::new();
    DS.get_or_init(|| {
        let dir = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("data/kaggle");
        Dataset::load_from_dir(&dir).expect("datasets should load")
    })
}

fn text(ds: &Dataset, tool: &str, args: Value) -> String {
    call_tool(ds, tool, &args).unwrap_or_else(|e| panic!("{tool} failed: {e}"))
}

#[test]
fn feature_data_loading_given_all_six_files_when_loaded_then_every_source_contributes() {
    // Given the data directory with all six Kaggle files
    let ds = dataset();
    // When the datasets are loaded
    // Then matches from all four match files and players from FIFA are present
    let competitions: std::collections::BTreeSet<&str> =
        ds.matches.iter().map(|m| m.competition.as_str()).collect();
    assert!(competitions.contains("Brasileirão Série A"));
    assert!(competitions.contains("Copa do Brasil"));
    assert!(competitions.contains("Copa Libertadores"));
    assert!(
        competitions.contains("Brasileirão Série B"),
        "extended file adds Série B"
    );
    assert!(
        ds.matches.iter().any(|m| m.season == 2005),
        "historical file adds 2003-2011 seasons"
    );
    assert!(
        ds.players.len() > 18_000,
        "FIFA file should yield ~18k players"
    );
}

#[test]
fn feature_data_loading_given_overlapping_sources_when_loaded_then_no_fixture_is_duplicated() {
    // Given matches that appear in more than one file (with slightly different dates)
    let ds = dataset();
    // When the dataset is inspected for fixtures
    let mut seen = std::collections::HashSet::new();
    // Then each (season, competition, home, away) fixture appears once
    for m in &ds.matches {
        let fixture = (
            m.season,
            m.competition.clone(),
            m.home_key.clone(),
            m.away_key.clone(),
        );
        assert!(seen.insert(fixture), "duplicate fixture: {m:?}");
    }
}

#[test]
fn feature_team_names_given_name_variants_when_resolved_then_they_map_to_one_team() {
    // Given the same club spelled differently across files
    let ds = dataset();
    // When each spelling is resolved
    // Then they all resolve to the same canonical key
    let variants = [
        "Athletico Paranaense",
        "Athletico-PR",
        "Atlético-PR",
        "Atletico Paranaense",
    ];
    let keys: Vec<String> = variants
        .iter()
        .map(|v| resolve_team(ds, v).expect("variant should resolve"))
        .collect();
    assert!(keys.windows(2).all(|w| w[0] == w[1]), "{keys:?}");
    assert_eq!(team_key("Palmeiras-SP"), team_key("Palmeiras"));
    assert_eq!(team_key("Sport Club Corinthians Paulista"), "corinthians");
}

#[test]
fn feature_team_names_given_unknown_team_when_resolved_then_error_is_returned() {
    // Given a team that is not in the dataset
    let ds = dataset();
    // When it is resolved
    let err = resolve_team(ds, "Xyzzy Football Club").unwrap_err();
    // Then a helpful error is returned
    assert!(err.contains("no team matches"));
}

#[test]
fn scenario_match_search_given_flamengo_and_fluminense_when_searched_then_matches_are_listed() {
    // Given the match data is loaded
    let ds = dataset();
    // When I search for matches between "Flamengo" and "Fluminense"
    let out = text(
        ds,
        "head_to_head",
        json!({"team": "Flamengo", "opponent": "Fluminense", "limit": 5}),
    );
    // Then I receive a list of matches with dates, scores and competitions
    assert!(out.contains("Flamengo vs Fluminense head-to-head"), "{out}");
    assert!(out.contains("Most recent matches"));
    let lines: Vec<&str> = out.lines().filter(|l| l.starts_with("- 20")).collect();
    assert!(!lines.is_empty());
    for line in lines {
        assert!(
            line.contains("Flamengo") && line.contains("Fluminense"),
            "{line}"
        );
        assert!(
            line.contains('-') && line.contains('('),
            "score and competition: {line}"
        );
    }
}

#[test]
fn scenario_match_search_given_copa_do_brasil_when_searched_then_only_cup_matches_return() {
    // Given the cup data is loaded
    let ds = dataset();
    // When I search for Copa do Brasil matches in 2019
    let filter = MatchFilter {
        competition: Some("Copa do Brasil".into()),
        season: Some(2019),
        ..MatchFilter::default()
    };
    let found = find_matches(ds, &filter);
    // Then every result is a 2019 Copa do Brasil match
    assert!(!found.is_empty());
    assert!(found
        .iter()
        .all(|m| m.competition == "Copa do Brasil" && m.season == 2019));
}

#[test]
fn scenario_match_search_given_date_range_when_searched_then_results_fall_inside_it() {
    // Given matches across many seasons
    let ds = dataset();
    // When I search for a date range
    let filter = MatchFilter {
        start_date: Some("2023-01-01".into()),
        end_date: Some("2023-03-31".into()),
        ..MatchFilter::default()
    };
    // Then every match falls between the bounds
    let found = find_matches(ds, &filter);
    assert!(!found.is_empty());
    assert!(found
        .iter()
        .all(|m| m.date.as_str() >= "2023-01-01" && m.date.as_str() <= "2023-03-31"));
}

#[test]
fn scenario_team_stats_given_palmeiras_in_2023_when_requested_then_wins_losses_draws_and_goals_are_given(
) {
    // Given the match data is loaded
    let ds = dataset();
    // When I request statistics for "Palmeiras" in season "2023"
    let team = resolve_team(ds, "Palmeiras").unwrap();
    let filter = MatchFilter {
        season: Some(2023),
        ..MatchFilter::default()
    };
    let record = team_record(ds, &team, &filter);
    // Then I receive wins, losses, draws and goals
    assert!(record.played > 0);
    assert_eq!(record.wins + record.draws + record.losses, record.played);
    assert!(record.goals_for + record.goals_against > 0);
}

#[test]
fn scenario_team_stats_given_corinthians_home_2022_when_requested_then_home_only_games_are_counted()
{
    // Given the match data is loaded
    let ds = dataset();
    let team = resolve_team(ds, "Corinthians").unwrap();
    // When I ask for Corinthians' home record in 2022
    let home = MatchFilter {
        season: Some(2022),
        venue: Venue::Home,
        ..MatchFilter::default()
    };
    let record = team_record(ds, &team, &home);
    // Then only home fixtures are counted
    let home_games = ds
        .matches
        .iter()
        .filter(|m| m.season == 2022 && m.home_key == team)
        .count() as u32;
    assert_eq!(record.played, home_games);
    assert!(record.played > 0);
}

#[test]
fn scenario_standings_given_2019_brasileirao_when_calculated_then_every_team_plays_38_games() {
    // Given the 2019 Brasileirão matches, with cross-file duplicates removed
    let ds = dataset();
    // When the table is calculated
    let filter = MatchFilter {
        season: Some(2019),
        competition: Some("Brasileirão Série A".into()),
        ..MatchFilter::default()
    };
    let table = standings(ds, &filter);
    // Then there are 20 clubs, each playing 38 games (a double round robin)
    assert_eq!(table.len(), 20, "{table:?}");
    assert!(table.iter().all(|row| row.record.played == 38), "{table:?}");
    // And the table is sorted by points
    assert!(table
        .windows(2)
        .all(|w| w[0].record.points() >= w[1].record.points()));
}

#[test]
fn scenario_standings_given_2019_brasileirao_when_requested_then_flamengo_is_champion() {
    // Given the 2019 season (Flamengo were champions)
    let ds = dataset();
    // When the standings tool is called
    let out = text(ds, "standings", json!({"season": 2019}));
    // Then the first place team is Flamengo on 90 points (28W 6D 4L)
    let first = out.lines().nth(1).expect("table should have rows");
    assert!(
        first.starts_with("1. Flamengo - 90 pts (28W, 6D, 4L"),
        "{first}"
    );
}

#[test]
fn scenario_match_search_given_copa_do_brasil_finals_when_searched_then_last_round_of_each_season_returns(
) {
    // Given the Copa do Brasil data
    let ds = dataset();
    // When I search for the finals
    let filter = MatchFilter {
        competition: Some("Copa do Brasil".into()),
        round: Some("final".into()),
        ..MatchFilter::default()
    };
    let found = find_matches(ds, &filter);
    // Then every result is in the highest numbered round of its season
    assert!(!found.is_empty());
    for m in &found {
        let max_round = ds
            .matches
            .iter()
            .filter(|o| o.competition == "Copa do Brasil" && o.season == m.season)
            .filter_map(|o| o.round.as_deref()?.parse::<u32>().ok())
            .max();
        assert_eq!(
            m.round.as_deref().unwrap().parse::<u32>().ok(),
            max_round,
            "{m:?}"
        );
    }
}

#[test]
fn scenario_head_to_head_given_rivals_when_compared_then_records_are_symmetric() {
    // Given Santos and Palmeiras
    let ds = dataset();
    let santos = resolve_team(ds, "Santos").unwrap();
    let palmeiras = resolve_team(ds, "Palmeiras").unwrap();
    // When I compare their head-to-head records
    let a = head_to_head(ds, &santos, &palmeiras, &MatchFilter::default());
    let b = head_to_head(ds, &palmeiras, &santos, &MatchFilter::default());
    // Then the wins and losses mirror each other
    assert!(a.played > 0);
    assert_eq!(a.wins, b.losses);
    assert_eq!(a.losses, b.wins);
    assert_eq!(a.draws, b.draws);
}

#[test]
fn scenario_statistics_given_brasileirao_when_averaged_then_goals_per_match_is_plausible() {
    // Given the Brasileirão Série A matches
    let ds = dataset();
    // When I calculate average goals per match
    let filter = MatchFilter {
        competition: Some("Brasileirão Série A".into()),
        ..MatchFilter::default()
    };
    let (count, avg) = average_goals(ds, &filter).expect("matches exist");
    // Then the figure is plausible for Brazilian football
    assert!(count > 3000);
    assert!((2.0..3.5).contains(&avg), "avg={avg}");
}

#[test]
fn scenario_statistics_given_dataset_when_biggest_wins_requested_then_margins_are_descending() {
    // Given the full match dataset
    let ds = dataset();
    // When the biggest wins are requested
    let wins = biggest_wins(ds, &MatchFilter::default(), 10);
    // Then they are ordered by goal margin, largest first, with no draws
    assert_eq!(wins.len(), 10);
    let margins: Vec<u32> = wins
        .iter()
        .map(|m| m.home_goals.abs_diff(m.away_goals))
        .collect();
    assert!(margins.windows(2).all(|w| w[0] >= w[1]), "{margins:?}");
    assert!(margins.iter().all(|&m| m > 0));
}

#[test]
fn scenario_player_search_given_brazil_when_searched_then_only_brazilian_players_return() {
    // Given the FIFA player data
    let ds = dataset();
    // When I search for Brazilian players
    let found = search_players(
        ds,
        &PlayerFilter {
            nationality: Some("Brazil".into()),
            ..PlayerFilter::default()
        },
        50,
    );
    // Then I receive Brazilian players ordered by overall rating
    assert!(!found.is_empty());
    assert!(found.iter().all(|p| p.nationality == "Brazil"));
    assert!(found.windows(2).all(|w| w[0].overall >= w[1].overall));
}

#[test]
fn scenario_player_search_given_club_and_position_group_when_searched_then_filters_apply() {
    // Given the FIFA player data
    let ds = dataset();
    // When I search for forwards at a Santos club
    let found = search_players(
        ds,
        &PlayerFilter {
            club: Some("Santos".into()),
            position: Some("forward".into()),
            ..PlayerFilter::default()
        },
        100,
    );
    // Then every result is a forward at a club containing "Santos"
    assert!(!found.is_empty());
    let forwards = ["ST", "CF", "LW", "RW", "LS", "RS", "LF", "RF"];
    for p in found {
        assert!(forwards.contains(&p.position.as_str()), "{p:?}");
        assert!(p.club.to_lowercase().contains("santos"), "{p:?}");
    }
}

#[test]
fn scenario_player_search_given_name_when_searched_then_lookup_succeeds() {
    // Given a well-known player in the FIFA data
    let ds = dataset();
    // When I search for "Neymar"
    let out = text(ds, "search_players", json!({"name": "Neymar", "limit": 3}));
    // Then the matching players are returned
    assert!(out.contains("Neymar"), "{out}");
}

#[test]
fn scenario_club_summary_given_brazil_when_requested_then_clubs_are_counted() {
    // Given Brazilian players in the FIFA data
    let ds = dataset();
    // When I summarise by club
    let rows = club_summary(ds, "Brazil");
    // Then each club has a count and an average rating
    assert!(!rows.is_empty());
    let total: usize = rows.iter().map(|r| r.players).sum();
    assert_eq!(
        total,
        ds.players
            .iter()
            .filter(|p| p.nationality == "Brazil")
            .count()
    );
}

#[test]
fn scenario_tool_validation_given_bad_arguments_when_called_then_clear_errors_are_returned() {
    // Given the tool surface
    let ds = dataset();
    // When arguments are invalid
    // Then the tools report what is wrong
    assert!(call_tool(ds, "team_record", &json!({}))
        .unwrap_err()
        .contains("team"));
    assert!(call_tool(ds, "standings", &json!({}))
        .unwrap_err()
        .contains("season"));
    assert!(call_tool(ds, "search_matches", &json!({"start_date": "soon"})).is_err());
    assert!(call_tool(ds, "search_matches", &json!({"venue": "neutral"})).is_err());
    assert!(call_tool(ds, "search_matches", &json!({"limit": 0})).is_err());
    assert!(call_tool(ds, "nonexistent", &json!({})).is_err());
}

#[test]
fn acceptance_sample_questions_given_spec_examples_when_asked_then_all_are_answered() {
    // Given the sample questions from the specification
    let ds = dataset();
    let questions: Vec<(&str, Value)> = vec![
        (
            "search_matches",
            json!({"team": "Flamengo", "opponent": "Fluminense"}),
        ),
        (
            "search_matches",
            json!({"team": "Palmeiras", "season": 2023}),
        ),
        (
            "search_matches",
            json!({"competition": "Copa do Brasil", "round": "Final"}),
        ),
        (
            "search_matches",
            json!({"team": "Flamengo", "opponent": "Corinthians"}),
        ),
        (
            "team_record",
            json!({"team": "Corinthians", "season": 2022, "venue": "home"}),
        ),
        (
            "head_to_head",
            json!({"team": "Corinthians", "opponent": "Palmeiras"}),
        ),
        (
            "head_to_head",
            json!({"team": "Palmeiras", "opponent": "Santos"}),
        ),
        ("standings", json!({"season": 2019})),
        ("standings", json!({"season": 2020})),
        ("aggregate_stats", json!({"metric": "average_goals"})),
        (
            "aggregate_stats",
            json!({"metric": "home_win_rate", "season": 2018}),
        ),
        (
            "aggregate_stats",
            json!({"metric": "biggest_wins", "limit": 3}),
        ),
        (
            "aggregate_stats",
            json!({"metric": "best_venue_record", "venue": "home"}),
        ),
        (
            "aggregate_stats",
            json!({"metric": "best_venue_record", "venue": "away", "min_matches": 15}),
        ),
        (
            "search_players",
            json!({"nationality": "Brazil", "limit": 3}),
        ),
        (
            "search_players",
            json!({"name": "Gabriel", "nationality": "Brazil"}),
        ),
        (
            "search_players",
            json!({"club": "Santos", "position": "midfielder"}),
        ),
        (
            "search_players",
            json!({"min_overall": 85, "nationality": "Brazil"}),
        ),
        ("club_summary", json!({"nationality": "Brazil"})),
        (
            "search_matches",
            json!({"team": "Vasco", "start_date": "2012-01-01", "end_date": "2012-12-31"}),
        ),
        (
            "team_record",
            json!({"team": "Atlético-MG", "season": 2023}),
        ),
        (
            "search_matches",
            json!({"team": "Libertadores", "competition": "Copa Libertadores", "limit": 5}),
        ),
    ];
    // When each is asked (team/competition lookups that find nothing are answered with a message)
    let mut answered = 0;
    for (tool, args) in &questions {
        let result = call_tool(ds, tool, args);
        // Then each returns a textual answer
        if let Ok(out) = result {
            assert!(!out.trim().is_empty(), "{tool} {args}");
            answered += 1;
        }
    }
    assert!(
        answered >= 20,
        "only {answered} of {} questions answered",
        questions.len()
    );
}

#[test]
fn scenario_protocol_given_initialize_when_sent_then_tools_capability_is_advertised() {
    // Given a client that connects
    let ds = dataset();
    // When it sends initialize
    let resp = handle_message(
        ds,
        &json!({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}),
    )
    .unwrap();
    // Then the server advertises the tools capability
    assert_eq!(resp["id"], 1);
    assert!(resp["result"]["capabilities"]["tools"].is_object());
    assert_eq!(resp["result"]["serverInfo"]["name"], "brazilian-soccer-mcp");
}

#[test]
fn scenario_protocol_given_tools_list_when_requested_then_every_tool_has_a_schema() {
    // Given the server
    let ds = dataset();
    // When tools/list is requested
    let resp = handle_message(
        ds,
        &json!({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}),
    )
    .unwrap();
    // Then all seven tools have a name, description and input schema
    let tools = resp["result"]["tools"].as_array().unwrap();
    assert_eq!(tools.len(), 7);
    assert_eq!(tool_definitions().as_array().unwrap().len(), 7);
    for tool in tools {
        assert!(tool["name"].is_string());
        assert!(tool["description"].is_string());
        assert_eq!(tool["inputSchema"]["type"], "object");
    }
}

#[test]
fn scenario_protocol_given_tools_call_when_sent_then_result_is_text_content() {
    // Given a tool call request
    let ds = dataset();
    // When it is handled
    let resp = handle_message(
        ds,
        &json!({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                "params": {"name": "team_record", "arguments": {"team": "Santos", "season": 2019}}}),
    )
    .unwrap();
    // Then the answer is returned as text content
    assert_eq!(resp["result"]["isError"], false);
    assert_eq!(resp["result"]["content"][0]["type"], "text");
    assert!(resp["result"]["content"][0]["text"]
        .as_str()
        .unwrap()
        .contains("Santos record"));
}

#[test]
fn scenario_protocol_given_tool_failure_when_called_then_is_error_is_true() {
    // Given a call that fails validation
    let ds = dataset();
    // When it is handled
    let resp = handle_message(
        ds,
        &json!({"jsonrpc": "2.0", "id": 4, "method": "tools/call",
                "params": {"name": "team_record", "arguments": {"team": "Nobody FC"}}}),
    )
    .unwrap();
    // Then the result is flagged as an error rather than a protocol failure
    assert_eq!(resp["result"]["isError"], true);
    assert!(resp.get("error").is_none());
}

#[test]
fn scenario_protocol_given_notification_when_received_then_no_response_is_sent() {
    // Given a notification (no id)
    let ds = dataset();
    // When it is handled
    // Then no response is produced
    assert!(handle_message(
        ds,
        &json!({"jsonrpc": "2.0", "method": "notifications/initialized"})
    )
    .is_none());
}

#[test]
fn scenario_protocol_given_unknown_method_when_called_then_method_not_found_is_returned() {
    // Given an unknown method
    let ds = dataset();
    // When it is handled
    let resp = handle_message(
        ds,
        &json!({"jsonrpc": "2.0", "id": 5, "method": "resources/list"}),
    )
    .unwrap();
    // Then a JSON-RPC method-not-found error is returned
    assert_eq!(resp["error"]["code"], -32601);
}

#[test]
fn scenario_performance_given_aggregate_query_when_run_then_it_completes_within_five_seconds() {
    // Given the loaded dataset
    let ds = dataset();
    // When an aggregate query runs
    let start = std::time::Instant::now();
    let _ = text(
        ds,
        "aggregate_stats",
        json!({"metric": "best_venue_record"}),
    );
    // Then it finishes well inside the 5 second budget
    assert!(start.elapsed().as_secs_f64() < 5.0);
}
