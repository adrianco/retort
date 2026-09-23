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

## C++ MCP server

Build and test (C++17, CMake, no external dependencies):

```
cmake -S . -B build && cmake --build build
./build/soccer_tests          # or: (cd build && ctest)
./build/brazilian_soccer_mcp data/kaggle   # MCP server, JSON-RPC over stdio
```

Tools: `search_matches`, `head_to_head`, `team_stats`, `standings` (league table or knockout bracket),
`search_players`, `brazilian_players_summary`, `competition_stats`, `biggest_wins`, `team_rankings`,
`team_competitions`, `derbies`, `team_profile`, `compare_seasons`, `dataset_info`.

Source layout: `src/json.*` (JSON), `src/text.cpp` (CSV, dates, team-name normalization),
`src/loader.cpp` (loading + de-duplication of overlapping sources), `src/queries.cpp` (queries/answers),
`src/mcp.*` (MCP protocol), `src/main.cpp` (stdio server), `tests/test_main.cpp` (BDD scenarios).
