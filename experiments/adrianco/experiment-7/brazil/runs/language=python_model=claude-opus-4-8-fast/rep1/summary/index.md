# Summary: language=python model=claude-opus-4-8-fast · rep 1

- **Shape:** FastMCP (Python MCP SDK) server over pandas DataFrames — a knowledge-graph query engine for Brazilian soccer data.
- **Structure:** 6 source modules + launcher, 7 test files (44 test functions), 1 Gherkin feature file.
- **Interfaces:** 13 MCP tools (match/team/player/competition/statistics + discovery); no HTTP/CLI; library API mirrors the tools via `KnowledgeGraph`.
- **Notable:** Clean separation (loader → graph → formatting → server adapter); name normalisation handles accents + state suffixes; multi-source dedup by priority to avoid double-counting; lazy cached load. All 12 pinned requirements implemented and tested.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
