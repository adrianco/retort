//! Integration tests against the real datasets in `data/kaggle`, covering
//! the sample questions and success criteria listed in `TASK.md`. Loading
//! is done once per process via `std::sync::OnceLock` since it takes a
//! fraction of a second and every test needs the same read-only store.

use std::path::PathBuf;
use std::sync::OnceLock;

use brazilian_soccer_mcp::queries;
use brazilian_soccer_mcp::store::Store;

fn store() -> &'static Store {
    static STORE: OnceLock<Store> = OnceLock::new();
    STORE.get_or_init(|| {
        let dir = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("data/kaggle");
        Store::load(&dir).expect("loading datasets should succeed")
    })
}

// ---- Data coverage (TASK.md "Success Criteria") -------------------------

#[test]
fn all_six_datasets_load_with_rows() {
    let s = store();
    assert_eq!(s.dataset_info.len(), 6);
    for d in &s.dataset_info {
        assert!(d.rows > 0, "{} should have loaded rows", d.file);
    }
    assert!(s.matches.len() > 15_000);
    assert!(s.players.len() > 15_000);
}

// ---- 1. Match queries -----------------------------------------------------

#[test]
fn find_flamengo_vs_fluminense_matches() {
    let out = queries::search_matches(store(), "Flamengo", "Fluminense", "", None, "", "", 100);
    assert!(out.contains("Flamengo vs Fluminense"));
    assert!(out.contains("Head-to-head in dataset"));
    assert!(out.contains("Fluminense"));
}

#[test]
fn palmeiras_matches_in_2023() {
    let out = queries::search_matches(store(), "Palmeiras", "", "", Some(2023), "", "", 200);
    assert!(out.contains("Palmeiras"));
    assert!(!out.contains("No matches found"));
}

#[test]
fn copa_do_brasil_matches_by_competition_filter() {
    let out = queries::search_matches(store(), "", "", "Copa do Brasil", None, "", "", 5);
    assert!(out.contains("Copa do Brasil"));
}

#[test]
fn date_range_filters_matches() {
    // Brazilian domestic competitions run roughly April-December; May 2023
    // has action across multiple competitions, unlike the January off-season.
    let out = queries::search_matches(store(), "", "", "", None, "2023-05-01", "2023-05-31", 500);
    assert!(!out.contains("No matches found"));
}

// ---- 2. Team queries --------------------------------------------------

#[test]
fn corinthians_home_record_2022() {
    let out = queries::team_record(store(), "Corinthians", "Brasileirao", Some(2022), "home");
    assert!(out.contains("Wins:"));
    assert!(out.contains("Win rate"));
    // A 19-round-per-venue season would be 19 home matches, but
    // Brasileirao_Matches.csv has ~80 unplayed ("NA" score) rows for 2022
    // specifically (a real gap in the source data, not a bug), so fewer
    // than 19 home matches actually have a result to count.
    assert!(out.contains("Matches: 15"), "got: {out}");
}

#[test]
fn team_scoring_the_most_goals_in_serie_a_2023() {
    // Brasileirao_Matches.csv only goes up to 2022; 2023 data lives in
    // BR-Football-Dataset.csv under the "Serie A" label (see TASK.md's own
    // sample question, which asks about "Serie A 2023" specifically).
    let out = queries::team_leaderboard(store(), "Serie A", Some(2023), "goals_for", "all", 1);
    assert!(out.starts_with("Leaderboard by Goals For"));
    assert!(out.contains("1."));
}

#[test]
fn compare_palmeiras_and_santos_head_to_head() {
    let out = queries::compare_teams(store(), "Palmeiras", "Santos", "", None);
    assert!(out.contains("Head-to-head in dataset"));
}

#[test]
fn ambiguous_base_names_are_not_merged_in_team_record() {
    // Atletico-MG and Atletico-GO share the loose base "Atletico" but are
    // different clubs; regression test for a real bug caught during manual
    // testing where they were silently combined into one 76-game "team".
    let mg = queries::team_record(store(), "Atletico-MG", "Brasileirao", Some(2019), "all");
    assert!(mg.contains("Matches: 38"), "expected a single 38-game season, got: {mg}");
    // Atletico-GO wasn't in Serie A in 2019 at all.
    let go = queries::team_record(store(), "Atletico-GO", "Brasileirao", Some(2019), "all");
    assert!(go.contains("No matches found"));
}

// ---- 3. Player queries --------------------------------------------------

#[test]
fn find_brazilian_players() {
    let out = queries::search_players(store(), "", "Brazil", "", "", None, 10);
    assert!(out.contains("Overall:"));
    assert!(out.contains("Brazil"));
}

#[test]
fn who_is_gabriel_jesus() {
    // The FIFA dataset used here (a 2019 snapshot) doesn't include every
    // Brazilian player (e.g. Gabriel Barbosa/"Gabigol" is absent), but
    // exercises the same "look up a player by name" capability.
    let out = queries::search_players(store(), "Gabriel Jesus", "", "", "", None, 5);
    assert!(!out.contains("No players found"));
    assert!(out.contains("Gabriel Jesus"));
}

#[test]
fn highest_rated_brazilian_players() {
    let out = queries::search_players(store(), "", "Brazil", "", "", Some(85), 50);
    assert!(out.contains("Neymar") || out.contains("Overall: 9"));
}

