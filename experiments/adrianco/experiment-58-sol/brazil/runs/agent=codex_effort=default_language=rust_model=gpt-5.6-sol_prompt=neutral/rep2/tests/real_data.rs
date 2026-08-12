use brazilian_soccer_mcp::{DataStore, SoccerService};
use serde_json::json;
use std::path::PathBuf;

fn data_dir() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("data/kaggle")
}

#[test]
fn loads_every_supplied_dataset_and_accounts_for_incomplete_rows() {
    let (store, report) = DataStore::load(data_dir()).expect("all supplied datasets load");
    assert_eq!(report.files_loaded, 6);
    assert_eq!(report.player_rows, 18_207);
    assert_eq!(report.matches_by_source["Brasileirao_Matches.csv"], 4_098);
    assert_eq!(report.matches_by_source["Brazilian_Cup_Matches.csv"], 1_321);
    assert_eq!(report.matches_by_source["Libertadores_Matches.csv"], 1_253);
    assert_eq!(report.matches_by_source["BR-Football-Dataset.csv"], 10_296);
    assert_eq!(
        report.matches_by_source["novo_campeonato_brasileiro.csv"],
        6_886
    );
    assert_eq!(report.incomplete_matches_skipped, 100);
    assert!(report.duplicate_matches_merged > 1_000);
    assert!(store.matches.len() > 15_000);
}

#[test]
fn answers_match_team_player_competition_and_cross_file_queries() {
    let (store, _) = DataStore::load(data_dir()).unwrap();
    let service = SoccerService::new(store);

    let h2h = service
        .call(
            "search_matches",
            json!({"team":"Flamengo-RJ","opponent":"Fluminense","limit":200}),
        )
        .unwrap();
    assert!(h2h["total"].as_u64().unwrap() > 20);
    assert!(h2h["provenance"]["datasets"].as_array().unwrap().len() >= 2);

    let record = service
        .call(
            "get_team_record",
            json!({"team":"Corinthians","competition":"Brasileirão","season":2022,"venue":"home"}),
        )
        .unwrap();
    assert!(record["record"]["matches"].as_u64().unwrap() >= 10);
    assert_eq!(
        record["record"]["matches"].as_u64().unwrap(),
        record["record"]["wins"].as_u64().unwrap()
            + record["record"]["draws"].as_u64().unwrap()
            + record["record"]["losses"].as_u64().unwrap()
    );

    let players = service
        .call(
            "search_players",
            json!({"nationality":"Brazil","sort":"overall_desc","limit":10}),
        )
        .unwrap();
    assert_eq!(players["total"], 827);
    assert_eq!(players["players"][0]["name"], "Neymar Jr");

    let standings = service
        .call(
            "analyze_competition",
            json!({"competition":"Brasileirão","season":2019,"analysis":"standings","limit":4}),
        )
        .unwrap();
    assert_eq!(standings["data"][0]["team"], "Flamengo-RJ");
    assert_eq!(standings["data"][0]["points"], 90);

    let explicit_standings = service
        .call("get_standings", json!({"season":2019,"limit":4}))
        .unwrap();
    assert_eq!(explicit_standings["data"][0]["team"], "Flamengo-RJ");

    let explicit_h2h = service
        .call(
            "get_head_to_head",
            json!({"team_a":"Flamengo","team_b":"Fluminense"}),
        )
        .unwrap();
    assert!(explicit_h2h["record"]["matches"].as_u64().unwrap() > 20);
}

#[test]
fn natural_language_entry_point_routes_common_questions() {
    let (store, _) = DataStore::load(data_dir()).unwrap();
    let service = SoccerService::new(store);
    let result = service
        .call(
            "ask_soccer",
            json!({"question":"What's the average goals per match in the Brasileirão in 2019?"}),
        )
        .unwrap();
    assert!(result["data"]["goals_per_match"].as_f64().unwrap() > 1.0);

    let champion = service
        .call(
            "ask_soccer",
            json!({"question":"Who won the 2019 Brasileirão?"}),
        )
        .unwrap();
    assert_eq!(champion["data"][0]["team"], "Flamengo-RJ");
    assert_eq!(champion["data"][0]["points"], 90);
}

#[test]
fn applies_date_competition_and_player_attribute_filters_and_aggregates_stats() {
    let (store, _) = DataStore::load(data_dir()).unwrap();
    let service = SoccerService::new(store);

    let matches = service
        .call(
            "search_matches",
            json!({
                "team":"Flamengo",
                "competition":"Copa do Brasil",
                "date_from":"2018-01-01",
                "date_to":"2023-12-31",
                "limit":200
            }),
        )
        .unwrap();
    assert!(matches["total"].as_u64().unwrap() > 0);
    for item in matches["matches"].as_array().unwrap() {
        assert_eq!(item["competition"], "Copa do Brasil");
        let date = item["date"].as_str().unwrap();
        assert!(("2018-01-01"..="2023-12-31").contains(&date));
    }

    let libertadores = service
        .call(
            "search_matches",
            json!({"competition":"Libertadores","season":2019,"limit":200}),
        )
        .unwrap();
    assert!(libertadores["total"].as_u64().unwrap() > 0);

    let players = service
        .call(
            "search_players",
            json!({"name":"Neymar","nationality":"Brazil","club":"Paris Saint-Germain"}),
        )
        .unwrap();
    assert_eq!(players["players"][0]["name"], "Neymar Jr");
    assert_eq!(players["players"][0]["overall"], 92);
    assert!(players["players"][0]["attributes"]["Dribbling"]
        .as_u64()
        .is_some());

    let summary = service
        .call(
            "analyze_competition",
            json!({"competition":"Brasileirão","season":2019,"analysis":"summary"}),
        )
        .unwrap();
    assert_eq!(summary["data"]["matches"], 380);
    assert!(summary["data"]["goals_per_match"].as_f64().unwrap() > 2.0);
}
