# Brazilian Soccer MCP Server

A Go implementation of a Model Context Protocol (MCP) server that provides queryable access to Brazilian soccer data.

## Implementation

The server (`main.go`, `data.go`, `tools.go`) implements the MCP JSON-RPC 2.0 protocol over stdio and exposes 7 tools for querying Brazilian soccer data.

### Running

```bash
go build -o brazilian-soccer-mcp .
./brazilian-soccer-mcp
# Reads JSON-RPC requests from stdin, writes responses to stdout
# Logs startup info to stderr
```

The server looks for data in `./data/kaggle/` relative to the working directory, or via the `DATA_DIR` environment variable.

### MCP Tools

| Tool | Description |
|------|-------------|
| `search_matches` | Find matches by team, competition, season, or head-to-head |
| `get_team_stats` | Win/loss/draw record for a team with optional filters |
| `get_standings` | Points table for a competition/season |
| `get_biggest_wins` | Matches with largest goal difference |
| `search_players` | FIFA player database search by name/club/nationality/position |
| `get_competition_stats` | Overall stats: goals/match, home win rate, top scorers |
| `list_teams` | All teams in database, filtered by competition/season |

### Data Coverage

- **20,365 matches** (after deduplication) across all competitions
- **18,207 players** from FIFA database
- Competitions: Brasileirão Serie A, Copa do Brasil, Copa Libertadores, extended Brazilian league stats
- Seasons: 2003–2023

### Key Features

- **Accent-insensitive matching**: `"brasileirao"` matches `"Brasileirão Serie A"`
- **Team name normalization**: strips state suffixes (`"Flamengo-RJ"` → `"Flamengo"`)
- **Multiple date formats**: ISO, Brazilian (`DD/MM/YYYY`), datetime with time
- **Cross-file queries**: single search spans all loaded datasets
- **Deduplication**: matches appearing in multiple files are deduplicated by date + teams + score

### Testing

```bash
go test -v ./...
```

25 tests covering unit tests (normalization, date parsing), integration tests (data loading, filtering, statistics), MCP protocol tests, and a 20-question benchmark.

---

## Specification

See [TASK.md](TASK.md) and [brazilian-soccer-mcp-guide.md](brazilian-soccer-mcp-guide.md).

## Data Sources

Kaggle data can't be downloaded without an account so these (freely available with attribution) datasets have been pre-downloaded:

https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro
- License: Attribution 4.0 International (CC BY 4.0)
- data/kaggle/Brasileirao_Matches.csv
- data/kaggle/Brazilian_Cup_Matches.csv
- data/kaggle/Libertadores_Matches.csv

https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches
- License: CC0: Public Domain
- data/kaggle/BR-Football-Dataset.csv

https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019
- License: World Bank - Attribution 4.0 International (CC BY 4.0)
- data/kaggle/novo_campeonato_brasileiro.csv

https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data
- License: Apache 2.0
- data/kaggle/fifa_data.csv
