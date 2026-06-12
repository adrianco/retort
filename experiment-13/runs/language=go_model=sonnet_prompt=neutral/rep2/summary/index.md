# Architecture Summary — brazilian-soccer-mcp (go/sonnet/neutral · rep2)

A single Go `main` package implementing a stdio JSON-RPC 2.0 MCP server over the
provided Kaggle CSV datasets. No external dependencies (stdlib only).

## Modules

| File | Responsibility |
|------|----------------|
| `main.go` | Process entrypoint, stdio JSON-RPC loop (`serve`), method dispatch (`initialize`, `tools/list`, `tools/call`, `ping`, notifications). |
| `tools.go` | MCP tool definitions (6 tools) + per-tool argument decoding, dispatch, and text formatting of results. |
| `query.go` | Pure query/aggregation layer: `filterMatches`, `calcTeamStats`, `headToHead`, `competitionStandings`, `searchPlayers`, `biggestWins`, `calcOverallStats`, dedup helpers. |
| `data.go` | CSV loading for all 6 datasets into `Match`/`Player` structs; date/number parsing; BOM handling; overlap de-duplication between Brasileirão sources. |
| `normalize.go` | Team-name normalization (state-suffix stripping, accent folding), `teamMatchesQuery`, `competitionMatchesQuery`. |
| `server_test.go` | 24 `Test*` functions across parsing, loading, query, and MCP-protocol layers. |

## Tools exposed

`search_matches`, `team_statistics`, `head_to_head`, `search_players`,
`competition_standings`, `match_analysis` (biggest_wins / average_goals /
home_advantage / top_scoring_teams / best_home_record / best_away_record).

## Data flow

`main` → `loadDatabase(DATA_DIR)` loads all CSVs into an in-memory `Database`
(matches + players). Each JSON-RPC `tools/call` decodes arguments, runs a pure
function in `query.go` against the in-memory slices, and formats a text result.
Team identity is reconciled across naming conventions via `normalize.go`; the
`novo_campeonato_brasileiro.csv` loader skips seasons ≥2012 to avoid
double-counting overlap with `Brasileirao_Matches.csv`.

## Notes

- Extended per-match stats (corners, shots) are parsed from `BR-Football-Dataset.csv`
  into `Match` but are not surfaced by any tool.
- Data-dependent tests skip gracefully if `data/kaggle/` is absent (it is present here, so all ran).
