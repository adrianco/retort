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

## Running the server

Build with `go build -o soccer-mcp .` and run `go test ./...` from this directory.
Configure a stdio MCP client to launch the absolute path to the binary, with
arguments `-data /absolute/path/to/data/kaggle`. The server loads the CSVs once
and communicates over stdin and stdout. The connected LLM translates questions
into tool calls and presents the results.

| Question | Tool and arguments |
| --- | --- |
| When did Flamengo last play Corinthians? | `matches {"team":"Flamengo","opponent":"Corinthians","limit":1}` |
| Who won the 2019 Brasileirão? | `records {"competition":"Serie A","season":"2019","limit":1}` |
| Which competitions has Palmeiras played in? | `summary {"team":"Palmeiras"}` |
| Who are the top-rated Brazilian forwards? | `players {"nationality":"Brazil","position":"forward"}` |

Match and player pages default to 20 rows. Use `offset` and `limit` (up to 100)
to retrieve further pages. Match results preserve original CSV rows under
`Sources`. A source filter takes the CSV basename. Unscored fixtures appear
in schedules and are excluded from record and average calculations. Standings
use available results, with points, wins, goal difference and goals scored
as ranking criteria. Some seasons have partial coverage. Player affiliations
and ratings refer to the FIFA snapshot, which has no Flamengo roster or
individual match scoring events.
