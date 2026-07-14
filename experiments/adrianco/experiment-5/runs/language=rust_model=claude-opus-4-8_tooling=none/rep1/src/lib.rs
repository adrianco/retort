//! Brazilian Soccer MCP server library.
//!
//! Loads the provided Kaggle CSV datasets into memory and answers natural
//! language style queries about matches, teams, players, competitions and
//! aggregate statistics. The [`mcp`] module exposes these as MCP tools over a
//! stdio JSON-RPC transport.

pub mod data;
pub mod mcp;
pub mod model;
pub mod normalize;
pub mod queries;

pub use data::Dataset;
