// Brazilian Soccer MCP Server
// ----------------------------
// Context: Library crate backing an MCP (Model Context Protocol) server that
// answers natural-language questions about Brazilian soccer. It loads the
// pre-downloaded Kaggle CSV datasets (matches across Brasileirão, Copa do
// Brasil, Libertadores and historical records, plus FIFA player data) into an
// in-memory store and exposes query + statistics primitives that the MCP tool
// layer formats into human-readable answers.
//
// Module map:
//   normalize - canonicalize team names for robust matching
//   model     - core domain types (Match, Player, Competition)
//   data      - CSV loaders for each provided dataset
//   query     - the in-memory Database and all query/statistics operations
//   mcp       - JSON-RPC MCP server: tool definitions and dispatch

pub mod data;
pub mod mcp;
pub mod model;
pub mod normalize;
pub mod query;
