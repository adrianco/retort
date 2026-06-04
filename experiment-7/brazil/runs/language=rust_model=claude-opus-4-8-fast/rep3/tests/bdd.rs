// =============================================================================
// BDD test-suite — Given/When/Then scenarios for the Brazilian Soccer MCP
// -----------------------------------------------------------------------------
// Context:
//   These tests follow the Behaviour-Driven-Development (GWT) structure
//   requested by TASK.md. They load the real datasets from `data/kaggle/` and
//   exercise every capability category plus the MCP dispatch layer. Each test is
//   annotated with its Given/When/Then steps.
// =============================================================================

use brazilian_soccer_mcp::normalize::{key_matches, parse_date, team_key};
use brazilian_soccer_mcp::queries::{
    self, compute_record, filter_matches, filter_players, MatchFilter, PlayerFilter, PlayerSort,
    Venue,
};
use brazilian_soccer_mcp::store::DataStore;
use serde_json::json;
use std::sync::OnceLock;

fn store() -> &'static DataStore {
    static STORE: OnceLock<DataStore> = OnceLock::new();
    STORE.get_or_init(|| {
        let dir = concat!(env!("CARGO_MANIFEST_DIR"), "/data/kaggle");
        DataStore::load_from_dir(dir)
    })
}

// --- Feature: Data loading ---------------------------------------------------

#[test]
fn scenario_all_datasets_load() {
    // Given the dataset directory
    let s = store();
    // When the data is loaded
    // Then a substantial number of matches and players are available
    assert!(s.match_count() > 15_000, "matches loaded: {}", s.match_count());
    assert!(s.player_count() > 18_000, "players loaded: {}", s.player_count());
}

#[test]
fn scenario_all_competitions_present() {
    // Given the loaded data
    let s = store();
    // When we list competitions
    let text = queries::list_competitions(s);
    // Then each required competition is represented
    for comp in ["Brasileirão Série A", "Copa do Brasil", "Copa Libertadores"] {
        assert!(text.contains(comp), "missing competition: {}\n{}", comp, text);
    }
}

// --- Feature: Match Queries --------------------------------------------------

#[test]
fn scenario_find_matches_between_two_teams() {
    // Given the match data is loaded
    let s = store();
    // When I search for matches between "Flamengo" and "Fluminense"
    let mut f = MatchFilter::new();
    f.team = Some("Flamengo".into());
    f.opponent = Some("Fluminense".into());
    let matches = filter_matches(s, &f);
    // Then I should receive a list of matches
    assert!(!matches.is_empty(), "expected Fla-Flu matches");
    // And each match should involve both teams
    let fla = team_key("Flamengo");
    let flu = team_key("Fluminense");
    for m in &matches {
        let teams = [m.home_key.as_str(), m.away_key.as_str()];
        assert!(teams.iter().any(|t| key_matches(t, &fla)));
        assert!(teams.iter().any(|t| key_matches(t, &flu)));
    }
    // And the rendered answer carries a head-to-head summary
    let text = queries::search_matches(s, &f, 25);
    assert!(text.contains("Head-to-head"), "{}", text);
}

#[test]
fn scenario_filter_matches_by_season_and_team() {
    // Given the match data is loaded
    let s = store();
    // When I ask what matches Palmeiras played in 2023
    let mut f = MatchFilter::new();
    f.team = Some("Palmeiras".into());
    f.season = Some(2023);
    let matches = filter_matches(s, &f);
    // Then every returned match is from 2023 and involves Palmeiras
    assert!(!matches.is_empty(), "expected Palmeiras 2023 matches");
    let pal = team_key("Palmeiras");
    for m in &matches {
        assert_eq!(m.season, 2023);
        assert!(key_matches(&m.home_key, &pal) || key_matches(&m.away_key, &pal));
    }
}

#[test]
fn scenario_filter_by_competition() {
    // Given the data is loaded
    let s = store();
    // When I filter by the Libertadores competition
    let mut f = MatchFilter::new();
    f.competition = Some("Libertadores".into());
    let matches = filter_matches(s, &f);
    // Then all results are Libertadores fixtures
    assert!(!matches.is_empty());
    for m in &matches {
        assert!(m.competition.contains("Libertadores"), "{}", m.competition);
    }
}

#[test]
fn scenario_filter_by_date_range() {
    // Given the data is loaded
    let s = store();
    // When I bound the search to a single season window via dates
    let mut f = MatchFilter::new();
    f.team = Some("Santos".into());
    f.start_key = Some(parse_date("2019-01-01").1);
    f.end_key = Some(parse_date("2019-12-31").1);
    let matches = filter_matches(s, &f);
    // Then every dated match lies within the window
    assert!(!matches.is_empty());
    for m in &matches {
        if m.date_key != 0 {
            assert!((20190101..=20191231).contains(&m.date_key), "{}", m.date_iso);
        }
    }
}

