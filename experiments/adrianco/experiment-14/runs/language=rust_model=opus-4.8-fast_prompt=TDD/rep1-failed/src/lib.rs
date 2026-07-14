//! Brazilian Soccer MCP server library.
//!
//! Provides an in-memory knowledge base over the bundled Kaggle datasets
//! (matches across Brasileirão, Copa do Brasil and Libertadores, plus the
//! FIFA player database) and a query engine that answers the natural-language
//! style questions described in the specification. The [`mcp`] module exposes
//! these queries as Model Context Protocol tools over stdio.

pub mod data;
pub mod mcp;
pub mod models;
pub mod normalize;
pub mod query;
