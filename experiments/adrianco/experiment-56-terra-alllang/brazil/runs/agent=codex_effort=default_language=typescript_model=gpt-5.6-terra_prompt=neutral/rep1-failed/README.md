# Brazilian Soccer MCP

A TypeScript stdio MCP server that makes the supplied Brazilian-football CSVs queryable by an LLM. It loads data once at startup and supports match search, team records, head-to-head comparisons, FIFA-player search, calculated league standings, and a dataset summary.

## Run

```sh
npm install
npm run build
npm start
```

The server uses `data/kaggle` by default. Set `SOCCER_DATA_DIR` to point it at another directory containing the six CSV files. Run `npm test` to build and execute the BDD-style data/query tests.

Available MCP tools: `search_matches`, `team_statistics`, `head_to_head`, `search_players`, `competition_standings`, and `dataset_summary`. Team matching ignores accents and state suffixes (for example, `São Paulo-SP` matches `Sao Paulo FC`).

## Specification

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