// --- Feature: Team Queries ---------------------------------------------------

#[test]
fn scenario_team_statistics_for_season() {
    // Given the match data is loaded
    let s = store();
    // When I request statistics for "Palmeiras" in season 2023
    let mut f = MatchFilter::new();
    f.team = Some("Palmeiras".into());
    f.season = Some(2023);
    let matches = filter_matches(s, &f);
    let rec = compute_record(&matches, &team_key("Palmeiras"), Venue::All);
    // Then I receive a coherent W/D/L and goals record
    assert!(rec.played > 0);
    assert_eq!(rec.played, rec.wins + rec.draws + rec.losses);
    assert!(rec.goals_for >= 0 && rec.goals_against >= 0);
    // And the formatted output reports the win rate
    let text = queries::team_record(s, "Palmeiras", Some(2023), None, Venue::All);
    assert!(text.contains("Win rate"), "{}", text);
}

#[test]
fn scenario_home_record_only_counts_home_games() {
    // Given the data is loaded
    let s = store();
    // When I compute a team's home record
    let mut f = MatchFilter::new();
    f.team = Some("Corinthians".into());
    f.season = Some(2022);
    f.venue = Venue::Home;
    let matches = filter_matches(s, &f);
    let cor = team_key("Corinthians");
    // Then only home fixtures are present
    assert!(!matches.is_empty());
    for m in &matches {
        assert!(key_matches(&m.home_key, &cor), "expected home game: {}", m.scoreline());
    }
}

#[test]
fn scenario_head_to_head_records_are_symmetric() {
    // Given the data is loaded
    let s = store();
    // When I compute Palmeiras vs Santos from each side
    let mut f1 = MatchFilter::new();
    f1.team = Some("Palmeiras".into());
    f1.opponent = Some("Santos".into());
    let pal_matches = filter_matches(s, &f1);
    let pal = compute_record(&pal_matches, &team_key("Palmeiras"), Venue::All);
    let san = compute_record(&pal_matches, &team_key("Santos"), Venue::All);
    // Then their records mirror each other over the same fixtures
    assert!(pal.played > 0);
    assert_eq!(pal.played, san.played);
    assert_eq!(pal.wins, san.losses);
    assert_eq!(pal.losses, san.wins);
    assert_eq!(pal.draws, san.draws);
    assert_eq!(pal.goals_for, san.goals_against);
}

// --- Feature: Player Queries -------------------------------------------------

#[test]
fn scenario_find_brazilian_players() {
    // Given the player data is loaded
    let s = store();
    // When I filter by nationality Brazil
    let f = PlayerFilter {
        nationality: Some("Brazil".into()),
        ..Default::default()
    };
    let players = filter_players(s, &f);
    // Then I get many players, all Brazilian
    assert!(players.len() > 500, "brazilian players: {}", players.len());
    for p in players.iter().take(50) {
        assert!(p.nationality.contains("Brazil"));
    }
}

#[test]
fn scenario_search_player_by_name() {
    // Given the player data is loaded
    let s = store();
    // When I search for "Neymar"
    let f = PlayerFilter {
        name: Some("Neymar".into()),
        ..Default::default()
    };
    let players = filter_players(s, &f);
    // Then Neymar is found with a high overall rating
    assert!(!players.is_empty());
    let top = players.iter().max_by_key(|p| p.overall).unwrap();
    assert!(top.overall.unwrap_or(0) >= 88, "overall {:?}", top.overall);
}

#[test]
fn scenario_players_sorted_by_overall_descending() {
    // Given the player data is loaded
    let s = store();
    // When I list top Brazilian players sorted by overall
    let f = PlayerFilter {
        nationality: Some("Brazil".into()),
        ..Default::default()
    };
    let text = queries::search_players(s, &f, PlayerSort::Overall, 10);
    // Then the highest-rated Brazilian (Neymar Jr, 92) leads the list
    assert!(text.contains("Neymar"), "{}", text);
}

// --- Feature: Competition Queries -------------------------------------------

#[test]
fn scenario_standings_have_champion() {
    // Given the data is loaded
    let s = store();
    // When I compute the 2019 Brasileirão standings
    let text = queries::standings(s, "Brasileirão", 2019);
    // Then a table with a champion is produced (Flamengo won 2019)
    assert!(text.contains("Standings"), "{}", text);
    assert!(text.contains("Champion"), "{}", text);
    assert!(text.contains("Flamengo"), "{}", text);
}

