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

Build with `make` using a C11 compiler, POSIX getline, and SQLite 3.38 or later with JSON support. Run `make test` for the Python 3 integration scenarios. The server imports the six CSVs into memory at startup and communicates over newline-delimited JSON-RPC on standard input and output.

Configure an MCP client with the absolute paths to the built executable and dataset directory. For example, replace both paths in this client configuration with your checkout paths.

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/path/to/checkout/soccer-mcp",
      "args": ["/path/to/checkout/data/kaggle"]
    }
  }
}
```

Ask the connected LLM a question such as “Who won the 2019 Brasileirão?” The server advertises the graph schema through `query_soccer`. The LLM translates the question into a read-only SQLite query and formats the returned columns and rows. For example, this query returns Flamengo with 90 points.

```sql
SELECT team, points FROM standings
WHERE competition = 'Serie A' AND season = 2019
ORDER BY points DESC, wins DESC, gd DESC, goals_for DESC
LIMIT 1
```

Use `matches` for fixtures, `appearances` for each team's side of a fixture, and `standings` for match-derived season totals. Join FIFA snapshot clubs with `team_key(players.Club) = appearances.team`. The keys fold Portuguese accents and map common club aliases. The `derbies` view covers selected traditional rivalries. For multi-page results, use a stable ORDER BY with LIMIT and OFFSET.

The league fixture list uses historical data through 2011, league schedules from 2012 through 2022, and extended data thereafter. Supplemental scores fill matching unplayed fixtures when available. Copa do Brasil fixtures use the cup schedule plus extended records without a matching scheduled pairing within one day. Name or date discrepancies can still affect cross-source matching. The `reports` table retains overlapping observations and the six original tables expose source-specific fields such as stadium, corners, and player skills.

Season totals reflect available results. For instance, the extended source includes 377 Serie A fixtures for 2023. Standings omit missing scores and reflect points earned on the field. Player data describes the FIFA snapshot. The datasets contain no individual goal events for calculating top scorers.
