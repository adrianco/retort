//! Query engine and MCP protocol surface for the bundled Brazilian soccer data.

pub mod mcp;
pub mod model;
pub mod normalize;
pub mod store;

pub use mcp::McpServer;
pub use model::*;
pub use store::SoccerStore;
