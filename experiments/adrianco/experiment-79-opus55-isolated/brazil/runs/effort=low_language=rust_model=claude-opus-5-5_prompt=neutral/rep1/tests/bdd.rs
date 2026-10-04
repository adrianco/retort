//! Behaviour scenarios (Given / When / Then) run against the real CSV files in
//! `data/kaggle`, covering the sample questions of the specification.

use brazilian_soccer_mcp::data::{find_data_dir, Competition, Database, Source};
use brazilian_soccer_mcp::mcp::{call_tool, handle_message, serve, tool_definitions};
use brazilian_soccer_mcp::queries::{MatchFilter, PlayerFilter, Venue};
use serde_json::{json, Value};
use std::sync::OnceLock;
use std::time::Instant;

/// Given the match and player data is loaded
fn given_data() -> &'static Database {
    static DB: OnceLock<Database> = OnceLock::new();
    DB.get_or_init(|| Database::load(&find_data_dir(None).unwrap()).unwrap())
}

/// When I call a tool
fn when(tool: &str, args: Value) -> String {
    call_tool(given_data(), tool, &args).unwrap_or_else(|e| panic!("{tool} failed: {e}"))
}

// ------------------------------------------------------------ data coverage

#[test]
fn scenario_all_six_csv_files_are_loaded() {
    let db = given_data();
    let rows: Vec<(&str, usize)> = db.file_rows.clone();
    assert_eq!(
        rows,
        vec![
            ("Brasileirao_Matches.csv", 4180),
            ("Brazilian_Cup_Matches.csv", 1337),
            ("Libertadores_Matches.csv", 1255),
            ("BR-Football-Dataset.csv", 10296),
            ("novo_campeonato_brasileiro.csv", 6886),
            ("fifa_data.csv", 18207),
        ]
    );
    assert_eq!(db.players.len(), 18207);
}

#[test]
fn scenario_every_match_file_is_queryable_by_source() {
    let db = given_data();
    for s in Source::ALL {
        let f = MatchFilter { team: Some("Palmeiras".into()), source: Some(s), ..Default::default() };
        let ms = db.filter_matches(&f).unwrap();
        assert!(!ms.is_empty(), "no Palmeiras matches from {}", s.file());
        assert!(ms.iter().all(|m| m.source == s));
    }
}

#[test]
fn scenario_overlapping_files_are_not_double_counted() {
    let db = given_data();
    // 2015 Série A exists in three files; the default view must hold one 380-match season.
    let f = MatchFilter { competition: Some(Competition::SerieA), season: Some(2015), ..Default::default() };
    assert_eq!(db.filter_matches(&f).unwrap().len(), 380);
}

#[test]
fn scenario_utf8_names_are_preserved() {
    let db = given_data();
    assert!(db.teams.values().any(|t| t == "Grêmio"));
    assert!(db.teams.values().any(|t| t == "São Paulo"));
    assert!(db.matches.iter().any(|m| m.arena.as_deref() == Some("Maracanã")));
}

// ------------------------------------------------------------ match queries

#[test]
fn scenario_find_matches_between_two_teams() {
    // When I search for matches between "Flamengo" and "Fluminense"
    let db = given_data();
    let f = MatchFilter { team: Some("Flamengo".into()), opponent: Some("Fluminense".into()), ..Default::default() };
    let ms = db.filter_matches(&f).unwrap();
    // Then I should receive a list of matches, each with date, scores and competition
    assert!(ms.len() > 30);
    for m in &ms {
        assert!(m.date.is_some());
        let teams = [m.home.as_str(), m.away.as_str()];
        assert!(teams.contains(&"Flamengo") && teams.contains(&"Fluminense"));
    }
    assert!(ms.iter().filter(|m| m.score().is_some()).count() > 30);
    let text = when("head_to_head", json!({"team_a": "Flamengo", "team_b": "Fluminense"}));
    assert!(text.contains("Fla-Flu derby"), "{text}");
    assert!(text.contains("Head-to-head in dataset"), "{text}");
    assert!(text.contains("more matches in dataset"), "{text}");
}

