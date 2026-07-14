# Interfaces

## Transport

MCP (Model Context Protocol) over stdio, newline-delimited JSON-RPC 2.0. Protocol version `2024-11-05`. Handled methods: `initialize`, `notifications/initialized` (and bare `initialized`), `ping`, `tools/list`, `tools/call`. Unknown methods return JSON-RPC error `-32601`. No HTTP server or CLI subcommands; the only CLI flag is `-data <dir>` (default `data/kaggle`).

## MCP tools (`tools/call`)

| Tool | Required args | Optional args | Returns |
|------|---------------|---------------|---------|
| `search_matches` | (none) | team, home_team, away_team, opponent, competition, season, from, to, limit | Text list of matches, most-recent first (default limit 20) |
| `head_to_head` | team_a, team_b | (none) | Text summary: matches, wins/draws, goals, last meeting |
| `team_record` | team | competition, season, venue | Text: played, W/D/L, goals for/against, points, win rate |
| `standings` | season | competition (default Brasileirão), limit | Text league table with position, points, W/D/L, GF/GA/GD |
| `search_players` | (none) | name, nationality, club, position, min_overall, limit | Text list of players sorted by overall rating (default limit 20) |
| `data_overview` | (none) | (none) | Text: match/player/team counts, competitions, season range, load warnings |
| `match_statistics` | (none) | team, competition, season, from, to | Text: total/avg goals, home/away wins, home win rate, biggest wins |

All tool results are returned as a single `text` content block; argument errors and empty results are returned as text (some as `isError` results).

## Data schema (in-memory, loaded from CSV)

`Match`: Competition, Season, Round, Stage, Date, HomeTeam/AwayTeam (display), HomeKey/AwayKey (normalised), HomeGoals/AwayGoals, HomeShots/AwayShots/HomeCorners/AwayCorners (-1 when unknown), Source.

`Player`: ID, Name, NameKey, Age, Nationality, Overall, Potential, Club, ClubKey, Position, Jersey, Height, Weight.

Source files parsed by `LoadDir`: `Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`, `Libertadores_Matches.csv`, `novo_campeonato_brasileiro.csv`, `BR-Football-Dataset.csv`, `fifa_data.csv`. Missing files are skipped with a warning rather than failing the load.
