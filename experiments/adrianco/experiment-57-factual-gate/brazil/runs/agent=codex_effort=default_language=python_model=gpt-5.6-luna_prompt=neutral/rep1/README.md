# Brazilian Soccer MCP with spec and basic data sets

## Run

The implementation is in `soccer_mcp.py` and uses only the Python standard library:

```bash
python soccer_mcp.py
```

It reads newline-delimited JSON-RPC from stdin and writes MCP-compatible responses to stdout.
The `SoccerDatabase` class can also be imported directly. Available tools are `search_matches`,
`team_statistics`, `head_to_head`, `search_players`, `standings`, `statistics`, and `ask_soccer`.

Run the tests with `python -m pytest`.

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
