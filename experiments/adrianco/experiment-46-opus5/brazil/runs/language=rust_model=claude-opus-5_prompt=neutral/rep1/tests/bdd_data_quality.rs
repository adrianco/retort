//! Feature: Data quality handling
//!
//! The specification calls out three hazards in the raw files — team name
//! variations, mixed date formats and UTF-8 Portuguese text — plus the implicit
//! hazard of six files that overlap. These scenarios pin down the behaviour.

mod common;

use common::*;
use serde_json::json;

use brazilian_soccer_mcp::model::{Competition, Source};
use brazilian_soccer_mcp::normalize::normalize_team;

#[test]
fn scenario_team_name_variations_resolve_to_one_club() {
    // GIVEN the match data is loaded
    let graph = given_the_knowledge_graph_is_loaded();

    // WHEN the same club is spelled the way each source file spells it
    let spellings = [
        "Palmeiras",
        "Palmeiras-SP",
        "Palmeiras - SP",
        "SE Palmeiras",
        "palmeiras",
        "PALMEIRAS",
    ];

    // THEN all of them resolve to the same knowledge-graph node
    let ids: Vec<_> = spellings
        .iter()
        .map(|name| {
            graph
                .require_team(name)
                .unwrap_or_else(|error| panic!("'{name}' should resolve: {error}"))
        })
        .collect();
    assert!(ids.windows(2).all(|pair| pair[0] == pair[1]));
    assert_eq!(graph.team(ids[0]).key, "palmeiras-SP");
}

#[test]
fn scenario_accented_and_plain_spellings_are_equivalent() {
    let graph = given_the_knowledge_graph_is_loaded();

    for (accented, plain) in [
        ("São Paulo", "Sao Paulo"),
        ("Grêmio", "Gremio"),
        ("Avaí", "Avai"),
        ("Vitória", "Vitoria"),
        ("Atlético-MG", "Atletico-MG"),
        ("Ceará", "Ceara"),
    ] {
        let left = graph.require_team(accented).unwrap();
        let right = graph.require_team(plain).unwrap();
        assert_eq!(
            left, right,
            "'{accented}' and '{plain}' must be the same club"
        );
    }
}

#[test]
fn scenario_club_naming_conventions_across_files_are_merged() {
    let graph = given_the_knowledge_graph_is_loaded();

    // Long-form, abbreviated and state-suffixed spellings of the same clubs.
    for (variant, canonical_key) in [
        ("Sport Club Corinthians Paulista", "corinthians-SP"),
        ("EC Bahia", "bahia-BA"),
        ("Sport Club do Recife", "sport-PE"),
        ("Ceará Sporting Club", "ceara-CE"),
        ("Vasco Da Gama RJ", "vasco-RJ"),
        ("Athletico Paranaense", "athletico-PR"),
        ("Atlético-PR", "athletico-PR"),
        ("Red Bull Bragantino", "bragantino-SP"),
        ("Fortaleza FC", "fortaleza-CE"),
    ] {
        let id = graph
            .require_team(variant)
            .unwrap_or_else(|error| panic!("'{variant}' should resolve: {error}"));
        assert_eq!(graph.team(id).key, canonical_key, "for '{variant}'");
    }
}

#[test]
fn scenario_clubs_that_share_a_base_name_stay_distinct() {
    let graph = given_the_knowledge_graph_is_loaded();

    let mineiro = graph.require_team("América-MG").unwrap();
    let potiguar = graph.require_team("América-RN").unwrap();
    assert_ne!(mineiro, potiguar);

    // Three different Atléticos must not be merged either.
    let mg = graph.require_team("Atlético Mineiro").unwrap();
    let go = graph.require_team("Atlético Goianiense").unwrap();
    let pr = graph.require_team("Athletico-PR").unwrap();
    assert_ne!(mg, go);
    assert_ne!(mg, pr);
    assert_ne!(go, pr);
}

#[test]
fn scenario_all_three_date_formats_are_parsed() {
    let graph = given_the_knowledge_graph_is_loaded();

    // DD/MM/YYYY (novo_campeonato_brasileiro.csv)
    let earliest = graph
        .matches
        .iter()
        .filter(|m| m.source == Source::NovoBrasileirao)
        .filter_map(|m| m.date)
        .min()
        .expect("the historical file should have dates");
    assert_eq!(earliest.to_string(), "2003-03-29");

    // YYYY-MM-DD HH:MM:SS (Brasileirao_Matches.csv)
    let with_kickoff = graph
        .matches
        .iter()
        .filter(|m| m.source == Source::Brasileirao)
        .find(|m| m.time.is_some())
        .expect("kick-off times should survive parsing");
    assert!(with_kickoff.time.as_deref().unwrap().contains(':'));

    // YYYY-MM-DD (BR-Football-Dataset.csv)
    let latest = graph
        .matches
        .iter()
        .filter(|m| m.source == Source::BrFootball)
        .filter_map(|m| m.date)
        .max()
        .unwrap();
    assert_eq!(latest.year, 2023);

    // AND every match that has a date has a sane one
    for m in &graph.matches {
        if let Some(date) = m.date {
            assert!((2003..=2024).contains(&date.year), "bad date {date}");
            assert!((1..=12).contains(&date.month));
            assert!((1..=31).contains(&date.day));
        }
    }
}

#[test]
fn scenario_utf8_portuguese_text_survives_the_pipeline() {
    let graph = given_the_knowledge_graph_is_loaded();

    let accented_clubs = graph
        .teams
        .iter()
        .filter(|team| !team.name.is_ascii())
        .count();
    assert!(
        accented_clubs > 20,
        "Portuguese club names should keep their accents"
    );

    let answer = when_i_call("team_profile", json!({ "team": "Gremio" }));
    assert_eq!(as_str(&answer.data, "team"), "Grêmio");

    let players = when_i_call(
        "search_players",
        json!({ "nationality": "Brazil", "limit": 200 }),
    );
    assert!(as_array(&players.data, "players")
        .iter()
        .any(|player| !as_str(player, "name").is_ascii()));
}

