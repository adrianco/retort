# Architecture Summary — Brazilian Soccer MCP Server (Go)

Single Go package `main` (module `brsoccer`), stdlib-only, 4 source files + 1 test file.

## Modules

| File | Lines | Responsibility |
|------|-------|----------------|
| `server.go` | 139 | MCP transport: newline-delimited JSON-RPC 2.0 over stdio. `initialize`/`ping`/`tools/list`/`tools/call` dispatch; `main()` loads the DB then serves. |
| `tools.go` | 660 | 14 MCP tool definitions (`search_matches`, `head_to_head`, `team_stats`, `standings`, `competition_stats`, `team_rankings`, `compare_seasons`, `team_competitions`, `derbies`, `search_players`, `player_details`, `brazilian_clubs_players`, `team_profile`, `dataset_info`) with JSON input schemas + handlers. |
| `data.go` | 366 | CSV ingestion of all 6 Kaggle files into `Match`/`Player` structs; team-name normalization (accent stripping, state-suffix removal, alias + ambiguity tables); multi-format date parsing; display-name resolution. |
| `query.go` | 472 | Query engine: `MatchFilter`/`Find` (dedup across sources, sort by date), `Record`/`Standings` aggregation, `Summary` stats, `BiggestWins`, `Rivalries` derby table, `PlayerFilter`/`FindPlayers` with position groups + nationality/club matching. |
| `soccer_test.go` | 340 | 17 BDD-style tests covering every tool, the MCP round-trip, normalization, date parsing, dedup, and cross-file profiles. |

## Data flow

`main()` → `LoadDB("data/kaggle")` reads 6 CSVs → normalizes team keys + dedups implicitly at query time → `NewServer(db)` registers tools → `Serve(stdin, stdout)` loops JSON-RPC requests → `tools/call` dispatches to the matching handler → handler queries `db` via `query.go` helpers → formats a text response.

## Key design choices

- **Deduplication**: matches from overlapping sources (5 match CSVs) are deduped in `Find` by a competition/season/team key (league) or competition/date/team key (cup), so a 38-game league season isn't double-counted.
- **Team normalization**: a canonical key per club via accent stripping, `-SP`-style state-suffix removal, an `aliases` map, and an `ambiguous` table (e.g. "Atlético" → MG/PR/GO by state).
- **Graceful gaps**: players/clubs absent from FIFA 19 data (e.g. Gabriel Barbosa, Flamengo squad) return a clear "not licensed / similar names" hint rather than an empty result.
