//! Brazilian soccer MCP server library.
//!
//! Layers, from the bottom up:
//! - [`normalize`]: team and text normalization (accents, state suffixes, aliases).
//! - [`data`]: CSV loading into an in-memory [`data::Dataset`].
//! - [`query`]: matching, aggregation, standings and player search.
//! - [`tools`]: MCP tool definitions and argument handling.
//! - [`mcp`]: JSON-RPC 2.0 message handling for the MCP protocol.

pub mod data;
pub mod mcp;
pub mod normalize;
pub mod query;
pub mod tools;
