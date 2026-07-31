# Summary: agent=claude-code effort=xhigh model=claude-opus-5 prompt=neutral · rep 1

- **Shape:** Python MCP server (mcp SDK, stdio) over an in-memory knowledge graph built from six Brazilian-soccer Kaggle CSVs, plus a mirror argparse CLI.
- **Structure:** 12 package modules (`brazilian_soccer/`, ~5,400 LOC incl. tests) in a strict bottom-up layer stack; 13 unit/integration test files (192 test functions) + 8 Gherkin feature files (59 pytest-bdd scenarios).
- **Interfaces:** 24 MCP tools + 4 resources + 2 prompts, mirrored by a 4-subcommand CLI (`serve`/`tools`/`summary`/`call`); a 6-node-type / 8-edge-type knowledge graph.
- **Notable:** Heavy investment in cross-dataset club-name reconciliation (curated ~150-club registry + observed clustering + fuzzy search) and cross-source match de-duplication (Serie A appears in three files). Errors are returned as helpful, suggestion-bearing messages rather than raised, and dataset coverage limits (FIFA-19 unlicensed clubs, no goalscorer/lineup data, penalty-decided finals) are explicitly surfaced. Among the more elaborate/complete implementations of this task.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
