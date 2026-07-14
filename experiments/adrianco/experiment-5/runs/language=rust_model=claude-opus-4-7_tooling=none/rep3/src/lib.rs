//! Brazilian Soccer MCP — library crate.
//!
//! Loads the bundled Kaggle datasets into in-memory collections and exposes a
//! query API used by both the MCP server (`src/main.rs`) and the integration
//! tests under `tests/`.

pub mod data;
pub mod normalize;
pub mod queries;
pub mod mcp;
