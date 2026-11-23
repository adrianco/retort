# Run Summary — brazilian-soccer-mcp-server (swift / codex / gpt-6.2-astra, low effort)

## Surface

A Model Context Protocol (MCP) server, in Swift, that answers natural-language
questions about Brazilian soccer. It loads the six bundled Kaggle CSVs (five match
files + one FIFA player file) into an in-memory SQLite database and exposes the data
to an LLM through a single read-only `soccer_query` SQL tool plus a `normalize_team`
helper. Rather than one typed tool per capability, the design hands the LLM a schema
description and lets it write SELECT/WITH queries against pre-built views.

## Architecture

- **Ingestion (`Import.swift`)** — a hand-rolled RFC-4180 CSV parser, team-name
  normalization (`teamKey` — diacritic folding, state-suffix stripping, alias table),
  and a loader that inserts every source into `source_matches` / `players`, then builds
  a reconciled `matches` table (deduping league fixtures across overlapping sources and
  back-filling missing scores by dated pair). Views `appearances`, `records`,
  `standings`, `derbies` provide the query surface.
- **Storage (`Database.swift`)** — `Graph` wraps an in-memory SQLite handle opened via
  the `CSQLite` system-library shim. Hardened read-only: `PRAGMA query_only`, an
  authorizer that permits only SELECT/READ and denies `load_extension`/`readfile`/
  `writefile`, a 4s progress-handler watchdog, and a 200-row result cap.
- **Protocol (`Server.swift`)** — a stdio JSON-RPC 2.0 loop implementing `initialize`,
  `ping`, `tools/list`, `tools/call`. Tool errors are returned as MCP `isError` content,
  not transport errors.
- **Tests (`SoccerTests.swift`)** — two XCTest methods: one asserting concrete facts
  (18,207 players; 2019 Serie A champion = Flamengo, 90 pts, 38 played; Copa do Brasil
  2019 has 2 final legs; write attempts throw; name normalization) and one running the
  20 sample questions and asserting non-empty results under a 2s latency bound.

## Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| `Import.swift` | CSV parse, team normalization, schema/view build | `readCSV`, `teamKey`, `Graph.load` |
| `Database.swift` | SQLite wrapper, read-only hardening, query exec | `Graph`, `Graph.query` |
| `Server.swift` | MCP JSON-RPC stdio server + tool dispatch | `dispatch`, top-level loop |
| `SoccerTests.swift` | XCTest suite over the query surface | 2 test functions |
| `Package.swift` | SwiftPM manifest (Soccer lib, Server exe, tests) | — |
| `CSQLite/` | system-library modulemap for libsqlite3 | — |

## Flow

stdin JSON-RPC line → `dispatch` → `tools/call` → `Graph.query(sql)` (authorizer +
watchdog + 200-row cap) → JSON result wrapped in MCP text content → stdout.
