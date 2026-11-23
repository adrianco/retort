# Interfaces

## Transport

stdio JSON-RPC 2.0 (one JSON object per line on stdin, one response line on stdout). MCP methods: `initialize` (negotiates protocolVersion from 2024-11-05 / 2025-03-26 / 2025-06-18), `ping`, `tools/list`, `tools/call`. Notifications (no `id`) are accepted and produce no response. Parse errors return `-32700`; unknown methods `-32601`.

## MCP tools (`Soccer.m:+tools`)

| Tool | Purpose | Key arguments |
|------|---------|---------------|
| `find_matches` | Fixtures/scores/head-to-head/derbies/biggest-wins/bracket legs | `team`, `opponent`, `side`, `competition`, `season`, `from`, `to`, `round`, `stage`, `derbies`, `source`, `sort` (recent/oldest/margin), `limit`, `offset` |
| `team_statistics` | W/D/L, goals, venue splits, head-to-head, group_by breakdowns | `team`, `opponent`, `side`, `competition`, `season`, `group_by` (team/season/competition), `sort`, `min_matches`, date range |
| `competition_standings` | Season league table computed from scores (Série A / Série B) | `season` (required), `competition`, `limit`, `offset` |
| `search_players` | FIFA roster search/filter, or per-club rating summary | `name`, `club`, `nationality`, `position`, `min_overall`, `brazilian_club`, `group_by` (club), `limit`, `offset` |
| `club_profile` | Joins a club's FIFA roster with its match record + competition breakdown | `team` (required) + match filters |
| `dataset_coverage` | Lists loaded CSVs and row counts | (none) |

All tools use JSON-Schema `inputSchema` with `additionalProperties:false` and server-side `validate()`.

## Data schema (loaded, in-memory)

- **Matches** (merged across 5 CSVs): `competition`, `home_id`/`away_id` (normalized keys), `home_team`/`away_team`, `date`, `season`, `kickoff`, `home_goal`, `away_goal`, `round`, `stage`, `stadium`, `statistics` (extended file), `sources` (provenance).
- **Players** (`fifa_data.csv`, 18,207 rows): all FIFA columns preserved + derived `club_id`, `brazilian_club`.

## HTTP routes

(none)

## CLI commands

`soccer-mcp [--data-dir DIRECTORY]` — defaults the data dir to `<binary>/data/kaggle`.
