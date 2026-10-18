# Interfaces

## MCP server (JSON-RPC 2.0 over stdio)

Protocol version `2024-11-05`. Methods handled in `src/mcp.rs:handle_line`:

| Method | Returns | Notes |
|--------|---------|-------|
| `initialize` | serverInfo + capabilities.tools | `src/mcp.rs:initialize_result` |
| `ping` | `{}` | |
| `tools/list` | tool definitions array | `src/tools.rs:definitions` |
| `tools/call` | `{content:[{type:text}], isError}` | bad args → `isError:true` |
| (notifications) | no reply | id-less requests ignored |

## MCP tools (`tools/call`)

| Tool | Arguments | Purpose |
|------|-----------|---------|
| `search_matches` | team, opponent, competition, season, date_from, date_to, limit | Filter matches; team+opponent adds head-to-head line |
| `team_stats` | team*, competition, season | W/D/L, goals, win rate, home/away split |
| `head_to_head` | team_a*, team_b*, competition | Two-team record + recent matches |
| `standings` | season*, competition | League table computed from matches (3-1-0) |
| `league_stats` | competition, season | Match count, avg goals, home/draw/away rates, biggest wins |
| `search_players` | name, nationality, club, position, min_overall, limit | FIFA player search sorted by overall |
| `dataset_info` | (none) | Loaded/skipped row counts per file |

(* required)

## Library API (crate `brazilian_soccer_mcp`)

Exposed via `src/lib.rs`: `data` (`Dataset`, `Match`, `Player`, `Competition`, `parse_date`),
`normalize` (`team_key`, `display_name`, `fold`), `query` (filters + aggregation fns),
`tools`, `mcp`.

## Data schema

In-memory `Dataset { matches: Vec<Match>, players: Vec<Player>, sources: Vec<SourceSummary> }`.
- `Match`: date (ISO), season, competition, round, home/away `Team{key,name}`, home_goals, away_goals.
- `Player`: name, age, nationality, overall, potential, club, position, jersey_number, height, weight.

Sources: 5 match CSVs + `fifa_data.csv` from `data/kaggle/`.
