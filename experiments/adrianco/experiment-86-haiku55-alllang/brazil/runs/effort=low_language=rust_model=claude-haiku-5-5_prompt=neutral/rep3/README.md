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

## Implementation (Rust)

An MCP server (JSON-RPC over stdio) that answers natural-language-friendly queries about Brazilian soccer from the CSV files in `data/kaggle/`.

```
cargo build --release
./target/release/brazilian_soccer_mcp [data/kaggle]   # or set SOCCER_DATA_DIR
cargo test
```

Layout:
- `src/normalize.rs` - team names (state suffixes, accents, aliases), dates, goals, competitions
- `src/data.rs` - loads the five match files and the FIFA file; de-duplicates fixtures that appear in several sources
- `src/query.rs` - match search, team records, head-to-head, standings (3/1/0 points), league statistics, player search
- `src/mcp.rs` - MCP tools: `search_matches`, `team_record`, `head_to_head`, `standings`, `league_stats`, `search_players`
- `tests/` - BDD-style scenarios (Given/When/Then comments inside `scenario_*` tests) over inline fixtures, plus a check that the real files load

Known data limits: the FIFA export is FIFA 19 and contains no Flamengo or other Brazilian-club-only rosters beyond what its Club column lists, so club filters for some clubs return nothing. Serie B/C results come only from `BR-Football-Dataset.csv`.
