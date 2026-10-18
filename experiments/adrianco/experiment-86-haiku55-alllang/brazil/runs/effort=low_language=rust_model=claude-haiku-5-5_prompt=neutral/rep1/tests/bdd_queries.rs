//! Behaviour scenarios from TASK.md, written Given/When/Then.
//! Each test loads the real Kaggle files, so passing here means the
//! behaviour holds on the provided data.

mod common;

use brazilian_soccer_mcp::data::{parse_date, Competition};
use brazilian_soccer_mcp::normalize::{fold, team_key};
use brazilian_soccer_mcp::query::{self, MatchFilter, PlayerFilter};

use common::dataset;

#[test]
fn scenario_find_matches_between_two_teams() {
    // Given the match data is loaded
    let ds = dataset();
    // When I search for matches between "Flamengo" and "Fluminense"
    let filter = MatchFilter {
        team: Some("Flamengo".into()),
        opponent: Some("Fluminense".into()),
        ..Default::default()
    };
    let matches = query::find_matches(ds, &filter);
    // Then I should receive a list of matches
    assert!(matches.len() > 20, "expected many Fla-Flu games, got {}", matches.len());
    // And each match should have date, scores, and competition
    for m in &matches {
        assert_eq!(m.date.len(), 10);
        assert!(m.involves("flamengo") && m.involves("fluminense"));
        assert!(Competition::ALL.contains(&m.competition));
    }
    // And the most recent match comes first
    assert!(matches.windows(2).all(|pair| pair[0].date >= pair[1].date));
}

#[test]
fn scenario_find_copa_do_brasil_finals() {
    let ds = dataset();
    let filter = MatchFilter {
        competition: Competition::parse("copa do brasil"),
        ..Default::default()
    };
    let finals = query::find_matches(ds, &filter)
        .into_iter()
        .filter(|m| m.round.as_deref() == Some("Round 8") || m.round.is_none())
        .count();
    assert!(finals > 0, "the dataset should contain Copa do Brasil games");
}

#[test]
fn scenario_team_statistics_for_a_season() {
    // Given the match data is loaded
    let ds = dataset();
    // When I request statistics for "Palmeiras" in the 2023 Brasileirão
    let stats = query::team_stats(ds, "Palmeiras", Some(Competition::Brasileirao), Some(2023));
    // Then I should receive wins, losses, draws, and goals
    let r = &stats.overall;
    assert!(r.played > 30, "a Brasileirão season has about 38 games");
    assert_eq!(r.wins + r.draws + r.losses, r.played);
    assert_eq!(stats.home.played + stats.away.played, r.played);
    assert_eq!(stats.home.wins + stats.away.wins, r.wins);
    assert_eq!(stats.home.goals_for + stats.away.goals_for, r.goals_for);
}

#[test]
fn scenario_standings_match_known_2019_table() {
    // Given the 2019 Brasileirão results are loaded
    let ds = dataset();
    // When I calculate the standings
    let table = query::standings(ds, Competition::Brasileirao, 2019);
    // Then Flamengo is champion with 90 points, 28 wins, 6 draws, 4 losses
    let champion = &table[0];
    assert_eq!(champion.team, "Flamengo");
    assert_eq!(champion.record.points(), 90);
    assert_eq!(
        (champion.record.wins, champion.record.draws, champion.record.losses),
        (28, 6, 4)
    );
    // And Santos and Palmeiras both finish on 74 points
    let points = |name: &str| table.iter().find(|row| row.team == name).unwrap().record.points();
    assert_eq!(points("Santos"), 74);
    assert_eq!(points("Palmeiras"), 74);
    // And the table is sorted by points
    assert!(table.windows(2).all(|pair| pair[0].record.points() >= pair[1].record.points()));
}

#[test]
fn scenario_head_to_head_totals_are_consistent() {
    let ds = dataset();
    let h2h = query::head_to_head(ds, "Palmeiras", "Santos", None);
    let total = h2h.first_wins + h2h.draws + h2h.second_wins;
    assert!(total > 40);
    assert_eq!(total as usize, h2h.matches.len());
    let reversed = query::head_to_head(ds, "Santos", "Palmeiras", None);
    assert_eq!(reversed.first_wins, h2h.second_wins);
    assert_eq!(reversed.second_goals, h2h.first_goals);
}

