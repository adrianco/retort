# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| `main.m` | stdio JSON-RPC loop + MCP method dispatch (`initialize`/`ping`/`tools/list`/`tools/call`), process arg handling | `main()`, `dispatchRequest()`, `rpcError()` |
| `Soccer.h` | Public interface for the data/query engine | `Soccer` class: `initWithDirectory:error:`, `+tools`, `call:arguments:` |
| `Soccer.m` | CSV load + normalization + all query logic (matches, team stats, standings, players, head-to-head) | `Soccer` impl; helpers `teamKey()`, `competitionName()`, `readCSV()`, `datePart()`, `summarize()`, `page()`, `validate()` |
| `tests.py` | Behavior tests driving the built binary over the real stdio MCP connection | 22 `test_*` methods |
| `Makefile` | Build (`clang -fobjc-arc -Werror`, Foundation) + `test` target | `all`, `test`, `clean` |

Build artifacts excluded: `soccer-mcp` (compiled binary, gitignored).
