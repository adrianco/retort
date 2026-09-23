//! BDD-style scenarios (Given / When / Then) covering the specification.

use brazilian_soccer_mcp::data::{normalize_date, team_key, Competition};
use brazilian_soccer_mcp::mcp;
use brazilian_soccer_mcp::query::{Engine, MatchFilter};
use serde_json::{json, Value};
use std::sync::OnceLock;
use std::time::Instant;

/// Given the match and player data is loaded
fn given_data_loaded() -> &'static Engine {
    static E: OnceLock<Engine> = OnceLock::new();
    E.get_or_init(|| Engine::load(concat!(env!("CARGO_MANIFEST_DIR"), "/data/kaggle")).expect("data loads"))
}

fn when_tool_called(name: &str, args: Value) -> String {
    let req = json!({"jsonrpc": "2.0", "id": 7, "method": "tools/call", "params": {"name": name, "arguments": args}});
    let resp = mcp::handle(given_data_loaded(), &req).expect("response");
    assert!(resp["result"]["isError"].is_null(), "tool error: {resp}");
    resp["result"]["content"][0]["text"].as_str().unwrap().to_string()
}

// ---------- Feature: data loading & normalization ----------

#[test]
fn scenario_all_six_files_are_loaded() {
    let e = given_data_loaded();
    let counts = &e.data.file_counts;
    assert_eq!(counts.len(), 6);
    for (f, n) in counts {
        assert!(*n > 1000, "{f} loaded only {n} rows");
    }
    assert_eq!(counts.iter().find(|c| c.0 == "fifa_data.csv").unwrap().1, 18207);
    assert_eq!(counts.iter().find(|c| c.0 == "novo_campeonato_brasileiro.csv").unwrap().1, 6886);
    assert_eq!(counts.iter().find(|c| c.0 == "BR-Football-Dataset.csv").unwrap().1, 10296);
}

#[test]
fn scenario_team_name_variations_normalize() {
    assert_eq!(team_key("Palmeiras-SP"), team_key("Palmeiras"));
    assert_eq!(team_key("São Paulo - SP"), team_key("Sao Paulo"));
    assert_eq!(team_key("Sport Club Corinthians Paulista"), team_key("Corinthians-SP"));
    assert_eq!(team_key("Grêmio"), team_key("Gremio RS"));
    assert_eq!(team_key("Atlético-MG"), team_key("Atletico Mineiro"));
    assert_eq!(team_key("Athletico"), team_key("Atletico-PR"));
    assert_eq!(team_key("Vasco Da Gama RJ"), team_key("Vasco"));
    assert_eq!(team_key("EC Bahia"), team_key("Bahia-BA"));
    assert_eq!(team_key("Fortaleza FC"), team_key("Fortaleza"));
    assert_ne!(team_key("Botafogo PB"), team_key("Botafogo-RJ"));
    assert_ne!(team_key("Atlético-GO"), team_key("Atlético-MG"));
}

#[test]
fn scenario_multiple_date_formats() {
    assert_eq!(normalize_date("29/03/2003"), "2003-03-29");
    assert_eq!(normalize_date("2012-05-19 18:30:00"), "2012-05-19");
    assert_eq!(normalize_date("2023-09-24"), "2023-09-24");
}

#[test]
fn scenario_utf8_names_are_preserved() {
    let out = when_tool_called("team_stats", json!({"team": "sao paulo"}));
    assert!(out.starts_with("São Paulo"), "{out}");
    let out = when_tool_called("team_stats", json!({"team": "Gremio"}));
    assert!(out.starts_with("Grêmio"), "{out}");
}

// ---------- Feature: Match Queries ----------

