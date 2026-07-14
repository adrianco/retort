// ============================================================================
// CONTEXT: BDD scenarios - Features: Team Queries & Player Queries
//
// Covers TASK.md "Team Queries" and "Player Queries":
//   - "What is Corinthians' home record in 2022?" - 19 home matches,
//     12W 4D 3L, 24 GF, 11 GA. Brasileirao_Matches.csv stops at round 31
//     ("NA" scores afterwards); the last four home results are filled in
//     from BR-Football-Dataset.csv, which is exactly the cross-file merge
//     the spec asks for.
//   - "Compare Palmeiras and Santos head-to-head"
//   - "Find all Brazilian players in the dataset" (827 in fifa_data.csv)
//   - "Who are the highest-rated players at <club>?"
//   - position / rating filters, single-player profile lookup,
//     cross-file query (FIFA club roster + that club's match data).
// ============================================================================

mod common;

use brazilian_soccer_mcp::queries::{
    head_to_head, search_matches, search_players, team_stats, get_player, MatchFilters, PlayerFilters,
};

fn pfilters<'a>() -> PlayerFilters<'a> {
    PlayerFilters { name: None, nationality: None, club: None, position: None, min_overall: None, limit: 20 }
}

#[test]
fn scenario_team_home_record_for_a_season() {
    // GIVEN the match data is loaded
    let ds = common::given_loaded_dataset();

    // WHEN I request Corinthians' record for the 2022 Brasileirão
    let stats = team_stats(ds, "Corinthians", Some(2022), Some("Brasileirão")).unwrap();

    // THEN the home split matches the merged sources exactly (15 played
    // fixtures from Brasileirao_Matches.csv + the 4 late-season results that
    // file lacks, deduplicated in from BR-Football-Dataset.csv)
    let home = &stats["home"];
    assert_eq!(home["matches"], 19);
    assert_eq!(home["wins"], 12);
    assert_eq!(home["draws"], 4);
    assert_eq!(home["losses"], 3);
    assert_eq!(home["goals_for"], 24);
    assert_eq!(home["goals_against"], 11);

    // AND wins + draws + losses always equals matches played
    let overall = &stats["overall"];
    assert_eq!(
        overall["wins"].as_u64().unwrap()
            + overall["draws"].as_u64().unwrap()
            + overall["losses"].as_u64().unwrap(),
        overall["matches"].as_u64().unwrap()
    );
}

#[test]
fn scenario_get_team_statistics_with_breakdown() {
    // GIVEN the match data is loaded
    let ds = common::given_loaded_dataset();

    // WHEN I request statistics for "Palmeiras" without filters
    let stats = team_stats(ds, "Palmeiras", None, None).unwrap();

    // THEN I should receive wins, losses, draws, and goals
    let overall = &stats["overall"];
    for key in ["matches", "wins", "draws", "losses", "goals_for", "goals_against"] {
        assert!(overall[key].is_u64() || overall[key].is_i64(), "missing {}", key);
    }
    assert!(overall["matches"].as_u64().unwrap() > 500);

    // AND a per-competition breakdown covering more than one competition
    let comps = stats["by_competition"].as_array().unwrap();
    assert!(comps.len() >= 2, "Palmeiras should appear in several competitions");
}

#[test]
fn scenario_compare_two_teams_head_to_head() {
    // GIVEN the match data is loaded
    let ds = common::given_loaded_dataset();

    // WHEN I compare Palmeiras and Santos head-to-head
    let h2h = head_to_head(ds, "Palmeiras", "Santos", None).unwrap();

    // THEN totals are consistent and recent matches are listed
    let total = h2h["total_matches"].as_u64().unwrap();
    assert!(total >= 20, "classic SP derby should have many matches, got {}", total);
    assert_eq!(
        h2h["team1_wins"].as_u64().unwrap()
            + h2h["team2_wins"].as_u64().unwrap()
            + h2h["draws"].as_u64().unwrap(),
        total
    );
    assert!(!h2h["recent_matches"].as_array().unwrap().is_empty());
}

