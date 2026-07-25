//! Feature: the specification's sample questions and performance budget
//!
//! ```gherkin
//! Feature: Answering natural language questions
//!   Scenario: The documented sample questions are answerable
//!     Given the knowledge graph is loaded
//!     When each sample question is routed to its tool
//!     Then every question returns a substantive answer
//!     And simple lookups finish in under 2 seconds
//!     And aggregate queries finish in under 5 seconds
//! ```

mod common;

use std::time::Instant;

use brazilian_soccer_mcp::samples::SAMPLE_QUESTIONS;
use brazilian_soccer_mcp::tools;
use common::*;

/// Aggregations (tables, rankings, competition-wide averages) get the looser
/// budget from the specification; everything else is a "simple lookup".
fn is_aggregate(tool: &str) -> bool {
    matches!(
        tool,
        "standings" | "competition_stats" | "team_rankings" | "biggest_wins" | "dataset_overview"
    )
}

#[test]
fn scenario_all_sample_questions_are_answered() {
    let graph = given_the_knowledge_graph_is_loaded();

    assert!(
        SAMPLE_QUESTIONS.len() >= 20,
        "the specification asks for at least 20 answerable questions, found {}",
        SAMPLE_QUESTIONS.len()
    );

    let mut failures = Vec::new();
    for sample in SAMPLE_QUESTIONS {
        match tools::call(graph, sample.tool, &(sample.arguments)()) {
            Ok(output) => {
                if output.text.len() < 40 {
                    failures.push(format!(
                        "{}: answer too thin ({:?})",
                        sample.question, output.text
                    ));
                }
                // An answer must contain at least one line of data, not just a
                // heading.
                if output.text.lines().count() < 2 {
                    failures.push(format!("{}: single-line answer", sample.question));
                }
            }
            Err(message) => failures.push(format!("{}: {message}", sample.question)),
        }
    }
    assert!(failures.is_empty(), "unanswered questions:\n{failures:#?}");
}

#[test]
fn scenario_every_capability_area_is_covered() {
    let mut categories: Vec<&str> = SAMPLE_QUESTIONS.iter().map(|s| s.category).collect();
    categories.sort();
    categories.dedup();
    for expected in [
        "Match queries",
        "Team queries",
        "Player queries",
        "Competition queries",
        "Statistical analysis",
        "Cross-file queries",
    ] {
        assert!(
            categories.contains(&expected),
            "no sample question for '{expected}'"
        );
    }

    // And every tool the server advertises is exercised by a question.
    let exercised: Vec<&str> = SAMPLE_QUESTIONS.iter().map(|s| s.tool).collect();
    for tool in tools::TOOLS {
        assert!(
            exercised.contains(&tool.name),
            "no sample question calls '{}'",
            tool.name
        );
    }
}

#[test]
fn scenario_queries_meet_the_latency_budget() {
    let graph = given_the_knowledge_graph_is_loaded();

    let mut slowest = (0.0_f64, "");
    for sample in SAMPLE_QUESTIONS {
        let started = Instant::now();
        let _ = tools::call(graph, sample.tool, &(sample.arguments)());
        let elapsed = started.elapsed().as_secs_f64();
        let budget = if is_aggregate(sample.tool) { 5.0 } else { 2.0 };
        assert!(
            elapsed < budget,
            "'{}' took {elapsed:.3}s, over its {budget:.0}s budget",
            sample.question
        );
        if elapsed > slowest.0 {
            slowest = (elapsed, sample.question);
        }
    }
    // The budget is generous; in practice everything is well under 100 ms.
    assert!(
        slowest.0 < 1.0,
        "slowest question '{}' took {:.3}s",
        slowest.1,
        slowest.0
    );
}

#[test]
fn scenario_repeated_queries_stay_fast() {
    let graph = given_the_knowledge_graph_is_loaded();

    // Worst case for the query engine: a full-graph scan with no index to
    // narrow it, repeated.
    let started = Instant::now();
    for _ in 0..20 {
        let output = tools::call(graph, "biggest_wins", &serde_json::json!({ "limit": 10 }))
            .expect("aggregate query should succeed");
        assert!(!output.text.is_empty());
    }
    let elapsed = started.elapsed().as_secs_f64();
    assert!(
        elapsed < 5.0,
        "20 full scans took {elapsed:.2}s; per-query cost is too high"
    );
}

#[test]
fn scenario_dataset_loads_within_startup_budget() {
    // A fresh load (not the shared one) must be fast enough for an MCP host to
    // start the server on demand.
    let started = Instant::now();
    let graph = brazilian_soccer_mcp::load_default_graph().expect("datasets should load");
    let elapsed = started.elapsed().as_secs_f64();
    assert!(elapsed < 15.0, "loading took {elapsed:.2}s");
    assert!(graph.matches.len() > 20_000);
    assert!(graph.players.len() > 18_000);
    assert!(graph.teams.len() > 300);
}
