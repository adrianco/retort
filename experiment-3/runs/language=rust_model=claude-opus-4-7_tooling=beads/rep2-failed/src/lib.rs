//! Brazilian Soccer MCP Server — library crate.
//!
//! This crate implements the knowledge interface described in `TASK.md`: it
//! loads six Kaggle CSV datasets covering Brazilian soccer matches and FIFA
//! player data, and exposes query capabilities over the Model Context Protocol
//! (MCP). The binary (`src/main.rs`) wires these modules to a JSON-RPC loop on
//! stdio; the library is also consumed directly by the BDD test suite.
//!
//! Module map:
//! * `models`    — domain types (`Match`, `Player`, `Date`).
//! * `normalize` — team-name / accent normalization for consistent matching.
//! * `data`      — CSV loading and the in-memory `Database`.
//! * `queries`   — match / team / player / competition / statistics queries.
//! * `mcp`       — MCP JSON-RPC protocol handling and tool dispatch.

pub mod data;
pub mod mcp;
pub mod models;
pub mod normalize;
pub mod queries;

pub use data::Database;