#[test]
fn scenario_head_to_head_totals_are_consistent_from_both_sides() {
    let a = when("head_to_head", json!({"team_a": "Palmeiras", "team_b": "Santos"}));
    let b = when("head_to_head", json!({"team_a": "Santos-SP", "team_b": "Palmeiras - SP"}));
    let grab = |t: &str, who: &str| -> u32 {
        let line = t.lines().find(|l| l.starts_with("Head-to-head")).unwrap();
        let tail = &line[line.find(&format!("{who} ")).unwrap() + who.len() + 1..];
        tail.split(' ').next().unwrap().parse().unwrap()
    };
    assert_eq!(grab(&a, "Palmeiras"), grab(&b, "Palmeiras"));
    assert_eq!(grab(&a, "Santos"), grab(&b, "Santos"));
    assert!(grab(&a, "Palmeiras") + grab(&a, "Santos") > 20);
}

#[test]
fn scenario_matches_by_team_and_season() {
    let text = when("search_matches", json!({"team": "Palmeiras", "season": 2023}));
    assert!(text.starts_with("Palmeiras matches (2023)"), "{text}");
    assert!(text.lines().filter(|l| l.starts_with("- 2023-")).count() == 20, "{text}");
}

#[test]
fn scenario_last_meeting_and_score() {
    // "When did Flamengo last play Corinthians?" / "What was the score?"
    let text = when("search_matches", json!({"team": "Flamengo", "opponent": "Corinthians", "limit": 1}));
    assert!(text.contains("- 2023-10-08: Corinthians 1-1 Flamengo"), "{text}");
}

#[test]
fn scenario_matches_by_date_range_in_both_formats() {
    let db = given_data();
    let iso = MatchFilter { date_from: Some("2019-10-01".into()), date_to: Some("2019-10-31".into()), competition: Some(Competition::SerieA), ..Default::default() };
    let br = MatchFilter { date_from: Some("01/10/2019".into()), date_to: Some("31/10/2019".into()), competition: Some(Competition::SerieA), ..Default::default() };
    let (a, b) = (db.filter_matches(&iso).unwrap(), db.filter_matches(&br).unwrap());
    assert!(!a.is_empty());
    assert_eq!(a.len(), b.len());
    assert!(a.iter().all(|m| m.date.as_deref().unwrap().starts_with("2019-10")));
}

#[test]
fn scenario_home_and_away_filters() {
    let db = given_data();
    let key = &db.resolve_team("Flamengo").unwrap()[0];
    let home = MatchFilter { team: Some("Flamengo".into()), venue: Venue::Home, season: Some(2019), competition: Some(Competition::SerieA), ..Default::default() };
    let ms = db.filter_matches(&home).unwrap();
    assert_eq!(ms.len(), 19);
    assert!(ms.iter().all(|m| &m.home_key == key));
    let away = MatchFilter { venue: Venue::Away, ..home };
    assert!(db.filter_matches(&away).unwrap().iter().all(|m| &m.away_key == key));
}

#[test]
fn scenario_copa_do_brasil_finals() {
    let text = when("search_matches", json!({"competition": "Copa do Brasil", "stage": "final", "limit": 50}));
    assert!(text.contains("2019-09-18: Internacional 1-2 Athletico-PR (Copa do Brasil 2019, final)"), "{text}");
    assert!(text.contains("2015-12-02: Palmeiras 2-1 Santos"), "{text}");
}

#[test]
fn scenario_extended_statistics_from_br_football_file() {
    let text = when("search_matches", json!({"team": "Sao Paulo", "opponent": "Flamengo", "source": "br-football", "date_from": "2023-09-24", "date_to": "2023-09-24"}));
    assert!(text.contains("São Paulo 1-1 Flamengo (Copa do Brasil 2023) [corners 2-4, shots 8-13, attacks 75-104]"), "{text}");
}

