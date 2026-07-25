# Summary: language=python model=claude-opus-5 prompt=neutral · rep 1

- **Shape:** Python FastMCP (MCP SDK) server over a hand-built in-memory knowledge graph of Brazilian football; pure-stdlib data/query layer, no pandas.
- **Structure:** 10 package modules + 13 test files (158 test functions); ~3.7k source LOC, ~2.4k test LOC.
- **Interfaces:** 21 MCP tools + 2 MCP resources, 2 CLI entry points (`server`, `demo`); Match/Player/Team data model loaded from all six `data/kaggle/` CSVs.
- **Notable:** Cross-source fixture de-duplication (45-day merge window) so overlapping CSVs aren't triple-counted; accent/suffix-tolerant team registry with fuzzy suggestions; standings computed from matches and withhold a champion label when fixtures are missing. This is a REPAIR run — prior attempt failed the build/test gate; the repaired code builds and all tests pass (`test_coverage=1.0`).

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
