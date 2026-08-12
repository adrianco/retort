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

The server is dependency-free Python and reads the six CSV files at startup.
Run it as an MCP stdio server with:

```bash
python server.py
```

Available MCP tools are `find_matches`, `team_stats`, `head_to_head`,
`search_players`, `standings`, `statistics`, and `biggest_wins`. Team matching
removes accents/state suffixes and handles common full-name aliases; dates in
ISO, Brazilian, and timestamp formats are accepted. The historical and
extended-statistics datasets are included in the same normalized match index.

Run the tests with:

```bash
pytest -q
```
