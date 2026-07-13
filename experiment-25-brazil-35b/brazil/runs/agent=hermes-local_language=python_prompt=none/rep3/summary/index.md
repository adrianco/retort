# Summary: agent=hermes-local language=python prompt=none · rep 3

- **Shape:** Python MCP server for Brazilian soccer data — pandas CSV loader + NetworkX knowledge graph, exposing 11 stdio MCP tools.
- **Structure:** 4 source modules (data_loader, knowledge_graph, models, server) + 3 test files (93 test functions total).
- **Interfaces:** 11 MCP `@app.tool()` functions; ~14 library methods across `MatchDataset` and `KnowledgeGraph`; 18 Pydantic models (defined but unused by tools).
- **Notable:** Queries filter row-by-row via `df.iterrows()` / list comprehensions rather than vectorized pandas; models.py schemas are decorative (tools return raw dicts); `KnowledgeGraph.get_connected_teams` has a `NameError` bug (undefined `next_hop`, line 119).

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
