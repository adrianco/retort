# Interfaces

## MCP protocol (JSON-RPC 2.0 over stdio)

Dispatched by `mcp.rs:McpServer::handle`.

| Method | Behavior |
|--------|----------|
| `initialize` | Returns protocol version, `tools` capability, and `serverInfo` |
| `ping` | Returns `{}` |
| `tools/list` | Returns the 8 tool definitions below |
| `tools/call` | Routes to a tool by `params.name`, returns `content` + `structuredContent` |

Notifications (no `id`) produce no response; unknown methods return JSON-RPC error `-32601`.

## MCP tools (`tools/call`)

| Tool | Arguments | Returns |
|------|-----------|---------|
| `dataset_summary` | (none) | Load/coverage counts for all 6 CSVs |
| `search_matches` | `team`, `opponent`, `competition`, `season`, `start_date`, `end_date`, `stage`, `source`, `limit` | Deduplicated matches (count + list) |
| `team_statistics` | `team`\*, `season`, `competition`, `venue` (`home`/`away`) | W/D/L, goals for/against, points, win rate |
| `head_to_head` | `team_a`\*, `team_b`\*, `season`, `competition` | Aggregate wins/draws/goals + match list |
| `search_players` | `name`, `nationality`, `club`, `position`, `min_overall`, `limit` | FIFA players sorted by overall |
| `standings` | `season`\*, `competition` (default `Brasileirão`) | League table computed from matches |
| `competition_statistics` | `competition`\*, `season` | Match count, goals/match, home/away wins, home win rate |
| `biggest_wins` | `competition`, `season`, `limit` | Matches sorted by goal margin |
| `team_overview` | `team`\*, `season` | Cross-file join: stats + competitions + FIFA players + recent matches |

\* required argument.

## Library API (exported from `brasileirao_mcp`)

- `SoccerStore::load(data_dir)` and query methods: `search_matches`, `team_statistics`, `head_to_head`, `search_players`, `standings`, `competition_statistics`, `biggest_wins`, `competitions_for_team`, `team_overview`, `counts`, `matches`, `players`.
- `McpServer::new(store)`, `McpServer::handle(request)`, `McpServer::store()`.
- Model types: `MatchRecord`, `Player`, `DatasetCounts`, `TeamStats`, `HeadToHead`, `Standing`, `MatchFilter`, `CompetitionStats`, `TeamOverview`.
- `store::format_matches(rows)` for human-readable match rendering.

## CLI (src/main.rs)

`brasileirao-mcp [--data-dir PATH] [--check]` — runs the MCP stdio server; `--check` prints dataset counts and exits. Data dir also settable via `BRAZILIAN_SOCCER_DATA_DIR` (default `data/kaggle`).

## Data sources loaded

| Source CSV | Competition | Loader |
|------------|-------------|--------|
| Brasileirao_Matches.csv | Brasileirão | `load_standard_matches` |
| Brazilian_Cup_Matches.csv | Copa do Brasil | `load_standard_matches` |
| Libertadores_Matches.csv | Copa Libertadores | `load_standard_matches` |
| BR-Football-Dataset.csv | (from `tournament` column) | `load_extended_matches` |
| novo_campeonato_brasileiro.csv | Brasileirão | `load_historical_matches` |
| fifa_data.csv | (players) | `load_players` |

## Data schema (in-memory)

`MatchRecord`: date, season, competition, home_team, away_team, home_goals, away_goals, round?, stage?, stadium?, source, home/away corners?, home/away shots?.

`Player`: id, name, age?, nationality, overall?, potential?, club?, position?, jersey_number?, height?, weight?, attributes (skill map).
