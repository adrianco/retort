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

## Implementation (C++17)

A dependency-free MCP server (`brazilian_soccer_mcp`) that loads the six CSV files into
memory and exposes them as tools over newline-delimited JSON-RPC 2.0 on stdio.

```bash
cmake -S . -B build && cmake --build build
ctest --test-dir build --output-on-failure      # or ./build/soccer_tests for the BDD log
./build/brazilian_soccer_mcp                    # MCP server on stdio
./build/brazilian_soccer_mcp --call standings '{"season": 2019}'   # one-off tool call
```

The data directory is `--data DIR`, else `$BRAZILIAN_SOCCER_DATA`, else `./data/kaggle`,
else the source tree the binary was built from. MCP client configuration:

```json
{"mcpServers": {"brazilian-soccer": {"command": "/path/to/build/brazilian_soccer_mcp"}}}
```

| Tool | Answers |
|------|---------|
| `search_matches` | matches by team / opponent / venue / competition / season / dates / stage |
| `head_to_head` | two-team comparison |
| `team_stats` | W/D/L, goals, win rate, by competition and by season |
| `standings` | league table from results (champion, relegation); cup / Libertadores bracket |
| `team_rankings` | best home / away record, most goals, ... |
| `biggest_wins`, `competition_stats`, `compare_seasons`, `derbies` | statistical analysis |
| `search_players`, `player_details`, `club_player_summary` | FIFA player data |
| `team_profile` | cross-file: match history + FIFA squad + rivals |
| `list_teams`, `dataset_info` | discovery |

Layout: `src/soccer.*` (loading, normalization, queries), `src/mcp_server.*` (tools and
protocol), `src/json.hpp` (JSON), `src/main.cpp`, `tests/test_soccer.cpp` (Given/When/Then
scenarios against the real data).

Data handling notes:
- Team names are normalized across files (state suffixes, accents, club-type words,
  alternate names such as Atlético-PR / Athletico Paranaense); clubs that share a name in
  different states (Atlético-MG / Atlético-GO, Flamengo / Flamengo-PI) stay separate.
- A match listed in several files is merged into one (same competition and teams, dates
  within two days), so the 23,954 source rows become 16,756 unique matches.
- Fixtures without a score are skipped, as are a few January/February rows that
  BR-Football labels as league matches. The `Mandante_UF`/`Visitante_UF` columns of
  `novo_campeonato_brasileiro.csv` are ignored because they are inconsistent.
- Standings use 3/1/0 points only; tribunal point deductions are not in the data.
- The data has no goal scorers, and the FIFA file has no Flamengo, Corinthians,
  Palmeiras or São Paulo squads; the tools say so rather than guess.
