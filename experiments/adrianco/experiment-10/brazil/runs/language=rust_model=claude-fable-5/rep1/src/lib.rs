//! Brazilian Soccer MCP server library.
//!
//! Loads the Kaggle datasets in `data/kaggle/` into an in-memory store and
//! exposes query tools over the Model Context Protocol (stdio JSON-RPC).

pub mod data;
pub mod mcp;
pub mod normalize;
pub mod query;