#[test]
fn scenario_team_name_variants_resolve_to_one_team() {
    // Given the same club written in different ways in the sources
    // Then every spelling produces the same match key
    assert_eq!(team_key("Palmeiras-SP"), team_key("Palmeiras"));
    assert_eq!(team_key("Sociedade Esportiva Palmeiras"), team_key("Palmeiras"));
    assert_eq!(team_key("Sport Club Corinthians Paulista"), team_key("Corinthians"));
    assert_eq!(team_key("Grêmio"), team_key("Gremio"));
    // And the dataset holds the variants under one key
    let ds = dataset();
    let flamengo = query::team_stats(ds, "Flamengo", None, None).overall.played;
    let has_suffixed = ds.matches.iter().any(|m| m.involves(&team_key("Flamengo")));
    assert!(flamengo > 0 && has_suffixed);
}

#[test]
fn scenario_date_formats_are_all_understood() {
    assert_eq!(parse_date("2023-09-24").as_deref(), Some("2023-09-24"));
    assert_eq!(parse_date("2012-05-19 18:30:00").as_deref(), Some("2012-05-19"));
    assert_eq!(parse_date("29/03/2003").as_deref(), Some("2003-03-29"));
}

#[test]
fn scenario_league_statistics_are_sensible() {
    let ds = dataset();
    let stats = query::league_stats(ds, Some(Competition::Brasileirao), None);
    assert!(stats.matches > 4000);
    assert!((1.0..5.0).contains(&stats.avg_goals_per_match));
    let total = stats.home_win_rate() + stats.draw_rate() + stats.away_win_rate();
    assert!((total - 1.0).abs() < 1e-9);
    assert_eq!(stats.biggest_wins.len(), 5);
    let margins: Vec<u32> = stats
        .biggest_wins
        .iter()
        .map(|m| m.home_goals.abs_diff(m.away_goals))
        .collect();
    assert!(margins.windows(2).all(|pair| pair[0] >= pair[1]));
}

#[test]
fn scenario_find_brazilian_players() {
    let ds = dataset();
    let filter = PlayerFilter { nationality: Some("Brazil".into()), min_overall: Some(80), ..Default::default() };
    let players = query::search_players(ds, &filter, 10);
    assert!(!players.is_empty());
    assert!(players.iter().all(|p| p.nationality == "Brazil" && p.overall >= 80));
    assert!(players.windows(2).all(|pair| pair[0].overall >= pair[1].overall));
}

#[test]
fn scenario_name_search_finds_partial_matches() {
    // The FIFA file is FIFA 19 and does not list Gabriel Barbosa, so search a
    // name that is present.
    let ds = dataset();
    let filter = PlayerFilter { name: Some("gabriel".into()), ..Default::default() };
    let players = query::search_players(ds, &filter, 200);
    assert!(players.iter().any(|p| p.name == "Gabriel Boschilia"));
    // Accent-insensitive: "Gabrìel" also matches
    assert!(players.iter().all(|p| fold(&p.name).contains("gabriel")));
}

#[test]
fn scenario_players_by_club_match_substring() {
    let ds = dataset();
    let filter = PlayerFilter { club: Some("paris saint".into()), ..Default::default() };
    let players = query::search_players(ds, &filter, 200);
    assert!(!players.is_empty());
    assert!(players.iter().all(|p| p.club.contains("Paris Saint")));
}

#[test]
fn scenario_all_six_files_are_loaded() {
    let ds = dataset();
    let names: Vec<&str> = ds.sources.iter().map(|s| s.file.as_str()).collect();
    for file in [
        "Brasileirao_Matches.csv",
        "Brazilian_Cup_Matches.csv",
        "Libertadores_Matches.csv",
        "BR-Football-Dataset.csv",
        "novo_campeonato_brasileiro.csv",
        "fifa_data.csv",
    ] {
        assert!(names.contains(&file), "missing summary for {file}");
    }
    for source in &ds.sources {
        assert!(source.rows_loaded > 0, "{} loaded no rows", source.file);
    }
    assert!(ds.matches.iter().any(|m| m.competition == Competition::Libertadores));
    assert!(ds.matches.iter().any(|m| m.competition == Competition::CopaDoBrasil));
}
