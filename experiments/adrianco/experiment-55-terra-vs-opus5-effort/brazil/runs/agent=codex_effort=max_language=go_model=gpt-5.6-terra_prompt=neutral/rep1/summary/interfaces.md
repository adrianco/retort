# Interfaces

## MCP transport (JSON-RPC 2.0 over stdio)

| Method | Handler | Notes |
|--------|---------|-------|
| initialize | `server.go:initializeResult` | Echoes protocol version, advertises tools/resources/prompts capabilities |
| ping | `HandleRequest` | Returns `{}` |
| tools/list | `toolDefinitions` | Lists 11 tools with JSON input schemas |
| tools/call | `handleToolCall` → `CallTool` | Dispatches to tool implementations |
| resources/list, resources/read | `resources`, `readResource` | Dataset inventory + per-source metadata |
| prompts/list, prompts/get | `prompts`, `getPrompt` | Single `brazilian_soccer_question` prompt |

## MCP tools

| Tool | Purpose | Requirement |
|------|---------|-------------|
| query_brazilian_soccer | Natural-language router to the tools below | R1 |
| search_matches | Matches by team/opponent/home/away, competition, season, date range, round, stage, source, derbies, finals | R3, R4, R5 |
| team_statistics | W/L/D, goals for/against, points, win rate for one team (all/home/away scope) | R6 |
| head_to_head | Two-team W/L/D record, goals, recent meetings | R11 |
| search_players | FIFA players by name, nationality, club, position, min overall | R7, R8 |
| competition_standings | League table calculated from match results | R9 |
| competition_statistics | Avg goals/match, home/away/draw rates, biggest wins, most goals, best home/away record | R10 |
| team_competitions | Competitions and season ranges a team appears in | (bonus) |
| compare_seasons | Aggregate stats across two+ seasons | (bonus) |
| competition_bracket | Copa Libertadores knockout matches grouped by stage | (bonus) |
| list_data_sources | Loaded CSV inventory + record counts | R2 |

## CLI

| Flag | Description |
|------|-------------|
| `-data-dir` | Directory containing the six Kaggle CSVs (default `data/kaggle`, or `$BRAZILIAN_SOCCER_DATA_DIR`) |
| `-query` | Run one natural-language question and print the answer instead of starting stdio |

## Data schema (in-memory)

`Match`: id, date, home/away team + key + state, goals, has_score, competition, season, round, stage, source, optional `MatchStats`.
`Player`: id, name, age, nationality, overall/potential, club, position, jersey, height/weight, foot, skills map.
Six sources loaded: Brasileirão (4180), Copa do Brasil (1337), Libertadores (1255), BR-Football extended (10296), historical (6886), FIFA players (18207).
