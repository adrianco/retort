# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/main.rs | CLI: `serve` MCP stdio loop, `ask` one-shot tool call | `main()`, `default_data_dir` |
| src/lib.rs | Crate root, re-exports, `default_data_dir()` | `default_data_dir` |
| src/mcp.rs | JSON-RPC 2.0 MCP server (initialize/tools/resources/prompts, batches) | `Server`, `serve()`, `handle()` |
| src/tools.rs | 14 tool specs + JSON schemas + arg parsing + dispatch | `TOOLS`, `call()`, `ToolOutput` |
| src/queries.rs | Query engine: match/h2h/team/standings/rankings/stats/players | `search_matches`, `standings`, `head_to_head`, `team_stats`, `team_rankings`, `competition_stats`, `biggest_wins`, `search_players`, `club_squad` |
| src/format.rs | Render query results → NL text + structured JSON | `match_search`, `standings`, `team_stats`, `rankings`, ... |
| src/graph.rs | Knowledge graph: nodes/edges, team resolution, file dedup | `KnowledgeGraph`, `resolve_team`, `neighbors`, `stats` |
| src/model.rs | Domain types | `Competition`, `Source`, `Date`, `Team`, `Match`, `Player` |
| src/normalize.rs | Team-name normalization (suffixes, accents, aliases) | normalization fns |
| src/data.rs | CSV loading via `csv` crate, BOM/casefold, per-file load reports | `load`, `LoadReport` |
| src/samples.rs | Built-in sample questions | sample list |
| tests/*.rs | 8 BDD/integration test files (75 `#[test]`) + unit tests | see below |

## Tests

| File | #[test] | Covers |
|------|---------|--------|
| tests/bdd_match_queries.rs | 10 | match search by team/opponent/competition/season/date |
| tests/bdd_team_queries.rs | 10 | team_stats, W/L/D, goals, home/away |
| tests/bdd_player_queries.rs | 10 | player search by name/nationality/club |
| tests/bdd_competition_queries.rs | 8 | standings computed from matches |
| tests/bdd_statistics.rs | 9 | aggregate stats, biggest wins, h2h |
| tests/bdd_data_quality.rs | 11 | name normalization, dedup, encoding |
| tests/mcp_protocol.rs | 12 | JSON-RPC initialize/tools/list/call/resources/prompts |
| tests/sample_questions.rs | 5 | end-to-end sample questions |
| tests/common/mod.rs | — | shared test harness (`given_.../when_.../then_...`) |

Total: 94 `#[test]` across tests/ + src/ unit tests. No `#[ignore]` / skipped tests.
