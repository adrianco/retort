# Interfaces

## MCP protocol (JSON-RPC 2.0)

Transport: newline-delimited JSON-RPC over stdin/stdout (`mcp/stdio.ex`), dispatched by `mcp/server.ex`.

| Method | Returns | Handler |
|--------|---------|---------|
| `initialize` | protocolVersion, capabilities, serverInfo | `server.ex:dispatch/3` |
| `notifications/initialized` | (no reply) | `server.ex:dispatch/3` |
| `ping` | `{}` | `server.ex:dispatch/3` |
| `tools/list` | `{tools: [...]}` | `server.ex` → `tools.ex:specs/0` |
| `tools/call` | content (text) + structuredContent + isError | `server.ex` → `tools.ex:call/2` |
| unknown method | error `-32601` (method not found) | `server.ex:dispatch/3` |

## MCP tools (tools/call)

| Tool | Required args | Optional args | Backed by |
|------|---------------|---------------|-----------|
| `find_matches` | — | team, opponent, home_team, away_team, competition, season, date_from, date_to, limit | `Matches.find/1` |
| `head_to_head` | team1, team2 | competition, season | `Teams.head_to_head/3` |
| `team_record` | team | season, competition, venue (home/away/all) | `Teams.record/2` |
| `search_players` | — | name, nationality, club, position, min_overall, limit | `Players.search/1` |
| `get_player` | name | — | `Players.get/1` |
| `competition_standings` | competition, season | — | `Competitions.standings/2` |
| `competition_statistics` | competition | season, biggest_wins_limit | `Statistics.competition_stats/2` |
| `list_competitions` | — | team | `Competitions.list_all/0` / `for_team/1` |

## Data schema (in-memory)

`Match`: competition, competition_key, home_team, away_team, home_key, away_key, home_goal, away_goal, season, round, stage, date, source.

`Player`: id, name, age, nationality, overall, potential, club, position, jersey_number, height, weight, name_key, club_key.

## Data sources

Six CSVs in `data/kaggle/`: `Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`, `Libertadores_Matches.csv`, `BR-Football-Dataset.csv`, `novo_campeonato_brasileiro.csv` (matches) and `fifa_data.csv` (players). All loaded at startup.

## CLI

`escript` `main_module: BrazilianSoccer.CLI` — launches the MCP stdio server.