#[test]
fn forwards_search_by_position() {
    let out = queries::search_players(store(), "", "", "", "ST", None, 5);
    assert!(!out.contains("No players found"));
}

// ---- 4. Competition queries --------------------------------------------

#[test]
fn who_won_the_2019_brasileirao() {
    let out = queries::standings(store(), "Brasileirao", 2019);
    assert!(out.contains("Champion"));
    let champion_line = out.lines().find(|l| l.contains("Champion")).unwrap();
    assert!(champion_line.starts_with("1. Flamengo"), "got: {champion_line}");
}

#[test]
fn brasileirao_2019_standings_has_twenty_teams_and_no_double_counting() {
    let out = queries::standings(store(), "Brasileirao", 2019);
    let team_lines: Vec<&str> = out.lines().filter(|l| l.contains(" pts (")).collect();
    assert_eq!(team_lines.len(), 20, "expected 20 teams, got:\n{out}");
    for line in &team_lines {
        // Every team must have played exactly 38 matches (37 wins+draws+losses).
        let w: u32 = extract_stat(line, "W)").unwrap_or_else(|| extract_stat(line, "W,").unwrap());
        let d: u32 = extract_stat(line, "D,").unwrap();
        let l: u32 = extract_stat(line, "L,").unwrap();
        assert_eq!(w + d + l, 38, "line did not sum to 38 games: {line}");
    }
}

fn extract_stat(line: &str, marker: &str) -> Option<u32> {
    let idx = line.find(marker)?;
    let start = line[..idx].rfind(|c: char| !c.is_ascii_digit())? + 1;
    line[start..idx].parse().ok()
}

#[test]
fn relegated_teams_in_2020() {
    let out = queries::standings(store(), "Brasileirao", 2020);
    assert!(out.contains("Relegation zone"));
}

#[test]
fn libertadores_2018_bracket_by_stage() {
    let out = queries::search_matches(store(), "", "", "Copa Libertadores", Some(2018), "", "", 500);
    assert!(out.contains("Copa Libertadores"));
}

#[test]
fn team_competitions_lists_multiple_competitions() {
    let out = queries::team_competitions(store(), "Palmeiras");
    assert!(out.contains("Brasileirao"));
    assert!(out.contains("Copa do Brasil"));
}

// ---- 5. Statistical analysis --------------------------------------------

#[test]
fn average_goals_per_match_in_brasileirao() {
    let out = queries::average_stats(store(), "Brasileirao", None);
    assert!(out.contains("Average goals per match"));
    assert!(out.contains("Home win rate"));
}

#[test]
fn best_away_record_leaderboard() {
    let out = queries::team_leaderboard(store(), "Brasileirao", None, "win_rate", "away", 5);
    assert!(!out.contains("(home only)"));
    assert!(out.contains("away only"));
}

#[test]
fn biggest_wins_in_dataset() {
    let out = queries::biggest_wins(store(), "", None, 5);
    assert!(out.contains("Biggest victories"));
    assert!(out.lines().count() >= 5);
}

// ---- Relationship queries / cross-file ----------------------------------

#[test]
fn derbies_in_2023() {
    let out = queries::derby_matches(store(), Some(2023), "");
    assert!(out.contains("Fla-Flu"));
}

#[test]
fn players_at_club_cross_file_lookup_is_consistent() {
    // Regression test for a real bug: an empty club key (free agents)
    // used to match every substring query because "x".contains("") is
    // true in Rust.
    let out = queries::search_players(store(), "", "", "Flamengo", "", None, 5);
    assert!(!out.contains("Free Agent"), "empty-club players should never match a club filter");
}

#[test]
fn brazilian_club_squads_cross_references_match_and_player_data() {
    let out = queries::brazilian_club_squads(store(), 5);
    assert!(out.contains("Brazilian players at Brazilian clubs"));
    assert!(out.contains("players (avg rating"));
}

#[test]
fn list_datasets_reports_all_six_files() {
    let out = queries::list_datasets(store());
    for f in [
        "Brasileirao_Matches.csv",
        "Brazilian_Cup_Matches.csv",
        "Libertadores_Matches.csv",
        "BR-Football-Dataset.csv",
        "novo_campeonato_brasileiro.csv",
        "fifa_data.csv",
    ] {
        assert!(out.contains(f), "missing {f} in:\n{out}");
    }
}

// ---- Data quality notes: name normalization ------------------------------

#[test]
fn state_suffixed_and_bare_team_names_are_treated_as_the_same_team() {
    // "Palmeiras-SP" (Brasileirao dataset) vs "Palmeiras" (BR-Football
    // dataset) must resolve to the same team for search purposes.
    let out = queries::team_competitions(store(), "Palmeiras");
    assert!(out.contains("matches"));
    let via_suffix = queries::team_competitions(store(), "Palmeiras-SP");
    assert_eq!(out, via_suffix);
}

#[test]
fn accented_and_unaccented_names_match() {
    let with_accent = queries::search_matches(store(), "Grêmio", "", "Brasileirao", Some(2019), "", "", 5);
    let without_accent = queries::search_matches(store(), "Gremio", "", "Brasileirao", Some(2019), "", "", 5);
    assert_eq!(with_accent, without_accent);
    assert!(!with_accent.contains("No matches found"));
}
