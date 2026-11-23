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

## Build and run

From the repository root run `make` with a C++17 compiler, pkg-config, SQLite 3.33 or newer, and json-c development headers installed. Run `make test` for the Python 3 standard-library integration suite.

Configure your MCP client's stdio server command as the absolute path to `soccer-mcp`. Pass the absolute path to `data/kaggle` as its single argument when launching from another directory. The server loads all six local CSVs at startup.

Ask the connected LLM a question such as “Who won the 2019 Brasileirão?” The `query_soccer` tool publishes its SQLite schema and accepts a read-only query. For example:

```sql
SELECT team, played, points
FROM standings
WHERE competition = 'Serie A' AND season = 2019
ORDER BY points DESC, wins DESC, gd DESC, goals_for DESC
LIMIT 1
```

The result is Flamengo with 90 points from 38 games. Tool responses include column names, rows, and a truncation flag. Use a stable ordering with LIMIT and OFFSET to page through larger results.

## Coverage

`matches` prefers the dedicated competition files, uses the historical file for earlier Série A seasons, and supplements results from the extended statistics file. Overlapping cup fixtures are matched by competition, normalized teams and dates within one day. Spelling differences and rescheduled matches can affect reconciliation. The raw source tables expose stadiums, extended statistics and original names. Team normalization preserves distinctions such as Atlético-MG and Atlético-GO.

`performances` provides one row per team in each scored fixture. Standings use three points per win and one per draw. Check the number of games played before interpreting a partial season as final. The player table contains FIFA snapshot ratings and skills. Individual match goalscorers are unavailable.
