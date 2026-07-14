# Summary: language=python model=sonnet-5 prompt=none · rep1

- **Shape:** Python FastMCP (stdio) server over an in-memory knowledge graph of Brazilian soccer matches + FIFA players, loaded from six Kaggle CSVs with pandas.
- **Structure:** 6 source modules (soccer_mcp/) + 4 test files (40 test functions) with a shared real-data fixture.
- **Interfaces:** 12 MCP tools (match/team/competition/stats/player queries), no HTTP or CLI; unified `Match`/`Player`/`TeamRecord` models.
- **Notable:** Substantial investment in the two hardest parts of the spec — a dedicated `team_names` normalizer (alias table + suffix/accent stripping) and per-season source deduplication so overlapping datasets don't double-count in aggregates. Data is loaded once as a lazy singleton and served synchronously; validation is minimal.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
