# Architecture Summary — brazilian-soccer-mcp (go, sonnet, prompt=TDD)

> `run-summary` skill was not callable in this session; this is a concise inline substitute.

## Modules

| Package | File(s) | Responsibility |
|---------|---------|----------------|
| `main` | `main.go` | MCP server entrypoint. Loads the store, builds `tools.Handlers`, registers 7 MCP tools on a `mark3labs/mcp-go` server, serves over stdio. |
| `loader` | `loader/loader.go`, `models.go`, `normalize.go`(impl in loader.go) | CSV ingestion. One `Load*` per dataset, header-indexed column access, multi-format date parsing, team-name normalization. |
| `store` | `store/store.go` | In-memory data layer. `New()` loads all 6 CSVs; `buildIndex()` flattens match datasets into a unified `[]MatchSummary` (`s.all`); query methods (matches, head-to-head, team stats, standings, biggest wins, average goals, player lookups). |
| `tools` | `tools/tools.go` | MCP tool handlers — thin adapters that translate tool args → store queries → formatted text. |

## Data flow

```
stdio (MCP client)
  → main.registerTools  (7 tools)
    → tools.Handlers.<X>  (arg parsing + text formatting)
      → store.Store.<query>  (in-memory filter/aggregate over s.all / s.Players)
        ← loader.Load*  (CSV → typed structs, loaded once at startup)
```

## Registered MCP tools (7)

`search_matches`, `head_to_head`, `team_stats`, `search_players`, `league_standings`, `biggest_wins`, `statistics`.

## Notable design points

- **Unified match index** (`s.all`): Brasileirão + Cup + Libertadores + Historical normalized into one struct for cross-competition queries. *Caveat:* Brasileirão appears in two overlapping source files (2012–2022 and 2003–2019), both indexed → double-counting for 2012–2019 in any `s.all` aggregate (see findings.jsonl). `LeagueStandings` avoids this by reading only `s.Brasileirao`.
- **Extended dataset** (`BR-Football-Dataset.csv`) is loaded but never indexed or queried.
- **Test layering**: each package has a co-located `_test.go` exercising real loaded data (25 test functions; loader/store/tools all covered), consistent with the TDD prompt factor.
