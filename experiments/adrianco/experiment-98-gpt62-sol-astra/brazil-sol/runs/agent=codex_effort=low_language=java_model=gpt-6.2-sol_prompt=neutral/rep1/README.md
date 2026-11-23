# Brazilian Soccer MCP with spec and basic data sets

## Specification
brazilian-soccer-mcp-guide.md

## Run the MCP server

Requires Java 17 or newer and Maven. From the repository root:

```sh
mvn clean verify
java -jar target/brazilian-soccer-mcp.jar data/kaggle
```

The process reads and writes newline-delimited JSON-RPC over UTF-8 stdio. Configure an MCP client connected to an LLM with the following entry, using absolute paths if it launches from a different directory. The client translates conversational questions into tool calls. [MCP stdio transport](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports)

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "java",
      "args": [
        "-jar",
        "/path/to/repository/target/brazilian-soccer-mcp.jar",
        "/path/to/repository/data/kaggle"
      ]
    }
  }
}
```

### Tools

| Tool | Example arguments |
| --- | --- |
| `search_matches` | `{"team":"Flamengo","opponent":"Corinthians","limit":1}` for the latest fixture |
| `search_matches` | `{"competition":"Libertadores","season":2018,"limit":200}` for results by bracket stage |
| `head_to_head` | `{"team":"Palmeiras","opponent":"Santos"}` |
| `team_record` | `{"team":"Corinthians","season":2022,"competition":"Série A"}` |
| `search_players` | `{"nationality":"Brazil","position":"forward","limit":5}` |
| `club_profile` | `{"team":"Grêmio","season":2019,"competition":"Série A"}` for league results and the FIFA roster |
| `standings` | `{"season":2020}` for the calculated Série A table and bottom positions |
| `team_rankings` | `{"season":2019,"competition":"Série A","venue":"away","minimumMatches":10}` |
| `match_statistics` | `{"mode":"bySeason","competition":"Série A","fromSeason":2018,"toSeason":2019}` |

Use the `nextOffset` value from a paginated response to retrieve the next page. Match results show source filenames, and the `source` filter queries a single match CSV. The merged view links fixtures and FIFA rosters through canonical club identities and combines overlapping fixture records. For Série A, the standings tool uses dedicated league rows where available and fills missing scores from matching records.

### Data coverage

- Results and schedules reflect the supplied files. A fixture with a missing score is excluded from win and goal calculations.
- Calculated standings use recorded scores and exclude administrative adjustments. The 2023 Série A file has 377 of 380 fixtures, so the table is marked incomplete. Rankings and team records reflect the available matches.
- FIFA clubs and attributes reflect the historical snapshot. The supplied FIFA file has no records under Flamengo or Gabriel Barbosa. The match CSVs contain team scores and lack individual goalscorer events.
- Cup final labels are inferred from the two legs of the final numbered round in the dedicated cup data, or the final pair of reversed fixtures in the extended cup data from 2021 onward. Penalty shootout scores are unavailable.

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
