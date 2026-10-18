//! Context: crate root for the Brazilian soccer MCP server.
//!
//! Layers: `normalize` (names, dates, goals) -> `data` (CSV loading into a
//! [`data::Dataset`]) -> `query` (matches, records, standings, players) ->
//! `mcp` (JSON-RPC tools). `main.rs` wires these to stdin/stdout.

pub mod data;
pub mod mcp;
pub mod normalize;
pub mod query;
