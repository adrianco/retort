# Run Summary — Brazilian Soccer MCP Server (Clojure)

**Surface:** A stdio JSON-RPC MCP server answering natural-language-style queries
about Brazilian soccer (matches, teams, players, competitions, statistics) backed
by the bundled Kaggle CSV datasets in `data/kaggle/`.

See [modules.md](modules.md) and [interfaces.md](interfaces.md).

## At a glance

- 3 source files, 349 LOC total (88 server / 177 domain / 84 tests).
- Clean layering: `soccer.clj` (pure data + query engine) ← `server.clj` (MCP
  protocol + schema validation) ← `soccer_test.clj` (behavioural tests).
- No external services; all answers computed from the 6 provided CSVs.
- Build + tests pass (test_coverage=1.0); 5 deftests, 42 assertions, 0 skips.

## Control flow

`-main` (server.clj) loads the DB once via `soccer/load-db`, then reads JSON-RPC
lines from stdin, dispatches `initialize` / `ping` / `tools/list` / `tools/call`,
validates arguments against each tool's `inputSchema`, and delegates data work to
`soccer/query`, which fans out by tool name to `matches` / `players` /
`team_profile` / `standings` / `statistics` / `biggest_wins`.
