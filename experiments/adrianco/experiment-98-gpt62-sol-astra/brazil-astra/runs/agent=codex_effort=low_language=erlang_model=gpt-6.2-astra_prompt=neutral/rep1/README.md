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

## Running the Erlang MCP server

Use Erlang/OTP 27 or later. Run `make build` to compile, `make test` for the dataset-backed EUnit scenarios, and `make run` to serve MCP over standard input and output. The server reads the bundled CSVs at startup and requires no network service or API key.

After building, configure a stdio MCP client with the following entry, replacing the path with the absolute directory containing this README. The client’s language model translates questions into tool arguments and formats the returned evidence.

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "erl",
      "args": ["-pa", "/absolute/path/to/project", "-noshell", "-s", "soccer_mcp", "main", "-s", "init", "stop"]
    }
  }
}
```

| Tool | Example arguments | Result |
|---|---|---|
| matches | `{"team":"Flamengo","opponent":"Fluminense","limit":1}` | Most recent derby fixture and score |
| records | `{"competition":"Brasileirão","season":2019}` | League table ordered by points, wins, goal difference and goals scored |
| summary | `{"team":"Palmeiras","group_by":"season"}` | Season totals, scoring averages and home win percentages |
| players | `{"nationality":"Brazil","limit":5}` | Five highest-rated Brazilians with FIFA attributes |
| club_profile | `{"team":"Santos","season":2019}` | Match record and FIFA snapshot roster |

Paged results include the total number of matches, teams or players found. Use `limit` (1–100, default 20) and `offset` to retrieve further pages. Match date bounds are inclusive. Missing scores appear as JSON null and only completed games contribute to records and averages. The source files contain team scores and FIFA attributes but lack individual scoring events. A partial season yields a partial table.

The combined Série A schedule uses the dedicated league files for 2003–2022 and adds extended statistics by season and ordered club pair. January and February 2021 Série A fixtures in the extended file belong to the 2020 season. Other competitions merge on competition, date and ordered club pair. Overlap resolution depends on team aliases. Use the optional source filename to inspect one file independently. Cup stage names are derived from season-specific round numbers where available. The derby filter covers traditional rivalries in Rio de Janeiro, São Paulo, Porto Alegre, Belo Horizonte, Salvador, Curitiba and Fortaleza.
