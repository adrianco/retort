//! ============================================================================
//! Context
//! ----------------------------------------------------------------------------
//! Crate:    brazilian_soccer_mcp (library)
//! Purpose:  A Model Context Protocol (MCP) server that exposes a knowledge
//!           graph over six Brazilian-soccer Kaggle datasets so that an LLM can
//!           answer natural-language questions about matches, teams, players,
//!           competitions and statistics.
//!
//! Module map:
//!   * `normalize` - team-name canonicalization, date & goal parsing.
//!   * `models`    - the `Match` and `Player` domain types.
//!   * `data`      - CSV loaders building the in-memory `Database`.
//!   * `query`     - pure analytical functions over the `Database`.
//!   * `format`    - render query results into the spec's text formats.
//!   * `mcp`       - JSON-RPC 2.0 / MCP protocol surface and tool catalog.
//!
//! The binary (`main.rs`) wires `mcp::Server` to a newline-delimited JSON
//! stdio transport. Everything else is library code, exercised by the BDD
//! tests in `tests/`.
//! ============================================================================

pub mod data;
pub mod format;
pub mod mcp;
pub mod models;
pub mod normalize;
pub mod query;

pub use data::Database;
pub use mcp::Server;
