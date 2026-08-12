use brazilian_soccer_mcp::{
    DataStore, SoccerService,
    json::{Json, object},
};
use std::{
    path::PathBuf,
    sync::OnceLock,
    time::{Duration, Instant},
};

fn service() -> &'static SoccerService {
    static SERVICE: OnceLock<SoccerService> = OnceLock::new();
    SERVICE.get_or_init(|| {
        let path = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("data/kaggle");
        SoccerService::new(DataStore::load(path).expect("all bundled datasets should load"))
    })
}

fn call(name: &str, args: Json) -> Json {
    service()
        .call_tool(name, &args)
        .unwrap_or_else(|error| panic!("{name} failed: {error}"))
        .structured
}

#[test]
fn loads_every_bundled_dataset_with_expected_source_rows() {
    let store = &service().store;
    assert_eq!(store.reports.len(), 6);
    let expected = [
        ("Brasileirao_Matches.csv", 4_180),
        ("Brazilian_Cup_Matches.csv", 1_337),
        ("Libertadores_Matches.csv", 1_255),
        ("BR-Football-Dataset.csv", 10_296),
        ("novo_campeonato_brasileiro.csv", 6_886),
        ("fifa_data.csv", 18_207),
    ];
    for (file, rows) in expected {
        let report = store
            .reports
            .iter()
            .find(|report| report.file == file)
            .unwrap();
        assert_eq!(report.rows, rows, "unexpected source row count for {file}");
        assert!(
            report.loaded > 0,
            "{file} did not produce queryable records"
        );
    }
    assert_eq!(store.players.len(), 18_207);
    assert!(store.matches.len() > 23_000);
}

#[test]
fn answers_more_than_twenty_representative_questions() {
    let cases = vec![
        ("dataset_info", object([] as [(&str, Json); 0])),
        (
            "search_matches",
            object([("team", "Flamengo".into()), ("limit", 5.into())]),
        ),
        (
            "search_matches",
            object([
                ("team", "Palmeiras".into()),
                ("season", 2023.into()),
                ("limit", 5.into()),
            ]),
        ),
        (
            "search_matches",
            object([
                ("team", "Flamengo".into()),
                ("opponent", "Fluminense".into()),
                ("limit", 5.into()),
            ]),
        ),
        (
            "search_matches",
            object([
                ("competition", "Copa do Brasil".into()),
                ("stage", "final".into()),
                ("limit", 5.into()),
            ]),
        ),
        (
            "search_matches",
            object([
                ("date_from", "2019-01-01".into()),
                ("date_to", "2019-12-31".into()),
                ("limit", 5.into()),
            ]),
        ),
        (
            "search_matches",
            object([
                ("source", "novo_campeonato".into()),
                ("season", 2003.into()),
                ("limit", 5.into()),
            ]),
        ),
        (
            "team_statistics",
            object([
                ("team", "Corinthians".into()),
                ("season", 2022.into()),
                ("venue", "home".into()),
            ]),
        ),
        (
            "team_statistics",
            object([
                ("team", "Palmeiras-SP".into()),
                ("competition", "Brasileirão".into()),
            ]),
        ),
        (
            "team_overview",
            object([("team", "Grêmio".into()), ("season", 2018.into())]),
        ),
        (
            "head_to_head",
            object([
                ("team_a", "Flamengo".into()),
                ("team_b", "Fluminense".into()),
                ("limit", 5.into()),
            ]),
        ),
        (
            "head_to_head",
            object([
                ("team_a", "Palmeiras".into()),
                ("team_b", "Santos".into()),
                ("limit", 5.into()),
            ]),
        ),
        (
            "search_derbies",
            object([("season", 2023.into()), ("limit", 10.into())]),
        ),
        (
            "search_players",
            object([("name", "Neymar".into()), ("limit", 5.into())]),
        ),
        (
            "search_players",
            object([("nationality", "Brazil".into()), ("limit", 5.into())]),
        ),
        (
            "search_players",
            object([("club", "Grêmio".into()), ("limit", 5.into())]),
        ),
        (
            "search_players",
            object([
                ("nationality", "Brazil".into()),
                ("position", "forward".into()),
                ("min_overall", 80.into()),
                ("limit", 5.into()),
            ]),
        ),
        (
            "standings",
            object([
                ("season", 2019.into()),
                ("competition", "Brasileirão".into()),
                ("limit", 20.into()),
            ]),
        ),
        (
            "competition_statistics",
            object([
                ("competition", "Brasileirão".into()),
                ("season", 2023.into()),
            ]),
        ),
        (
            "competition_statistics",
            object([("competition", "Copa Libertadores".into())]),
        ),
        (
            "team_rankings",
            object([
                ("competition", "Brasileirão".into()),
                ("season", 2022.into()),
                ("venue", "home".into()),
                ("minimum_matches", 10.into()),
            ]),
        ),
        (
            "team_rankings",
            object([
                ("competition", "Brasileirão".into()),
                ("venue", "away".into()),
                ("minimum_matches", 20.into()),
            ]),
        ),
        (
            "biggest_wins",
            object([
                ("competition", "Copa Libertadores".into()),
                ("limit", 10.into()),
            ]),
        ),
    ];
    assert!(cases.len() >= 20);
    for (name, args) in cases {
        let _ = call(name, args);
    }
}

#[test]
fn standings_and_normalized_identity_are_correct() {
    let result = call(
        "standings",
        object([
            ("season", 2019.into()),
            ("competition", "Brasileirão".into()),
            ("limit", 3.into()),
        ]),
    );
    let Json::Array(rows) = result.get("standings").unwrap() else {
        panic!()
    };
    assert_eq!(rows[0].get("team").and_then(Json::as_str), Some("Flamengo"));
    assert_eq!(rows[0].get("points").and_then(Json::as_i64), Some(90));
    assert_eq!(rows[0].get("matches").and_then(Json::as_i64), Some(38));

    let plain = call(
        "team_statistics",
        object([("team", "São Paulo".into()), ("season", 2023.into())]),
    );
    let suffixed = call(
        "team_statistics",
        object([("team", "Sao Paulo-SP".into()), ("season", 2023.into())]),
    );
    assert_eq!(plain.get("matches"), suffixed.get("matches"));
    assert_eq!(plain.get("goals_for"), suffixed.get("goals_for"));
}

#[test]
fn warm_queries_meet_the_lookup_performance_target() {
    let _ = service();
    let started = Instant::now();
    for _ in 0..10 {
        let result = call(
            "head_to_head",
            object([
                ("team_a", "Flamengo".into()),
                ("team_b", "Fluminense".into()),
                ("limit", 20.into()),
            ]),
        );
        assert!(result.get("matches").and_then(Json::as_i64).unwrap() > 0);
    }
    assert!(
        started.elapsed() < Duration::from_secs(2),
        "ten warm lookups took {:?}",
        started.elapsed()
    );
}
