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

Use Python 3.10 or newer. The server uses the standard library and the six CSVs
in `data/kaggle/`. Run the checks from this directory:

```sh
python3 -m compileall -q server.py soccer.py test_soccer.py
python3 -m unittest -v
```

Add the following entry to a local MCP host that supports stdio. Replace the
script path with its absolute path and use the absolute Python path if required
by the host.

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "python3",
      "args": ["/absolute/path/to/server.py"]
    }
  }
}
```

The host's LLM translates natural-language questions into tool calls. The
server implements the [MCP stdio transport](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports)
and returns JSON tool results.

| Question | Tool and arguments |
| --- | --- |
| When did Flamengo last play Corinthians, and what was the score? | `search_matches(team="Flamengo", opponent="Corinthians", limit=1)` |
| What was Corinthians' home record in 2022? | `team_stats(team="Corinthians", season=2022, competition="Série A", venue="home")` |
| Who are the highest-rated Brazilian players? | `search_players(nationality="Brazil", limit=10)` |
| Who won Série A in 2019? | `standings(season=2019)` |
| Which teams were in the 2020 relegation places? | `standings(season=2020)` |
| Show the 2018 Libertadores bracket. | `tournament_bracket(season=2018)` |
| Which team had the best away win rate in Série A in 2019? | `team_rankings(competition="Série A", season=2019, venue="away", sort_by="win_rate")` |
| Compare goals per match in 2018 and 2019. | `match_statistics(competition="Série A")`, then use `by_season` |
| Show Grêmio's results and FIFA players. | `club_profile(club="Grêmio", season=2019)` |

Use `coverage` for source counts and `search_matches(source=...)` for
source-specific fixture rows. Paginated tools return `total` and
`next_offset`. Aggregate results use merged fixtures, with season-specific
dates and rounds preferred when available. Extended-only fixtures use the
exported date and calendar year unless they link to a season-specific row.

Standings are based on supplied scores and may differ from official tables.
The 2023 Série A data contains 377 of 380 fixtures, and the historical file
lists both 2009 Botafogo–Flamengo fixtures with Botafogo at home.
The FIFA file is a historical snapshot. A search for Flamengo's roster or
Gabriel Barbosa returns an empty result in this snapshot. The match CSVs
contain team scores, so individual top scorers are unavailable.
