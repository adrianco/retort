# Interfaces

## MCP transport (JSON-RPC 2.0 over stdio)

Newline-delimited JSON on stdin/stdout; diagnostics on stderr. Protocol version `2024-11-05`.

| Method | Handler | Notes |
|--------|---------|-------|
| initialize | `McpServer.initializeResult` | returns serverInfo `brazilian-soccer-mcp` 1.0.0, tools capability |
| notifications/initialized, notifications/cancelled | (no reply) | notifications swallowed |
| ping | `McpServer.handleMessage` | empty result |
| tools/list | `Tools.listTools` | advertises the 9 tools below |
| tools/call | `Tools.callTool` | wraps answer text in `content[].text`, sets `isError` |

## MCP tools (tools/call)

| Tool | Required args | Optional args | Returns |
|------|---------------|---------------|---------|
| search_matches | (none) | team, opponent, home_team, away_team, competition, season, date_from, date_to, limit(50) | match list; appends H2H line if team+opponent |
| head_to_head | team_a, team_b | — | aggregate W/D/L, goals, up to 15 recent meetings |
| team_record | team | season, competition, scope(all/home/away) | matches, W/D/L, GF/GA, GD, points, win rate |
| search_players | (none) | name, nationality, club, position, min_overall, limit(25) | players sorted by overall desc |
| standings | competition, season | — | computed league table (3/1/0 points) |
| match_statistics | (none) | competition, season | match count, total/avg goals, home/away/draw rates |
| biggest_wins | (none) | competition, season, limit(10) | largest-margin matches |
| best_records | (none) | competition, season, scope, min_matches(5), limit(10) | teams ranked by win rate |
| list_competitions | (none) | — | competition names + corpus size |

## Library API (key public types)

- `KnowledgeGraph.load(Path)` -> indexed Match/Player store.
- `QueryService` -> the 9 analytical methods backing the tools; result records `TeamRecord`, `HeadToHead`, `StandingRow`, `GoalStats`.
- `TeamNames.canonical/display/stripAccents` -> name normalization.
- `CsvReader.parse(Path, Consumer<List<String>>)` -> streaming CSV.

## Data schema (in-memory models, loaded from CSV)

- **Match**: competition, source, home/away team (raw + canonical key + display), home/away goals (nullable), season, round, date (nullable), stage, venue.
- **Player**: id, name, age, nationality, overall, potential, club (+ canonical), position, jerseyNumber, height, weight.

Source CSVs (read at startup, not part of `src/`): Brasileirao_Matches, Brazilian_Cup_Matches, Libertadores_Matches, BR-Football-Dataset, novo_campeonato_brasileiro, fifa_data. Canonical competitions: Brasileirão Série A, Copa do Brasil, Copa Libertadores, Brasileirão (histórico 2003-2019), plus per-tournament names from BR-Football.

## HTTP routes / CLI commands

(none) — apart from `Main` args: optional data-dir path, and `--selftest` flag.
