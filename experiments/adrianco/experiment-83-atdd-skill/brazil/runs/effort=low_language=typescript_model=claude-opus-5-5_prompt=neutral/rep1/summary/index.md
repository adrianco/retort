# Summary: effort=low_language=typescript_model=claude-opus-5-5_prompt=neutral · rep 1

- **Shape:** TypeScript MCP (stdio) server over 6 in-memory Kaggle CSV datasets, exposing 18 Brazilian-soccer query tools.
- **Structure:** 5 source modules (~767 LOC) + 2 test files (32 tests).
- **Interfaces:** 18 MCP tools; no HTTP/CLI; 17 exported query functions.
- **Notable:** Thorough team-name normalization (alias table + state-suffix disambiguation), cross-source match deduplication, Copa do Brasil final-round labelling, and cross-dataset `team_profile` joining match data with FIFA squads. Goes well beyond the spec's minimum capability set.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
