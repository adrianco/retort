use brasileirao_mcp::{MatchFilter, SoccerStore};
use chrono::NaiveDate;
use std::path::PathBuf;
use std::sync::OnceLock;
use std::time::Instant;

fn store() -> &'static SoccerStore {
    static STORE: OnceLock<SoccerStore> = OnceLock::new();
    STORE.get_or_init(|| {
        SoccerStore::load(PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("data/kaggle"))
            .expect("all bundled datasets should load")
    })
}

#[test]
fn given_bundled_data_when_loaded_then_all_six_files_are_covered() {
    let counts = store().counts();
    assert_eq!(counts.matches_by_source.len(), 5);
    assert_eq!(counts.players_by_source.len(), 1);
    assert!(
        counts.total_matches >= 23_000,
        "loaded {}",
        counts.total_matches
    );
    assert_eq!(counts.total_players, 18_207);
    for source in [
        "Brasileirao_Matches.csv",
        "Brazilian_Cup_Matches.csv",
        "Libertadores_Matches.csv",
        "BR-Football-Dataset.csv",
        "novo_campeonato_brasileiro.csv",
    ] {
        assert!(
            counts.matches_by_source.get(source).copied().unwrap_or(0) > 0,
            "{source} was not loaded"
        );
    }
}

#[test]
fn given_name_variations_when_searching_then_cross_file_matches_are_found() {
    let plain = store().search_matches(
        &MatchFilter {
            team: Some("São Paulo"),
            ..Default::default()
        },
        1000,
    );
    let suffix = store().search_matches(
        &MatchFilter {
            team: Some("Sao Paulo-SP"),
            ..Default::default()
        },
        1000,
    );
    let fc = store().search_matches(
        &MatchFilter {
            team: Some("São Paulo FC"),
            ..Default::default()
        },
        1000,
    );
    assert!(!plain.is_empty());
    assert_eq!(plain.len(), suffix.len());
    assert_eq!(plain.len(), fc.len());
    assert!(plain.iter().any(|m| m.source == "Brasileirao_Matches.csv"));
    assert!(plain
        .iter()
        .any(|m| m.source == "novo_campeonato_brasileiro.csv"));
}

#[test]
fn given_two_rivals_when_compared_then_every_result_contains_both_teams() {
    let (summary, matches) = store().head_to_head("Flamengo", "Fluminense", None, None);
    assert!(summary.matches > 10);
    assert_eq!(
        summary.matches,
        summary.team_a_wins + summary.team_b_wins + summary.draws
    );
    assert_eq!(matches.len(), summary.matches as usize);
    assert!(matches.iter().all(|m| {
        let names = format!("{} {}", m.home_team, m.away_team).to_lowercase();
        names.contains("flamengo") && names.contains("fluminense")
    }));
}

#[test]
fn given_a_team_and_season_when_aggregated_then_record_is_consistent() {
    let stats = store().team_statistics("Palmeiras", Some(2023), Some("Brasileirão"), None);
    assert!(stats.matches > 0);
    assert_eq!(stats.matches, stats.wins + stats.draws + stats.losses);
    assert_eq!(stats.matches, stats.home_matches + stats.away_matches);
    assert_eq!(stats.points, stats.wins * 3 + stats.draws);
}

#[test]
fn given_a_season_when_calculating_standings_then_points_are_sorted() {
    let table = store().standings(2019, "Brasileirão");
    assert_eq!(table.len(), 20, "2019 Série A must have exactly 20 clubs");
    assert_eq!(table[0].team, "Flamengo");
    assert!(table
        .windows(2)
        .all(|pair| pair[0].stats.points >= pair[1].stats.points));
}

#[test]
fn given_overlapping_sources_when_calculating_2019_then_fixtures_are_reconciled() {
    let table = store().standings(2019, "Brasileirão");
    let flamengo = table
        .iter()
        .find(|standing| standing.team == "Flamengo")
        .expect("Flamengo should be present");
    assert_eq!(flamengo.stats.matches, 38);
    assert_eq!(flamengo.stats.wins, 28);
    assert_eq!(flamengo.stats.draws, 6);
    assert_eq!(flamengo.stats.losses, 4);
    assert_eq!(flamengo.stats.points, 90);

    let names: Vec<_> = table
        .iter()
        .map(|standing| standing.team.as_str())
        .collect();
    assert_eq!(
        names
            .iter()
            .filter(|name| name.contains("Atletico"))
            .count(),
        1
    );
    assert_eq!(
        names
            .iter()
            .filter(|name| name.contains("Athletico"))
            .count(),
        1
    );
}

#[test]
fn given_player_filters_when_searching_then_results_match_every_filter() {
    let players = store().search_players(None, Some("Brazil"), None, None, Some(85), 100);
    assert!(!players.is_empty());
    assert!(players
        .iter()
        .all(|p| p.nationality == "Brazil" && p.overall.unwrap_or(0) >= 85));
    let neymar = store().search_players(Some("Neymar"), None, None, None, None, 10);
    assert!(neymar.iter().any(|p| p.name.contains("Neymar")));
}

#[test]
fn given_date_competition_and_stage_filters_when_searching_then_all_apply() {
    let start = NaiveDate::from_ymd_opt(2018, 1, 1).unwrap();
    let end = NaiveDate::from_ymd_opt(2018, 12, 31).unwrap();
    let rows = store().search_matches(
        &MatchFilter {
            competition: Some("Libertadores"),
            start_date: Some(start),
            end_date: Some(end),
            stage: Some("final"),
            ..Default::default()
        },
        100,
    );
    assert!(!rows.is_empty());
    assert!(rows
        .iter()
        .all(|m| m.date >= start && m.date <= end && m.competition.contains("Libertadores")));
}

#[test]
fn given_cross_file_team_overview_then_matches_and_players_are_joined() {
    // The FIFA snapshot does not necessarily contain every modern Brazilian club; this
    // assertion uses a club represented in both the player and match datasets.
    let overview = store().team_overview("Internacional", None);
    assert!(overview.statistics.matches > 100);
    assert!(!overview.competitions.is_empty());
    assert!(!overview.players.is_empty());
    assert!(!overview.recent_matches.is_empty());
}

#[test]
fn representative_queries_stay_inside_the_performance_budget() {
    let start = Instant::now();
    // Four representative sets exercise 20 user questions while keeping the test
    // aligned with the specification's per-query latency budget.
    for _ in 0..4 {
        let _ = store().search_matches(
            &MatchFilter {
                team: Some("Flamengo"),
                season: Some(2023),
                ..Default::default()
            },
            100,
        );
        let _ =
            store().team_statistics("Corinthians", Some(2022), Some("Brasileirão"), Some("home"));
        let _ = store().head_to_head("Palmeiras", "Santos", None, None);
        let _ = store().search_players(None, Some("Brazil"), None, None, Some(80), 50);
        let _ = store().standings(2019, "Brasileirão");
    }
    assert!(
        start.elapsed().as_secs_f64() < 5.0,
        "representative query suite took {:?}",
        start.elapsed()
    );
}