#[test]
fn scenario_find_matches_between_two_teams() {
    // When I search for matches between "Flamengo" and "Fluminense"
    let e = given_data_loaded();
    let f = MatchFilter { team: Some("Flamengo".into()), opponent: Some("Fluminense".into()), ..Default::default() };
    let ms = e.find_matches(&f).unwrap();
    // Then I should receive a list of matches, each with date, scores and competition
    assert!(ms.len() > 20);
    for m in &ms {
        assert_eq!(m.date.len(), 10);
        let keys = [m.home_key.as_str(), m.away_key.as_str()];
        assert!(keys.contains(&"flamengo") && keys.contains(&"fluminense"));
    }
    // Sources from multiple files contribute
    let comps: std::collections::HashSet<_> = ms.iter().map(|m| m.competition).collect();
    assert!(comps.contains(&Competition::Brasileirao) && comps.contains(&Competition::CopaDoBrasil));
    let text = when_tool_called("head_to_head", json!({"team_a": "Flamengo", "team_b": "Fluminense"}));
    assert!(text.contains("Head-to-head in dataset: Flamengo"), "{text}");
}

#[test]
fn scenario_palmeiras_matches_in_2023() {
    let out = when_tool_called("search_matches", json!({"team": "Palmeiras", "season": 2023, "limit": 100}));
    assert!(out.contains("Found"));
    assert!(out.contains("Brasileirão") && out.contains("Copa do Brasil"), "{out}");
    assert!(!out.contains("2022-"));
}

#[test]
fn scenario_copa_do_brasil_finals() {
    let out = when_tool_called("search_matches", json!({"competition": "Copa do Brasil", "round": "final", "limit": 50}));
    assert!(out.contains("Palmeiras 2-0 Grêmio (Copa do Brasil Final)"), "{out}");
    assert!(out.contains("Athletico Paranaense"));
}

#[test]
fn scenario_last_flamengo_vs_corinthians() {
    let e = given_data_loaded();
    let f = MatchFilter { team: Some("Flamengo".into()), opponent: Some("Corinthians".into()), ..Default::default() };
    let ms = e.find_matches(&f).unwrap();
    let last = ms[0];
    assert!(ms.iter().all(|m| m.date <= last.date));
    assert!(last.date.starts_with("2023"), "{}", last.date);
}

#[test]
fn scenario_date_range_filter() {
    let e = given_data_loaded();
    let f = MatchFilter { team: Some("Santos".into()), date_from: Some("2015-01-01".into()), date_to: Some("2015-12-31".into()), ..Default::default() };
    let ms = e.find_matches(&f).unwrap();
    assert!(!ms.is_empty());
    assert!(ms.iter().all(|m| m.date.starts_with("2015")));
}

#[test]
fn scenario_libertadores_matches_are_queryable() {
    let out = when_tool_called("search_matches", json!({"competition": "Libertadores", "team": "Palmeiras", "round": "final"}));
    assert!(out.contains("Libertadores final"), "{out}");
}

#[test]
fn scenario_historical_matches_have_arena() {
    let out = when_tool_called("search_matches", json!({"team": "Guarani", "season": 2003, "limit": 3}));
    assert!(out.contains(" @ "), "{out}");
}

// ---------- Feature: Team Queries ----------

#[test]
fn scenario_team_statistics_for_season() {
    // When I request statistics for "Palmeiras" in season "2023"
    let e = given_data_loaded();
    let f = MatchFilter { season: Some(2023), competition: Some(Competition::Brasileirao), ..Default::default() };
    let r = e.team_record("Palmeiras", &f).unwrap();
    // Then I should receive wins, losses, draws, and goals
    // The provided 2023 data is missing one Palmeiras fixture.
    assert!(r.played >= 37 && r.played <= 38, "{}", r.played);
    assert_eq!(r.wins + r.draws + r.losses, r.played);
    assert!(r.goals_for > 0 && r.goals_against > 0);
}

#[test]
fn scenario_corinthians_home_record_2022() {
    let out = when_tool_called("team_stats", json!({"team": "Corinthians", "season": 2022, "venue": "home", "competition": "Brasileirão"}));
    assert!(out.contains("Corinthians home record (2022 Brasileirão)"), "{out}");
    assert!(out.contains("Matches: 19"), "{out}");
    assert!(out.contains("Win rate:"));
}

