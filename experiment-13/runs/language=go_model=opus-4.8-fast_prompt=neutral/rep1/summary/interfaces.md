# Interfaces

This is an MCP (Model Context Protocol) server over the stdio transport. It exposes no HTTP routes. The interface is JSON-RPC 2.0 methods plus a set of registered tools.

## CLI

| Command | Flags | Description |
|---------|-------|-------------|
| `brazilian-soccer-mcp` | `-data <dir>` (default `data/kaggle`) | Serve MCP over stdio |
| `brazilian-soccer-mcp -demo` | `-demo` | Print answers to sample questions and exit (no server) |

## JSON-RPC methods (`mcp/server.go`)

| Method | Handling |
|--------|----------|
| `initialize` | Returns protocolVersion `2024-11-05`, tools capability, serverInfo |
| `notifications/initialized` / `initialized` | Notification, no response |
| `ping` | Returns `{}` |
| `tools/list` | Returns registered tools with name/description/inputSchema |
| `tools/call` | Invokes named tool; execution errors returned as `isError: true` result |
| (other) | `method not found` error (-32601) |

## MCP tools (`tools.go`)

| Tool | Required args | Optional args | Backing method |
|------|---------------|---------------|----------------|
| `search_matches` | (none) | team, opponent, home_team, away_team, competition, season, season_min, season_max, date_from, date_to, limit | `Store.SearchMatches` |
| `head_to_head` | team_a, team_b | competition, season, limit | `Store.HeadToHeadQuery` |
| `team_record` | team | competition, season, venue (all/home/away) | `Store.TeamRecordQuery` |
| `team_competitions` | team | — | `Store.TeamCompetitionsQuery` |
| `standings` | season | competition, limit | `Store.StandingsQuery` |
| `competition_stats` | (none) | competition, season | `Store.CompetitionStatsQuery` |
| `biggest_wins` | (none) | competition, season, limit | `Store.BiggestWinsQuery` |
| `top_scoring_teams` | (none) | competition, season, limit | `Store.TopScoringTeamsQuery` |
| `search_players` | (none) | name, nationality, club, position, min_overall, limit | `Store.SearchPlayersQuery` |
| `player_info` | name | — | `Store.PlayerInfoQuery` |
| `club_players` | club | limit | `Store.ClubPlayersQuery` |
| `dataset_overview` | (none) | — | `Store.DatasetOverview` |

All tools return a single plain-text content block (LLM-friendly formatted answer), not structured JSON.

## Data schemas (`soccer/models.go`)

`Match` (unified across all 5 match CSVs): Competition (canonical), Date, HasTime, Season, Round, Stage, HomeTeam, AwayTeam, HomeKey, AwayKey, HomeGoals, AwayGoals, Stadium, Source; extended stats (BR-Football only): HasStats, HomeShots, AwayShots, HomeCorners, AwayCorners.

`Player` (FIFA data): ID, Name, Age, Nationality, Overall, Potential, Club, ClubKey, Position, Jersey, Height, Weight, PreferredFoot, Value, Wage, NameKey, NationKey.

Canonical competition names: Brasileirão Série A / B / C, Copa do Brasil, Copa Libertadores.

## Source datasets (`data/kaggle/`)

`Brasileirao_Matches.csv`, `novo_campeonato_brasileiro.csv`, `Brazilian_Cup_Matches.csv`, `Libertadores_Matches.csv`, `BR-Football-Dataset.csv`, `fifa_data.csv`.
