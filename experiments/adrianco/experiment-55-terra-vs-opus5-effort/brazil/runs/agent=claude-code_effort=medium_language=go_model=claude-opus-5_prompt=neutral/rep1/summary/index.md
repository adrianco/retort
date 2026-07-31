# Architecture Summary

`brazilian-soccer-mcp` — a Go MCP (Model Context Protocol) stdio server exposing
a Brazilian-soccer knowledge graph built from six Kaggle CSV datasets.

## Modules

| Package | Responsibility |
|---------|----------------|
| `main` (`main.go`) | Entrypoint: parses `-data`/`-check` flags, loads the graph, serves MCP over `mcp.StdioTransport`. |
| `internal/soccer` | Domain core. Loads CSVs into an in-memory `Graph`; provides all query/aggregation functions. |
| `internal/mcpserver` | MCP tool registration (14 tools) + text rendering of results. |
| `internal/normalize` | Team-name normalisation (strips state suffixes, accents, alternate spellings). |

## `internal/soccer` files

- `load.go` — reads all six CSVs (`Brasileirao_Matches`, `Brazilian_Cup_Matches`, `Libertadores_Matches`, `novo_campeonato_brasileiro`, `BR-Football-Dataset`, `fifa_data`), tolerant CSV reader for ragged rows, dedup across overlapping match files.
- `model.go` — `Match`, `Player`, `Team`, `Graph` types.
- `matches.go` — `FindMatches` (team/venue/competition/season/date/round filters), `HeadToHead`.
- `teams.go` — `TeamStatistics` (W/L/D, goals for/against, home/away), `SearchTeams`, `Compare`.
- `players.go` — `FindPlayers` (name/nationality/club/position/rating/age), `Squad`, `BrazilianClubRatings`.
- `standings.go` — `LeagueStandings` computed from match results (points, champion, relegation).
- `stats.go` — `AggregateStats`, `Leaderboard`, `CompareSeasons`, `DerbyMatches`.

## MCP tools (14)

`find_matches`, `team_statistics`, `head_to_head`, `compare_teams`, `search_teams`,
`find_players`, `club_squad`, `brazilian_club_ratings`, `league_standings`,
`competition_stats`, `team_leaderboard`, `compare_seasons`, `find_derbies`, `dataset_info`.

Each tool returns both a human-readable text block and a structured JSON payload.

## Data flow

`main` → `soccer.Load(dir)` (CSV → normalised in-memory graph, ~100ms) →
`mcpserver.New(g)` registers tools → JSON-RPC over stdio → each tool calls a
`Graph` query method → `render*` formats result.

## Tests

- `internal/soccer/bdd_test.go` — Gherkin-style feature tests (data loading, match/team/player/competition queries, statistical analysis, query performance, concurrency).
- `internal/soccer/load_test.go`, `internal/mcpserver/server_test.go`, `internal/normalize/normalize_test.go` — unit tests.
- 31 top-level test functions, no skipped/disabled tests.
