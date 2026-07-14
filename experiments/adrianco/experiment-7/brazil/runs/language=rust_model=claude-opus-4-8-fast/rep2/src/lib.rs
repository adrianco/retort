// =============================================================================
// Context
// -----------------------------------------------------------------------------
// Crate:   brazilian_soccer_mcp (library)
// Purpose: Library root re-exporting the building blocks of the Brazilian
//          Soccer MCP server so they can be exercised by both the binary
//          (`src/main.rs`) and the integration / BDD test suite (`tests/`).
//
// Modules:
//   normalize -> team-name + date normalisation helpers
//   data      -> CSV loaders and the unified in-memory model
//   queries   -> the query engine (one method per spec capability)
//   mcp       -> JSON-RPC 2.0 / MCP request dispatch over stdio
// =============================================================================

pub mod data;
pub mod mcp;
pub mod normalize;
pub mod queries;

pub use data::{Dataset, Match, Player};
pub use queries::MatchFilter;