#[test]
fn scenario_standings_points_are_consistent() {
    // Given the 2019 Brasileirão matches
    let s = store();
    let mut f = MatchFilter::new();
    f.competition = Some("Brasileirão".into());
    f.season = Some(2019);
    let matches = filter_matches(s, &f);
    // And the season is the expected size (20 teams x 38 rounds = 380 fixtures)
    assert_eq!(matches.len(), 380, "2019 Série A fixture count");
    // When I compute Flamengo's record directly
    let rec = compute_record(&matches, &team_key("Flamengo"), Venue::All);
    // Then Flamengo (the real 2019 champions) played 38 games for 90 points
    assert_eq!(rec.played, 38, "flamengo 2019 games");
    assert_eq!(rec.points(), 90, "flamengo 2019 points");
    assert_eq!(rec.points(), rec.wins * 3 + rec.draws);
}

// --- Feature: Statistical Analysis -------------------------------------------

#[test]
fn scenario_competition_summary_reports_averages() {
    // Given the data is loaded
    let s = store();
    // When I summarise the Brasileirão
    let text = queries::competition_summary(s, Some("Brasileirão"), None, 5);
    // Then averages, home-win rate and biggest wins are reported
    assert!(text.contains("Average goals per match"), "{}", text);
    assert!(text.contains("Home win rate"), "{}", text);
    assert!(text.contains("Biggest victories"), "{}", text);
}

#[test]
fn scenario_average_goals_is_plausible() {
    // Given the data is loaded
    let s = store();
    // When I compute summary stats across all data
    let text = queries::competition_summary(s, None, None, 3);
    // Then the average goals per match is a realistic football value (1.5–4.0)
    let avg_line = text
        .lines()
        .find(|l| l.contains("Average goals per match"))
        .expect("avg line");
    let value: f64 = avg_line
        .rsplit(':')
        .next()
        .unwrap()
        .trim()
        .parse()
        .expect("parse avg");
    assert!((1.5..=4.0).contains(&value), "avg goals {}", value);
}

// --- Feature: Data-quality handling -----------------------------------------

#[test]
fn scenario_team_name_variations_match() {
    // Given names with suffixes, accents and parentheses
    // When normalised
    // Then equivalent clubs share a key
    assert_eq!(team_key("Palmeiras-SP"), team_key("Palmeiras"));
    assert_eq!(team_key("São Paulo"), team_key("Sao Paulo"));
    assert!(key_matches(&team_key("Grêmio-RS"), &team_key("Gremio")));
}

#[test]
fn scenario_multiple_date_formats_parse() {
    // Given dates in three formats
    // When parsed
    // Then they normalise to the same ISO date
    assert_eq!(parse_date("29/03/2003").0, "2003-03-29");
    assert_eq!(parse_date("2003-03-29 18:30:00").0, "2003-03-29");
    assert_eq!(parse_date("2003-03-29").0, "2003-03-29");
}

// --- Feature: MCP dispatch layer --------------------------------------------

#[test]
fn scenario_mcp_tool_dispatch_search_matches() {
    // Given the MCP server backed by the data
    let s = store();
    // When the LLM calls the search_matches tool
    let args = json!({ "team": "Flamengo", "opponent": "Fluminense", "limit": 5 });
    let out = brazilian_soccer_mcp::mcp::dispatch_tool(s, "search_matches", &args).unwrap();
    // Then a head-to-head answer is returned
    assert!(out.contains("Head-to-head"), "{}", out);
}

#[test]
fn scenario_mcp_tool_dispatch_players() {
    // Given the MCP server
    let s = store();
    // When the LLM searches Brazilian goalkeepers
    let args = json!({ "nationality": "Brazil", "position": "GK", "sort_by": "overall", "limit": 3 });
    let out = brazilian_soccer_mcp::mcp::dispatch_tool(s, "search_players", &args).unwrap();
    // Then players are returned
    assert!(out.contains("player(s) found"), "{}", out);
}

#[test]
fn scenario_mcp_required_arg_validation() {
    // Given the MCP server
    let s = store();
    // When a required argument is missing
    let err = brazilian_soccer_mcp::mcp::dispatch_tool(s, "competition_standings", &json!({}));
    // Then dispatch returns an error message
    assert!(err.is_err());
}

#[test]
fn scenario_mcp_unknown_tool() {
    // Given the MCP server
    let s = store();
    // When an unknown tool is called
    let err = brazilian_soccer_mcp::mcp::dispatch_tool(s, "does_not_exist", &json!({}));
    // Then it is rejected
    assert!(err.is_err());
}