#[test]
fn scenario_derbies_in_a_season() {
    let text = when("derbies", json!({"season": 2023}));
    assert!(text.contains("[Fla-Flu]"), "{text}");
    assert!(text.lines().filter(|l| l.starts_with("- [")).all(|l| l.contains("2023-")), "{text}");
}

// ------------------------------------------------------------- team queries

#[test]
fn scenario_team_statistics_for_a_season() {
    // When I request statistics for "Palmeiras" in season "2023"
    let text = when("team_stats", json!({"team": "Palmeiras", "season": "2023"}));
    // Then I should receive wins, losses, draws, and goals
    for needle in ["Matches:", "Wins:", "Draws:", "Losses:", "Goals For:", "Goals Against:", "Win rate:", "By competition:"] {
        assert!(text.contains(needle), "missing {needle} in {text}");
    }
}

#[test]
fn scenario_home_record_in_a_season() {
    // "What is Corinthians' home record in 2022?"
    let text = when("team_stats", json!({"team": "Corinthians", "venue": "home", "season": 2022, "competition": "Brasileirão"}));
    assert!(text.contains("Corinthians home record (Brasileirão Série A, 2022)"), "{text}");
    assert!(text.contains("- Matches: 19\n- Wins: 12, Draws: 4, Losses: 3"), "{text}");
    assert!(text.contains("Win rate: 63.2%"), "{text}");
}

#[test]
fn scenario_team_name_variations_resolve_to_the_same_team() {
    let db = given_data();
    let expect = db.resolve_team("Atlético-MG").unwrap();
    assert_eq!(expect.len(), 1);
    for n in ["Atletico-MG", "Atlético - MG", "Atletico Mineiro", "atletico mg"] {
        assert_eq!(db.resolve_team(n).unwrap(), expect, "{n}");
    }
    for n in ["Sao Paulo", "São Paulo-SP", "São Paulo - SP", "sao paulo fc"] {
        assert_eq!(db.resolve_team(n).unwrap(), db.resolve_team("São Paulo").unwrap(), "{n}");
    }
    assert!(db.resolve_team("Nonexistent United").is_err());
}

#[test]
fn scenario_competitions_a_team_played_in() {
    // "What competitions has Palmeiras played in?" - also a cross-file query.
    let text = when("team_profile", json!({"team": "Palmeiras"}));
    for c in ["Brasileirão Série A", "Copa do Brasil", "Copa Libertadores"] {
        assert!(text.contains(c), "{text}");
    }
    assert!(text.contains("FIFA player data"), "{text}");
}

#[test]
fn scenario_cross_file_profile_joins_matches_and_players() {
    let text = when("team_profile", json!({"team": "Gremio"}));
    assert!(text.contains("Grêmio - profile"), "{text}");
    assert!(text.contains("Copa Libertadores"), "{text}");
    assert!(text.contains("FIFA squad: 20 players"), "{text}");
}

// ----------------------------------------------------------- player queries

#[test]
fn scenario_top_brazilian_players() {
    let text = when("search_players", json!({"nationality": "Brazil", "limit": 5}));
    assert!(text.contains("827 found"), "{text}");
    assert!(text.contains("1. Neymar Jr - Overall: 92, Position: LW, Club: Paris Saint-Germain"), "{text}");
    let ps = given_data().filter_players(&PlayerFilter { nationality: Some("Brazilian".into()), ..Default::default() });
    assert!(ps.windows(2).all(|w| w[0].overall >= w[1].overall));
    assert!(ps.iter().all(|p| p.nationality == "Brazil"));
}

#[test]
fn scenario_search_player_by_name() {
    let text = when("player_details", json!({"name": "neymar"}));
    assert!(text.starts_with("Neymar Jr"), "{text}");
    for needle in ["Nationality: Brazil", "Overall: 92", "Position: LW", "Dribbling 96"] {
        assert!(text.contains(needle), "{text}");
    }
}

