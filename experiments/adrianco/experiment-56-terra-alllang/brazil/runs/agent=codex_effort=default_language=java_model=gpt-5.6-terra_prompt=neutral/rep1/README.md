# Brazilian Soccer MCP Server

A dependency-free Java 17 MCP stdio server over the six included Brazilian-soccer CSV files. It loads data into memory at startup and offers tools for match search, records, head-to-head comparisons, calculated standings, player search, biggest wins, and a lightweight `ask` entry point.

Build and run:

```sh
mvn test
mvn -q package
java -cp target/classes com.brazilsoccer.mcp.Main data/kaggle
```

The process speaks newline-delimited JSON-RPC on standard input/output. For example:

```json
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}
{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"head_to_head","arguments":{"first_team":"Flamengo","second_team":"Fluminense","competition":"Brasileirão"}}}
```

Team comparison is accent-insensitive and accepts state suffix variants such as `Palmeiras-SP` and `São Paulo`.

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
