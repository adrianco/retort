//! Brazilian Soccer MCP server: loads the Kaggle CSV datasets in `data/kaggle`
//! into memory and answers match, team, player, competition and statistics
//! queries over the Model Context Protocol (JSON-RPC 2.0 on stdio).

pub mod data;
pub mod mcp;
pub mod normalize;
pub mod queries;

pub use data::{Competition, Database, Match, Player, Source};
