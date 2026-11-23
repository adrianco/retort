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

## Build and run

Requires a C11 compiler, Make, pkg-config, GLib and json-c. Python 3 runs the
integration tests.

```sh
make
make test
./soccer-mcp data/kaggle
```

The executable is an MCP server over stdio. Configure your MCP client to launch
it using absolute paths to the executable and the data directory. For clients
that use an `mcpServers` configuration object:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/absolute/path/to/soccer-mcp",
      "args": ["/absolute/path/to/data/kaggle"]
    }
  }
}
```

The client's LLM interprets questions and calls the tools. It can use the
returned JSON to format answers and refer to results from previous turns.
The server reads the bundled datasets at startup and runs locally.

## Query tools

| Tool | Example question |
| --- | --- |
| `search_matches` | When did Flamengo last play Corinthians, and what was the score? |
| `team_stats` | Compare Palmeiras and Santos head-to-head, or rank the best away records in 2019. |
| `standings` | Who won the 2019 Brasileirão? Which teams finished in the 2020 relegation places? |
| `search_players` | Which Brazilian forwards at Grêmio have the highest FIFA ratings? |
| `competition_stats` | Compare Palmeiras's league performance in 2018 and 2019. |
| `club_profile` | Show Grêmio's 2018 results alongside its FIFA roster snapshot. |
| `top_scorers` | Can the supplied data identify the top scorers of the 2019 Brasileirão? |
| `data_coverage` | How many records were loaded from each CSV? |

Use `stage: "knockout"` with Libertadores to get the bracket fixtures and
their stage labels. Use `stage: "final"` for Copa do Brasil finals.
Fixture and player lists include `total` and `next_offset` for pagination.
Win rates are percentages. Date filters are inclusive and accept
`YYYY-MM-DD` or `DD/MM/YYYY`.

## Data coverage and interpretation

Combined match queries merge rows by normalized clubs, competition, and
nearby dates or corresponding league rounds. Dedicated sources supply
rounds, stages, and season labels where available. The extended source
adds match statistics and fills missing scores. Use `source` with an
exact match CSV filename to query that file's rows and scores directly.
These views share normalized club names and inferred season and stage
labels. The combined view leaves Brasília FC vs CA Taguatinga in January 2016
unclassified because its Série A label conflicts with the league fixture
list. That row remains available under its original label in the source view.

Série A tables use match results and flag partial coverage. They sort by
points, wins, goal difference, and goals scored. Official tables can also
reflect administrative decisions and additional tiebreakers. The dataset
contains 377 of the 380 expected Série A fixtures for 2023.

Copa do Brasil finals use the final round of the dedicated Cup file through
2020. For 2021–2023 the server identifies the last two fixtures when they
feature the same finalists reversing home and away. Derby queries use a
curated list of traditional rivals.

FIFA ratings and roster memberships reflect the bundled snapshot. Searches
for Flamengo and São Paulo rosters or Gabriel Barbosa return empty results
from this snapshot. Match files have team-level goals, so individual
goalscorer rankings are unavailable.
