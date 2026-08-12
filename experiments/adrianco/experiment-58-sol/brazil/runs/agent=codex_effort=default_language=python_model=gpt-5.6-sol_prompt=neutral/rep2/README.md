# Brazilian Soccer MCP Server

A Python MCP server and deterministic knowledge graph over all six bundled
Brazilian soccer/FIFA CSV datasets. It supports normalized match search, team
records, head-to-head comparisons, calculated standings, player search,
competition statistics, rivalry matches, and natural-language questions.

## Install and run

Python 3.11 or newer is required. From this directory:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
python server.py                         # local MCP over stdio
python server.py --transport streamable-http --port 8000
```

For MCP Inspector development:

```bash
pip install -e '.[test]'
mcp dev server.py
```

The server exposes these MCP tools:

- `search_matches`: team, opponent, date, competition, season, stage, and source filters
- `get_team_statistics`: W/D/L, goals, points, and home/away records
- `compare_teams`: head-to-head results and totals
- `find_players`: name, nationality, club, position, and rating filters
- `get_standings`: calculated season table
- `get_competition_statistics`: goals and result aggregates
- `get_biggest_wins`, `find_derbies`, and `rank_teams`
- `get_club_overview`: cross-file club performance plus FIFA players
- `ask_soccer`: deterministic natural-language routing for common questions
- `dataset_summary`: data coverage and provenance

It also exposes the `soccer://dataset/summary` resource and the
`analyze_brazilian_soccer` prompt. Calculated tables describe the supplied
dataset; they are not presented as a separate official data feed.

## Test

```bash
pytest -q
```

The suite includes BDD-style behavior coverage for more than 20 sample
questions, every source file, normalization and deduplication, cross-file
queries, MCP registration, statistical invariants, and the specified response
time budgets.

## Design

`soccer_graph.py` loads UTF-8 CSV files and maps their five match schemas into
one `Match` entity. Team aliases, accents, Brazilian state suffixes, date
formats, incomplete fixtures, and one-day timezone shifts are normalized before
duplicates are merged. Source filenames remain attached to each match as
provenance. In-memory team and club indexes keep lookups fast.

`query_engine.py` routes common Portuguese-name/English-question patterns to
the graph without requiring an API key or making network calls. `server.py`
wraps the same tested functions with the MCP Python SDK, so protocol and domain
logic do not diverge.

## Specification

See `TASK.md` and `brazilian-soccer-mcp-guide.md`.

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
