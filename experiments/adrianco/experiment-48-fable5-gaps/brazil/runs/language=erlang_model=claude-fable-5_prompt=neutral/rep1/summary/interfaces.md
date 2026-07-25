# Interfaces

## Transport

The server is an MCP (Model Context Protocol) server speaking JSON-RPC 2.0 over
stdio (newline-delimited JSON on stdin/stdout; diagnostics on stderr). Launched
as an escript; optional first arg is the data directory (default `data/kaggle`,
overridable via `BSMCP_DATA_DIR`).

## JSON-RPC methods (`bsmcp_rpc:handle/1`)

| Method | Kind | Returns |
|--------|------|---------|
| `initialize` | request | `protocolVersion`, `capabilities.tools`, `serverInfo` (negotiates 2024-11-05 / 2025-03-26 / 2025-06-18) |
| `ping` | request | `{}` |
| `tools/list` | request | array of tool definitions from `bsmcp_tools:tools/0` |
| `tools/call` | request | `{content: [{type:"text", text}], isError}` |
| `resources/list` | request | `{resources: []}` |
| `prompts/list` | request | `{prompts: []}` |
| notifications (method, no id) | notification | ignored (noreply) |
| unknown method | request | error `-32601 Method not found` |
| malformed JSON | — | error `-32700 Parse error` |
| non-map / missing name | — | error `-32600` / `-32602` |

## MCP tools (`bsmcp_tools:tools/0`, dispatched by `call/2`)

| Tool | Required args | Optional args | Result |
|------|---------------|---------------|--------|
| `search_matches` | (none) | team, opponent, competition, season, stage, date_from, date_to, limit | match list (+ head-to-head summary when team & opponent given) |
| `team_stats` | team | season, competition, venue (home/away/all) | W/D/L record, goals for/against, home/away splits |
| `head_to_head` | team1, team2 | limit | every meeting + wins/draws/goals summary |
| `competition_standings` | season | competition, limit | league table (3 pts/win), champion tagged |
| `search_players` | (none) | name, nationality, club, position, min_overall, limit | FIFA players sorted by overall |
| `league_stats` | (none) | competition, season | goals/match, home-win / draw / away-win rates |
| `biggest_wins` | (none) | competition, season, limit | largest victory margins |
| `data_summary` | (none) | (none) | per-competition match counts, season coverage, team/player counts |

## Data schemas (in-memory ETS, populated from CSV)

- **Match** record (map): `id`, `competition`, `source`, `date` (`{Y,M,D}`|undefined),
  `season`, `round`, `stage`, `home`, `away`, `home_canon`, `away_canon`,
  `hg`, `ag`, `arena`, `extra` (corners/shots/attacks from the extended file).
- **Player** record (map): `id`, `fifa_id`, `name`, `name_canon`, `age`,
  `nationality`, `nat_canon`, `overall`, `potential`, `club`, `club_canon`,
  `position`, `jersey`, `height`, `weight`, `value`, `wage`, `foot`.
- **Team** entry: `{CanonicalName, DisplayName}`.

## Source CSV files loaded

`Brasileirao_Matches.csv`, `novo_campeonato_brasileiro.csv` (both → Brasileirão Série A),
`Brazilian_Cup_Matches.csv` (Copa do Brasil, highest round/season labeled "final"),
`Libertadores_Matches.csv` (Copa Libertadores), `BR-Football-Dataset.csv`
(extended stats, tournament-mapped), `fifa_data.csv` (FIFA 19 players).

## CLI commands

(none — no subcommand CLI; the escript is a stdio MCP server.)
