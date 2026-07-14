# Summary: language=python · model=sonnet-5 · prompt=tdd · rep 1

- **Shape:** Python MCP server (`FastMCP`) over pandas, unifying 6 Kaggle CSVs into cached DataFrames queried by 9 tools.
- **Structure:** 5 source modules (521 LOC) + 4 test files (382 LOC, 49 tests, all green).
- **Interfaces:** 0 HTTP routes / 0 CLI commands / 9 MCP tools backed by 9 query functions.
- **Notable:** Clean layered split (normalize → data_loader → queries → server); real data-quality handling (name canonicalization with alias/disambiguation tables, multi-format date parsing, NaN-score rendering, pre-2012 trim to avoid double-counting). Two real bugs found & fixed during the run (double-counted standings, `int(NaN)` crash).

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
