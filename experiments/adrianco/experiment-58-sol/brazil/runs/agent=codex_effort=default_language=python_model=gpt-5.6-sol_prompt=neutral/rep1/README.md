# Brazilian Soccer MCP Server

A Python Model Context Protocol server for natural-language exploration of the six bundled Brazilian football datasets. It provides structured tools for match lookup, team records, head-to-head comparisons, calculated standings, competition statistics, biggest wins, player search, and cross-file competition history.

The server normalizes accents, punctuation, common full club names, and state suffixes such as `Flamengo-RJ`. All five match CSV formats are adapted into one canonical match model while retaining source, competition, round/stage, and extended statistics.

## Install and run

Python 3.10 or newer is required. Use an isolated environment so the MCP SDK and Pydantic versions remain compatible:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
brazilian-soccer-mcp
```

The console command starts the MCP server over standard input/output. An MCP client can also run it as:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "python",
      "args": ["-m", "brazilian_soccer_mcp.server"]
    }
  }
}
```

Run the behavioral and performance tests with:

```bash
pytest
```

## MCP tools

- `search_matches`: team/opponent, competition, season, date range, and stage filters
- `team_statistics`: W/D/L, goals, points, goal difference, and home/away records
- `compare_teams`: head-to-head record and chronological results
- `calculate_standings`: 3/1/0 points table with standard tie sorting
- `competition_statistics`: goals per game and home/away/draw rates
- `biggest_wins`: largest result margins
- `search_players`: name, country, club, position, overall-rating filters
- `team_competitions`: cross-file competition appearances
- `dataset_summary`: verification counts for all six CSVs

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
