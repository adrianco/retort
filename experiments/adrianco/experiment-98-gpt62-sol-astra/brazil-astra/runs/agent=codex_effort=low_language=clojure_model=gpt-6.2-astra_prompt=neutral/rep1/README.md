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

With the Clojure CLI installed, run `clojure -M:server` from this directory. Configure an MCP client's stdio launcher with command `clojure`, argument `-M:server`, and this directory as its working directory. An optional second argument selects a different dataset directory. Run `clojure -M:test` for the acceptance and protocol tests.

The connected LLM interprets natural-language questions and selects from six tools. For example, “When did Flamengo last play Corinthians?” maps to `matches` with `{"team_name":"Flamengo","opponent":"Corinthians","limit":1}`. Each row includes the score, so the client can answer a follow-up about the result.

| Tool | What it returns |
| --- | --- |
| matches | Fixtures in reverse date order, scores, rounds or stages, source fields and available extended statistics |
| team_profile | Win/draw/loss record, goals, records by season and competition, and the club’s FIFA roster. Supply an opponent for head-to-head records. |
| standings | Points table ordered by points, wins, goal difference and goals scored. Use venue and rank_by for home or away rankings. |
| players | Rating-ranked FIFA players with full attributes, filtered by name, club, nationality or position |
| statistics | Played and scheduled fixture counts, goals per played match and home win fraction, optionally grouped by season or competition |
| biggest_wins | Played matches ordered by victory margin |

List results include total and offset. The default page contains 20 rows and the maximum is 100. Dates are inclusive ISO dates. Team identities connect home teams, away teams and player clubs in memory. Source labels and player attributes preserve original spellings.

## Coverage and interpretation

Default Serie A queries use the historical file through 2011, the dedicated Serie A file for 2012–2022 and the extended file for later fixtures. Copa do Brasil uses its dedicated fixture list through its last supplied date, then the extended feed. Matching extended records can supply missing scores and additional statistics. To inspect any match file independently, pass its exact filename as `source`.

Standings reflect played matches in the supplied data. A partially covered season yields a partial table. The extended feed uses calendar year for season and has no round information. Cup finals are searchable where the tournament feed identifies the stage or its season-specific round. Derby searches use the rivalry pairs defined in soccer.clj. Win rates are fractions from zero to one. Missing scores are excluded from all result-based statistics.

The FIFA file is a historical snapshot with gaps in club coverage. An empty roster means the file has no matching players. The match files contain team scores only, so individual goal scorers cannot be inferred.
