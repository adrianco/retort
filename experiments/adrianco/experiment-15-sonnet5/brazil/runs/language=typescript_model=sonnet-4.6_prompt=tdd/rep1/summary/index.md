# Architecture Summary — Brazilian Soccer MCP (TypeScript, sonnet-4.6, prompt=tdd)

MCP stdio server exposing 8 tools over pre-downloaded Kaggle CSVs. Layered design:
data loading → pure query functions → formatting handlers → MCP server wiring.

## Modules

| File | Role |
|------|------|
| `src/server.ts` | MCP entrypoint. `@modelcontextprotocol/sdk` `Server` over `StdioServerTransport`; registers 8 tools with JSON-schema inputs; lazily loads data on first `CallTool`; dispatches to handlers. |
| `src/dataLoader.ts` | `loadAllData(dataDir)` reads all 6 CSVs (`csv-parse/sync`), strips BOM, coerces numerics, precomputes normalized team names. Typed interfaces per dataset; historical file tagged `Brasileirao-Historical`. |
| `src/teamNormalizer.ts` | `normalizeTeamName` (strips `-UF` state suffix) + state-aware `teamsMatch` (avoids Atletico-MG/PR conflation). |
| `src/matchQueries.ts` | Pure match functions over a unified `AnyMatch`: `findMatches`, `getHeadToHead`, `getBiggestWins`, `getAverageGoals` + field accessors. |
| `src/teamQueries.ts` | `getTeamRecord` (W/L/D, GF/GA, pts), `getStandings` (computed table, tie-break pts→wins→GD), `getTopScoringTeams`. |
| `src/playerQueries.ts` | `searchPlayers`, `getTopRatedPlayers`, `getPlayersByClub` over FIFA data. |
| `src/handlers.ts` | Thin formatting layer mapping query results to MCP response payloads. |

## Tools exposed
`find_matches`, `get_head_to_head`, `get_team_record`, `get_standings`,
`search_players`, `get_top_players`, `get_biggest_wins`, `get_average_goals`.

## Data flow
`CallTool` → `ensureData()` (cached `loadAllData`) → `handleX(data, params)` →
pure query fn over in-memory arrays → JSON text content.

## Notable design decisions
- Competition tags separate 2003–2019 historical from 2012–2022 main Brasileirão to
  avoid double-counting **in competition-filtered queries**.
- Standings key on state-qualified names, display normalized.

## Correctness caveat
`findMatches` unions all five match arrays. When **no** competition filter is given
(`get_team_record`, `get_head_to_head` default), the overlapping Brasileirão /
historical / BR-Football datasets are counted together, inflating all-time aggregates.
See `findings.jsonl` (R6).
