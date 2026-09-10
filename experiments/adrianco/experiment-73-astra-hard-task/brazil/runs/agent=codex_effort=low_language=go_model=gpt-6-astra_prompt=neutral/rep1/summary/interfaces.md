# Interfaces

## Transport

Newline-delimited JSON-RPC 2.0 over stdio (`main.go:Serve`). Standard MCP
lifecycle: `initialize` → `notifications/initialized` → `tools/list` /
`tools/call`. `ping` and unknown-method/parse errors handled per spec. Tool
calls before `notifications/initialized` return `-32002 Server not initialized`.

## MCP tools (10)

| Tool | Required args | Purpose |
|------|---------------|---------|
| search_matches | — | Filter fixtures by team/opponent/venue/dates/season/competition/stage/source/derby; sort by date or biggest_win; paginated |
| search_players | — | FIFA snapshot search by name/nationality/club/position; sorted by overall desc |
| team_stats | team | W/L/D record, home/away splits, by-competition and by-season trends, match history |
| head_to_head | team, opponent | Head-to-head records in both fixture directions |
| team_profile | team | Cross-file: match record + competitions + history + FIFA player snapshot |
| standings | competition, season | Serie A/B league table computed from match results (3pts/win) |
| statistics | — | Aggregate goals/home-away/season comparisons, ranked team records, biggest wins |
| competition_info | — | Cup fixtures grouped by season/stage/round |
| graph | team | Knowledge-graph traversal: match/team/competition/player nodes and edges |
| data_info | — | Dataset coverage, row counts, normalized team names, conflict warnings |

## Data schema (in-memory)

- **Match**: id, date, home, away, competition, season, round, stage, stadium, home_goals (*int, nullable), away_goals (*int), sources[], attributes{}.
- **Player**: id, name, club, nationality, position, overall, attributes{}.
- **Store**: Matches[], Players[], Sources{name→count}, Warnings[], Teams{name→match idxs}.

## CLI

`-data <dir>` (default `data/kaggle`) — directory holding the six CSV datasets.