#[test]
fn scenario_top_scoring_team_serie_a_2023() {
    let out = when_tool_called("rank_teams", json!({"metric": "goals", "competition": "Serie A", "season": 2023, "limit": 3}));
    // Calculated from the provided data: Grêmio 63 goals, Palmeiras 61.
    assert!(out.lines().nth(1).unwrap().starts_with("1. Grêmio - 38P"), "{out}");
    assert!(out.contains("2. Palmeiras"), "{out}");
}

#[test]
fn scenario_team_competitions_across_files() {
    let out = when_tool_called("team_competitions", json!({"team": "Palmeiras"}));
    for c in ["Brasileirão", "Copa do Brasil", "Libertadores"] {
        assert!(out.contains(c), "{out}");
    }
}

// ---------- Feature: Competition Queries ----------

#[test]
fn scenario_2019_brasileirao_champion() {
    let e = given_data_loaded();
    let rows = e.standings(2019, Competition::Brasileirao).unwrap();
    assert_eq!(rows.len(), 20);
    assert_eq!(rows[0].team, "Flamengo");
    assert_eq!(rows[0].record.points(), 90);
    assert_eq!((rows[0].record.wins, rows[0].record.draws, rows[0].record.losses), (28, 6, 4));
    assert_eq!(rows[1].team, "Santos");
    assert_eq!(rows[1].record.points(), 74);
    assert!(rows.iter().all(|r| r.record.played == 38));
}

#[test]
fn scenario_historical_standings_from_brazilian_date_file() {
    // 2003-2011 only exists in novo_campeonato_brasileiro.csv (DD/MM/YYYY dates)
    let out = when_tool_called("standings", json!({"season": 2003, "limit": 1}));
    assert!(out.contains("1. Cruzeiro"), "{out}");
}

#[test]
fn scenario_relegated_teams_2020() {
    let out = when_tool_called("standings", json!({"season": 2020}));
    assert!(out.contains("Relegation zone (bottom 4)"));
    for t in ["Vasco da Gama", "Goiás", "Coritiba", "Botafogo"] {
        assert!(out.lines().last().unwrap().contains(t), "{out}");
    }
}

#[test]
fn scenario_libertadores_2018_bracket() {
    let out = when_tool_called("search_matches", json!({"competition": "Libertadores", "season": 2018, "round": "final"}));
    assert!(out.contains("River Plate") && out.contains("Boca Juniors"), "{out}");
}

// ---------- Feature: Statistical Analysis ----------

#[test]
fn scenario_average_goals_per_match() {
    let out = when_tool_called("league_stats", json!({"competition": "Brasileirão"}));
    assert!(out.contains("Average goals per match: 2."), "{out}");
    assert!(out.contains("Home win rate:"));
    assert!(out.contains("By season:"));
}

#[test]
fn scenario_best_home_and_away_records() {
    let home = when_tool_called("rank_teams", json!({"metric": "home", "min_matches": 100}));
    assert!(home.contains("home matches"));
    let away = when_tool_called("rank_teams", json!({"metric": "away", "min_matches": 100}));
    assert!(away.contains("away matches") && away.contains("1. "));
}

#[test]
fn scenario_biggest_wins() {
    let out = when_tool_called("biggest_wins", json!({"limit": 5}));
    assert!(out.contains("1. 2021-06-08: São Paulo 9-1"), "{out}");
    // no duplicate fixtures across overlapping files
    assert_eq!(out.matches("9-1").count(), 1, "{out}");
}

#[test]
fn scenario_compare_two_seasons() {
    let a = when_tool_called("league_stats", json!({"competition": "Serie A", "season": 2018}));
    let b = when_tool_called("league_stats", json!({"competition": "Serie A", "season": 2019}));
    assert!(a.contains("Statistics for 380 matches"), "{a}");
    assert!(b.contains("Statistics for 380 matches"), "{b}");
}

