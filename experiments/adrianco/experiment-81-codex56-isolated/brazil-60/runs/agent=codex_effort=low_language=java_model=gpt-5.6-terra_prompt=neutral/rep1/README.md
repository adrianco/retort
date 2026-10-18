# Brazilian Soccer MCP

A dependency-light Java 17 MCP stdio server over the six supplied Brazilian soccer CSV datasets. It exposes `search_matches`, `team_statistics`, `head_to_head`, `search_players`, `standings`, and `competition_statistics`; team matching is accent- and state-suffix-insensitive.

Build and test with `mvn test`. Run with `mvn package && java -jar target/brazilian-soccer-mcp-1.0.0.jar` (optionally pass the data directory as its first argument). The process speaks newline-delimited MCP JSON-RPC on standard input/output.

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
