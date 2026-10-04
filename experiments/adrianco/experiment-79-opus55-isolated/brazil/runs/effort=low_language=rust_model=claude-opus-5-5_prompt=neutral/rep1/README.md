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

A dependency-light MCP server (`csv` + `serde_json` only) that loads the six CSV files into
memory and serves tools over JSON-RPC 2.0 on stdio.

```bash
cargo build --release
cargo test                                   # unit tests + BDD-style scenarios in tests/bdd.rs
./target/release/brazilian-soccer-mcp        # MCP server on stdio
./target/release/brazilian-soccer-mcp tools  # list tools
./target/release/brazilian-soccer-mcp call standings '{"season": 2019}'   # one-off query
```

The data directory is `--data-dir DIR`, else `$BR_SOCCER_DATA_DIR`, else `./data/kaggle`.

MCP client configuration:

```json
{"mcpServers": {"brazilian-soccer": {"command": "/path/to/target/release/brazilian-soccer-mcp",
                                     "args": ["--data-dir", "/path/to/data/kaggle"]}}}
```

### Tools

| Tool | Answers |
|------|---------|
| `search_matches` | matches by team, opponent, venue, competition, season, date range, stage, source file |
| `head_to_head` | record and match list between two teams |
| `team_stats` | W/D/L, goals, win rate, per-competition breakdown |
| `team_profile` | cross-file view: competitions played + FIFA squad |
| `standings` | league table computed from results, champion, relegation zone |
| `competition_summary` | season totals, champion, cup brackets by stage |
| `league_stats` | goals per match, home/draw/away rates |
| `biggest_wins` | largest winning margins |
| `team_rankings` | best home/away record, most goals, points, ... |
| `compare_seasons` | two seasons side by side |
| `derbies` | matches between traditional rivals |
| `search_players`, `player_details`, `brazilian_clubs_players` | FIFA player data |
| `list_teams`, `dataset_info` | discovery |

### Layout

- `src/normalize.rs` - team-name canonicalisation (state suffixes, accents, aliases), date parsing, derby list
- `src/data.rs` - CSV loading and de-duplication of overlapping files
- `src/queries.rs` - query logic and answer formatting
- `src/mcp.rs` - MCP protocol and tool definitions
- `tests/bdd.rs` - Given/When/Then scenarios against the real data

### Data caveats

- Three files overlap on Série A and two on Copa do Brasil. Each competition season is served by a
  single file so nothing is double counted; pass `source` to query a specific file.
- `BR-Football-Dataset.csv` has no season column, so its seasons are calendar years. Série A 2022
  and 2023 come from this file and are one and three matches short, so no champion is labelled.
- Standings use 3/1/0 points with wins, goal difference, goals scored as tie-breakers; points
  deductions and the official tie-break rules are not in the data.
- The FIFA file does not license several Brazilian clubs (Flamengo, Palmeiras, Corinthians,
  São Paulo...), and uses fictitious names for players of some licensed Brazilian clubs.
- There is no goalscorer data, so "top scorers" cannot be answered for players (only for teams).