#[test]
fn scenario_unknown_player_offers_similar_names_instead_of_guessing() {
    // "Who is Gabriel Barbosa?" - not in the FIFA file under that name.
    let text = when("player_details", json!({"name": "Gabriel Barbosa"}));
    assert!(text.starts_with("No player named 'Gabriel Barbosa'"), "{text}");
    assert!(text.contains("Gabriel Jesus"), "{text}");
}

#[test]
fn scenario_players_by_club_and_position() {
    let db = given_data();
    let squad = db.filter_players(&PlayerFilter { club: Some("Grêmio".into()), ..Default::default() });
    assert_eq!(squad.len(), 20);
    // "Show me all forwards from Santos" must not include Santos Laguna.
    let fw = db.filter_players(&PlayerFilter { club: Some("Santos".into()), position: Some("forwards".into()), ..Default::default() });
    assert!(!fw.is_empty());
    assert!(fw.iter().all(|p| p.club == "Santos" && ["ST", "CF", "LF", "RF", "LS", "RS", "LW", "RW"].contains(&p.position.as_str())));
    // Alternative club spellings reach the same squad.
    let a = db.filter_players(&PlayerFilter { club: Some("Atletico-MG".into()), ..Default::default() });
    assert_eq!(a.len(), 20);
    assert!(a.iter().all(|p| p.club == "Atlético Mineiro"));
}

#[test]
fn scenario_unlicensed_club_is_reported_honestly() {
    let text = when("search_players", json!({"club": "Flamengo"}));
    assert!(text.contains("No players found"), "{text}");
    assert!(text.contains("not licensed"), "{text}");
}

#[test]
fn scenario_brazilian_players_grouped_by_brazilian_club() {
    let text = when("brazilian_clubs_players", json!({"nationality": "Brazil"}));
    assert!(text.contains("- Grêmio: 20 players (avg rating:"), "{text}");
    assert!(!text.contains("Paris Saint-Germain"), "{text}");
}

// ------------------------------------------------------ competition queries

#[test]
fn scenario_who_won_the_2019_brasileirao() {
    let text = when("standings", json!({"competition": "Brasileirão", "season": 2019}));
    assert!(text.contains("1. Flamengo - 90 pts (28W, 6D, 4L)"), "{text}");
    assert!(text.contains("- Champion"), "{text}");
    assert!(text.contains("2. Santos - 74 pts (22W, 8D, 8L)"), "{text}");
    assert!(text.contains("3. Palmeiras - 74 pts (21W, 11D, 6L)"), "{text}");
    for t in ["Cruzeiro", "CSA", "Chapecoense", "Avaí"] {
        assert!(text.lines().any(|l| l.contains(t) && l.ends_with("- Relegated")), "{t}: {text}");
    }
}

#[test]
fn scenario_standings_arithmetic_is_consistent() {
    let rows = given_data().table(Competition::SerieA, 2019, Venue::Either);
    assert_eq!(rows.len(), 20);
    for (_, r) in &rows {
        assert_eq!(r.played, 38);
        assert_eq!(r.wins + r.draws + r.losses, r.played);
    }
    assert_eq!(rows.iter().map(|r| r.1.goals_for).sum::<u32>(), rows.iter().map(|r| r.1.goals_against).sum::<u32>());
    assert_eq!(rows.iter().map(|r| r.1.wins).sum::<u32>(), rows.iter().map(|r| r.1.losses).sum::<u32>());
}

#[test]
fn scenario_relegated_teams_in_2020() {
    let text = when("standings", json!({"season": 2020}));
    assert!(text.contains("1. Flamengo - 71 pts"), "{text}");
    let relegated: Vec<&str> = text.lines().filter(|l| l.ends_with("- Relegated")).collect();
    assert_eq!(relegated.len(), 4, "{text}");
    for t in ["Vasco", "Goiás", "Coritiba", "Botafogo"] {
        assert!(relegated.iter().any(|l| l.contains(t)), "{t}: {text}");
    }
}

