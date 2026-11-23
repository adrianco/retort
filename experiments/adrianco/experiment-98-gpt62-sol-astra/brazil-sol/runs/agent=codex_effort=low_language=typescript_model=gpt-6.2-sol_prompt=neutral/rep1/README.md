# Brazilian Soccer MCP with spec and basic data sets

## Specification
brazilian-soccer-mcp-guide.md

## Run the MCP server

Use Node.js 20 or later.

```sh
npm ci
npm run build
npm test
```

Register the following stdio server in a tool-capable MCP host. Replace the example path with the absolute path to this directory. The host translates natural-language questions into tool calls and formats the results for the user. The server reads the bundled CSV files at startup and requires no API keys.

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "node",
      "args": ["/absolute/path/to/project/dist/index.js"]
    }
  }
}
```

### Example questions

| Question | MCP tool and arguments |
|---|---|
| When did Flamengo last play Corinthians? | `search_matches` with `{"team":"Flamengo","opponent":"Corinthians","limit":1}` |
| What was Corinthians’ Série A home record in 2022? | `team_stats` with `{"team":"Corinthians","competition":"Série A","season":2022,"venue":"home"}` |
| Compare Palmeiras and Santos head-to-head. | `head_to_head` with `{"team":"Palmeiras","opponent":"Santos"}` |
| Who are the highest-rated Brazilian players? | `search_players` with `{"nationality":"Brazil","limit":5}` |
| Who won the 2019 Brasileirão? | `standings` with `{"competition":"Brasileirão","season":2019}` |
| Show the 2018 Copa Libertadores bracket. | `competition_results` with `{"competition":"Libertadores","season":2018,"stage":"knockout"}` |
| Compare scoring in the 2018 and 2019 seasons. | `match_statistics` with `{"competition":"Série A","seasons":[2018,2019]}` |
| Show Grêmio’s 2023 results and its FIFA roster. | `club_profile` with `{"team":"Grêmio","season":2023}` |

Call `data_coverage` for dataset counts, source keys and seasons. Pass `source` to query one match CSV directly. Paged results include `total` and `nextOffset`. Win rates are fractions between zero and one. Date ranges are inclusive and accept ISO and Brazilian dates.

### Data interpretation

- The default match view reconciles overlapping fixtures across sources. Where a dedicated Série A file covers a season, its fixture list takes precedence and the extended feed supplies matching scores and statistics. Direct source queries expose the original fixture rows with normalized fields.
- Standings use recorded team scores. The 2023 Série A file contains 377 of the expected 380 fixtures, so its table is provisional. Official administrative adjustments, individual scorers and penalty shootout details are unavailable.
- Copa do Brasil stages use the season’s round numbering where available. Finals in the extended feed are identified from the final pair of fixtures in each of the 2021–2023 seasons.
- FIFA ratings, ages and clubs come from the supplied snapshot. Some sample lookups, including Gabriel Barbosa and Flamengo’s roster, have no matching records. A club profile associates the snapshot with the club’s results without implying that those players appeared in those matches.

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
