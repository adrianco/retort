# Summary: language=typescript, model=opus-4.8, prompt=bdd · rep 1

- **Shape:** TypeScript MCP server (`@modelcontextprotocol/sdk` over stdio) with an in-memory CSV data layer and a transport-agnostic query library.
- **Structure:** 13 source modules + 7 test files (+ shared fixtures), ~2,240 LOC, 6 dependencies.
- **Interfaces:** 11 MCP tools covering match/team/player/competition/statistical queries; each backed by an independently unit-tested library function.
- **Notable:** Clean layering (dataStore → normalize/filters → query modules → format → server); Zod-validated tool inputs; handles real-world data quirks (accent/BOM normalization, lenient team matching, suffix-preserving standings keys, overlapping-dataset dedup per season). All 45 BDD tests pass.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
