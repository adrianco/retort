# Run Summary: brazilian-soccer-mcp (go / codex / gpt-5.6-sol)

## Surface

A stdio JSON-RPC 2.0 **MCP server** exposing a knowledge-graph interface over six
Kaggle Brazilian-soccer CSV datasets (matches across Brasileirão/Copa do
Brasil/Libertadores/extended/historical, plus 18,207 FIFA players). It answers
natural-language questions (`ask`) and offers nine specialized tools for match
search, team statistics, head-to-head, player search, computed standings,
competition statistics, biggest wins, team competitions, and a cross-file club
overview. No external dependencies — Go standard library only.

## Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| `main.go` | CLI entrypoint, data-dir resolution, server boot | `main`, `defaultDataDir` |
| `mcp.go` | JSON-RPC 2.0 loop, MCP methods, 10 tool definitions + dispatch | `MCPServer`, `Serve`, `callTool`, `toolDefinitions` |
| `loader.go` | CSV parsing for all 6 files into `Match`/`Player` | `LoadDatabase`, `loadBrasileirao`, `loadPlayers`, `parseDate` |
| `query.go` | Filtering + analytics (standings, stats, H2H, dedup) | `SearchMatches`, `Standings`, `TeamStatistics`, `HeadToHead`, `AggregateStats`, `analyticalMatches` |
| `natural.go` | NL question router → tool calls | `Answer`, `mentionedTeams` |
| `normalize.go` | Team-name/competition normalization, fuzzy match, UTF-8 fold | `normalizeTeam`, `fuzzyEqual`, `fold` |
| `format.go` | Human-readable text rendering of results | `formatMatches`, `formatStandings`, `formatTeamStats` |
| `models.go` | Domain types (`Match`, `Player`, `Standing`, filters, stats) | struct defs |
| `*_test.go` | 9 test functions across loader/mcp/query/normalize | — |

## Notable design choices

- **Union vs analytical views:** `SearchMatches` returns a deduplicated *union* of
  all sources so every game is queryable, while `analyticalMatches` selects one
  authoritative source per (competition, season) via `sourcePriority` so computed
  standings/stats don't double-count overlapping CSVs. Well-reasoned.
- **Name normalization:** state suffixes ("Palmeiras-SP") retained internally to
  disambiguate clubs (Atlético-MG vs Atlético-PR), stripped for display.
- **Multi-format dates** and **UTF-8 accent folding** per the spec's data-quality notes.

Architecture analysis produced inline (run-summary skill not separately invoked).
