// =============================================================================
// CONTEXT: Brazilian Soccer MCP Server — library root
//
// This crate implements an MCP (Model Context Protocol) server over stdio that
// answers natural-language-driven queries about Brazilian soccer using six
// Kaggle CSV datasets located in data/kaggle/:
//   - Brasileirao_Matches.csv        (Serie A 2012-2022)
//   - Brazilian_Cup_Matches.csv      (Copa do Brasil 2012-2021)
//   - Libertadores_Matches.csv       (Copa Libertadores 2013-2022)
//   - BR-Football-Dataset.csv        (extended stats, Serie A/B/C + Cup 2014-2023)
//   - novo_campeonato_brasileiro.csv (historical Serie A 2003-2019)
//   - fifa_data.csv                  (FIFA 19 player database, 18k players)
//
// Modules:
//   data   — CSV loading, team-name normalization, date parsing, dedup keys
//   query  — query engine: match search, team stats, head-to-head, standings,
//            player search, competition-wide statistics
//   server — JSON-RPC 2.0 / MCP protocol handling and tool definitions
// =============================================================================

pub mod data;
pub mod query;
pub mod server;
