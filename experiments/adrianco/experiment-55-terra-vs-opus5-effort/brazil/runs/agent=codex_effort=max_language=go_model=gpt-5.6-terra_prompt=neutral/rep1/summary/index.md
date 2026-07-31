# Summary: agent=codex effort=max language=go model=gpt-5.6-terra prompt=neutral · rep 1

- **Shape:** Go MCP server (hand-rolled JSON-RPC over stdio, standard library only) over six in-memory Kaggle CSV datasets for Brazilian soccer.
- **Structure:** 6 source modules + 1 test file (2,648 source LOC, 273 test LOC), zero third-party dependencies.
- **Interfaces:** 11 MCP tools + resources/prompts, a natural-language routing tool, and a `-query` CLI mode; 8 MCP methods handled.
- **Notable:** Every statistic is calculated from match scores (standings, head-to-head, most goals) rather than hardcoded; cross-file duplicate seasons are collapsed via `selectPreferredSources`; team names normalized across accents, state suffixes, and formal-name aliases. Goes well beyond the spec with bracket, season-comparison, and team-competition tools.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
