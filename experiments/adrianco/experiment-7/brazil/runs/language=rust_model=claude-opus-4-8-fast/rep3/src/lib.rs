// =============================================================================
// Brazilian Soccer MCP Server — library root
// -----------------------------------------------------------------------------
// Context:
//   This crate implements a Model Context Protocol (MCP) server that exposes a
//   queryable knowledge graph over a set of Brazilian-soccer datasets (matches,
//   teams, players and competitions). The datasets live as CSV files under
//   `data/kaggle/` and are described in TASK.md.
//
// Architecture:
//   * `normalize`  — team-name normalization, accent stripping and multi-format
//                    date parsing (handles the data-quality notes in the spec).
//   * `data`       — record models (`Match`, `Player`) and the per-file CSV
//                    loaders. Loaders unify heterogeneous schemas into one model
//                    and de-duplicate overlapping rows across source files.
//   * `store`      — `DataStore`, the in-memory dataset loaded once at start-up.
//   * `queries`    — the analytical query layer (match search, team records,
//                    head-to-head, player search, standings, statistics). These
//                    functions are pure over `&DataStore` and are unit-tested
//                    directly as well as exercised via the BDD test-suite.
//   * `mcp`        — the JSON-RPC 2.0 / stdio MCP transport: `initialize`,
//                    `tools/list` and `tools/call` wiring around `queries`.
//
// The library is deliberately dependency-light (csv + serde_json) so that it
// builds quickly and is easy to audit.
// =============================================================================

pub mod normalize;
pub mod data;
pub mod store;
pub mod queries;
pub mod mcp;

pub use store::DataStore;
