//! Brazilian Soccer MCP Server
//!
//! Loads the six provided Kaggle datasets (Brasileirão, Copa do Brasil,
//! Libertadores, extended match stats, historical Brasileirão, and FIFA
//! player data) into an in-memory knowledge base, and exposes it as MCP
//! tools for natural-language querying by a connected LLM.

pub mod dates;
pub mod loaders;
pub mod model;
pub mod normalize;
pub mod server;
pub mod store;

pub use loaders::load_from_dir;
pub use store::KnowledgeBase;
