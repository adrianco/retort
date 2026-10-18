# Architecture Summary — Brazilian Soccer MCP Server (Objective-C)

A single-binary Foundation/Objective-C (ARC) command-line MCP server. No third-party
dependencies — only `-framework Foundation`. Built with the included `Makefile`
(`make` → server, `make test` → test binary).

## Modules

| File | Role |
|------|------|
| `src/main.m` | Entry point. Loads `data/kaggle`, builds the tool/server stack, serves MCP over stdio. |
| `src/CSVParser.{h,m}` | RFC-4180-ish CSV parser: quoted fields, embedded commas/newlines, `""` escapes, CRLF, BOM stripping. Emits `[{header: value}]` records. |
| `src/Text.{h,m}` | `BSText` helpers: accent/case folding (`São Paulo`→`sao paulo`), multi-format date → ISO (`29/03/2003`, `2012-05-19 18:30:00`, `2023-09-24`), tolerant number parse (`"1.0"`→1, `"NA"`→nil). |
| `src/Models.{h,m}` | Domain types: `TeamName` (base/state/identity/display, variant matching), `Match`, `Player`, `PlayerQuery`, `TeamTally` (W/L/D, goals, points, win rate), `MatchStatistics`. Competition canonicalisation (`CanonicalCompetition`). |
| `src/DataStore.{h,m}` | Loads all six CSVs into a de-duplicated, date-sorted match list + player list; query engine for matches, tallies, standings, statistics, player search. |
| `src/Tools.{h,m}` | `MCPTools`: six tool descriptors + dispatch + human-readable formatting (`search_matches`, `team_stats`, `head_to_head`, `standings`, `search_players`, `match_statistics`). |
| `src/MCPServer.{h,m}` | JSON-RPC 2.0 MCP layer: `initialize`, `ping`, `tools/list`, `tools/call`, notification suppression, error codes; line-delimited stdio transport. |
| `tests/test_main.m` | 14 BDD Given/When/Then scenarios, hand-computed fixtures + a real-dataset scenario. |

## Data flow

`main` → `DataStore storeFromDirectory:` (CSVParser → BuildMatch/PlayerFromRow →
normalise via BSText/TeamName → dedup → sort) → `MCPTools initWithStore:` →
`MCPServer serveInput:output:` reads one JSON-RPC message per line, dispatches to a
tool, writes the reply.

## Notable qualities

- Multi-source merge with de-duplication (same fixture across files counted once);
  earlier sources win.
- Team-name normalisation handles state suffixes (`Palmeiras-SP`), full names
  (`Sport Club Corinthians Paulista`), and parenthetical countries (`Nacional (URU)`).
- Standings computed from match results with points → goal-difference → goals-for →
  name tiebreak.
- Beyond spec: stdio transport, `ping`, Serie B/C competitions, venue (home/away) filters.
