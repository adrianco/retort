# Interfaces

## MCP transport

JSON-RPC 2.0 over stdio (newline-delimited). Methods: `initialize`, `ping`,
`tools/list`, `tools/call`, plus `notifications/initialized`. Protocol version
`2024-11-05`. Each `tools/call` returns `content` (text) + `structuredContent`
(machine-readable), with tool errors surfaced as `isError: true`.

## MCP tools

| Tool | Key arguments | Returns |
|------|---------------|---------|
| `search_matches` | team, opponent, home_team, away_team, competition, season, start_date, end_date, limit | match list (+ head-to-head when team+opponent given) |
| `team_record` | team (req), competition, season, venue (home/away/all) | matches, W/D/L, goals for/against, points, win_rate |
| `head_to_head` | team_a (req), team_b (req), competition | total meetings, each side's wins/goals, draws, match list |
| `search_players` | name, nationality, club, position, min_overall, sort_by, limit | player list with ratings/attributes, count |
| `league_standings` | competition, season (req) | ranked table: points, played, W/D/L, GF/GA/GD |
| `competition_stats` | competition, season | match count, avg goals/match, home/away/draw split, home win rate, biggest wins |
| `list_competitions` | (none) | competitions with match counts and season ranges |

## Data schema (in-memory)

- `Match`: competition, season, round?, stage?, date (ISO), home/away display + canonical key, home/away goals.
- `Player`: name, age, nationality, overall, potential, club, position, jersey, height, weight.

## Data sources (data/kaggle/)

5 match CSVs (`novo_campeonato_brasileiro`, `Brasileirao_Matches`,
`Brazilian_Cup_Matches`, `Libertadores_Matches`, `BR-Football-Dataset`) unified
and de-duplicated, plus `fifa_data.csv` for players.
