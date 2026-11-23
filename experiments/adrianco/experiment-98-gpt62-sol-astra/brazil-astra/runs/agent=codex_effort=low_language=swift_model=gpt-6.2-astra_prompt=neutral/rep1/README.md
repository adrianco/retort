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

## Running the Swift MCP server

Build with `swift build -c release` and run the bundled-data tests with `swift test`.
Configure your MCP client to launch `.build/release/soccer-mcp` using its absolute path,
with the absolute path to `data/kaggle` as its single argument. From the repository
root the data argument is optional. The server imports the six files into SQLite
at startup and communicates over newline-delimited JSON-RPC on stdin and stdout.

The connected language model translates questions into SQLite using the schema in
the `soccer_query` tool description. Use `normalize_team` to resolve team spellings.
For example, “When did Flamengo last play Corinthians?” translates to:

```sql
SELECT date, venue, gf, ga, competition
FROM appearances
WHERE team = 'flamengo' AND opponent = 'corinthians' AND gf IS NOT NULL
ORDER BY date DESC LIMIT 1
```

League standings are calculated from recorded results. Season coverage varies, and
some fixtures have missing scores. Individual goalscorers are unavailable. Match
and player details retain the original CSV columns for questions about skill
ratings, stadiums and extended match statistics. Use the source_matches table to
inspect individual source records and matches for combined statistics.
