pub mod data;
pub mod domain;
pub mod mcp;
pub mod normalize;
pub mod query;

pub use data::{DataError, DataStore, LoadReport};
pub use mcp::McpServer;
pub use query::SoccerService;
