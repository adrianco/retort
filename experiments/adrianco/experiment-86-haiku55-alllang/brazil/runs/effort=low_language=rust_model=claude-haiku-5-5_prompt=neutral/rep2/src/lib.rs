//! Brazilian soccer knowledge-graph-style query layer exposed as an MCP server.
//!
//! - [`normalize`]: team-name and date normalization
//! - [`data`]: CSV loading into a unified [`data::Dataset`]
//! - [`query`]: pure query functions (matches, records, standings, players)
//! - [`tools`]: MCP tool definitions, argument handling and text formatting
//! - [`mcp`]: JSON-RPC over stdio

pub mod data;
pub mod mcp;
pub mod normalize;
pub mod query;
pub mod tools;
