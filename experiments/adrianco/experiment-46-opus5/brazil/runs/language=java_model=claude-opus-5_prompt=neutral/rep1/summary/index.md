# Summary: language=java · model=claude-opus-5 · prompt=neutral · rep 1

Brazilian Soccer MCP Server — an MCP server exposing a knowledge-graph interface over six Kaggle
CSV datasets (Brasileirão A/B/C, Copa do Brasil, Copa Libertadores matches + FIFA players) for
natural-language queries about matches, teams, players, competitions and statistics.

- **Shape:** Java 21 / Maven MCP server (official `io.modelcontextprotocol.sdk` Java SDK) over
  stdio, backed by an in-memory knowledge graph loaded from CSV at startup; shaded-jar executable
  with a CLI fallback (`--call`, `--list-tools`).
- **Structure:** 30 main source files across 6 packages (data, graph, model, query, format, tools,
  util) + 10 test files + 7 Cucumber feature files (~48 BDD scenarios plus ~39 JUnit `@Test`s).
- **Interfaces:** 15 MCP tools (search_matches, head_to_head, find_derbies, team_stats,
  standings, competition_summary, compare_seasons, search_players, player_profile, statistics,
  …); no HTTP; a small transport-independent library core (`ToolRegistry`, `SoccerTool`) plus a
  4-flag CLI.
- **Notable:** Unusually complete and layered — clean separation of transport (MCP factory) from
  a transport-independent tool catalogue and query services; explicit multi-file de-duplication/
  merge of overlapping datasets; club-name canonicalisation with ambiguity notes; standings and
  statistics computed from raw match results. Answers are plain text, not JSON. Optional external
  APIs from the spec (API-Football, TheSportsDB) are not integrated. Scored code_quality 1.0,
  test_coverage 1.0, defect_rate 1.0, idiomatic 0.87 (token_efficiency very low — a large,
  thorough implementation).

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
