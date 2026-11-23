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

On macOS with the Xcode command-line tools, run `make` to build the Objective-C
server against Foundation and SQLite. Run `make test` for the Python 3 stdio
integration suite. Configure a local MCP client with the absolute executable and
dataset paths, for example

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/absolute/path/to/soccer-mcp",
      "args": ["/absolute/path/to/data/kaggle"]
    }
  }
}
```

Ask the connected LLM a question such as “Who won the 2019 Brasileirão?”.
The server advertises the schema through its `query_soccer` tool. The client
translates the question into a read-only SQLite query and interprets the
returned JSON rows. For example, the league champion query is

```sql
SELECT team, points, wins, draws, losses
FROM standings
WHERE season = 2019 AND competition = 'Serie A'
ORDER BY points DESC, wins DESC, gd DESC, goals_for DESC
LIMIT 1
```

The server builds its in-memory database at startup. Match endpoints and FIFA
club memberships share normalized team keys. Use `club_key()` for team inputs.
Use `raw_matches` to inspect every source record and its original JSON
attributes, including arenas, shots and corners. Use `matches` for schedules,
scores and match-level averages, `team_results` for home, away and head-to-head
performance, and `players` for FIFA ratings and attributes. Results are paged
at 100 rows. Use a stable ordering with LIMIT and OFFSET for subsequent pages.

For the bundled coverage, consolidated Série A fixtures come from the historical
file through 2011, the league file for 2012–2022 and the extended file for 2023.
Cup fixtures use the dedicated file through its August 2021 cutoff and extended
coverage thereafter. Matching observations within one calendar day can fill
missing scores. Remaining unknown scores are null and excluded from records.
Cup final stages in the extended data are inferred from the closing pair of
reversed fixtures. Standings reflect observed fixtures and the 3–1–0 points
formula. Check season completeness before interpreting a final rank. Player
records reflect the FIFA snapshot. Individual match scorers are unavailable.
