//! # Brazilian Soccer MCP Server
//!
//! A Model Context Protocol server that answers natural-language questions
//! about Brazilian soccer by exposing a knowledge graph built from six Kaggle
//! datasets (match results for Série A/B/C, Copa do Brasil and Libertadores,
//! plus the FIFA player database).
//!
//! Layering:
//!
//! ```text
//! data.rs      CSV ingestion (header-indexed, tolerant of dirty rows)
//! normalize.rs club-name folding: accents, state suffixes, aliases
//! model.rs     entities: Date, Competition, Source, Team, Match, Player, Record
//! graph.rs     KnowledgeGraph: identity resolution, de-duplication, adjacency
//! queries.rs   analytics: searches, head-to-head, tables, rankings, averages
//! format.rs    natural-language answers + structured JSON
//! tools.rs     MCP tool schemas, argument validation, dispatch
//! mcp.rs       JSON-RPC 2.0 over stdio
//! samples.rs   the worked example questions used by the demo and tests
//! ```

pub mod data;
pub mod format;
pub mod graph;
pub mod mcp;
pub mod model;
pub mod normalize;
pub mod queries;
pub mod samples;
pub mod tools;

use std::path::{Path, PathBuf};

/// Environment variable overriding the dataset location.
pub const DATA_DIR_ENV: &str = "BRAZILIAN_SOCCER_DATA_DIR";

/// Finds `data/kaggle`: the `BRAZILIAN_SOCCER_DATA_DIR` environment variable,
/// then the working directory, then the crate root (so tests work from
/// anywhere).
pub fn default_data_dir() -> PathBuf {
    if let Ok(dir) = std::env::var(DATA_DIR_ENV) {
        return PathBuf::from(dir);
    }
    let candidates = [
        PathBuf::from("data/kaggle"),
        Path::new(env!("CARGO_MANIFEST_DIR")).join("data/kaggle"),
    ];
    for candidate in candidates {
        if candidate
            .join(model::Source::Brasileirao.file_name())
            .exists()
        {
            return candidate;
        }
    }
    PathBuf::from("data/kaggle")
}

/// Loads the knowledge graph from [`default_data_dir`].
pub fn load_default_graph() -> Result<graph::KnowledgeGraph, data::DataError> {
    graph::KnowledgeGraph::load(&default_data_dir())
}
