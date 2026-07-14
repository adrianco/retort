//! ============================================================================
//! Crate: brazilian_soccer_mcp
//!
//! Context
//! -------
//! A Model Context Protocol (MCP) server exposing a knowledge-graph query
//! interface over the provided Brazilian soccer datasets (Brasileirão, Copa do
//! Brasil, Copa Libertadores match data plus the FIFA player database).
//!
//! Layering:
//!   normalize -> model -> loader -> db (query engine) -> mcp (protocol) -> main
//!
//! The library is transport-independent and fully testable: `Database` answers
//! all the query categories in the specification, and `mcp::Server` wraps it in
//! the JSON-RPC tool protocol that an LLM connects to.
//! ============================================================================

pub mod db;
pub mod loader;
pub mod mcp;
pub mod model;
pub mod normalize;

pub use db::Database;
pub use mcp::Server;
