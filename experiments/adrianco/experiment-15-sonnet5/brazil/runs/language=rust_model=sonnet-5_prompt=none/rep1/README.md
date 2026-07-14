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

A Rust MCP server (stdio transport, via the [`rmcp`](https://github.com/modelcontextprotocol/rust-sdk) SDK) that loads all
six CSVs into memory at startup and exposes 12 tools for querying matches, teams, standings, and players. See `TASK.md` for
the full spec.

Team names are normalized (state-suffix stripped, accents/punctuation folded) so e.g. "Palmeiras", "Palmeiras-SP", and
"São Paulo" style variants join across files. A handful of base names collide across states in the real data (e.g.
"Atletico" is Atletico-MG/GO/PR/...); these are disambiguated automatically using the state codes embedded in the
Brasileirao/Cup/historical datasets so aggregate stats (standings, records) never merge distinct clubs.

Build and run:

```
cargo build --release
./target/release/brazilian-soccer-mcp   # reads data/kaggle relative to the cwd by default
```

Test:

```
cargo test
```

Tools: `search_matches`, `compare_teams`, `team_record`, `standings`, `team_leaderboard`, `biggest_wins`, `average_stats`,
`derby_matches`, `team_competitions`, `search_players`, `brazilian_club_squads`, `list_datasets`.