#[test]
fn scenario_unplayed_fixtures_are_reported_as_such() {
    let graph = given_the_knowledge_graph_is_loaded();

    // The Brasileirão file carries "NA" scores: 81 in the part-scraped 2022
    // season plus one in 2016.
    let unplayed = graph
        .matches
        .iter()
        .filter(|m| m.source == Source::Brasileirao && !m.played())
        .count();
    assert_eq!(unplayed, 82);
    assert_eq!(
        graph
            .matches
            .iter()
            .filter(|m| m.source == Source::Brasileirao && m.season == 2022 && !m.played())
            .count(),
        81
    );

    // Those rows never contribute to a record ...
    let stats = when_i_call(
        "team_stats",
        json!({ "team": "Corinthians", "season": 2022, "competition": "Serie A", "include_all_sources": true }),
    );
    assert_eq!(
        as_i64(&stats.data, "record.matches"),
        as_i64(&stats.data, "record.wins")
            + as_i64(&stats.data, "record.draws")
            + as_i64(&stats.data, "record.losses")
    );

    // ... and when listed they are labelled honestly rather than as 0-0.
    let listed = when_i_call(
        "search_matches",
        json!({
            "team": "Flamengo",
            "opponent": "Corinthians",
            "season": 2022,
            "include_all_sources": true,
            "limit": 0
        }),
    );
    then_text_contains(&listed.text, "no result recorded");
}

#[test]
fn scenario_every_source_file_is_loaded_and_queryable() {
    let graph = given_the_knowledge_graph_is_loaded();

    assert_eq!(graph.reports.len(), 6);
    for report in &graph.reports {
        assert!(
            report.rows_used > 1_000,
            "{} contributed only {} rows",
            report.source.file_name(),
            report.rows_used
        );
        assert!(
            report.rows_skipped * 100 < report.rows_read,
            "{} skipped too many rows",
            report.source.file_name()
        );
    }

    // Every match source is reachable through the graph.
    for source in Source::MATCH_SOURCES {
        assert!(
            graph.matches.iter().any(|m| m.source == source),
            "no matches from {}",
            source.file_name()
        );
    }
}

#[test]
fn scenario_overlapping_files_produce_one_canonical_view() {
    let graph = given_the_knowledge_graph_is_loaded();

    // Each competition-season is served by exactly one file.
    let mut seen: std::collections::HashMap<(Competition, i32), Source> =
        std::collections::HashMap::new();
    for m in graph.matches.iter().filter(|m| m.canonical) {
        let entry = seen.entry((m.competition, m.season)).or_insert(m.source);
        assert_eq!(
            *entry,
            m.source,
            "{:?} {} mixes {} and {}",
            m.competition,
            m.season,
            entry.file_name(),
            m.source.file_name()
        );
    }

    // Série A 2019 is present in three files but canonical in one.
    let serie_a_2019: Vec<_> = graph
        .matches
        .iter()
        .filter(|m| m.competition == Competition::SerieA && m.season == 2019)
        .collect();
    assert!(serie_a_2019.len() > 1_000);
    assert_eq!(serie_a_2019.iter().filter(|m| m.canonical).count(), 380);

    // The 2022 season falls back to the more complete file because the
    // preferred one was scraped mid-season.
    assert_eq!(seen[&(Competition::SerieA, 2019)], Source::Brasileirao);
    assert_eq!(seen[&(Competition::SerieA, 2022)], Source::BrFootball);
    assert_eq!(seen[&(Competition::SerieA, 2005)], Source::NovoBrasileirao);
    assert_eq!(
        seen[&(Competition::CopaDoBrasil, 2019)],
        Source::BrazilianCup
    );
}

#[test]
fn scenario_normalization_is_deterministic_for_unseen_names() {
    // Unit-level check that the folding rules hold outside the loaded data.
    assert_eq!(normalize_team("Ipatinga - MG", None).id(), "ipatinga-MG");
    assert_eq!(normalize_team("Ipatinga", Some("MG")).id(), "ipatinga-MG");
    assert_eq!(normalize_team("Nacional (URU)", None).id(), "nacional-URU");
    assert_eq!(normalize_team("A.s.a. - AL", None).id(), "asa-AL");
    assert_eq!(
        normalize_team("Independiente Del Valle", None).id(),
        normalize_team("Independiente del Valle", None).id()
    );
}

#[test]
fn scenario_graph_edges_connect_the_entity_types() {
    let graph = given_the_knowledge_graph_is_loaded();

    let answer = when_i_call(
        "graph_neighbors",
        json!({ "node_type": "team", "name": "Santos", "limit": 2 }),
    );
    let relations: Vec<&str> = as_array(&answer.data, "edges")
        .iter()
        .map(|edge| as_str(edge, "relation"))
        .collect();
    assert!(relations.contains(&"hosted"));
    assert!(relations.contains(&"visited"));
    assert!(relations.contains(&"has_player"), "cross-file edge missing");

    // A match node links back to both clubs and its competition.
    let match_id = graph
        .matches
        .iter()
        .find(|m| m.canonical && m.played())
        .unwrap()
        .id;
    let from_match = when_i_call(
        "graph_neighbors",
        json!({ "node_type": "match", "name": match_id.to_string() }),
    );
    let relations: Vec<&str> = as_array(&from_match.data, "edges")
        .iter()
        .map(|edge| as_str(edge, "relation"))
        .collect();
    assert_eq!(relations, vec!["home_team", "away_team", "part_of"]);
}
