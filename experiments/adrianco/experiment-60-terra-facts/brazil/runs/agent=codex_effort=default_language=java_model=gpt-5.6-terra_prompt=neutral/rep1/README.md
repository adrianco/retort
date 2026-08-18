# Brazilian Soccer MCP

A dependency-free Java 21 stdio MCP server over the six supplied Brazilian soccer CSV datasets. It exposes MCP tools for match/player search, team records, head-to-head comparisons, calculated standings, aggregate competition statistics, and a convenience natural-language query tool.

## Run

```bash
mvn test package
java -jar target/brazilian-soccer-mcp-1.0.0.jar data/kaggle
```

The process uses newline-delimited JSON-RPC on stdin/stdout, as required by stdio MCP clients. Start it with `data/kaggle` omitted when launched from the project root. Send `initialize`, `tools/list`, and `tools/call` requests in the normal MCP sequence.

Team matching is accent-insensitive and treats state suffixes such as `Palmeiras-SP` and `Palmeiras` as the same team. CSV loading accepts quoted fields, UTF-8 text, ISO dates, Brazilian `DD/MM/YYYY` dates, and date-times.

## Tools

- `search_matches` — team, opponent, competition, season, date, round/stage filters
- `team_statistics`, `head_to_head`, `standings`, `competition_statistics`
- `search_players` — name, nationality, club, position filters (rating-sorted)
- `answer_question` — common natural-language question convenience interface

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
