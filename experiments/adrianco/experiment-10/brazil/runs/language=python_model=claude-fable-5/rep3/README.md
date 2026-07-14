# Brazilian Soccer MCP with spec and basic data sets

## Specification
brazilian-soccer-mcp-guide.md

## Data Sources
Kaggle data can't be downloaded without an account so these (freely available with attribution) data sets have been downloaded for use here:

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

## MCP Server

`server.py` implements the MCP server specified in TASK.md. It loads all six
CSV files into an in-memory knowledge graph (≈24k matches, 18k players) with
normalized team names, so "Flamengo", "Flamengo-RJ" and "flamengo" all refer
to the same club, and duplicate rows for the same real-world match across
overlapping datasets are reported only once.

### Setup

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### Run

The server speaks MCP over stdio:

```sh
.venv/bin/python server.py
```

Example Claude Code / Claude Desktop configuration:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/path/to/repo/.venv/bin/python",
      "args": ["/path/to/repo/server.py"]
    }
  }
}
```

### Tools

| Tool | Purpose |
|------|---------|
| `search_matches` | Find matches by team, opponent, competition, season, date range |
| `head_to_head` | Win/draw/loss record and recent meetings between two teams |
| `team_statistics` | A team's record (overall, home or away; by season/competition) |
| `competition_standings` | League table for a season, calculated from results |
| `goal_statistics` | Average goals per match, home/draw/away rates |
| `biggest_wins` | Largest margins of victory |
| `best_records` | Teams ranked by win rate (e.g. best away record) |
| `search_players` | FIFA player search by name/nationality/club/position/rating |
| `get_player` | Detailed profile for one player |
| `data_summary` | Dataset coverage (competitions, seasons, counts) |

### Code layout

- `team_names.py` — team name normalization (accents, state suffixes, renames)
- `data_loader.py` — CSV loading, date parsing, cross-file unification
- `queries.py` — query engine (filtering, head-to-head, standings, stats)
- `server.py` — MCP tool definitions and response formatting
- `tests/` — BDD-style pytest suite covering the spec's scenarios

### Tests

```sh
.venv/bin/python -m pytest tests/ -q
```
