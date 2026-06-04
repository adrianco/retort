// =============================================================================
// Context: Brazilian Soccer MCP Server
// File:    src/lib.rs
// Purpose: Library crate root. Wires together the data, model, normalization,
//          query, MCP-protocol and tool modules so they can be exercised both
//          by the `brazilian-soccer-mcp` binary and by the integration tests.
// =============================================================================

pub mod data;
pub mod mcp;
pub mod model;
pub mod normalize;
pub mod queries;
pub mod tools;

pub use data::Database;
