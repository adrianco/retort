# Architecture summary — brazilian-soccer-mcp (go, opus-5, effort=xhigh)

MCP server exposing a Brazilian-soccer knowledge graph over the official Go MCP SDK
(`github.com/modelcontextprotocol/go-sdk`). Layered cleanly:

## Modules

- **`main.go`** — command entrypoint. Serves MCP over stdio by default; also `-http`,
  `-list-tools`, `-call <tool> -args <json>`, and `-demo` (answers 12 sample questions
  through the real in-process protocol via `connectLoopback`). Loads the graph once.
- **`internal/mcpserver/`** — protocol surface.
  - `server.go` — builds the `mcp.Server`, registers 15 tools, 5 read-only resources
    (`soccer://datasets|teams|competitions|sample-questions|tools`) and 3 prompt
    templates (`club_report`, `season_review`, `compare_clubs`). Graph is immutable
    after load, so no locking.
  - `tools.go` — the 15 tool definitions, argument structs (LLM-forgiving: any team
    spelling, competition aliases, ISO dates, year seasons), and mapping onto
    `soccer.MatchFilter`/`PlayerFilter`. Each tool returns dual text + structured result.
- **`internal/soccer/`** — the domain/knowledge-graph core (loader, model, graph,
  matches, teams, players, competitions, analytics, names normalization, format).
  - `loader.go` — a dedicated reader per CSV normalises 6 heterogeneous Kaggle files
    (differing columns/date formats/naming) onto common `rawMatch`/`Player` shapes;
    unusable rows are counted, not silently dropped.
  - `graph.go` + siblings — resolves team identity across name variants, de-duplicates
    overlapping Série A files, and computes standings/champions/head-to-head/aggregates
    from match results rather than reading a table.
- **`bdd/`** + **`features/`** — a hand-rolled Gherkin runner. Six `.feature` files
  (match/player/team/competition/statistics/data-quality) whose English steps bind to
  tool calls in `steps_test.go` and run as Go subtests; unbound sentences fail the run.

## Test surface

55 `Test*` functions across `internal/soccer` (queries, names, graph), `internal/mcpserver`
(protocol discoverability, every-tool-runs, error quality, structured results, resources,
prompts, latency, concurrency), `bdd` (all feature scenarios), and `main`. Zero `t.Skip`.

## Data flow

CSV files → per-file loader → raw records → `Graph.Load` (identity resolution +
de-dup) → immutable graph → tool handlers filter/aggregate → dual text+structured
MCP result.
