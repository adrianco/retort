# Architecture Summary — brazilian-soccer-mcp (Swift)

A SwiftPM package with two targets: a `SoccerCore` library and a thin `soccer-mcp`
executable. Clean separation of transport, query engine, and data loading.

## Modules

| File | Role |
|------|------|
| `Sources/soccer-mcp/main.swift` | Entry point. Resolves the data dir (`--data-dir` → `$SOCCER_DATA_DIR` → `./data/kaggle`), loads the DB, runs the stdio serve loop. Diagnostics to stderr, JSON-RPC to stdout. |
| `Sources/SoccerCore/MCPServer.swift` | Minimal MCP (JSON-RPC 2.0 over NDJSON on stdio): `initialize`, `ping`, `tools/list`, `tools/call`. Notifications (no id) get no reply; tool errors surface as `isError:true` results. |
| `Sources/SoccerCore/SoccerTools.swift` | The 7 registered tools: `find_teams`, `find_matches`, `team_record`, `head_to_head`, `standings`, `league_stats`, `search_players`. Arg parsing + output formatting. |
| `Sources/SoccerCore/SoccerDatabase.swift` | In-memory query engine. Team-name resolution to keys, composable `MatchFilter` (team/venue/opponent/competition/season/date-range/stage), records, standings, league stats, biggest wins, best records, player search. |
| `Sources/SoccerCore/DataLoader.swift` | Loads the 6 Kaggle CSVs into `Match`/`Player`. Per-file column mapping; overlap resolved per competition-season by file priority. |
| `Sources/SoccerCore/CSV.swift` | RFC-4180-ish CSV parser (quoted fields, escaped quotes, embedded newlines, CRLF, BOM). |
| `Sources/SoccerCore/Normalization.swift` | Accent-folding / keying for team and name matching; state-suffix handling. |
| `Sources/SoccerCore/Models.swift` | `Match`, `TeamRef`, `Player` value types. |

## Flow

LLM → JSON-RPC `tools/call` → `MCPServer.callTool` → `SoccerTools` handler →
`SoccerDatabase` query over data loaded once at startup → formatted text result.

## Notable design choices

- Single `MatchFilter` path so every match query composes the same filters.
- Standings use exact competition match (not substring) to avoid pulling Série B/C into
  a Brasileirão table; 3-1-0 scoring with GD/GF tiebreakers.
- Copa do Brasil "final" is inferred as the highest round per season (read from the raw
  file, so an unplayed final still marks the final round).
- Dataset overlap (Brasileirão 2012–2019 appears in two files; Série A 2020–2022 in a
  third) is deduped by competition-season priority rather than row matching.
