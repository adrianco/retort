# Interfaces

## MCP tools (JSON-RPC over stdio)

Server responds to `initialize`, `tools/list`, `tools/call`, `notifications/initialized`.
Supports both line-delimited and `Content-Length:`-framed messages.

| Tool | Arguments | Returns | Handler |
|------|-----------|---------|---------|
| `search_matches` | team, opponent, competition, season, from, to, limit | Formatted match list + count | `main.cpp:call` → `Database::find_matches` |
| `team_statistics` | team, competition, season, home_only | W/D/L + goals for/against | `main.cpp:call` → `Database::team_record` |
| `head_to_head` | team_a, team_b, competition, season | H2H wins/draws + match list | `main.cpp:call` → `Database::find_matches` |
| `standings` | competition, season | Points table sorted desc | `main.cpp:call` → `Database::standings` |
| `search_players` | name, nationality, club, position, limit | Players sorted by overall | `main.cpp:call` → `Database::find_players` |
| `ask_brazilian_soccer` | question | NL-routed match/player answer | `main.cpp:call` → `Database::answer` |

## Library API (`soccer::Database`)

- `bool load(dir, error&)` — reads 6 CSVs from `data/kaggle/`
- `find_matches(team, opponent, competition, season, from, to)` — substring/normalized filters, sorted by date desc
- `find_players(name, nationality, club, position, limit)` — sorted by overall desc
- `team_record(team, competition, season, home_only)` — aggregated W/D/L + goals
- `standings(competition, season)` — points map (3/1/0)

## Data schema (in-memory)

- `Match`: date, home, away, competition, stage, home_goals, away_goals, season, round
- `Player`: name, nationality, club, position, age, overall, potential

## Data sources loaded

Brasileirao_Matches.csv, Brazilian_Cup_Matches.csv, Libertadores_Matches.csv,
BR-Football-Dataset.csv, novo_campeonato_brasileiro.csv, fifa_data.csv (6 files).
