# Interfaces

## HTTP routes

(none) — this is an MCP server over stdio, not an HTTP service.

## MCP protocol methods

JSON-RPC 2.0, newline-delimited over stdin/stdout. Protocol version `2024-11-05`.

| Method | Behaviour | Handler |
|--------|-----------|---------|
| initialize | Returns protocolVersion, `tools` capability, serverInfo | `mcp.go:dispatch` |
| ping | Returns empty object | `mcp.go:dispatch` |
| tools/list | Returns the 7-tool catalogue | `mcp.go:dispatch` |
| tools/call | Runs a tool; tool errors returned as `isError` text result, not protocol errors | `mcp.go:dispatch` → `Handler.Call` |
| notifications/* | No reply (notifications have nil id) | `mcp.go:handleLine` |

## MCP tools (tools/call)

| Tool | Purpose | Required args | Optional args | Handler |
|------|---------|---------------|---------------|---------|
| search_matches | Find matches across competitions, newest first | (at least one filter) | team, opponent, venue, competition, season, from, to, limit | `tools.go:searchMatches` |
| team_record | W/D/L, goals for/against, win rate for a team | team | venue, competition, season | `tools.go:teamRecord` |
| head_to_head | All-time record between two teams | team, opponent | limit | `tools.go:headToHead` |
| standings | League table for a season (3pt win, 1pt draw) | season | competition (default Brasileirão Série A) | `tools.go:standings` |
| league_stats | Goals/match, home/draw/away percentages | (competition or season) | competition, season | `tools.go:leagueStats` |
| biggest_wins | Matches with largest winning margin | (none) | competition, season, limit | `tools.go:biggestWins` |
| search_players | FIFA player search, sorted by overall | (at least one filter) | name, nationality, club, position, min_overall, brazilian_clubs_only, limit | `tools.go:searchPlayers` |

All tools return plain text laid out like the spec's example answers. `limit` defaults to 20.

## Library API (exported symbols)

- `LoadDataset(dir) (*Dataset, error)` — load all CSVs.
- `Dataset` methods: `FindMatches`, `TeamRecord`, `HeadToHead`, `Standings`, `Aggregate`, `BiggestWins`, `SearchPlayers`.
- `ParseTeam(raw, fallbackState) TeamName`; `TeamName.Matches`, `.Key`, `.Empty`, `.SameClub`.
- `Server.Serve(in, out)`; `Tools() []Tool`; `Handler.Call(name, args)`.

## Data schema

`Match`: Date, Home/Away (TeamName), HomeGoals, AwayGoals (int), Competition, Season (int), Round, Source.

`Player`: Name, Age, Nationality, Overall, Potential, Club, Position, Jersey, Value, Wage, Height, Weight, Foot.

`TeamName`: Raw, Base (accent-free, noise-stripped), State (UF code), Tokens.

Source CSVs (loaded in priority order with competition/season de-dup + fixture de-dup): Brasileirao_Matches.csv, novo_campeonato_brasileiro.csv, Brazilian_Cup_Matches.csv, Libertadores_Matches.csv, BR-Football-Dataset.csv, fifa_data.csv.

Competition constants: Brasileirão Série A/B/C, Copa do Brasil, Copa Libertadores.
