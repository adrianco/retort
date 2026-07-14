//! ============================================================================
//! Crate: brazilian-soccer-mcp (library)
//! Project: Brazilian Soccer MCP Server (Rust)
//!
//! Context:
//!   Library root that wires together the modules of the MCP server so both the
//!   binary (`src/main.rs`) and the integration/BDD test-suite (`tests/`) can
//!   share the exact same logic. The pipeline is:
//!
//!       loader  -> parses the six CSVs into model types
//!       model   -> Match / Player / Competition domain structs
//!       normalize -> team-name & date normalization for consistent matching
//!       store   -> in-memory knowledge graph + typed query engine
//!       format  -> renders query results as human-readable answers
//!       mcp     -> JSON-RPC 2.0 stdio server exposing the queries as tools
//!
//!   Nothing here performs I/O at import time; `Store::load_from_dir` is the
//!   single entry point that reads data.
//! ============================================================================

pub mod format;
pub mod loader;
pub mod mcp;
pub mod model;
pub mod normalize;
pub mod store;

pub use store::Store;
