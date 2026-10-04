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

## Implementation

- `soccer.py` — loads all 6 CSVs (standard library only), normalizes team names, parses dates, and provides the query functions.
- `server.py` — MCP server speaking JSON-RPC 2.0 over stdio, with 19 tools (matches, head-to-head, team records, standings, champions, relegation, stats, biggest wins, derbies, Libertadores bracket, player search, club profiles).
- `test_soccer.py` — pytest suite with 25+ sample questions, plus MCP protocol and performance tests.

Run: `python3 server.py` (Claude Desktop config: `{"command": "python3", "args": ["/path/to/server.py"]}`).
Test: `python3 -m pytest -q`.

Data notes: the 2022 season in `Brasileirao_Matches.csv` is incomplete (unplayed rounds have no score). The FIFA data leaves out several Brazilian clubs (Flamengo, Corinthians, Palmeiras, São Paulo). When files overlap, each competition and season is taken from one primary file so matches aren't counted twice.
