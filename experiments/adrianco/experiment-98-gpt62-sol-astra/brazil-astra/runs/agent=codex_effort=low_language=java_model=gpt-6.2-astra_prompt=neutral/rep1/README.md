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

## Run the Java MCP server

With JDK 17 or later and Maven, run `mvn package` from this directory. This runs the dataset and protocol tests and builds an executable JAR. Configure a stdio MCP client to launch the following command, substituting absolute paths for both arguments.

```sh
java -jar /path/to/target/soccer-mcp.jar /path/to/data/kaggle
```

The server loads the six local CSVs at startup. The connected LLM translates questions into tool calls. For example, “When did Flamengo last play Corinthians?” maps to `matches` with `{"team":"Flamengo","opponent":"Corinthians","limit":1}`. A follow-up about the score can use the same result.

| Tool | Questions it answers |
|---|---|
| matches | Which fixtures involved Palmeiras in 2023? When was the last Fla-Flu? What was the score? Which derbies are in the dataset? What were the Copa do Brasil finals? What were the legs of the 2018 Libertadores quarterfinals? Which wins had the largest margins? How many corners did a team earn in a particular match? |
| records | Who topped the 2019 league table? Who finished in the bottom four in 2020? Which team scored the most? How did Corinthians perform at home? Who had the highest away win rate? How did two rivals fare head-to-head? Which competitions did a team play in? |
| summary | How many goals were scored per match? How often did home sides win? How did 2018 compare with 2019? Which competition had the most draws? |
| players | Which Brazilians had the highest ratings? Who played for a named club? Which forwards played there? What was a player's finishing rating? |
| club_profile | How did a club perform in each competition, and who appears on its FIFA roster? |

Each page reports the total matching rows and its offset. The default page size is 20 and the maximum is 100. Date ranges include both endpoints. A match carries links to its clubs, competition, season and original source rows. Use the CSV basename as the source filter to inspect any individual match dataset, including its stadium or extended statistics.

### Interpreting the data

The combined view prefers competition-specific fixtures, fills missing scores from matching historical or extended rows, and retains source attributes. League fixtures match by season and ordered team pair. Other cross-source matches use the ordered pair and dates within one day to accommodate kickoff time differences. The dedicated league and cup fixture lists take precedence during their coverage periods. Unmatched source rows remain accessible with the source filter. Known aliases and accents are normalized. The derby filter covers a curated list of traditional rivalries.

Statistics include fixtures with two recorded scores. Standings use three points for a win and one for a draw, then wins, goal difference and goals scored as tiebreakers. These are standings calculated from the available results. Partial seasons, disciplinary adjustments and further official tiebreakers can affect final placement. The files contain team goals but no scorer identities. FIFA club membership reflects the player snapshot and can differ from the squad in a queried match season.
