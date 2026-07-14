# Summary: language=python_model=sonnet-5_prompt=bdd · rep 1

- **Shape:** Python MCP server (FastMCP over stdio) with a pandas knowledge-graph backend over 6 local Kaggle CSVs.
- **Structure:** 6 source modules + 6 test modules (85 tests), clean layering: data_loader → graph → queries → formatting → server.
- **Interfaces:** 14 MCP tools; parallel plain-data `QueryEngine` API for unit testing; no HTTP/network surface.
- **Notable:** Careful data-quality handling — name normalization with state-suffix disambiguation, cross-source match dedup, and per-competition/season authoritative-source selection so standings/champions don't double-count overlapping datasets.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
