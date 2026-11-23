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

## Run the server

Use the Clojure CLI and run these commands from the repository root.

```sh
clojure -M:run
clojure -M:test
```

Configure an MCP client to launch `clojure` with arguments `["-M:run"]` and the repository as its working directory. An optional directory argument after `:run` overrides `data/kaggle`. The server speaks newline-delimited JSON-RPC over UTF-8 stdio. The client's LLM translates questions into tool calls and uses the returned data to compose answers and handle conversational follow-ups.

| Question | Tool and arguments |
| --- | --- |
| When did Flamengo last play Corinthians? | `find_matches` with `team: "Flamengo", opponent: "Corinthians", limit: 1` |
| What was Corinthians' 2022 home record? | `team_stats` with `team: "Corinthians", season: 2022, venue: "home", competition: "Serie A"` |
| Who won Série A in 2019? | `standings` with `season: 2019` |
| Show the 2018 Libertadores knockout bracket | `knockout_bracket` with `competition: "Libertadores", season: 2018` |
| Show the top Brazilian FIFA players | `find_players` with `nationality: "Brazil"` |
| Show Santos match records and FIFA players | `club_profile` with `team: "Santos"` |
| Which teams had the best away record? | `team_leaders` with `venue: "away", min-played: 20` |

Tools return structured JSON and a JSON text representation. For paginated results, use `next-offset` as the next call's `offset`.

## Data interpretation

- The combined view reconciles league fixtures by competition and canonical home and away clubs, using dates and seasons to associate overlapping records. Cup fixtures use nearby dates to distinguish separate legs. Competition-specific files take precedence, with missing scores and available details supplemented by the other files. Where a primary Série A schedule is complete, unmatched extended rows are available through the `source` filter.
- Standings are calculated from the scores provided and include a completeness flag. The extended file is missing fixtures for 2023 Série A, so its computed leader reflects the available scores. Rules and administrative decisions beyond the recorded results can affect official standings.
- The FIFA CSV is a historical snapshot with uneven club coverage. Player lookup returns an empty page for names and affiliations absent from the file. Individual scorers and penalty shootout results are unavailable.
