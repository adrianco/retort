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

## Running the MCP server

This repository now contains a standalone Go MCP server. It uses newline-delimited JSON-RPC 2.0 over stdio, so standard MCP clients can start it with:

```sh
go run . --data-dir data/kaggle
```

`BRAZILIAN_SOCCER_DATA_DIR` is an alternative to `--data-dir` when the CSV files live elsewhere. The server writes only MCP messages to stdout; load errors and diagnostics go to stderr.

The implementation has no external Go dependencies. At startup it loads all six supplied CSV files into an immutable, in-memory graph/index. Typical interactive requests are served from memory rather than scanning CSV files repeatedly.

## MCP tools

| Tool | Purpose |
| --- | --- |
| `search_matches` | Find matches by team, opponent, home/away side, competition, season, date range, round, stage, or source. |
| `get_team_stats` | Calculate played-match W/D/L, goals, and win rate for a team, including home or away splits. |
| `compare_teams` | Calculate head-to-head results and list the relevant matches. |
| `search_players` | Search the offline FIFA snapshot by name, nationality, club, position, age, rating range, and sort order; retained skill attributes are included in each player result. |
| `get_standings` | Calculate a Brasileirão season table from completed matches. |
| `get_competition_stats` | Calculate goals-per-match, home advantage, best home/away records, biggest wins, or top-scoring teams. |
| `list_team_competitions` | List the competitions in which a team appears. |
| `list_derbies` | List matches for a small documented set of traditional rivalries. |
| `ask_brazilian_soccer` | Convenience support for common natural-language question patterns. |
| `list_data_sources` | Report the six local source files and their load counts. |

All tool calls return both readable MCP text content and `structuredContent` for clients that want JSON. Match rows include a stable `source:row` ID, source name, score status, and any available extended statistics. Aggregate responses include their source scope/data sources and the number of unknown fixtures excluded. Useful match filters include `source` (`canonical`, `all`, `brasileirao`, `brazilian_cup`, `libertadores`, `extended_statistics`, or `historical_brasileirao`), `season`, `date_from`, `date_to`, `limit`, and `offset`.

## Data semantics

- Team search is case- and accent-insensitive and handles common aliases and state suffixes such as `São Paulo-SP`, `Sao Paulo FC`, and `Palmeiras-SP`. State-distinct teams such as Atlético-MG/Atlético-GO, Flamengo-RJ/Flamengo-PI, and Santos-SP/Santos-AP remain distinct; explicit qualifiers are retained in returned rows when needed to avoid ambiguity.
- `NA`, `-`, and blank score values are represented as `scoreKnown: false` with `homeGoals`/`awayGoals: null`; they can be found by match search but are excluded from records, standings, and aggregates.
- Match datasets overlap. The default `canonical` source scope chooses historical Brasileirão for 2003–2019, the dedicated Brasileirão file for 2020–2022, dedicated Copa/Libertadores files, and the extended source for 2023 Serie A. Use `source: "all"` only to inspect every raw match; aggregate tools reject it so overlapping rows cannot be silently double-counted.
- The dedicated 2022 Brasileirão source contains unknown late fixtures. Team/competition aggregates report `unknownFixturesExcluded` so a partial source is never presented as complete. Standings are deliberately limited to league competition; use final/stage match search for Copa do Brasil and Libertadores.
- `BR-Football-Dataset.csv` has no official season column. A `season` filter on that source is transparently interpreted as calendar year; source-backed season fields remain separate from match date where present.
- Extended-match output preserves kickoff, corners, attacks, shots, result difference/outcome fields, and nullable blanks. FIFA player results retain common skill ratings such as finishing, dribbling, passing, pace-related attributes, and tackling.
- The FIFA file is an offline historical snapshot. It has no scorer/event data, so top-scorer questions cannot be calculated. Copa/Libertadores rows also do not contain enough tie metadata to reconstruct a reliable knockout bracket.

## Verification

```sh
go test ./...
go vet ./...
go build ./...
```

The BDD-style tests cover all six CSV loaders, UTF-8/BOM and date handling, state-aware normalization, unknown scores, source-aware aggregates, 2019 Brasileirão standings, player attributes, Cup/Libertadores finals, extended statistics, MCP validation/stdio behavior, and more than 20 natural-language question paths.
