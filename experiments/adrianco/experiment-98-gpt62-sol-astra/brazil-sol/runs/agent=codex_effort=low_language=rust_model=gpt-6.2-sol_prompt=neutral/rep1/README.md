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

## Run the MCP server

Run `cargo build --release --locked` from this directory. In a stdio-capable MCP
host, configure the server command as the absolute path to
`target/release/brazilian-soccer-mcp`. The server defaults to this checkout's
`data/kaggle` directory. When moving the binary or datasets, pass the absolute
path to the directory containing the six CSVs as the first argument.

The host's language model translates questions into tool calls and turns the
returned JSON into answers. For follow-up questions like “What was the score?”,
the host can use the match from the preceding tool result. The server uses MCP
stdio and negotiates revision `2025-11-25` or `2025-06-18`.
[Transport specification](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports)

## Example questions

| Question | Tool | Arguments |
| --- | --- | --- |
| When did Flamengo last play Corinthians, and what was the score? | `search_matches` | `{"team":"Flamengo","opponent":"Corinthians","limit":1}` |
| Show all Fla-Flu matches. | `search_matches` | `{"team":"Flamengo","opponent":"Fluminense"}` |
| What Série A matches did Palmeiras play in 2023? | `search_matches` | `{"team":"Palmeiras","competition":"Série A","season":2023}` |
| Show away matches for Grêmio in August 2023. | `search_matches` | `{"team":"Grêmio","venue":"away","start_date":"01/08/2023","end_date":"31/08/2023"}` |
| Show all recorded Copa do Brasil finals. | `search_matches` | `{"competition":"Copa do Brasil","stage":"final"}` |
| Show me the 2023 derbies. | `search_matches` | `{"season":2023,"derbies":true}` |
| Show the biggest wins. | `search_matches` | `{"order":"biggest_win","limit":10}` |
| What matches have extended statistics for Santos? | `search_matches` | `{"team":"Santos","source":"BR-Football-Dataset.csv"}` |
| What was Corinthians' Série A home record in 2022? | `team_stats` | `{"team":"Corinthians","venue":"home","competition":"Série A","season":2022}` |
| Compare Palmeiras and Santos head-to-head. | `team_stats` | `{"team":"Palmeiras","opponent":"Santos"}` |
| What competitions has Palmeiras played in? | `team_stats` | `{"team":"Palmeiras","limit":0}` |
| Show Grêmio's record by season and venue. | `team_stats` | `{"team":"Grêmio","limit":0}` |
| Show Santos' match record and FIFA roster. | `team_stats` | `{"team":"Santos"}` |
| Show Neymar's rating and attributes. | `search_players` | `{"name":"Neymar"}` |
| Who are the top-rated Brazilian players? | `search_players` | `{"nationality":"Brazil","limit":10}` |
| Find all Brazilian players. | `search_players` | `{"nationality":"Brazil","limit":100}` |
| Show me forwards at Santos. | `search_players` | `{"club":"Santos FC","position":"forward"}` |
| Who won the 2019 Brasileirão? | `standings` | `{"competition":"Brasileirão","season":2019}` |
| Which Série A teams were relegated in 2020? | `standings` | `{"competition":"Série A","season":2020}` |
| Show the 2018 Libertadores bracket. | `cup_bracket` | `{"competition":"Libertadores","season":2018}` |
| What's the average number of goals per Brasileirão match? | `analyze_matches` | `{"competition":"Brasileirão"}` |
| Which team scored most in the recorded 2023 Série A matches? | `analyze_matches` | `{"competition":"Série A","season":2023,"rank_by":"goals","limit":1}` |
| Which teams had the best away win rate in Série A 2019? | `analyze_matches` | `{"competition":"Série A","season":2019,"venue":"away","min_matches":19}` |
| Compare Série A scoring and outcomes in 2018 and 2019. | `analyze_matches` | `{"competition":"Série A","seasons":[2018,2019]}` |

For paginated lists, repeat the call with `offset` set to `next_offset` until
it is null. Use `limit: 0` for totals or records without the list.

## Dataset behavior

- Team matching folds accents and resolves common aliases and state suffixes.
  Match output retains source spellings and includes provenance in `sources`.
- Aggregates use merged fixtures. Dedicated Série A files supply the fixture
  lists for 2003–2022, with overlapping extended rows contributing details and
  missing scores. The `source` filter queries the selected CSV directly.
- Unscored fixtures appear in match searches. Result aggregates use fixtures
  with both scores. League tables use three points per win and one per draw,
  based on recorded scores. The 2023 Série A feed has 377 of 380 fixtures, so its
  standings are provisional. Relegation results use the bottom four in complete
  Série A tables from 2006 onward.
- The match files contain team totals. Individual scorers and some cup
  advancement details are unavailable. The FIFA file is a historical snapshot
  and returns zero results for absent entries such as Flamengo's roster or
  Gabriel Barbosa. Club links use the club name recorded in that snapshot.
- Derby searches use a curated list of traditional rivalries.

Run `cargo test --locked` to verify the dataset queries and the stdio server.
