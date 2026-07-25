# Interfaces

## MCP tools/handlers

(none) — `main.go` defines `Request`/`Response`/`Error`/`Notification` structs and an
`MCPVersion` constant, but no MCP transport, no JSON-RPC dispatch, and no registered
tools. `Server.Listen()` loads data then drops into a local CLI (see `main.go:77-79`).

## CLI commands (interactive REPL, `main.go:runCLI`)

| Command | Args | Backing function |
|---------|------|------------------|
| `matches` | `<team>` | `MatchDataStore.FindMatchesByTeam` |
| `teams` | `<name>` | `MatchDataStore.FindTeams` |
| `players` | `<name>` | `PlayerDataStore.SearchPlayers` |
| `stats` | `<team> <year>` | `MatchDataStore.GetTeamStats` |
| `standings` | `<year>` | `MatchDataStore.GetBrasileiraoStandings` |
| `help` / `quit` | — | — |

## Library API (exported, not surfaced via CLI or MCP)

`PlayerDataStore.FindPlayersByNationality`, `FindPlayersByClub`, `GetPlayersByClub`,
`GetTopBrazilianPlayers`, `GetBrazilianPlayersByClub`, `GetTopPlayers`,
`FindPlayersByPosition`, `GetPlayerStats`.

## Data schema

`Match{DateTime, HomeTeam, AwayTeam, HomeGoals, AwayGoals, Season, Round, Competition,
Stage, ...}` sourced from 5 match CSVs. `Player{ID, Name, Nationality, Club, Position,
Overall, Potential, skill ratings...}` from `fifa_data.csv`.
