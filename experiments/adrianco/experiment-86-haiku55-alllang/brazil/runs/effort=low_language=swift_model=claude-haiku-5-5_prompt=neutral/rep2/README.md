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

## Swift MCP server

Implementation of the spec in `brazilian-soccer-mcp-guide.md`, written in Swift (no external dependencies).

- `Sources/SoccerCore` — CSV parsing, team-name normalisation, multi-source loader, query engine, MCP JSON-RPC layer, tool catalogue
- `Sources/BrazilianSoccerMCP` — stdio executable
- `Tests/SoccerCoreTests` — Given/When/Then XCTest specs against the real CSVs (`swift test`)

Build and run:

```sh
swift build -c release
.build/release/brazilian-soccer-mcp data/kaggle        # or set SOCCER_DATA_DIR
```

Tools exposed over MCP: `search_matches`, `team_record`, `head_to_head`, `standings`, `match_stats`, `biggest_wins`, `best_away_record`, `search_players`.

Example MCP client config:

```json
{ "mcpServers": { "brazilian-soccer": { "command": "/path/to/.build/release/brazilian-soccer-mcp", "args": ["/path/to/data/kaggle"] } } }
```

Notes on the data: Serie A seasons 2012–2019 appear in both the Brasileirão and historical files (and partly in the extended file), so each season is taken from one source. Copa do Brasil rows carry round numbers only, so "final" is inferred as round 8. Some seasons (e.g. 2021 in the cup file) are partial in the source data.
