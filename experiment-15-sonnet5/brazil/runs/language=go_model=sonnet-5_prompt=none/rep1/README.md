# Brazilian Soccer MCP with spec and basic data sets

## Specification
brazilian-soccer-mcp-guide.md (see also TASK.md)

## Implementation

A Go MCP server (`go 1.26`, stdlib only, no third-party dependencies) implementing the
spec's required capabilities. All source files are at the repository root:

- `loaders.go`, `load.go`, `parse.go` — CSV parsing for all six datasets into a common
  `Match`/`Player` model, with flexible date/number parsing and header-based column lookup
  (robust to quoting differences across files).
- `normalize.go`, `store.go` — team-name normalization and the in-memory `Store`/index.
  Team names are folded to a base key (accents/case/punctuation stripped) plus an optional
  state/country suffix (e.g. `"Palmeiras-SP"` → base `palmeiras`, state `SP`). Because the
  data genuinely contains distinct clubs sharing a short name in different states (e.g.
  América-MG vs. América-RN, Botafogo-RJ vs. Botafogo-PB vs. Botafogo-SP), a plain-name
  query resolves to *all* matching state variants rather than silently merging them, and the
  tool responses report exactly which variants were included.
- `queries.go` — the query/aggregation logic behind each tool (match search, head-to-head,
  team records, standings, stats, player search).
- `mcp.go` — a minimal MCP server over the stdio transport (newline-delimited JSON-RPC 2.0):
  `initialize`, `tools/list`, `tools/call`, `ping`.
- `tools.go` — registers six tools with their JSON Schema input contracts:
  `search_matches`, `head_to_head`, `team_record`, `standings`, `stats_overview`,
  `search_players`.
- `main.go` — loads the CSVs and starts the stdio server. Data directory defaults to
  `./data/kaggle`, overridable with `-data-dir` or `BRAZIL_MCP_DATA_DIR`.

Brasileirão data is deduplicated across `Brasileirao_Matches.csv` (2012+) and
`novo_campeonato_brasileiro.csv` (pre-2012) so seasons aren't double-counted; the extended
per-match stats in `BR-Football-Dataset.csv` (corners/shots/attacks) are kept under distinct
`"... (Extended Stats)"` competition tags for the same reason, while remaining fully
searchable and cross-referenced against player data.

### Build & test

```
go build ./...
go test ./...
```

### Run

```
go run . -data-dir data/kaggle
```

The server speaks MCP over stdio, so it's meant to be launched by an MCP client (e.g. as a
`command`/`args` entry in a client's server config) rather than run interactively.

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
