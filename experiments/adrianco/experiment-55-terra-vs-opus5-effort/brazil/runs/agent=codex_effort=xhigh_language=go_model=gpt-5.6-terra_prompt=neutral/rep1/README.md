# Brazilian Soccer MCP with spec and basic data sets

## Run the MCP server

The server is implemented in Go and communicates using JSON-RPC over standard
input/output, as required by MCP. It has no third-party dependencies.

```sh
go run .
```

Pass `-data-dir /path/to/kaggle` when the CSV files are not under
`data/kaggle`. Configure an MCP client to run the built binary (or `go run .`)
with its working directory set to this repository. Do not write logs to stdout:
that stream is reserved for protocol messages.

Available tools cover match search, team records, head-to-head comparisons,
FIFA player search, calculated standings and rankings, competition statistics,
largest wins, traditional derbies, and the competitions played by a team.
Names are accent-insensitive and normalize common state suffixes such as
`Flamengo-RJ` and long forms such as `Sport Club Corinthians Paulista`.

Run the checks with:

```sh
go test ./...
```

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
