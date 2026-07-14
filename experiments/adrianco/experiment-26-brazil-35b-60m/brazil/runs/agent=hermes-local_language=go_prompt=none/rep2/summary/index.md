# Architecture Summary — Brazilian Soccer MCP Server (Go)

> Authored inline during `evaluate-run` (the `run-summary` skill was not tool-invocable in this session).

## Modules

| File | LOC | Role |
|------|-----|------|
| `main.go` | 219 | Entry point. Builds the in-memory `Store`, loads 5 match CSVs + FIFA players, registers 7 MCP tools with typed handlers over the go-sdk `mcp` server, serves on stdio. |
| `models.go` | 89 | Data types: `Match`, `Player`, `TeamStats`, `H2HRecord`, `StandingsEntry`, `BigWin`, `StatsSummary`. |
| `loader.go` | 352 | Per-dataset CSV parsers (`LoadBrasileirao`, `LoadCopaBrasil`, `LoadLibertadores`, `LoadBRFootball`, `LoadNovoCampeonato`, `LoadFIFAPlayers`), `normalizeTeamName`, `parseInt`. |
| `store.go` | 350 | In-memory index (`teamMatches` map: lowercased team → match indices) + query functions for every tool. |
| `tools.go` | 397 | MCP tool definitions (JSON-schema-generated inputs), input/output structs, human-readable formatters. |

## Data flow

```
CSV files (data/kaggle/*)
   └─ loader.go  → []Match / []Player
        └─ Store.AddMatches (builds teamMatches index) / AddPlayers
             └─ tools.go handlers → Store query funcs → typed Output structs
                  └─ MCP stdio transport → client
```

## Tools exposed (7)

`search_matches`, `team_stats`, `player_search`, `head_to_head`, `standings`, `biggest_wins`, `stats`.

## Query strategy

- Team lookup is O(1) via a `map[string][]int` keyed on `strings.ToLower(team)`; other filters (competition, season, date range) are linear scans over the candidate slice.
- Standings/stats/biggest-wins iterate the full match slice.

## Notable design points

- Team-name normalization strips a fixed list of state suffixes (`-SP`, `-RJ`, …).
- FIFA loader resolves columns by header name (BOM-tolerant), so it is robust to column reordering; the match loaders use hard-coded positional indices.
- See `findings.jsonl` for a positional-index defect in the Brasileirão loader.
