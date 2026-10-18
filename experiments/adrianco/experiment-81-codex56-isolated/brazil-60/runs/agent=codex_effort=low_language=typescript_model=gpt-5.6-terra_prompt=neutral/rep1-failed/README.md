# Brazilian Soccer MCP Server

An MCP stdio server over the included Brazilian soccer CSV datasets. It uses no runtime npm dependencies and supports match search, team statistics, head-to-head comparisons, calculated standings, player searches, and aggregate competition statistics.

## Run

```sh
npm install
npm test
npm start
```

Configure an MCP client to run `node /absolute/path/to/dist/src/server.js` after building. Set `SOCCER_DATA_DIR` when the data directory is not `data/kaggle` below the working directory. The server implements `initialize`, `tools/list`, and `tools/call` over newline-delimited JSON-RPC stdio.

Available tools: `search_matches`, `team_statistics`, `compare_teams`, `competition_standings`, `search_players`, and `competition_statistics`.

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
