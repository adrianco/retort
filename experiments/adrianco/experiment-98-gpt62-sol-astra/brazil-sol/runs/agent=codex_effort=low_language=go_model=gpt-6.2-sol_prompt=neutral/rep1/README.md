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

Requires Go 1.22 or later. Build and test from the repository root.

```sh
go build -o brazilian-soccer-mcp .
go test ./...
./brazilian-soccer-mcp -data-dir data/kaggle
```

Configure an LLM-enabled MCP client to start the executable over stdio. Use
absolute paths so the client can launch it from any working directory.

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/absolute/path/to/brazilian-soccer-mcp",
      "args": ["-data-dir", "/absolute/path/to/data/kaggle"]
    }
  }
}
```

The client translates natural-language questions into tool calls. The server
loads all six CSVs at startup and answers from memory without external services.
It uses newline-delimited JSON-RPC on stdin and stdout, with diagnostics on stderr.

| MCP tool | Example question | Example arguments |
| --- | --- | --- |
| `search_matches` | When did Flamengo last play Fluminense? | `{"team":"Flamengo","opponent":"Fluminense","status":"played","limit":1}` |
| `search_matches` | Show the 2018 Libertadores knockout bracket. | `{"competition":"Libertadores","season":2018,"stage":"knockout"}` |
| `team_stats` | What was Corinthians' 2022 Série A home record? | `{"team":"Corinthians","competition":"Serie A","season":2022,"side":"home"}` |
| `search_players` | Who are the highest-rated Brazilian players? | `{"nationality":"Brazil","limit":10}` |
| `competition_standings` | Who won the 2019 Brasileirão? | `{"season":2019}` |
| `analyze_matches` | Compare the 2018 and 2019 Série A seasons. | `{"competition":"Serie A","season_from":2018,"season_to":2019}` |
| `club_profile` | Show Grêmio's record and FIFA roster. | `{"team":"Grêmio","season":2019}` |

Tool results are JSON in MCP text content. Paginated results include a total
and a `next_offset` when more records are available. Match date bounds are
inclusive and accept ISO and Brazilian date formats. Season filters use the
competition edition year.

### Data interpretation

- Default match queries reconcile overlapping sources to count a fixture once.
  Use a match tool's `source` argument with a CSV filename to inspect that
  file's records. The reconciliation prioritizes dedicated competition files
  and fills available stadium and match statistics from the other files.
- Fixtures with missing scores remain searchable. Statistics use scored
  fixtures. Série A and Série B standings use recorded results and flag
  incomplete seasons, including Série A 2023. Point deductions and individual
  goalscorer records are unavailable in the CSVs.
- FIFA names, clubs, positions and ratings reflect the included snapshot.
  Some requested players or club rosters may yield empty results. A club
  profile joins that snapshot to match history using normalized club names.
