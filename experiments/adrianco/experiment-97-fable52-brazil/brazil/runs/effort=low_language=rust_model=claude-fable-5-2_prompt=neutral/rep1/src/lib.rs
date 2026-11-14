//! Brazilian Soccer MCP server: loads the Kaggle CSV datasets into memory and
//! exposes match, team, player, competition and statistical queries as MCP tools.
pub mod data;
pub mod mcp;
pub mod normalize;
pub mod queries;
