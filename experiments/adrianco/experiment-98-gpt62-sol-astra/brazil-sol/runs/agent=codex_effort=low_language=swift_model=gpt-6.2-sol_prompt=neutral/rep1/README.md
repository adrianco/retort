# Brazilian Soccer MCP Server

A Swift Package Manager executable for querying the six bundled Brazilian soccer and FIFA datasets. The server builds an in-memory graph linking teams, fixtures, competitions, seasons, and FIFA 19 players. An MCP client with an LLM translates natural-language questions into tool calls and uses conversation context for follow-up questions.

## Build and connect

From the project root with Swift 5.9 or later:

```sh
swift build
swift test
```

Configure your MCP client to launch `.build/debug/soccer-mcp` as a stdio server. Use absolute paths if the client starts it from another working directory. The server uses newline-delimited JSON-RPC over stdin and stdout. [MCP stdio transport](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports)

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/absolute/path/to/repo/.build/debug/soccer-mcp",
      "args": ["--data-dir", "/absolute/path/to/repo/data/kaggle"]
    }
  }
}
```

The default data directory is `data/kaggle` relative to the working directory. No credentials or external runtime services are needed by the server.

## Tools

| Tool | Example question | Example arguments |
| --- | --- | --- |
| `search_matches` | When did Flamengo last play Corinthians? | `{"team":"Flamengo","opponent":"Corinthians","limit":1}` |
| `search_matches` | Show the 2023 Copa do Brasil finals. | `{"competition":"Copa do Brasil","season":2023,"stage":"final"}` |
| `team_record` | What was Corinthians' 2022 Série A home record? | `{"team":"Corinthians","season":2022,"competition":"Série A","venue":"home"}` |
| `team_record` | Compare Palmeiras and Santos head-to-head. | `{"team":"Palmeiras","opponent":"Santos"}` |
| `team_record` | Show Grêmio's 2018 results and FIFA roster. | `{"team":"Grêmio","season":2018,"includePlayers":true}` |
| `search_players` | Who were the top-rated Brazilian players at domestic clubs? | `{"nationality":"Brazil","domesticClubsOnly":true,"limit":10}` |
| `competition_season` | Who won the 2019 Brasileirão? | `{"competition":"Série A","season":2019,"mode":"champion"}` |
| `competition_season` | Show the 2018 Libertadores bracket. | `{"competition":"Libertadores","season":2018,"mode":"bracket"}` |
| `analyze_matches` | Compare Série A scoring in 2018 and 2019. | `{"competition":"Série A","seasons":[2018,2019]}` |
| `analyze_matches` | Who had the best 2022 Série A away record? | `{"competition":"Série A","season":2022,"mode":"rank_teams","rankVenue":"away"}` |
| `data_coverage` | What data can I query? | `{}` |

For paginated tools, pass the returned `nextOffset` as `offset` to request the next page. Dates accept `YYYY-MM-DD` and `DD/MM/YYYY`. Returned win rates are fractions from 0 to 1.

## Interpreting the data

- Match searches and aggregates use merged fixtures by default. Set `source` to a specific match CSV filename to see that source's imported rows, including omissions or discrepancies in its scores and labels. Match results retain source filenames. Dates and times use the source conventions. For some matches, sources differ by a calendar day.
- Match outcomes, standings, champions and relegation places are calculated from recorded scores. Standings use points, wins, goal difference and goals scored. Administrative points adjustments, later tiebreakers, and shootout totals are unavailable. Partial seasons are flagged. In particular the 2023 Série A feed has 377 fixtures, and its calculated points leader can differ from the official champion.
- Copa do Brasil rounds come from the dedicated cup file where available. For seasons covered only by the extended feed, finals are inferred from the last pair of reciprocal fixtures. A few contradictory rows are reconciled in the merged view, including the 2019 Vila Nova run and the 2021 CRB–Cuiabá fixture. [Juventude match preview](https://www.juventude.com.br/blog/ju-tera-sequencia-de-jogos-importante-nas-proximas-duas-semanas), [CBF fixture record](https://www.cbf.com.br/futebol-brasileiro/jogos/copa-do-brasil/profissional/2021/crb-x-cuiaba/817756?view=escalacao)
- FIFA 19 ratings and club affiliations reflect the bundled snapshot. Searches for Gabriel Barbosa and the Flamengo or São Paulo rosters return no rows in that snapshot. The match files have team scores. They contain no goal-scorer events from which to calculate player scoring totals.

See [TASK.md](TASK.md) for the scope and original requirements.

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
