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

## Implementation (Clojure MCP server)

An MCP server over stdio (newline-delimited JSON-RPC) that answers questions about Brazilian soccer from the CSV files in `data/kaggle/`.

- `src/brazil_soccer/teams.clj` — team/club name normalization (state suffixes, accents, variant spellings such as Atlético-MG / Atletico Mineiro), competition labels.
- `src/brazil_soccer/data.clj` — loads all six CSVs into one match table (duplicate fixtures across files are counted once) and the FIFA player table.
- `src/brazil_soccer/queries.clj` — match filtering, team records, head-to-head, standings (3 pts win / 1 draw), rankings, league summaries, player search, cross-file team profile.
- `src/brazil_soccer/tools.clj` — the nine MCP tools and the text they return to the model.
- `src/brazil_soccer/mcp.clj` — JSON-RPC handling (`initialize`, `tools/list`, `tools/call`, `ping`).
- `test/brazil_soccer/` — `clojure.test` specs written as Given/When/Then.

Requires the Clojure CLI and a JDK.

```sh
clojure -M:test                 # run all tests
clojure -M:run                  # start the MCP server on stdio
BRAZIL_SOCCER_DATA=/path clojure -M:run   # use a different data directory
```

Example client configuration:

```json
{ "mcpServers": { "brazilian-soccer": { "command": "clojure", "args": ["-M:run"], "cwd": "/path/to/repo" } } }
```

Notes on the data: the FIFA file is the 2019 edition, so it has no Flamengo or Palmeiras squads; Brasileirão data covers 2003–2023 (not every season appears in every file); "finals" for the Copa do Brasil are the highest round of each season, which is two legs.
