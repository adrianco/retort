# Architecture Summary

A single-package Go MCP server (`package main`, `module brazilian-soccer-mcp`, go 1.23,
no external dependencies) that answers natural-language-style queries over five bundled
match CSVs plus the FIFA player CSV.

## Modules

| File | Role |
|------|------|
| `main.go` | Entry point. Parses `-data` flag (default `data/kaggle`), loads the store, serves MCP over stdio. |
| `server.go` | JSON-RPC 2.0 / MCP protocol layer. Handles `initialize`, `server/discover`, `ping`, `tools/list`, `tools/call`. Defines 9 tools with JSON input schemas and dispatches to store methods. |
| `store.go` | Query engine. `Matches`, `TeamStatistics`, `HeadToHead`, `Players`, `Standings`, `CompetitionStatistics`, `BiggestWins`, `TeamProfile`, `Derbies`. Dedup logic + curated derby table. |
| `loader.go` | CSV ingestion. Per-file converters normalize five heterogeneous match schemas + FIFA players into shared structs; builds a team→match index and a per-(competition,season) authoritative-feed map. |
| `normalize.go` | Team-name normalization (accent folding, `-SP` state-suffix stripping, alias table), competition normalization, nationality aliases, multi-format date parsing. |
| `model.go` | Shared structs: `Match`, `Player`, `TeamRecord`, `Standing`, `DerbyResult`. |

## Data flow

`LoadStore(dataDir)` reads 5 match CSVs + `fifa_data.csv` → 23,954 matches, 18,207 players.
It builds a `matchIndexes` map (normalized team → row indices) for fast lookup and a
`preferredSources` map that picks **one authoritative feed per (competition, season)** so
aggregate queries (standings, team stats, competition stats) don't double-count the same
fixture appearing in official + historical + extended feeds. `search_matches` instead
dedups on a composite match key so cross-feed searches merge, while a `source` filter
returns raw per-feed rows (retaining extended stats like corners).

## MCP tools (9)

`search_matches`, `team_statistics`, `head_to_head`, `search_players`, `standings`,
`competition_statistics`, `biggest_wins`, `team_profile`, `derbies`. All carry
`readOnlyHint`/`idempotentHint` annotations.

## Notable design choices

- **Dedup correctness verified**: 2019 Série A standings compute Flamengo at 38 played / 90
  points (factual_accuracy=1.0) despite 23,954 concatenated rows — the authoritative-feed
  selection reconciles the overlap.
- **Name normalization** handles state suffixes, full club names, and Portuguese accents.
- **Cross-file query** (`team_profile`) joins match record + FIFA squad by club.