#[test]
fn scenario_derbies_in_2023() {
    let out = when_tool_called("derbies", json!({"season": 2023}));
    assert!(out.contains("Fla-Flu") && out.contains("Grenal") && out.contains("Derby Paulista"), "{out}");
}

#[test]
fn scenario_extended_stats_from_br_football_dataset() {
    let out = when_tool_called("league_stats", json!({"competition": "Serie B"}));
    assert!(out.contains("avg corners"), "{out}");
}

// ---------- Feature: Player Queries ----------

#[test]
fn scenario_top_brazilian_players() {
    let e = given_data_loaded();
    let ps = e.find_players(None, Some("Brazilian"), None, None, None);
    assert!(ps.len() > 800);
    assert_eq!(ps[0].name, "Neymar Jr");
    assert_eq!(ps[0].overall, 92);
}

#[test]
fn scenario_search_player_by_name_with_accents() {
    let out = when_tool_called("search_players", json!({"name": "neymar"}));
    assert!(out.contains("Neymar Jr - Overall: 92, Position: LW, Club: Paris Saint-Germain"), "{out}");
    assert!(out.contains("Skills:"));
    let out = when_tool_called("search_players", json!({"name": "Gremio", "club": "Grêmio"}));
    assert!(out.contains("Found 0 players") || out.contains("Grêmio"));
}

#[test]
fn scenario_players_at_brazilian_club_by_position() {
    let e = given_data_loaded();
    let ps = e.find_players(None, None, Some("Grêmio"), None, None);
    assert_eq!(ps.len(), 20);
    let fw = e.find_players(None, None, Some("Santos"), Some("forward"), None);
    assert!(fw.iter().any(|p| p.club == "Santos"));
    assert!(fw.iter().all(|p| ["ST", "CF", "LW", "RW", "LS", "RS", "LF", "RF"].contains(&p.position.as_str())));
}

#[test]
fn scenario_cross_file_players_and_matches() {
    let out = when_tool_called("brazilian_club_players", json!({"nationality": "Brazil"}));
    assert!(out.contains("Grêmio: 20 players"), "{out}");
    assert!(out.contains("matches in dataset, win rate"));
    assert!(!out.contains("Santos Laguna"));
}

// ---------- Feature: MCP protocol ----------

#[test]
fn scenario_mcp_handshake_and_tool_list() {
    let e = given_data_loaded();
    let init = mcp::handle(e, &json!({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05"}})).unwrap();
    assert_eq!(init["result"]["serverInfo"]["name"], "brazilian-soccer-mcp");
    assert!(mcp::handle(e, &json!({"jsonrpc": "2.0", "method": "notifications/initialized"})).is_none());
    let list = mcp::handle(e, &json!({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})).unwrap();
    assert!(list["result"]["tools"].as_array().unwrap().len() >= 10);
    let bad = mcp::handle(e, &json!({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "team_stats", "arguments": {"team": "Nonexistent Club XYZ"}}})).unwrap();
    assert_eq!(bad["result"]["isError"], true);
    let unknown = mcp::handle(e, &json!({"jsonrpc": "2.0", "id": 4, "method": "nope"})).unwrap();
    assert_eq!(unknown["error"]["code"], -32601);
}

#[test]
fn scenario_query_performance() {
    let _ = given_data_loaded();
    let t = Instant::now();
    when_tool_called("search_players", json!({"name": "Gabriel"}));
    when_tool_called("head_to_head", json!({"team_a": "Palmeiras", "team_b": "Santos"}));
    assert!(t.elapsed().as_secs_f64() < 2.0);
    let t = Instant::now();
    when_tool_called("rank_teams", json!({"metric": "home"}));
    when_tool_called("league_stats", json!({}));
    when_tool_called("standings", json!({"season": 2010}));
    when_tool_called("brazilian_club_players", json!({}));
    assert!(t.elapsed().as_secs_f64() < 5.0);
}
