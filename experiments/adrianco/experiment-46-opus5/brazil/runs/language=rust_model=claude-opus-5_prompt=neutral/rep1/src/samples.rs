//! The worked example questions from the specification, each bound to the tool
//! call that answers it.
//!
//! `cargo run -- demo` executes the list and prints every answer; the
//! integration tests execute the same list and assert that all of them return
//! substantive answers inside the required latency budget. Keeping one list
//! means the demo can never drift from what is tested.

use serde_json::{json, Value};

/// A natural-language question and the tool call that answers it.
pub struct SampleQuestion {
    /// The question a user would ask the LLM.
    pub question: &'static str,
    /// Capability category from the specification.
    pub category: &'static str,
    pub tool: &'static str,
    pub arguments: fn() -> Value,
}

/// Sample questions covering all five specified capability areas.
pub const SAMPLE_QUESTIONS: &[SampleQuestion] = &[
    // ---- 1. match queries ---------------------------------------------------
    SampleQuestion {
        question: "Show me all Flamengo vs Fluminense matches",
        category: "Match queries",
        tool: "search_matches",
        arguments: || json!({ "team": "Flamengo", "opponent": "Fluminense", "limit": 10 }),
    },
    SampleQuestion {
        question: "What matches did Palmeiras play in 2023?",
        category: "Match queries",
        tool: "search_matches",
        arguments: || json!({ "team": "Palmeiras", "season": 2023, "limit": 15 }),
    },
    SampleQuestion {
        question: "Find all Copa do Brasil finals",
        category: "Match queries",
        tool: "search_matches",
        arguments: || json!({ "competition": "Copa do Brasil", "stage": "8", "limit": 25 }),
    },
    SampleQuestion {
        question: "Show me the Copa Libertadores finals",
        category: "Match queries",
        tool: "search_matches",
        arguments: || json!({ "competition": "Libertadores", "stage": "final", "limit": 25 }),
    },
    SampleQuestion {
        question: "When did Flamengo last play Corinthians, and what was the score?",
        category: "Match queries",
        tool: "head_to_head",
        arguments: || json!({ "team_a": "Flamengo", "team_b": "Corinthians", "recent": 3 }),
    },
    SampleQuestion {
        question:
            "Which matches were played at the Maracanã derby between Vasco and Botafogo in 2019?",
        category: "Match queries",
        tool: "search_matches",
        arguments: || json!({ "team": "Vasco", "opponent": "Botafogo", "season": 2019 }),
    },
    SampleQuestion {
        question: "What Série A matches were played in the first week of November 2019?",
        category: "Match queries",
        tool: "search_matches",
        arguments: || {
            json!({
                "competition": "Serie A",
                "date_from": "2019-11-01",
                "date_to": "2019-11-07",
                "limit": 20
            })
        },
    },
    // ---- 2. team queries ----------------------------------------------------
    SampleQuestion {
        question: "What is Corinthians' home record in 2022?",
        category: "Team queries",
        tool: "team_stats",
        arguments: || json!({ "team": "Corinthians", "season": 2022, "venue": "home" }),
    },
    SampleQuestion {
        question: "Which team scored the most goals in Série A 2023?",
        category: "Team queries",
        tool: "team_rankings",
        arguments: || json!({ "metric": "goals_for", "competition": "Serie A", "season": 2023, "limit": 5 }),
    },
    SampleQuestion {
        question: "Compare Palmeiras and Santos head-to-head",
        category: "Team queries",
        tool: "head_to_head",
        arguments: || json!({ "team_a": "Palmeiras", "team_b": "Santos", "recent": 5 }),
    },
    SampleQuestion {
        question: "What competitions has Palmeiras played in?",
        category: "Team queries",
        tool: "team_profile",
        arguments: || json!({ "team": "Palmeiras" }),
    },
    SampleQuestion {
        question: "How did Cruzeiro do in the 2003 Brasileirão?",
        category: "Team queries",
        tool: "team_stats",
        arguments: || json!({ "team": "Cruzeiro", "season": 2003, "competition": "Serie A" }),
    },
    SampleQuestion {
        question: "What is Corinthians' record in the Copa Libertadores?",
        category: "Team queries",
        tool: "team_stats",
        arguments: || json!({ "team": "Corinthians", "competition": "Libertadores" }),
    },
    SampleQuestion {
        question: "Which club does 'Atlético' refer to?",
        category: "Team queries",
        tool: "find_team",
        arguments: || json!({ "query": "Atlético" }),
    },
    // ---- 3. player queries --------------------------------------------------
    SampleQuestion {
        question: "Find all Brazilian players in the dataset",
        category: "Player queries",
        tool: "search_players",
        arguments: || json!({ "nationality": "Brazil", "limit": 10 }),
    },
    SampleQuestion {
        question: "Who are the highest-rated players at Grêmio?",
        category: "Player queries",
        tool: "club_players",
        arguments: || json!({ "club": "Grêmio", "limit": 10 }),
    },
    SampleQuestion {
        question: "Who are the highest-rated players at Flamengo?",
        category: "Player queries",
        tool: "club_players",
        arguments: || json!({ "club": "Flamengo" }),
    },
    SampleQuestion {
        question: "Show me all strikers at Brazilian clubs",
        category: "Player queries",
        tool: "search_players",
        arguments: || json!({ "position": "ST", "brazilian_clubs_only": true, "limit": 10 }),
    },
    SampleQuestion {
        question: "Who is Neymar Jr?",
        category: "Player queries",
        tool: "player_profile",
        arguments: || json!({ "name": "Neymar Jr" }),
    },
    SampleQuestion {
        question: "Which Brazilian players at Brazilian clubs are rated 80 or above?",
        category: "Player queries",
        tool: "search_players",
        arguments: || {
            json!({
                "nationality": "Brazil",
                "brazilian_clubs_only": true,
                "min_overall": 78,
                "limit": 10
            })
        },
    },
    // ---- 4. competition queries ---------------------------------------------
    SampleQuestion {
        question: "Who won the 2019 Brasileirão?",
        category: "Competition queries",
        tool: "standings",
        arguments: || json!({ "competition": "Serie A", "season": 2019, "limit": 6 }),
    },
    SampleQuestion {
        question: "Which teams were relegated in 2020?",
        category: "Competition queries",
        tool: "standings",
        arguments: || json!({ "competition": "Serie A", "season": 2020 }),
    },
    SampleQuestion {
        question: "Show the 2018 Copa Libertadores knockout stages",
        category: "Competition queries",
        tool: "search_matches",
        arguments: || json!({ "competition": "Libertadores", "season": 2018, "stage": "final", "limit": 10 }),
    },
    SampleQuestion {
        question: "What did the 2015 Série B table look like?",
        category: "Competition queries",
        tool: "standings",
        arguments: || json!({ "competition": "Serie B", "season": 2015, "limit": 8 }),
    },
    // ---- 5. statistical analysis --------------------------------------------
    SampleQuestion {
        question: "What's the average goals per match in the Brasileirão?",
        category: "Statistical analysis",
        tool: "competition_stats",
        arguments: || json!({ "competition": "Serie A" }),
    },
    SampleQuestion {
        question: "Compare the 2018 and 2019 Série A seasons",
        category: "Statistical analysis",
        tool: "competition_stats",
        arguments: || json!({ "competition": "Serie A", "seasons": [2018, 2019] }),
    },
    SampleQuestion {
        question: "Which team has the best away record in the Brasileirão?",
        category: "Statistical analysis",
        tool: "team_rankings",
        arguments: || {
            json!({
                "metric": "win_rate",
                "competition": "Serie A",
                "venue": "away",
                "min_matches": 100,
                "limit": 5
            })
        },
    },
    SampleQuestion {
        question: "Which team has the best home record in the Brasileirão?",
        category: "Statistical analysis",
        tool: "team_rankings",
        arguments: || {
            json!({
                "metric": "win_rate",
                "competition": "Serie A",
                "venue": "home",
                "min_matches": 100,
                "limit": 5
            })
        },
    },
    SampleQuestion {
        question: "Show me the biggest wins in the dataset",
        category: "Statistical analysis",
        tool: "biggest_wins",
        arguments: || json!({ "limit": 10 }),
    },
    SampleQuestion {
        question: "How does the Libertadores compare to the Brasileirão for goals per game?",
        category: "Statistical analysis",
        tool: "competition_stats",
        arguments: || json!({ "competition": "Libertadores" }),
    },
    // ---- cross-file and graph queries ---------------------------------------
    SampleQuestion {
        question:
            "Which Brazilian clubs have both squad and match data, and how do their squads rate?",
        category: "Cross-file queries",
        tool: "search_players",
        arguments: || json!({ "brazilian_clubs_only": true, "limit": 10 }),
    },
    SampleQuestion {
        question: "What is connected to Santos in the knowledge graph?",
        category: "Cross-file queries",
        tool: "graph_neighbors",
        arguments: || json!({ "node_type": "team", "name": "Santos", "limit": 3 }),
    },
    SampleQuestion {
        question: "What data is loaded and what are its limits?",
        category: "Cross-file queries",
        tool: "dataset_overview",
        arguments: || json!({}),
    },
];
