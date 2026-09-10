# Summary: agent=codex effort=low language=go model=gpt-6-astra prompt=neutral · rep 1

- **Shape:** Go stdlib-only MCP server (JSON-RPC 2.0 over stdio) with an in-memory query engine over six Brazilian-soccer CSV datasets. No external dependencies (`go.mod` declares only the module).
- **Structure:** 3 source modules (main/data/query, ~915 LOC) + 1 test file (17 tests, 2 benchmarks, ~377 LOC).
- **Interfaces:** 10 MCP tools (search_matches, search_players, team_stats, head_to_head, team_profile, standings, statistics, competition_info, graph, data_info); 1 CLI flag (`-data`).
- **Notable:** Careful team-name normalization (state-suffix stripping, alias map, club-collision guards), cross-source match dedup with enrichment and conflict warnings, standings computed from results, and pervasive caveat notes about what the data cannot prove (goalscorers, official relegation, bracket winners). Unusually complete for a "low effort" run.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
