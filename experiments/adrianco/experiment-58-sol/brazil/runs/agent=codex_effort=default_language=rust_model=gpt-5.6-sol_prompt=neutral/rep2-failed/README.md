# Brazilian Soccer MCP with spec and basic data sets

A dependency-light Rust MCP server that loads all six supplied CSV datasets into a normalized,
deduplicated in-memory soccer graph. It exposes completed-match lookup, team and head-to-head
records, FIFA player search, league standings/competition analysis, and a convenience natural
language question router.

## Build and test

```sh
cargo build --release
cargo test
```

The default data directory is `data/kaggle`. Override it with
`BRAZILIAN_SOCCER_DATA_DIR=/path/to/csvs`. The server uses MCP's JSON-RPC-over-stdio transport;
diagnostics go to stderr and stdout contains protocol messages only.

Example client configuration:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/absolute/path/to/target/release/brazilian-soccer-mcp",
      "env": { "BRAZILIAN_SOCCER_DATA_DIR": "/absolute/path/to/data/kaggle" }
    }
  }
}
```

## MCP tools

- `search_matches`: team/opponent, home/away, competition, season, inclusive dates, stage/round,
  sorting, and pagination.
- `get_team_record`: W/D/L, points, goals, goal difference, and win rate, including head-to-head.
- `search_players`: FIFA snapshot filters for name, nationality, club, position, rating, and age.
- `analyze_competition`: standings, summaries, rankings, and biggest wins. Standings intentionally
  reject knockout competitions where a league table would be misleading.
- `ask_soccer`: maps common natural-language questions to those deterministic operations.

Incomplete scheduled/cancelled rows are accounted for but excluded from result statistics. Exact
cross-source duplicates are merged while retaining every source filename as provenance. Dedicated
Brasileirão rows are authoritative for league tables in covered seasons, preventing overlapping
historical and extended datasets from inflating points.

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