#[test]
fn scenario_find_all_brazilian_players() {
    // GIVEN the player data is loaded
    let ds = common::given_loaded_dataset();

    // WHEN I search players with nationality Brazil
    let result = search_players(ds, &PlayerFilters { nationality: Some("Brazil"), limit: 100, ..pfilters() }).unwrap();

    // THEN hundreds of Brazilian players are found, sorted by rating
    assert_eq!(result["total_players_found"], 827);
    let players = result["players"].as_array().unwrap();
    for p in players {
        assert_eq!(p["nationality"], "Brazil");
    }
    // AND the top-rated Brazilian is Neymar Jr (overall 92)
    assert_eq!(players[0]["name"], "Neymar Jr");
    assert_eq!(players[0]["overall"], 92);
}

#[test]
fn scenario_highest_rated_players_at_a_club() {
    // GIVEN the player data is loaded
    let ds = common::given_loaded_dataset();

    // WHEN I ask for players at Grêmio (accent-insensitive: "Gremio")
    let result = search_players(ds, &PlayerFilters { club: Some("Gremio"), limit: 30, ..pfilters() }).unwrap();

    // THEN the Grêmio squad is returned in rating order
    let players = result["players"].as_array().unwrap();
    assert!(players.len() >= 15, "expected a full squad, got {}", players.len());
    let ratings: Vec<i64> = players.iter().map(|p| p["overall"].as_i64().unwrap()).collect();
    for w in ratings.windows(2) {
        assert!(w[0] >= w[1], "players should be sorted by overall desc");
    }
}

#[test]
fn scenario_filter_players_by_position_and_rating() {
    // GIVEN the player data is loaded
    let ds = common::given_loaded_dataset();

    // WHEN I search Brazilian goalkeepers rated at least 85
    let result = search_players(
        ds,
        &PlayerFilters {
            nationality: Some("Brazil"),
            position: Some("GK"),
            min_overall: Some(85),
            ..pfilters()
        },
    )
    .unwrap();

    // THEN every hit is a Brazilian GK rated >= 85, and Alisson is among them
    let players = result["players"].as_array().unwrap();
    assert!(!players.is_empty());
    for p in players {
        assert_eq!(p["position"], "GK");
        assert!(p["overall"].as_i64().unwrap() >= 85);
    }
    assert!(players.iter().any(|p| p["name"] == "Alisson"));
}

#[test]
fn scenario_single_player_profile() {
    // GIVEN the player data is loaded
    let ds = common::given_loaded_dataset();

    // WHEN I ask "Who is Neymar?"
    let p = get_player(ds, "Neymar").unwrap();

    // THEN a full profile is returned
    assert_eq!(p["name"], "Neymar Jr");
    assert_eq!(p["club"], "Paris Saint-Germain");
    assert_eq!(p["overall"], 92);
    assert!(!p["skills"].as_array().unwrap().is_empty());

    // AND an unknown name yields a clear error
    assert!(get_player(ds, "Zzyzx Nobody").is_err());
}

#[test]
fn scenario_cross_file_query_players_and_matches_of_same_club() {
    // GIVEN both player and match data are loaded
    let ds = common::given_loaded_dataset();

    // WHEN I fetch Fluminense's FIFA squad AND Fluminense's match history
    let squad = search_players(ds, &PlayerFilters { club: Some("Fluminense"), ..pfilters() }).unwrap();
    let matches = search_matches(
        ds,
        &MatchFilters {
            team: Some("Fluminense"),
            opponent: None,
            competition: None,
            season: None,
            date_from: None,
            date_to: None,
            limit: 5,
        },
    )
    .unwrap();

    // THEN both sides of the knowledge base answer for the same club
    assert!(squad["total_players_found"].as_u64().unwrap() >= 15);
    assert!(matches["total_matches_found"].as_u64().unwrap() > 500);
}

#[test]
fn scenario_club_name_normalization_links_fifa_to_match_data() {
    // GIVEN the player data is loaded (FIFA spells it "Atlético Paranaense")
    let ds = common::given_loaded_dataset();

    // WHEN I search players using the match-data spelling "Athletico-PR"
    let result = search_players(ds, &PlayerFilters { club: Some("Athletico-PR"), ..pfilters() }).unwrap();

    // THEN the normalizer bridges both spellings
    assert!(
        result["total_players_found"].as_u64().unwrap() >= 15,
        "Athletico-PR should match FIFA club 'Atlético Paranaense'"
    );
}
