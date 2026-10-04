# Summary: effort=low_language=java_model=claude-opus-5-5_prompt=neutral · rep 1

- **Shape:** Java MCP server (JSON-RPC 2.0 over stdio) for Brazilian soccer data, backed by an in-memory store loaded from six Kaggle CSVs; hand-rolled JSON and CSV parsers, no external runtime dependencies.
- **Structure:** 8 main modules, 4 test files (~2,420 lines total; 42 `@Test` methods).
- **Interfaces:** 15 MCP tools (matches, standings, rankings, stats, cup brackets, FIFA players, cross-dataset club profiles); 4 JSON-RPC methods (initialize, ping, tools/list, tools/call).
- **Notable:** Substantial domain modeling for a low-effort cell — cross-source fixture de-duplication, a dedicated team-name canonicalizer (accents, state suffixes, aliases, ambiguous-club handling), inferred seasons for a season-less dataset, and lenient in-band argument coercion so a calling LLM can self-correct.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
