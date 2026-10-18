# Architecture: brazilian-soccer-mcp (Go)

A standard-library-only Go MCP server (no external deps; `go.sum` empty). Three
internal packages plus a thin `main`.

## Modules

| Package | Files | Role |
|---------|-------|------|
| `main` | `main.go` | CLI entrypoint: `-data` flag, loads the store, runs the MCP server over stdio. |
| `internal/mcp` | `server.go`, `tools.go`, `format.go` | JSON-RPC 2.0 MCP server and the 7 soccer tools. |
| `internal/data` | `loader.go`, `store.go`, `stats.go`, `players.go`, `model.go` | CSV loading, the in-memory store, and all query/aggregation logic. |
| `internal/names` | `names.go` | Club-name normalization (accents, state suffixes, aliases, noise words). |

## Interfaces / flow

1. `main` calls `data.LoadDir(dir)` → reads 6 Kaggle CSVs, de-duplicates overlapping
   Brasileirão sources, parses players, returns a `*data.Store` (sorted by date).
2. `mcp.NewServer(store)` registers 7 tools: `search_matches`, `team_record`,
   `head_to_head`, `standings`, `league_stats`, `search_players`, `team_profile`.
3. `Server.Serve(stdin, stdout)` reads newline-delimited JSON-RPC requests, dispatches
   `initialize` / `ping` / `tools/list` / `tools/call`, and writes responses. Tool
   errors are returned in-band (`isError: true`).
4. Each tool decodes typed args → builds a `data.MatchFilter` / `data.PlayerFilter` →
   calls a `Store` query → formats a human-readable text block (`format.go`).

## Key design choices

- **Name normalization** (`internal/names`) is the backbone: `Team{Display, Base, State}`
  with accent folding, state-suffix parsing (`Palmeiras-SP`), long-name aliases, and
  noise-word stripping (`FC`/`EC`). A missing state matches any state.
- **Standings** computed from match results (3/1/0), with tiebreakers (pts, GD, GF, name)
  and same-name disambiguation by state.
- **Multi-format dates** handled in `ParseDate` (ISO, DD/MM/YYYY, with/without time);
  unplayed fixtures (`NA`/`-`/empty) skipped rather than fatal.

Testing: 32 test functions across 6 `_test.go` files (812 LOC), with a checked-in
`internal/data/testdata/` CSV subset plus a full-dataset performance test.
