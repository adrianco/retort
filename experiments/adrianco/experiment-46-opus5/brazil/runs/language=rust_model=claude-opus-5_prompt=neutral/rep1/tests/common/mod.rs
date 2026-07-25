//! Shared Given/When/Then helpers for the BDD-style integration tests.
//!
//! The knowledge graph is expensive to build (six CSV files), so each test
//! binary builds it once and shares it across scenarios.

#![allow(dead_code)]

use std::sync::OnceLock;

use brazilian_soccer_mcp::graph::KnowledgeGraph;
use brazilian_soccer_mcp::tools::{self, ToolOutput};
use serde_json::Value;

static GRAPH: OnceLock<KnowledgeGraph> = OnceLock::new();

/// GIVEN the match, player and competition data is loaded.
pub fn given_the_knowledge_graph_is_loaded() -> &'static KnowledgeGraph {
    GRAPH.get_or_init(|| {
        brazilian_soccer_mcp::load_default_graph()
            .expect("the Kaggle CSV files should load from data/kaggle")
    })
}

/// WHEN I call a tool that is expected to succeed.
pub fn when_i_call(tool: &str, arguments: Value) -> ToolOutput {
    let graph = given_the_knowledge_graph_is_loaded();
    match tools::call(graph, tool, &arguments) {
        Ok(output) => output,
        Err(message) => panic!("tool '{tool}' failed unexpectedly: {message}"),
    }
}

/// WHEN I call a tool that is expected to be rejected.
pub fn when_i_call_expecting_error(tool: &str, arguments: Value) -> String {
    let graph = given_the_knowledge_graph_is_loaded();
    match tools::call(graph, tool, &arguments) {
        Ok(output) => panic!("tool '{tool}' unexpectedly succeeded with: {}", output.text),
        Err(message) => message,
    }
}

/// THEN the answer mentions ...
pub fn then_text_contains(text: &str, needle: &str) {
    assert!(
        text.contains(needle),
        "expected the answer to contain {needle:?}, got:\n{text}"
    );
}

/// Reads `path` (dotted, e.g. `record.wins`) out of a structured payload.
pub fn field<'a>(data: &'a Value, path: &str) -> &'a Value {
    let mut current = data;
    for segment in path.split('.') {
        current = match segment.parse::<usize>() {
            Ok(index) => current
                .get(index)
                .unwrap_or_else(|| panic!("missing index {index} of {path} in {current}")),
            Err(_) => current
                .get(segment)
                .unwrap_or_else(|| panic!("missing field {segment} of {path} in {current}")),
        };
    }
    current
}

pub fn as_i64(data: &Value, path: &str) -> i64 {
    field(data, path)
        .as_i64()
        .unwrap_or_else(|| panic!("field {path} is not an integer: {}", field(data, path)))
}

pub fn as_f64(data: &Value, path: &str) -> f64 {
    field(data, path)
        .as_f64()
        .unwrap_or_else(|| panic!("field {path} is not a number: {}", field(data, path)))
}

pub fn as_str<'a>(data: &'a Value, path: &str) -> &'a str {
    field(data, path)
        .as_str()
        .unwrap_or_else(|| panic!("field {path} is not a string: {}", field(data, path)))
}

pub fn as_array<'a>(data: &'a Value, path: &str) -> &'a Vec<Value> {
    field(data, path)
        .as_array()
        .unwrap_or_else(|| panic!("field {path} is not an array: {}", field(data, path)))
}
