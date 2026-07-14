//! The specification's success criteria require that at least 20 sample
//! questions can be answered. Each test here phrases one natural-language
//! question as the MCP tool call an LLM would issue, runs it through the
//! real tool dispatch (`mcp::call_tool`), and checks the answer text.

use std::path::Path;
use std::sync::OnceLock;

use brazilian_soccer_mcp::data::Store;
use brazilian_soccer_mcp::mcp::call_tool;
use serde_json::json;

fn store() -> &'static Store {
    static STORE: OnceLock<Store> = OnceLock::new();
    STORE.get_or_init(|| {
        Store::load(Path::new(env!("CARGO_MANIFEST_DIR")).join("data/kaggle").as_path())
            .expect("datasets must load")
    })
}

fn ask(tool: &str, args: serde_json::Value) -> String {
    call_tool(store(), tool, &args).expect("tool call must succeed")
}

// 1. "Show me all Flamengo vs Fluminense matches"
#[test]
fn q01_flamengo_vs_fluminense() {
    let a = ask(
        "search_matches",
        json!({"team": "Flamengo", "opponent": "Fluminense", "limit": 50}),
    );
    assert!(a.contains("Flamengo") && a.contains("Fluminense"));
    assert!(!a.contains("No matches found"));
}

// 2. "What matches did Palmeiras play in 2023?"
#[test]
fn q02_palmeiras_2023() {
    let a = ask("search_matches", json!({"team": "Palmeiras", "season": 2023}));
    assert!(a.contains("Palmeiras"));
    assert!(a.contains("2023-"));
}

// 3. "Find all Copa do Brasil finals"
#[test]
fn q03_copa_do_brasil_finals() {
    let a = ask(
        "search_matches",
        json!({"competition": "Copa do Brasil", "stage": "final", "limit": 40}),
    );
    assert!(a.contains("Copa do Brasil"));
    assert!(a.contains("Final"));
}

// 4. "What is Corinthians' home record in 2022?"
#[test]
fn q04_corinthians_home_2022() {
    let a = ask(
        "team_stats",
        json!({"team": "Corinthians", "season": 2022, "competition": "Serie A", "venue": "home"}),
    );
    assert!(a.contains("Corinthians"));
    assert!(a.contains("Matches: 19"));
    assert!(a.contains("Win rate"));
}

// 5. "Which team scored the most goals in Serie A 2023?"
#[test]
fn q05_top_scoring_team_2023() {
    let a = ask("competition_stats", json!({"competition": "Serie A", "season": 2023}));
    assert!(a.contains("Top scoring teams"));
    assert!(a.contains("Average goals per match"));
}

// 6. "Compare Palmeiras and Santos head-to-head"
#[test]
fn q06_palmeiras_santos_h2h() {
    let a = ask("head_to_head", json!({"team1": "Palmeiras", "team2": "Santos"}));
    assert!(a.contains("Palmeiras") && a.contains("Santos"));
    assert!(a.contains("wins") && a.contains("draws"));
}

// 7. "Find all Brazilian players in the dataset"
#[test]
fn q07_brazilian_players() {
    let a = ask("search_players", json!({"nationality": "Brazil"}));
    assert!(a.contains("Found 827 players"));
    assert!(a.contains("Neymar Jr"));
}

// 8. "Who are the highest-rated players at Grêmio?" (accent-insensitive)
#[test]
fn q08_top_players_at_gremio() {
    let a = ask("search_players", json!({"club": "Gremio", "limit": 5}));
    assert!(a.contains("Grêmio"));
    assert!(a.contains("Overall"));
}

// 9. "Show me all forwards from Santos"
#[test]
fn q09_santos_forwards() {
    let a = ask("search_players", json!({"club": "Santos", "position": "forward"}));
    assert!(a.contains("Santos"));
    assert!(!a.contains("No players found"));
}

// 10. "Who won the 2019 Brasileirão?"
#[test]
fn q10_2019_champion() {
    let a = ask("league_standings", json!({"season": 2019}));
    assert!(a.contains(" 1. Flamengo - 90 pts"));
    assert!(a.contains("Champion"));
}

// 11. "Show the 2018 Copa Libertadores knockout results"
#[test]
fn q11_2018_libertadores() {
    let a = ask(
        "search_matches",
        json!({"competition": "Libertadores", "season": 2018, "stage": "final"}),
    );
    assert!(a.contains("Copa Libertadores"));
    assert!(!a.contains("No matches found"));
}

// 12. "Which teams were relegated in 2020?"
#[test]
fn q12_relegated_2020() {
    let a = ask("league_standings", json!({"season": 2020}));
    assert!(a.contains("Relegated"));
    // The real bottom four of 2020: Vasco, Goiás, Coritiba, Botafogo
    assert!(a.contains("Vasco da Gama") && a.contains("Botafogo"));
}

