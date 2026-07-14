# Interfaces

## MCP tools (JSON-RPC 2.0 over stdio)

Protocol methods handled (`mcp.rs:handle`): `initialize`, `ping`, `tools/list`, `tools/call`. Protocol version `2024-11-05`.

| Tool | Purpose | Required args |
|------|---------|---------------|
| find_matches | Matches by team/opponent/competition/season/date range/venue; appends head-to-head when two teams given | — |
| head_to_head | All-time H2H W/L/D + goals between two teams | team_a, team_b |
| team_record | W/D/L + goals for a team, scoped by season/competition/venue | team |
| standings | League table computed from match results (3pts win, 1 draw) | season |
| search_players | FIFA players by name/nationality/club/position/min_overall, sorted by rating | — |
| league_stats | Avg goals/match, home/away win rates over competition/season/team | — |
| biggest_wins | Largest-margin victories within a scope | — |
| team_competitions | Competitions a team appears in, with match counts | team |
| list_competitions | All loaded competitions with season ranges + match counts | — |

## Library API (exported from `lib.rs`)

`Database` (query engine) and `Server` (MCP wrapper). Database methods: `load_from_dir`, `from_parts`, `find_matches`, `team_record`, `head_to_head`, `standings`, `league_stats`, `biggest_wins`, `search_players`, `competitions_for_team`, `competitions`, `resolve_team`.

## Data sources (CSV → competition)

| File | Competition mapped |
|------|--------------------|
| Brasileirao_Matches.csv | Brasileirão Série A |
| Brazilian_Cup_Matches.csv | Copa do Brasil |
| Libertadores_Matches.csv | Copa Libertadores |
| BR-Football-Dataset.csv | Série B / Série C only (+ shots/corners extras) |
| novo_campeonato_brasileiro.csv | Brasileirão Série A (historical 2003–2019) |
| fifa_data.csv | FIFA player database |

## CLI

`brazilian-soccer-mcp [DATA_DIR]` serves MCP over stdio (default `data/kaggle`). `--selftest` loads data, prints `list_competitions`, exits.
