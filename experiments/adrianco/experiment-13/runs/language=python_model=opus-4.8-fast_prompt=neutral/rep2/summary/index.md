# Summary: language=python · model=opus-4.8-fast · prompt=neutral · rep 2

- **Shape:** Python MCP server (FastMCP/stdio) over pandas, with a parallel argparse CLI, querying 6 Brazilian-soccer Kaggle CSVs.
- **Structure:** 7 source modules (`bsoccer/`) + 4 test files (47 test functions) + conftest.
- **Interfaces:** 11 MCP tools (matches, teams, players, competitions, stats) mirrored by 9 CLI subcommands; no HTTP routes.
- **Notable:** Dedicated `normalize` module with an alias map and ambiguous-base handling (Atlético-MG vs -GO); a deduplicated `matches_dedup` view to avoid double-counting overlapping Brasileirão files; clean layered separation (data → queries → format → server/cli).

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
