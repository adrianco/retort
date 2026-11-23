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

On macOS with Apple Clang and Foundation, run `make`. Run `make test` with
Python 3 to exercise the Objective-C server over its stdio connection.

Register the absolute path to the binary as a stdio MCP server in your client.
For clients that use an `mcpServers` JSON configuration:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/absolute/path/to/soccer-mcp"
    }
  }
}
```

The server reads `data/kaggle` beside the executable. Pass
`--data-dir /absolute/path/to/data/kaggle` as two arguments to override that
path. The MCP client supplies the language model that translates natural
language questions into tool calls. Server startup and queries run locally.

| Tool | Example question | Example arguments |
| --- | --- | --- |
| `find_matches` | When did Flamengo last play Corinthians, and what was the score? | `{"team":"Flamengo","opponent":"Corinthians","limit":1}` |
| `find_matches` | Show the 2018 Libertadores knockout bracket | `{"competition":"Libertadores","season":2018,"stage":"knockout","limit":50}` |
| `team_statistics` | What was Corinthians' home record in 2022 Série A? | `{"team":"Corinthians","side":"home","competition":"Série A","season":2022}` |
| `team_statistics` | Who had the best away win rate in 2019 Série A? | `{"competition":"Série A","season":2019,"side":"away","group_by":"team","sort":"win_rate"}` |
| `competition_standings` | Who finished first in 2019? | `{"season":2019}` |
| `search_players` | Who are the highest-rated Brazilian players in the FIFA data? | `{"nationality":"Brazil","limit":5}` |
| `club_profile` | Show Santos' FIFA roster and 2018 record by competition | `{"team":"Santos FC","season":2018}` |
| `dataset_coverage` | What sources and data are available? | `{}` |

List results default to 25 rows. Pass the returned `next_offset` as the next
call's `offset` with the same filters. Team filters use accent-insensitive
identities and aliases. Dates accept ISO or Brazilian notation.

Aggregate match queries count reconciled fixtures. Série A fixtures use
competition, season and the home/away pairing as their identity. Other
competitions use dates and the home/away pairing, with a one-day tolerance
when matching the extended file. The detailed CSVs supply season and stage
labels when available, and the extended file adds match statistics and fills
some missing scores. Pass a CSV filename as `source` to inspect its rows.
Goals, win rates and standings use fixtures with both scores recorded.
Standings are calculated from supplied results, with data coverage and the
ranking method displayed in the response.

Player and club results reflect the FIFA snapshot. For example, the snapshot
has a Santos roster and returns zero rows for Flamengo. Individual match
scorers cannot be determined from the team-level scores. The 2023 Série A
table contains 377 of the expected 380 completed matches and is provisional.
