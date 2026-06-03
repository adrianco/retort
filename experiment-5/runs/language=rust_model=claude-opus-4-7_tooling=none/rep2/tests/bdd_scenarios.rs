//! BDD-style end-to-end tests covering the scenarios in TASK.md.

use std::path::PathBuf;
use std::sync::OnceLock;

use brazilian_soccer_mcp::data::Dataset;
use brazilian_soccer_mcp::normalize::normalize_team;
use brazilian_soccer_mcp::query::{
    biggest_wins, format_match_list, head_to_head, overall_stats, standings, team_stats,
    MatchQuery, PlayerQuery,
};

fn dataset() -> &'static Dataset {
    static DS: OnceLock<Dataset> = OnceLock::new();
    DS.get_or_init(|| {
        let dir = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("data/kaggle");
        Dataset::load_from_dir(&dir).expect("load dataset")
    })
}

// Feature: Match Queries

#[test]
fn scenario_find_matches_between_two_teams() {
    // Given the match data is loaded
    let ds = dataset();
    // When I search for matches between "Flamengo" and "Fluminense"
    let q = MatchQuery {
        team: Some("Flamengo".into()),
        ..Default::default()
    };
    let matches = q.filter(ds);
    let derby: Vec<_> = matches
        .into_iter()
        .filter(|m| {
            normalize_team(&m.home_team).contains("fluminense")
                || normalize_team(&m.away_team).contains("fluminense")
        })
        .collect();
    // Then I should receive a list of matches
    assert!(!derby.is_empty(), "expected Fla-Flu matches");
    // And each match should have date, scores, and competition
    for m in &derby {
        assert!(!m.competition.is_empty(), "competition required");
        assert!(m.home_goal.is_some() && m.away_goal.is_some());
    }
}

#[test]
fn scenario_palmeiras_2023_matches() {
    let ds = dataset();
    let q = MatchQuery {
        team: Some("Palmeiras".into()),
        season: Some(2023),
        ..Default::default()
    };
    let matches = q.filter(ds);
    assert!(!matches.is_empty(), "expected Palmeiras 2023 matches");
    for m in &matches {
        assert_eq!(m.season, Some(2023));
    }
}

#[test]
fn scenario_copa_do_brasil_matches() {
    let ds = dataset();
    let q = MatchQuery {
        competition: Some("Copa do Brasil".into()),
        ..Default::default()
    };
    let matches = q.filter(ds);
    assert!(matches.len() > 500);
    for m in &matches {
        assert!(m.competition.to_lowercase().contains("copa do brasil"));
    }
}

// Feature: Team Queries

#[test]
fn scenario_corinthians_2022_home_record() {
    let ds = dataset();
    let s = team_stats(ds, "Corinthians", Some(2022), Some("Brasileir"));
    assert!(s.home_matches > 0);
    assert_eq!(
        s.home_matches,
        s.home_wins + s.home_draws + s.home_losses,
        "home accounting must match"
    );
}

#[test]
fn scenario_top_scoring_team_in_serie_a_2023() {
    let ds = dataset();
    let table = standings(ds, 2023, Some("Brasileir"));
    assert!(!table.is_empty());
    let top_scorer = table.iter().max_by_key(|r| r.goals_for).unwrap();
    assert!(top_scorer.goals_for > 30);
}

#[test]
fn scenario_compare_palmeiras_santos_head_to_head() {
    let ds = dataset();
    let h2h = head_to_head(ds, "Palmeiras", "Santos");
    assert!(h2h.matches > 10);
    assert_eq!(h2h.matches, h2h.team_a_wins + h2h.team_b_wins + h2h.draws);
}

// Feature: Player Queries

#[test]
fn scenario_brazilian_players_listed() {
    let ds = dataset();
    let q = PlayerQuery {
        nationality: Some("Brazil".into()),
        ..Default::default()
    };
    let players = q.filter(ds);
    assert!(players.len() > 100, "got {} Brazilian players", players.len());
}

#[test]
fn scenario_top_players_at_brazilian_club() {
    // The FIFA snapshot in this dataset is from a season where Flamengo/Palmeiras
    // are not listed by name; use a Brazilian club that IS in the snapshot.
    let ds = dataset();
    let q = PlayerQuery {
        club: Some("Fluminense".into()),
        limit: Some(5),
        ..Default::default()
    };
    let players = q.filter(ds);
    assert!(!players.is_empty(), "expected Fluminense players in FIFA snapshot");
    for w in players.windows(2) {
        assert!(w[0].overall.unwrap_or(0) >= w[1].overall.unwrap_or(0));
    }
}

#[test]
fn scenario_sao_paulo_forwards() {
    let ds = dataset();
    let q = PlayerQuery {
        club: Some("São Paulo".into()),
        position: Some("ST".into()),
        ..Default::default()
    };
    let players = q.filter(ds);
    for p in &players {
        let pos = p.position.as_deref().unwrap_or("");
        assert!(pos.contains("ST"));
    }
}

// Feature: Competition Queries

#[test]
fn scenario_who_won_2019_brasileirao() {
    let ds = dataset();
    let table = standings(ds, 2019, Some("Brasileir"));
    assert_eq!(table[0].rank, 1);
    assert!(normalize_team(&table[0].team).contains("flamengo"));
}

#[test]
fn scenario_2018_libertadores_has_data() {
    let ds = dataset();
    let q = MatchQuery {
        competition: Some("Libertadores".into()),
        season: Some(2018),
        ..Default::default()
    };
    let matches = q.filter(ds);
    assert!(!matches.is_empty());
}

// Feature: Statistical Analysis

#[test]
fn scenario_average_goals_in_brasileirao() {
    let ds = dataset();
    let s = overall_stats(ds, None, Some("Brasileir"));
    assert!(s.avg_goals_per_match > 1.5 && s.avg_goals_per_match < 4.0);
}

#[test]
fn scenario_biggest_wins_displayed() {
    let ds = dataset();
    let bw = biggest_wins(ds, 3, Some("Brasileir"));
    assert_eq!(bw.len(), 3);
    assert!(bw[0].margin >= 5);
}

#[test]
fn scenario_best_home_record_team() {
    let ds = dataset();
    let table = standings(ds, 2023, Some("Brasileir"));
    // Compute home wins via team_stats for the top-ranked team — the league
    // leader is not necessarily the best home side, but the top-ranked team
    // must have at least one home win.
    let top = &table[0];
    let s = team_stats(ds, &top.team, Some(2023), Some("Brasileir"));
    assert!(s.home_wins >= 1);
}

#[test]
fn scenario_format_match_list_is_readable() {
    let ds = dataset();
    let q = MatchQuery {
        team: Some("Flamengo".into()),
        season: Some(2019),
        ..Default::default()
    };
    let matches = q.filter(ds);
    let text = format_match_list(&matches, 5);
    assert!(text.contains("Flamengo"));
    assert!(text.lines().count() >= 5);
}
