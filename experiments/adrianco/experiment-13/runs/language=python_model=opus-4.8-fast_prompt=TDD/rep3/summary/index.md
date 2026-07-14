# Summary: language=python · model=opus-4.8-fast · prompt=TDD · rep 3

- **Shape:** Python MCP server (FastMCP/stdio) over Brazilian-soccer CSVs, with a layered KB → service → server design.
- **Structure:** 6 source modules, 6 test files (~98 test functions).
- **Interfaces:** 9 MCP tools; `SoccerKB` library API; in-memory `Match`/`Player` dataclasses loaded from 6 CSVs.
- **Notable:** Clean separation — `service`/`knowledge_base` hold no MCP imports and are directly unit-tested; centralized accent/suffix/date normalization; standings, records and stats are all computed from match results; cross-source de-duplication keeps one authoritative source per (competition, season). Integration tests exercise the real `data/kaggle` datasets.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
