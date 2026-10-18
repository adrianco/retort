# Brazilian Soccer MCP with spec and basic data sets

## Specification
brazilian-soccer-mcp-guide.md

## Implementation (Java)
A stdio MCP server (JSON-RPC 2.0, protocol 2024-11-05) over the six CSV files. It exposes seven tools:
`search_matches`, `team_record`, `head_to_head`, `standings`, `find_players`, `club_player_summary`
and `aggregate_stats`. The connected LLM turns natural-language questions into tool calls.

    mvn package                          # builds target/brazilian-soccer-mcp-1.0.0.jar
    mvn test                             # unit tests plus BDD-style scenarios over the real data
    java -jar target/brazilian-soccer-mcp-1.0.0.jar [data/kaggle]

Requires Java 17+. The data directory defaults to `data/kaggle` or `$SOCCER_DATA_DIR`.

How the data is reconciled:
- Team names are normalised (state suffixes, parentheses, accents, known aliases such as
  "Vasco Da Gama RJ" and "Athletico Paranaense"). Clubs that share a base name across states, such as
  Atletico-MG and Athletico-PR, keep their state.
- Fixtures listed in more than one file are counted once, keyed by season, competition and ordered teams.
  Source files disagree on match dates by a day, so dates are not part of the key.
- Unplayed rows (`NA` or `-` scores) are skipped.
- Copa do Brasil finals are labelled as the last round of each season. 2021 is left unlabelled because the
  source file stops at round 3.

Known gaps in the provided data:
- `fifa_data.csv` has no Flamengo players.
- The 2021 Brasileirão has more than 20 clubs in the match files, and a few clubs have partial seasons.
- Some 2023 Brasileirão fixtures are missing.
- Series B and C and the cup files use the same normalisation but have not been audited club by club.

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
