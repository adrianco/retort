// ============================================================================
// CONTEXT: Brazilian Soccer MCP Server - library root
//
// Purpose:  Exposes a knowledge base of Brazilian soccer data (matches from
//           five Kaggle CSV datasets plus the FIFA player database) through
//           an MCP (Model Context Protocol) server speaking JSON-RPC 2.0
//           over stdio.
//
// Modules:
//   normalize - team-name canonicalization (state suffixes, accents,
//               aliases) and date/competition normalization
//   data      - CSV loading into unified Match / Player models
//   queries   - query + aggregation engine (search, stats, standings, H2H)
//   server    - MCP protocol handling: initialize, tools/list, tools/call
//
// Data dir:  ./data/kaggle by default; override with BRAZIL_SOCCER_DATA env
//            var or the first CLI argument of the binary.
//
// Testing:   BDD (Given/When/Then) integration tests live in tests/.
// ============================================================================

pub mod data;
pub mod normalize;
pub mod queries;
pub mod server;
