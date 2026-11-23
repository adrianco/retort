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

## Run the MCP server

Requires Elixir 1.18 or newer. Build the executable and run the tests from the
project directory.

```sh
mix compile --warnings-as-errors
mix test
mix escript.build
```

Configure an MCP client with the absolute paths to the executable and data.
The client launches the server and translates natural-language questions into
tool calls. The server runs locally over MCP stdio and needs no API key.

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/absolute/path/to/project/soccer",
      "args": ["--data-dir", "/absolute/path/to/project/data/kaggle"]
    }
  }
}
```

When launched from the project directory, `./soccer` defaults to `data/kaggle`.
The `SOCCER_DATA_DIR` environment variable also sets the dataset directory.

| Tool | Example question |
| --- | --- |
| `find_matches` | When did Flamengo last play Corinthians, and what was the score? |
| `team_profile` | What's Grêmio's home record, and who is in its FIFA roster? |
| `find_players` | Who are the highest-rated Brazilian players in the FIFA snapshot? |
| `competition` | Who won the 2019 Brasileirão? Show the 2018 Libertadores bracket. |
| `statistics` | Compare Série A scoring in 2018 and 2019. Which team had the best away record? |
| `data_sources` | How many rows are loaded from each CSV? |

List tools return a total and a `next_offset` for additional results. Match
filters accept inclusive date ranges, and `season` refers to the competition
edition even when a game took place the following year. Team profiles join
matches with the FIFA roster using normalized club names. That roster reflects
the historical FIFA export, including gaps such as Flamengo and São Paulo.

Match queries use reconciled fixtures by default. Historical Série A rows take
precedence through 2019. Other sources supply missing scores and additional
fields where fixtures can be matched. Use the `source` filter to query a
specific match file directly. Records count only games with scores on both
sides. Standings use recorded results and flag incomplete seasons, including
the 377 available Série A results for 2023. The match files have no individual
scorer events, so the server cannot calculate player goal totals. Brackets
show the reported stage and fixture scores. Penalty shootout results are
unavailable in these files.
