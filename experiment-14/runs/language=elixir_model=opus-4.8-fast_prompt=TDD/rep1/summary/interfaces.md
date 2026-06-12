# Interfaces

## HTTP routes

(none) — this is an MCP server over stdio, not HTTP.

## MCP protocol (JSON-RPC 2.0 over stdio)

Methods handled by `mcp/server.ex:handle/2`: `initialize`, `tools/list`,
`tools/call`, `ping`, `notifications/*` (no-reply). Protocol version
`2024-11-05`; server identifies as `brazilian-soccer-mcp` 0.1.0.

## MCP tools (`mcp/tools.ex`)

| Tool | Purpose | Key args |
|------|---------|----------|
| search_matches | Find matches by team/opponent/competition/season/date | team, opponent, competition, season, from, to, limit |
| head_to_head | Head-to-head record between two teams | team_a*, team_b* |
| team_record | W/L/D record, goals, win rate for a team | team*, season, competition, venue |
| compare_teams | Two teams' records + head-to-head | team_a*, team_b* |
| search_players | FIFA players by name/nationality/club/position | name, nationality, club, position, brazilian, min_overall, limit |
| standings | Season standings computed from match results | competition*, season* |
| list_competitions | Competitions and their season ranges | (none) |
| match_stats | Aggregate stats (avg goals, home/away/draw rates) | competition, season |
| biggest_wins | Largest victories by goal margin | competition, season, team, limit |
| best_record | Rank teams by win rate at a venue | venue, competition, season, min_matches, limit |

(`*` = required argument)

## CLI

`./brazilian_soccer_mcp [data_dir]` (escript, `mcp/cli.ex:main/1`) — loads CSVs
from the given dir (or `$DATA_DIR`, default `data/kaggle`), then serves
newline-delimited JSON-RPC on stdin/stdout; diagnostics go to stderr.

## Data schema

Loaded from `data/kaggle/`:
- **Match** (from 5 match CSVs): competition, source, date, home_team/away_team
  (+ normalized keys), home_goals/away_goals, season, round/stage.
- **Player** (from `fifa_data.csv`): name, nationality, club (+ key), position,
  overall and attributes.

Six source files: `Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`,
`Libertadores_Matches.csv`, `BR-Football-Dataset.csv`,
`novo_campeonato_brasileiro.csv`, `fifa_data.csv`.
