# Summary: language=go_model=claude-opus-4-8_tooling=none · rep 1

- **Shape:** Go stdlib-only port (`wombat-go/`) of the FunkyGibbon MCP client — inbetweenies-v2 sync engine + durable JSON graph cache + stdio JSON-RPC MCP server with 12 tools.
- **Structure:** 12 source modules across 9 packages, 6 test files (30 test functions); ~1,894 non-test LOC; zero external dependencies.
- **Interfaces:** 12 MCP tools over stdio JSON-RPC; 1 outbound sync HTTP call (`POST /api/v1/sync/`, bearer auth); JSON-file persistence.
- **Notable:** Additive and clean — no modification of the Python/TypeScript clients. Conformance-first: tests read the shared `fixtures/*.json` directly. Idiomatic Go (internal packages, mutex-guarded store, atomic temp-file rename, context timeouts). All fixtures reproduced; build + tests pass.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