#[test]
fn scenario_incomplete_season_gets_no_champion_label() {
    let text = when("standings", json!({"season": 2023}));
    assert!(!text.contains("- Champion"), "{text}");
    assert!(text.contains("incomplete"), "{text}");
}

#[test]
fn scenario_libertadores_bracket() {
    let text = when("competition_summary", json!({"competition": "Libertadores", "season": 2018}));
    for stage in ["round of 16:", "quarterfinals:", "semifinals:", "final:"] {
        assert!(text.contains(stage), "{stage}: {text}");
    }
    assert!(text.contains("River Plate"), "{text}");
}

#[test]
fn scenario_cup_champion_from_final_aggregate() {
    let text = when("competition_summary", json!({"competition": "Copa do Brasil", "season": 2019}));
    assert!(text.contains("Champion: Athletico-PR (final aggregate 3-1 over Internacional)"), "{text}");
}

// ----------------------------------------------------------- statistics

#[test]
fn scenario_average_goals_per_match() {
    let text = when("league_stats", json!({"competition": "Brasileirão", "season": 2019}));
    assert!(text.contains("Matches played: 380"), "{text}");
    assert!(text.contains("Total goals: 876"), "{text}");
    assert!(text.contains("Average goals per match: 2.31"), "{text}");
    assert!(text.contains("Home win rate:"), "{text}");
}

#[test]
fn scenario_biggest_wins() {
    let text = when("biggest_wins", json!({"limit": 5}));
    assert!(text.contains("1. 2021-06-08: São Paulo 9-1 4 de Julho-PI"), "{text}");
    let margins: Vec<i32> = text
        .lines()
        .skip(1)
        .filter_map(|l| {
            let score = l.split(' ').find(|w| w.contains('-') && w.chars().all(|c| c.is_ascii_digit() || c == '-') && w.len() <= 5)?;
            let (h, a) = score.split_once('-')?;
            Some((h.parse::<i32>().ok()? - a.parse::<i32>().ok()?).abs())
        })
        .collect();
    assert_eq!(margins.len(), 5, "{text}");
    assert!(margins.windows(2).all(|w| w[0] >= w[1]), "{margins:?}");
}

#[test]
fn scenario_best_home_and_away_records() {
    let home = when("team_rankings", json!({"metric": "win_rate", "venue": "home", "competition": "Serie A", "season": 2019, "limit": 3}));
    assert!(home.contains("1. Flamengo - 89.5% wins (19 matches: 17W 2D 0L"), "{home}");
    let away = when("team_rankings", json!({"venue": "away", "competition": "Serie A", "season": 2019, "limit": 1}));
    assert!(away.contains("1. Flamengo"), "{away}");
}

#[test]
fn scenario_most_goals_in_a_season() {
    // "Which team scored the most goals in Serie A 2023?"
    let text = when("team_rankings", json!({"metric": "goals_for", "competition": "Serie A", "season": 2023, "limit": 1}));
    assert!(text.contains("1. Grêmio - 63 goals"), "{text}");
}

#[test]
fn scenario_compare_two_seasons() {
    let text = when("compare_seasons", json!({"season_a": 2018, "season_b": 2019}));
    assert!(text.contains("Champion: Palmeiras (80 pts"), "{text}");
    assert!(text.contains("Champion: Flamengo (90 pts"), "{text}");
    assert_eq!(text.matches("Average goals per match").count(), 2);
}

// ---------------------------------------------------------------- protocol

