# Summary: language=go model=opus tooling=none · rep 1

- **Shape:** Go stdio MCP server (hand-rolled JSON-RPC, stdlib only) over an in-memory store of Brazilian-soccer CSV data.
- **Structure:** 3 source modules (`main.go`, `soccer/loader.go`, `soccer/query.go`) + 1 test file; no external dependencies (stdlib `encoding/csv`, `encoding/json`).
- **Interfaces:** 10 MCP tools (match/team/player/competition/stats queries); 4 JSON-RPC methods; ingests 6 datasets.
- **Notable:** Thoughtful team-name normalization (diacritic stripping, club-prefix removal, state-suffix preservation). No official MCP SDK — JSON-RPC implemented by hand. Tests are data-dependent and skip when `data/kaggle` is absent.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
