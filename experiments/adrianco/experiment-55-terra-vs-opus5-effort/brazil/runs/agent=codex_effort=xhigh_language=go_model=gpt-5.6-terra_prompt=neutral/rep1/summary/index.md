# Summary: codex · go · gpt-5.6-terra · effort=xhigh · prompt=neutral · rep 1

- **Shape:** Go MCP server (JSON-RPC 2.0 over stdio), zero third-party deps — stdlib `encoding/json` + `encoding/csv` only.
- **Structure:** 6 source modules + 1 test file (~1,265 source LOC + 162 test LOC), 11 MCP tools.
- **Interfaces:** 11 registered MCP tools covering match/team/player/competition/statistics queries; 6 CSV datasets loaded from `data/kaggle/`.
- **Notable:** Strong team-name normalization (accent folding, state-suffix stripping, club aliases, derby rivalry map); cross-source fixture deduplication with an authoritative-source priority for calculated tables; loader fails hard on any missing CSV.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
