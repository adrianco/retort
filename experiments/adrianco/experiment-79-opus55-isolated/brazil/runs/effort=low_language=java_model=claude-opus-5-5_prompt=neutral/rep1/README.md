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

## Implementation (Java)

A dependency-free Java 21 MCP server (stdio, newline-delimited JSON-RPC 2.0) in `src/main/java/br/soccer`.

```bash
mvn package                                        # builds and runs the tests
java -jar target/brazilian-soccer-mcp-1.0.0.jar    # reads data/kaggle, or pass a directory / set BR_SOCCER_DATA_DIR
```

MCP client configuration:

```json
{"mcpServers": {"brazilian-soccer": {"command": "java",
  "args": ["-jar", "target/brazilian-soccer-mcp-1.0.0.jar", "data/kaggle"]}}}
```

Tools: `search_matches`, `head_to_head`, `team_stats`, `standings`, `team_rankings`, `match_statistics`,
`biggest_wins`, `compare_seasons`, `derbies`, `knockout_stages`, `search_players`, `player_details`,
`players_by_club`, `club_profile`, `dataset_info`.

Notes on the data:
- Team names are normalized across files (state suffixes, accents, full names), and a fixture that
  appears in several files is merged into one match, so the three overlapping Brasileirão sources
  are not double counted.
- Rows without a final score (unplayed fixtures marked `NA`) are skipped.
- Standings are calculated from results (3 points per win); tribunal point deductions are not in the data.
- The FIFA dataset has no squads for some clubs (e.g. Flamengo, Palmeiras, Corinthians, São Paulo),
  so player queries for those clubs return nothing.
