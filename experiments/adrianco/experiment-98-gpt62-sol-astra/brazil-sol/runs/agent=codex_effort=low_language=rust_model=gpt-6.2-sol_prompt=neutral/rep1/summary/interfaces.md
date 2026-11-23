# Interfaces

## MCP protocol (JSON-RPC 2.0 over stdio)

| Method | Behavior | Handler |
|--------|----------|---------|
| `initialize` | Negotiates protocolVersion (supports `2025-11-25`, `2025-06-18`), returns serverInfo + `tools` capability | `lib.rs:request` |
| `ping` | Returns `{}` | `lib.rs:request` |
| `tools/list` | Lists the 7 tools (requires prior initialize) | `lib.rs:request` → `query::tools()` |
| `tools/call` | Dispatches to a named tool, wraps result as `content` text + `structuredContent` | `lib.rs:request` → `Graph::call` |

Errors follow JSON-RPC: `-32700` parse, `-32600` invalid request, `-32601` method not found, `-32602` invalid params/unknown tool, `-32002` not initialized.

## MCP tools (`query::tools()`)

| Tool | Purpose | Key args |
|------|---------|----------|
| `search_matches` | Filter matches by team/opponent/venue/competition/season/date range/stage/round/source/derbies; order latest/earliest/biggest_win; paginated | `team, opponent, venue, competition, season, start_date, end_date, stage, round, source, derbies, order, limit, offset` |
| `team_stats` | W/L/D + goals record, by venue/competition/season, head-to-head (opponent), cross-linked FIFA club players | `team` (required), `opponent, season, competition, venue, …` |
| `search_players` | FIFA snapshot by name/nationality/club/position (FIFA codes or broad groups), sorted by overall | `name, nationality, club, position, limit, offset` |
| `cup_bracket` | Knockout rounds/legs by stage for Copa do Brasil / Libertadores | `competition, season` (required), `source` |
| `standings` | Computed league table, leader/champion, relegation (Brasileirão / Série B) | `competition, season` (required), `source` |
| `analyze_matches` | Aggregate scoring/outcome trends, team rankings by win_rate/goals/wins/points | `competition, season(s), venue, rank_by, min_matches, limit, source` |
| `dataset_info` | Row counts per source, merged fixture count, competitions, data limitations | (none) |

## Data schema

- **`Match`**: date, time, competition, season, round, stage, home/away team (+ normalized keys), states, home/away goal, stadium, source_id, sources[], extra{}.
- **`Player`**: id, name, nationality, club, position, age, overall, potential, jersey, height, weight, attributes{} (+ folded name/club/nationality keys).
- **Sources (6 CSVs)**: `novo_campeonato_brasileiro`, `Brasileirao_Matches`, `Brazilian_Cup_Matches`, `Libertadores_Matches`, `BR-Football-Dataset` (match feeds), `fifa_data` (players). Match feeds are merged into deduplicated `fixtures`; raw rows remain queryable via `source`.
