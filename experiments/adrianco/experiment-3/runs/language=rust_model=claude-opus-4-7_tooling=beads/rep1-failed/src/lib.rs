//! Brazilian Soccer MCP server — library crate.
//!
//! Context: this crate implements the MCP (Model Context Protocol) server
//! specified in `TASK.md` / `brazilian-soccer-mcp-guide.md`. It loads six
//! Kaggle CSV datasets about Brazilian soccer (matches, competitions and FIFA
//! players) into an in-memory knowledge graph and exposes query tools over a
//! JSON-RPC stdio transport.
//!
//! Module map:
//! - [`csvparse`]      — minimal RFC-4180 CSV reader (handles BOM + quotes)
//! - [`normalize`]     — team-name normalization (state suffixes, accents)
//! - [`model`]         — core `Match` / `Player` data structures
//! - [`data`]          — dataset loading and the in-memory `Database`
//! - [`matches`]       — match lookup queries
//! - [`teams`]         — team statistics and head-to-head records
//! - [`players`]       — FIFA player queries
//! - [`competitions`]  — league-table / standings calculation
//! - [`stats`]         — aggregated statistical analysis
//! - [`mcp`]           — JSON-RPC 2.0 / MCP protocol server

pub mod csvparse;
pub mod normalize;
pub mod model;
pub mod data;
pub mod matches;
pub mod teams;
pub mod players;
pub mod competitions;
pub mod stats;
pub mod mcp;