#[test]
fn scenario_mcp_handshake_and_tool_listing() {
    let db = given_data();
    let init = handle_message(db, &json!({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}}})).unwrap();
    assert_eq!(init["result"]["serverInfo"]["name"], "brazilian-soccer-mcp");
    assert_eq!(init["result"]["protocolVersion"], "2024-11-05");
    assert!(init["result"]["capabilities"]["tools"].is_object());
    assert!(handle_message(db, &json!({"jsonrpc": "2.0", "method": "notifications/initialized"})).is_none());

    let list = handle_message(db, &json!({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})).unwrap();
    let tools = list["result"]["tools"].as_array().unwrap();
    assert_eq!(tools.len(), tool_definitions().as_array().unwrap().len());
    for t in tools {
        assert!(t["name"].is_string() && t["description"].is_string());
        assert_eq!(t["inputSchema"]["type"], "object");
        // Every advertised tool is callable (required args aside) and never panics.
        let _ = call_tool(db, t["name"].as_str().unwrap(), &json!({}));
    }
}

#[test]
fn scenario_mcp_tool_call_over_stdio() {
    let input = concat!(
        r#"{"jsonrpc":"2.0","id":"a","method":"tools/call","params":{"name":"standings","arguments":{"season":2019}}}"#, "\n",
        "not json\n",
        r#"{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"team_stats","arguments":{"team":"Nonexistent United"}}}"#, "\n",
        r#"{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"nope","arguments":{}}}"#, "\n",
        r#"{"jsonrpc":"2.0","id":5,"method":"resources/list"}"#, "\n",
    );
    let mut out = Vec::new();
    serve(given_data(), input.as_bytes(), &mut out).unwrap();
    let lines: Vec<Value> = String::from_utf8(out).unwrap().lines().map(|l| serde_json::from_str(l).unwrap()).collect();
    assert_eq!(lines.len(), 5);
    assert_eq!(lines[0]["id"], "a");
    assert_eq!(lines[0]["result"]["isError"], false);
    assert!(lines[0]["result"]["content"][0]["text"].as_str().unwrap().contains("Flamengo - 90 pts"));
    assert_eq!(lines[1]["error"]["code"], -32700);
    assert_eq!(lines[2]["result"]["isError"], true);
    assert!(lines[2]["result"]["content"][0]["text"].as_str().unwrap().contains("No team matching"));
    assert_eq!(lines[3]["error"]["code"], -32602);
    assert_eq!(lines[4]["error"]["code"], -32601);
}

#[test]
fn scenario_invalid_arguments_are_rejected_with_a_message() {
    let db = given_data();
    assert!(call_tool(db, "standings", &json!({})).unwrap_err().contains("season"));
    assert!(call_tool(db, "standings", &json!({"season": "abc"})).is_err());
    assert!(call_tool(db, "search_matches", &json!({"competition": "Premier League"})).is_err());
    assert!(call_tool(db, "search_matches", &json!({"date_from": "yesterday"})).is_err());
    assert!(call_tool(db, "search_matches", &json!({"venue": "moon"})).is_err());
    assert!(call_tool(db, "standings", &json!({"competition": "Libertadores", "season": 2018})).is_err());
    assert!(call_tool(db, "standings", &json!({"season": 1990})).unwrap_err().contains("available seasons"));
}

// ------------------------------------------------------------- performance

#[test]
fn scenario_queries_meet_the_response_time_budget() {
    let db = given_data();
    let t = Instant::now();
    when("search_matches", json!({"team": "Flamengo", "opponent": "Corinthians"}));
    when("player_details", json!({"name": "Neymar"}));
    assert!(t.elapsed().as_secs_f64() < 2.0, "simple lookups took {:?}", t.elapsed());
    let t = Instant::now();
    when("team_rankings", json!({"venue": "home"}));
    when("league_stats", json!({}));
    when("biggest_wins", json!({}));
    assert!(t.elapsed().as_secs_f64() < 5.0, "aggregates took {:?}", t.elapsed());
    let t = Instant::now();
    Database::load(&find_data_dir(None).unwrap()).unwrap();
    assert!(t.elapsed().as_secs_f64() < 5.0, "loading took {:?}", t.elapsed());
    let _ = db;
}