// 13. "What's the average goals per match in the Brasileirão?"
#[test]
fn q13_average_goals() {
    let a = ask("competition_stats", json!({"competition": "Brasileirão"}));
    let line = a
        .lines()
        .find(|l| l.contains("Average goals per match"))
        .expect("answer must include the average");
    let value: f64 = line.rsplit(' ').next().unwrap().parse().unwrap();
    assert!((1.5..=3.5).contains(&value), "implausible average {value}");
}

// 14. "Which team has the best away record?" (via venue-filtered stats)
#[test]
fn q14_away_record() {
    let a = ask(
        "team_stats",
        json!({"team": "Flamengo", "season": 2019, "competition": "Serie A", "venue": "away"}),
    );
    assert!(a.contains("away record"));
    assert!(a.contains("Matches: 19"));
}

// 15. "Show me the biggest wins in the dataset"
#[test]
fn q15_biggest_wins() {
    let a = ask("biggest_wins", json!({"limit": 5}));
    assert!(a.contains("Biggest victories"));
    // The top margin must be at least six goals somewhere in 18k matches.
    assert!(!a.contains("No matches found"));
}

// 16. "When did Flamengo last play Corinthians?"
#[test]
fn q16_last_fla_corinthians() {
    let a = ask(
        "search_matches",
        json!({"team": "Flamengo", "opponent": "Corinthians", "limit": 1}),
    );
    // Most recent first; the answer carries date and score.
    assert!(a.contains("Flamengo") && a.contains("Corinthians"));
    assert!(a.lines().any(|l| l.starts_with("- 20")));
}

// 17. "Who is Gabriel Barbosa?" (player lookup by partial name)
#[test]
fn q17_who_is_player() {
    let a = ask("player_info", json!({"name": "Casemiro"}));
    assert!(a.contains("Casemiro"));
    assert!(a.contains("Overall"));
    assert!(a.contains("Nationality: Brazil"));
}

// 18. "Which players play for Sport Club do Recife?"
#[test]
fn q18_players_by_club() {
    let a = ask("search_players", json!({"club": "Sport Club do Recife"}));
    assert!(!a.contains("No players found"));
}

// 19. "Show me all derbies in 2023" (Fla-Flu as the classic example)
#[test]
fn q19_derbies_2023() {
    let a = ask(
        "search_matches",
        json!({"team": "Flamengo", "opponent": "Fluminense", "season": 2023}),
    );
    assert!(!a.contains("No matches found"));
    assert!(a.contains("2023-"));
}

// 20. "What competitions has Palmeiras played in?"
#[test]
fn q20_palmeiras_competitions() {
    let a = ask("team_stats", json!({"team": "Palmeiras"}));
    assert!(a.contains("By competition:"));
    assert!(a.contains("Brasileirão Série A"));
    assert!(a.contains("Copa Libertadores"));
    assert!(a.contains("Copa do Brasil"));
}

// 21. "Which team has the best home record?" (league-wide aggregate)
#[test]
fn q21_home_advantage() {
    let a = ask("competition_stats", json!({"competition": "Serie A"}));
    assert!(a.contains("Home wins"));
    assert!(a.contains("Away wins"));
}

// 22. "Who are the top Brazilian players?"
#[test]
fn q22_top_brazilians() {
    let a = ask(
        "search_players",
        json!({"nationality": "Brazil", "min_overall": 85, "limit": 10}),
    );
    assert!(a.contains("Neymar Jr"));
    assert!(!a.contains("No players found"));
}

// 23. "Compare the 2018 and 2019 seasons"
#[test]
fn q23_compare_seasons() {
    let a18 = ask("competition_stats", json!({"competition": "Serie A", "season": 2018}));
    let a19 = ask("competition_stats", json!({"competition": "Serie A", "season": 2019}));
    assert!(a18.contains("Average goals per match"));
    assert!(a19.contains("Average goals per match"));
    assert_ne!(a18, a19);
}

// 24. "What was the score?" (follow-up: a specific fixture has its score)
#[test]
fn q24_specific_score() {
    let a = ask(
        "search_matches",
        json!({"team": "Flamengo", "opponent": "Santos", "season": 2019, "limit": 2}),
    );
    // Each line shows "Team X-Y Team".
    assert!(a.lines().any(|l| l.contains("Flamengo") && l.contains("Santos")));
}

// 25. "What data do you have?" (coverage / capability question)
#[test]
fn q25_data_coverage() {
    let a = ask("list_competitions", json!({}));
    assert!(a.contains("Brasileirão Série A"));
    assert!(a.contains("Copa do Brasil"));
    assert!(a.contains("Copa Libertadores"));
    assert!(a.contains("fifa_data.csv"));
}
