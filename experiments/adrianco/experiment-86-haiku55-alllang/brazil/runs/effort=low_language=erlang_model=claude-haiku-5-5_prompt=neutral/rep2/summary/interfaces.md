# Interfaces

## MCP protocol (JSON-RPC 2.0 over stdio)

| Method | Returns | Handler |
|--------|---------|---------|
| `initialize` | protocolVersion `2025-06-18`, capabilities.tools, serverInfo | `bsm_mcp.erl:request` |
| `ping` | `{}` | `bsm_mcp.erl:request` |
| `tools/list` | `{tools: [...]}` — 7 tool schemas | `bsm_tools:definitions/0` |
| `tools/call` | `{content:[{type:text,text}], isError}` | `bsm_tools:call/2` |

Notifications (no `id`) get no reply; unknown method → -32601, unknown tool → -32602, parse error → -32700.

## MCP tools

| Tool | Purpose | Required args |
|------|---------|---------------|
| `find_teams` | Resolve canonical team names from a fragment | — |
| `search_matches` | Matches by team/opponent, competition, season, date range, venue | — |
| `team_record` | W/D/L, goals for/against, win rate for a team | `team` |
| `head_to_head` | Head-to-head W/D/L, goals, recent matches between two teams | `team_a`, `team_b` |
| `standings` | Brasileirão Série A table for a season (computed) | `season` |
| `league_stats` | Aggregate: avg goals/match, home/draw/away %, biggest wins | — |
| `search_players` | FIFA players by name/nationality/club/position/min_overall | — |

## Data schema (in-memory maps)

- **Match**: `date` (ISO), `season` (int), `competition`, `stage`, `home`/`away` (team maps), `home_goals`, `away_goals`.
- **Team**: `name` (display), `base` (folded key), `state` (UF/country code or `<<>>`).
- **Player**: `id`, `name`, `age`, `nationality`, `club`, `position`, `overall`, `potential`, `value`, `wage`, plus physical attrs.

## CLI

`brazil_soccer_mcp [DataDir]` — escript; DataDir defaults to `$BSM_DATA_DIR` or `data/kaggle`. Loads data, logs counts to stderr, then serves MCP on stdio.
