# Architecture Summary — brazilian-soccer-mcp (go / sonnet / ATDD)

> Generated inline by `evaluate-run` (the `run-summary` skill was unavailable in this environment).

## Modules

| Package | File | Responsibility |
|---------|------|----------------|
| `main` | `main.go` | Entrypoint. Resolves `data/kaggle` relative to the executable, loads the store, registers tools, serves MCP over stdio. |
| `main` | `acceptance_test.go` | ATDD acceptance suite (AT-01…AT-12) driving the system through the MCP tool handlers. |
| `soccer` | `data.go` | Domain types: `Match`, `Player`, `TeamStats`, `StandingEntry`, `HeadToHead`, `Store`. |
| `soccer` | `loader.go` | CSV ingestion — one loader per dataset (5 match files + FIFA players), date/goal/season parsing, BOM handling. |
| `soccer` | `normalize.go` | Team-name normalization (strips `-SP`/`-RJ` state suffixes, case-folds) for cross-dataset matching. |
| `soccer` | `store.go` | Query engine: `FindMatches`, `GetTeamStats`, `GetStandings`, `GetHeadToHead`, `FindPlayers`, `BiggestWins`, `GoalsAverage`, `HomeAwayRecord`. |
| `tools` | `tools.go` | MCP tool definitions + handlers: `find_matches`, `get_team_stats`, `find_players`, `get_standings`, `get_head_to_head`, `get_statistics`. |

## Flow

```
stdin (MCP) → server.MCPServer → tools.*Handler → soccer.Store query → formatted text → MCP CallToolResult
                                       ↑
                          soccer.LoadStore(data/kaggle)  (6 CSVs → in-memory slices)
```

## Interfaces (MCP tools)

- `find_matches(team|team1+team2|home_team|away_team, season, competition, limit)`
- `get_team_stats(team*, season, competition)`
- `find_players(name, nationality, club, position, min_overall, limit)`
- `get_standings(season*, competition=brasileirao)`
- `get_head_to_head(team1*, team2*, competition)`
- `get_statistics(stat_type=biggest_wins|goals_average|home_away_record, competition, season, limit)`

## Notable design points

- In-memory store, linear scans — fine for this dataset size (well under the <2s / <5s budget).
- Competition is normalized to an enum (`brasileirao`, `copa_brasil`, `libertadores`, `other`).
- **Data-integrity gap:** `Brasileirao_Matches.csv` and `novo_campeonato_brasileiro.csv` are both tagged `brasileirao` and overlap on seasons 2012–2019, with no de-duplication — standings/team-stats double-count those seasons (see `findings.jsonl`).
