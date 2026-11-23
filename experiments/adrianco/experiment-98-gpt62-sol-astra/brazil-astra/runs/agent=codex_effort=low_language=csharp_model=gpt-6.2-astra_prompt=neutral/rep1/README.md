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

## Run the C# MCP server

From this directory, run `dotnet build` and `dotnet run --no-build -- --test` with the .NET 10 SDK. The scenario suite uses the bundled CSVs. No packages, account, or API key are needed.

For an MCP client, configure a stdio server with command `dotnet` and a single argument containing the absolute path to `bin/Debug/net10.0/Soccer.dll`. Set the server environment variable `SOCCER_DATA` to the absolute path to `data/kaggle` if the client runs from another directory. The client’s LLM translates questions into calls to the advertised tools.

- `matches` returns fixtures, scores, rounds, venues where available, extended stats, and source names. Use either club as the team, and the other as opponent. Use the same team key across tools.
- `records` ranks teams by points, goals or win rate. League standings use scored matches and break points ties by wins, goal difference and goals scored. They describe dataset results and omit administrative adjustments.
- `trends` groups by competition and season, optionally for one team.
- `players` returns the original FIFA snapshot attributes. Name and club accept partial matches. Position accepts a FIFA position or forward.
- `coverage` lists dataset names for source filters and raw row counts.

All paginated tools return a total and accept limit (1–100, default 20) and offset. Dates are inclusive. Unknown scores remain null. Match records combine source observations by competition and directed team pair, using nearby dates or the league season. The dedicated league schedules take precedence for aggregate statistics in covered seasons. Later seasons may have incomplete coverage. Rivalry filtering covers the major Rio, São Paulo, Porto Alegre, Belo Horizonte, Salvador, Fortaleza and Curitiba derbies. Individual goalscorers cannot be identified from team scores.
