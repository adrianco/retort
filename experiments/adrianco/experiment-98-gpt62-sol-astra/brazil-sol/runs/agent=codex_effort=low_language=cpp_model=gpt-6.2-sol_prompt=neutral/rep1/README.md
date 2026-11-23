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

## Build and test

The server requires a C++20 compiler, CMake 3.20 or newer, Boost.JSON 1.75 or
newer, pkg-config, and utf8proc. The test runner also requires Python 3.

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
ctest --test-dir build --output-on-failure
```

Configure with `-DBUILD_TESTING=OFF` for a server-only build.

## Connect an MCP client

Configure the LLM host to launch the executable over stdio. Use an absolute
path to the executable. The server defaults to this checkout's `data/kaggle`
directory. Pass a different directory as the sole argument when needed.

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/absolute/path/to/build/soccer_mcp",
      "args": ["/absolute/path/to/data/kaggle"]
    }
  }
}
```

The host translates questions into tool arguments and can use results from
earlier turns to answer follow-ups such as “What was the score?” The server
returns structured JSON and mirrors it in MCP text content. The server works
offline and uses the [MCP stdio transport](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports).

| Example questions | Tool |
| --- | --- |
| Show Flamengo vs. Fluminense. When did Flamengo last play Corinthians, and what was the score? Show Palmeiras fixtures in 2023. Show Copa do Brasil finals. Find derbies from 2023. | `search_matches` |
| What was Corinthians' home record in 2022? What competitions has Palmeiras played in? | `team_stats` |
| Compare Palmeiras and Santos. What's the Fla-Flu head-to-head record? | `head_to_head` |
| Who are the highest-rated Brazilians? Find Neymar. Which players does the FIFA snapshot list for Flamengo? Which forwards are listed at São Paulo FC? Which domestic clubs have the most Brazilian players? | `search_players` |
| Show Grêmio's match history and FIFA roster. | `team_profile` |
| Who tops the calculated 2019 table? Which teams finish in the 2020 relegation positions? Show the 2018 Libertadores bracket. Show results in the last round of Série A 2022. | `competition_data` |
| How many goals per match in Série A? Who scored the most team goals in Série A 2023? Who had the best away record? Show the biggest wins. Compare the 2018 and 2019 seasons. | `analyze_matches` |

For paginated results, pass the returned `next_offset` as `offset` on the
next call with the same filters. Use `status: "played"` for recent results
and `status: "unscored"` for fixtures without a recorded score.

## Dataset interpretation

- Fixtures link team nodes and keep contributing CSV filenames. Overlapping
  records are merged by competition, season, and normalized teams, using dates
  for cup matches. A merged fixture uses the date and scored result of the
  first applicable source in this order: dedicated Série A, historical
  Série A, Copa do Brasil, Libertadores, extended match statistics.
- Standings use recorded scores, three points per win, and common score-based
  tiebreakers. The `complete` flag indicates whether the expected home-and-away
  results are present. Standings omit administrative point adjustments and
  may differ from official tables. The 2023 Série A file supplies 377 of 380
  expected fixtures. League seasons from the extended CSV use date-based
  inference for the delayed 2020 editions.
- The FIFA snapshot has no date-specific roster history. Queries for Flamengo
  or São Paulo FC players and for the display name Gabriel Barbosa can return
  empty results. The match files contain team scores and lack individual
  goalscorers and penalty shootout outcomes.
