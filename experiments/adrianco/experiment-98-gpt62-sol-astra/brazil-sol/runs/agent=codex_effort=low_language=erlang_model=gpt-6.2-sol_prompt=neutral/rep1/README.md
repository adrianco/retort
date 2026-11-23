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

The server uses Erlang/OTP 27 or newer for the standard library JSON module.
Run `make` to build and `make test` to run the dataset scenarios and the MCP
stdio integration test.

Configure an MCP client with the absolute path to `_build/soccer-mcp` as its
command. The executable uses `data/kaggle` from this checkout by default. You
can also pass the absolute path to the dataset directory as its sole argument.
The client supplies the language model, which translates questions into tool
calls and uses the returned results to answer them.

## Tools

| Tool | Example question |
| --- | --- |
| `find_matches` | When did Flamengo last play Corinthians? |
| `team_stats` | How did Corinthians do at home in the 2022 Brasileirão? |
| `standings` | Who led the 2019 Brasileirão table? |
| `analyze_matches` | How did goals per match compare across 2018 and 2019? |
| `find_players` | Who were the highest-rated Brazilian players in the FIFA snapshot? |
| `club_profile` | Show the Santos squad in the FIFA snapshot alongside the club's 2019 league record. |
| `data_coverage` | Which sources and seasons are available? |

Match searches support pagination, dates, seasons, competition, stage, venue,
opponent, and traditional derbies. Use `stage: "knockout"` and
`competition: "Libertadores"` for knockout fixtures. The optional `source`
argument selects a specific match CSV. The default uses merged fixtures and
preserves source filenames on each result. Tables and rankings reflect the
available scores, and win rates are fractions between zero and one.

The extended file has 377 of the 380 Série A fixtures for 2023. The computed
table identifies this coverage gap. Administrative points adjustments and
some official tie-breakers are unavailable. The player file is a FIFA snapshot
and contains no rows matching Flamengo or Gabriel Barbosa. The match files
contain team scores and lack individual goalscorer events.

The server uses the [MCP stdio transport](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports).
