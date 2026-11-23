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

## Running the Elixir MCP server

Use Elixir 1.18 or newer with Erlang/OTP 27 or newer. From this directory run:

```sh
mix test
mix escript.build
```

Configure a stdio server in your MCP client, replacing the example path with the
absolute path of the built executable:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/absolute/path/to/soccer",
      "args": []
    }
  }
}
```

The executable loads all six CSVs from the adjacent `data/kaggle` directory at
startup. To use another copy, pass its directory as the first argument. It runs
offline. The connected client's LLM interprets questions and calls the tools.

| Tool | Example question | Arguments |
| --- | --- | --- |
| matches | When did Flamengo last play Corinthians? | `{"team":"Flamengo","opponent":"Corinthians","limit":1}` |
| matches | Which Libertadores quarterfinals took place in 2018? | `{"competition":"Libertadores","season":2018,"stage":"quarterfinals"}` |
| statistics | How did Palmeiras perform at home and away in 2023? | `{"team":"Palmeiras","season":2023,"group_by":"venue"}` |
| standings | Who led the 2019 Brasileirão on points? | `{"competition":"Brasileirão","season":2019,"limit":1}` |
| players | Who are the highest-rated Brazilian forwards? | `{"nationality":"Brazil","position":"forward"}` |
| team_profile | What are Grêmio's 2019 results and which players represent it in FIFA? | `{"team":"Grêmio","season":2019}` |

List tools to inspect every filter. List results include a total and accept
`offset` and `limit` (default 20, maximum 100). Match details retain the original
column names, including arena and extended statistics where available.

The default match view reconciles overlapping sources by competition, normalized
home and away teams, and date (allowing a one-day difference). Série A also uses
season and team pairing for rescheduled fixtures. The competition-specific sources
take precedence, with other files supplying missing scores and additional columns.
Set `source` to a CSV basename without the extension to inspect original records.
Fixtures with missing scores are searchable and excluded from result statistics.
Sources cover different periods and may contain incomplete seasons or inconsistent
results. For matches with no supplied season, the calendar year is used unless
the fixture matches a season-labelled record in the combined view.

Standings award three points for a win and one for a draw, then order tied teams by
wins, goal difference, goals scored and name. They report positions calculated from
the available matches. Player attributes and club membership come from the FIFA
snapshot. Individual goalscorer events are unavailable.
