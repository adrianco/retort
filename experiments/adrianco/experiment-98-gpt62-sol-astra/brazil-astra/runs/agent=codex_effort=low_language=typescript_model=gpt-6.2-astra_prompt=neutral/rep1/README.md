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

From this directory, run `npm ci`, then `npm test` to compile the TypeScript and run the dataset and stdio tests. To use the server with an MCP host, configure a stdio server with command `node` and the absolute path to `dist/server.js` as its sole argument. The server locates the CSVs relative to the build and runs offline.

The host's language model translates questions into calls to four tools. Use `matches` for fixtures and results, `records` for standings and head-to-head records, `statistics` for competition or season summaries, and `players` for the FIFA snapshot. For example, “Who won the 2019 Brasileirão?” maps to `records` with `{"competition":"Serie A","season":2019,"limit":1}`. Use a player's club as the team in a follow-up match query. The player data describes clubs at the time of the FIFA snapshot. The match files do not identify individual goalscorers.

Results use normalized club names. The combined match view merges overlapping Série A home/away pairings within a season and other cross-source fixtures with matching teams and dates within a day. Competition-specific files take priority, with historical and extended records supplying missing results. Select a source filename to inspect original rows, including stadium or shot statistics. Standings reflect recorded scores and the available season coverage. Win rates are percentages. The derby filter covers a curated set of rivalries. Use limit and offset to page through fixtures, standings and players.
