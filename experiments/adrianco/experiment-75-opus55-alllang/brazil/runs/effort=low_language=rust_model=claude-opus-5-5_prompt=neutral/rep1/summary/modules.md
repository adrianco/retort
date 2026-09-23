# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/main.rs | CLI entrypoint: loads data, runs a JSON-RPC/stdio read loop | `main()` |
| src/lib.rs | Crate root re-exporting the three modules | `data`, `mcp`, `query` |
| src/data.rs | CSV loading, team-name normalization, date parsing, `Match`/`Player`/`Dataset` types | `Dataset::load`, `team_key`, `fold`, `normalize_date`, `Competition` |
| src/query.rs | Query engine: match search, team records, standings, players, aggregates, head-to-head | `Engine`, `MatchFilter`, `Record`, `StandingRow`, `DERBIES` |
| src/mcp.rs | Minimal MCP server over JSON-RPC 2.0: tool schemas + dispatch | `handle`, `tool_definitions`, `call_tool` |
| tests/bdd.rs | BDD-style Given/When/Then scenarios covering every capability | 31 `#[test]` functions |
