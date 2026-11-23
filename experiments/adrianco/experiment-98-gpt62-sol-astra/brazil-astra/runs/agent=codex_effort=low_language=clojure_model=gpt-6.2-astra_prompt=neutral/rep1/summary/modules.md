# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| soccer.clj | Data loading, team-name normalization, and the query engine | `load-db`, `query`, `matches`, `players`, `standings`, `summary`, `team` |
| server.clj | MCP JSON-RPC server: tool catalog, schema validation, dispatch | `-main`, `dispatch`, `call-tool`, `catalog` |
| soccer_test.clj | Behavioural tests over the query engine + protocol | 5 deftests (`source-coverage`, `match-questions`, `league-questions`, `relationship-questions`, `protocol`) |
| deps.edn | tools.deps project: clojure 1.12, data.csv, data.json; `:server` and `:test` aliases | — |

Build artifacts / data (not source): `data/kaggle/*.csv` (6 datasets).
