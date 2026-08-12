# Interfaces

## MCP JSON-RPC methods

Transport is line-delimited JSON-RPC 2.0 over stdin/stdout (`server.go:Serve`).

| Method | Returns | Handler |
|--------|---------|---------|
| `initialize` | protocolVersion `2024-11-05`, capabilities, serverInfo | `server.go:Serve` |
| `notifications/initialized` | (no response) | `server.go:Serve` |
| `tools/list` | array of 6 tool definitions | `server.go:toolDefinitions` |
| `resources/list` | one resource `soccer://datasets` | `server.go:Serve` |
| `resources/read` | dataset counts as text (or -32602 for unknown URI) | `server.go:Serve` |
| `tools/call` | tool result, or -32602 on bad params/unknown tool | `server.go:callTool` |

Unknown methods return JSON-RPC error -32601 (method not found).

## MCP tools (`tools/call`)

| Tool | Arguments | Handler |
|------|-----------|---------|
| `search_matches` | team, competition, from, to (YYYY-MM-DD), season, limit | `Store.SearchMatches` |
| `team_stats` | team (required), competition, season, home_only, away_only | `Store.Stats` |
| `player_search` | name, nationality, club, position, min_overall, limit | `Store.SearchPlayers` |
| `competition_stats` | competition, season | `Store.Average` |
| `standings` | competition, season | `Store.Standings` |
| `head_to_head` | team_a (required), team_b (required), competition, season | `Store.HeadToHead` |

Every tool result is wrapped by `jsonResult()` as both `content` (text) and `structuredContent` (typed object).

## Library API (exported symbols)

- `LoadStore(dir string) (*Store, error)` — loads 6 CSVs into an in-memory `Store`.
- `Serve(in io.Reader, out io.Writer, s *Store) error` — runs the JSON-RPC loop.
- `Store` with methods `SearchMatches`, `Stats`, `SearchPlayers`, `Average`, `Standings`, `HeadToHead`.
- Types `Match`, `Player`, `TeamStats`, `Standing`, `HeadToHead`.

## Data schema (in-memory, parsed from CSV)

`Match`: Competition, Home, Away, Round, Stage, Date (string); Season, HomeGoals, AwayGoals (int).

`Player`: ID, Name, Nationality, Club, Position (string); Age, Overall, Potential (int).

Source files loaded: `Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`, `Libertadores_Matches.csv`, `BR-Football-Dataset.csv`, `novo_campeonato_brasileiro.csv`, `fifa_data.csv`. Data dir resolved from `SOCCER_DATA_DIR`, then `./data/kaggle`, then next to the binary.

## HTTP routes / CLI commands

(none) — no HTTP server and no CLI subcommands/flags; the process speaks MCP over stdio only.
