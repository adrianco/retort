//! Integration tests against the real, checked-in datasets under
//! `data/kaggle/`. These confirm all six files load without error, with
//! the row counts documented in TASK.md, and that cross-cutting queries
//! (team-name normalization, head-to-head, standings, player search)
//! behave sensibly end to end.

use std::path::PathBuf;

use brazilian_soccer_mcp::model::{Competition, Venue};
use brazilian_soccer_mcp::store::{MatchFilter, PlayerFilter, PlayerSort};

fn data_dir() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("data/kaggle")
}

// Given the six checked-in Kaggle CSV files
// When loading them all into a knowledge base
// Then every file's rows are present with the documented counts, minus the
// handful of rows with no recorded result (goals logged as "NA" or "-",
// e.g. the Brasileirao 2016 Chapecoense fixture never played after the
// team's air disaster, and an abandoned Libertadores fixture)
#[test]
fn test_given_all_dataset_files_when_loading_then_row_counts_match_specification() {
    let kb = brazilian_soccer_mcp::load_from_dir(&data_dir()).expect("datasets should load");

    let count = |c: Competition| kb.matches.iter().filter(|m| m.competition == c).count();
    assert_eq!(count(Competition::Brasileirao), 4180 - 82);
    assert_eq!(count(Competition::CopaDoBrasil), 1337 - 16);
    assert_eq!(count(Competition::Libertadores), 1255 - 2);
    assert_eq!(count(Competition::ExtendedStats), 10296);
    assert_eq!(count(Competition::HistoricalBrasileirao), 6886);
    assert_eq!(kb.players.len(), 18207);
}

// Given the loaded Brasileirao dataset
// When finding matches for a team using its bare name (no state suffix)
// Then matches recorded with the state-suffixed spelling are still found
#[test]
fn test_given_state_suffixed_data_when_finding_matches_by_bare_team_name_then_they_are_found() {
    let kb = brazilian_soccer_mcp::load_from_dir(&data_dir()).expect("datasets should load");
    let filter = MatchFilter {
        team: Some("Palmeiras"),
        competition: Some(Competition::Brasileirao),
        ..Default::default()
    };
    let result = kb.find_matches(&filter, 10);
    assert!(
        result.total_count > 0,
        "expected Palmeiras matches to be found"
    );
}

// Given the loaded Brasileirao and Libertadores datasets
// When computing head-to-head between two well-known Brazilian clubs
// Then the aggregated win/draw/loss counts sum to the matches considered
#[test]
fn test_given_derby_rivals_when_computing_head_to_head_then_tallies_sum_to_matches_considered() {
    let kb = brazilian_soccer_mcp::load_from_dir(&data_dir()).expect("datasets should load");
    let h2h = kb.head_to_head("Flamengo", "Fluminense", None, None, 5);
    assert!(h2h.matches_considered > 0);
    assert_eq!(
        h2h.team_a_wins + h2h.team_b_wins + h2h.draws,
        h2h.matches_considered as u32
    );
}

// Given the loaded Brasileirao dataset
// When computing the 2019 standings
// Then the champion has the most points and rows are ranked in order
#[test]
fn test_given_2019_season_when_computing_standings_then_table_is_ranked_by_points_descending() {
    let kb = brazilian_soccer_mcp::load_from_dir(&data_dir()).expect("datasets should load");
    let table = kb.standings(Competition::Brasileirao, 2019);
    assert!(!table.is_empty());
    for pair in table.windows(2) {
        assert!(pair[0].points >= pair[1].points);
    }
}

// Given the FIFA player dataset
// When searching for Brazilian players
// Then only Brazilian players are returned, sorted by overall rating
#[test]
fn test_given_fifa_player_data_when_searching_brazilian_players_then_only_brazilians_are_returned()
{
    let kb = brazilian_soccer_mcp::load_from_dir(&data_dir()).expect("datasets should load");
    let filter = PlayerFilter {
        nationality: Some("Brazil"),
        limit: Some(10),
        ..Default::default()
    };
    let (players, total) = kb.search_players(&filter, PlayerSort::Overall, true);
    assert!(total > 0);
    assert!(players.iter().all(|p| p.nationality == "Brazil"));
    for pair in players.windows(2) {
        assert!(pair[0].overall >= pair[1].overall);
    }
}

// Given the extended-stats dataset covering Serie A/B/C and Copa do Brasil
// When computing match stats restricted to that source
// Then a plausible average-goals figure is produced (no divide-by-zero, no NaN)
#[test]
fn test_given_extended_stats_dataset_when_computing_match_stats_then_average_goals_is_plausible() {
    let kb = brazilian_soccer_mcp::load_from_dir(&data_dir()).expect("datasets should load");
    let stats = kb.match_stats(Some(Competition::ExtendedStats), None);
    assert_eq!(stats.matches_considered, 10296);
    assert!(stats.average_total_goals > 0.0 && stats.average_total_goals < 10.0);
}

// Given a home-record query restricted by venue
// When computing a team's record for home matches only
// Then the match count is strictly less than its overall record
#[test]
fn test_given_home_venue_filter_when_computing_team_record_then_it_is_a_subset_of_all_matches() {
    let kb = brazilian_soccer_mcp::load_from_dir(&data_dir()).expect("datasets should load");
    let overall = kb.team_record("Corinthians", None, None, Venue::Either);
    let home_only = kb.team_record("Corinthians", None, None, Venue::Home);
    assert!(home_only.matches_played < overall.matches_played);
    assert!(home_only.matches_played > 0);
}
