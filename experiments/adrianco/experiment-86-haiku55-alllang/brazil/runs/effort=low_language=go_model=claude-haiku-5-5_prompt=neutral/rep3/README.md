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

## Implementation

A Go MCP server (standard library only) that answers natural-language questions
about Brazilian soccer through seven tools. Spec: `brazilian-soccer-mcp-guide.md` / `TASK.md`.

Build and test:

```sh
go build -o brazilian-soccer-mcp .
go test ./...
```

Run (speaks MCP JSON-RPC over stdio; logs go to stderr):

```sh
./brazilian-soccer-mcp -data data/kaggle
```

Example client config:

```json
{ "mcpServers": { "brazilian-soccer": { "command": "/path/to/brazilian-soccer-mcp", "args": ["-data", "/path/to/data/kaggle"] } } }
```

Tools: `search_matches`, `team_record`, `head_to_head`, `standings`, `league_stats`,
`biggest_wins`, `search_players`.

Design notes:

- **Team names** are normalized (accents, noise words like "Sport Club"/"Esporte Clube",
  parentheticals, state suffixes in `-SP`, ` - MG` or ` RJ` form). A query matches a
  dataset club when every query word appears in the club name and any states agree.
  A bare name such as "Atletico" therefore matches every Atletico with no state given.
- **Dates** accept ISO, ISO with time, and `DD/MM/YYYY`.
- **Overlapping files**: the six files overlap (the 2003–2019 file and the BR-Football
  extract repeat Brasileirão seasons that the curated files already cover, often under
  different club spellings). Files load in priority order and a later file only supplies
  competition/season pairs no earlier file has, so no season is counted twice.
- **Unplayed fixtures** (`NA` scores in the 2022 file) are skipped.
- **Player/club cross-file query**: `brazilian_clubs_only` keeps players whose club
  appears in the Brasileirão match data.

Tests are written as Given/When/Then scenarios (nested `t.Run`) against the real CSVs.
