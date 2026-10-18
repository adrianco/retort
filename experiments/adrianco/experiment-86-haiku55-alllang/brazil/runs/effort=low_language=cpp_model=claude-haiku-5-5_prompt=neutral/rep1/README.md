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

## C++ MCP Server

A Model Context Protocol server (stdio, JSON-RPC 2.0) that answers match, team, player,
competition and statistics queries over the datasets above. No third-party dependencies.

Build and test (CMake 3.16+, C++17 compiler):

    cmake -S . -B build
    cmake --build build
    ctest --test-dir build        # or ./build/soccer_tests

Run the server (data directory defaults to data/kaggle; override with an argument or $SOCCER_DATA_DIR):

    ./build/brazilian_soccer_mcp [data_dir]

Tools exposed: `find_matches`, `team_record`, `head_to_head`, `standings`, `search_players`,
`goal_statistics`. Example MCP client config:

    {"mcpServers": {"brazilian-soccer": {"command": "/path/to/build/brazilian_soccer_mcp"}}}

Notes:
- Brasileirão Série A matches appear in three files and are merged by season, competition,
  teams and score. Some sources record a fixture a day apart, so dates are not part of the key.
- Team names are normalized: state suffixes (`-SP`, ` RJ`), parentheticals, accents, and common
  full names (e.g. "Sport Club Corinthians Paulista") map to one key. The three Atlético clubs are
  told apart by state.
- FIFA 2019 ratings contain no São Paulo club, so player queries for it return nothing.
