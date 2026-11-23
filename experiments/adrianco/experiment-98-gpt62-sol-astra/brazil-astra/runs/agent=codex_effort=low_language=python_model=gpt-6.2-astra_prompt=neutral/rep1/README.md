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

Use Python 3.9 or newer. The server loads the six bundled CSVs once at startup and runs offline using the standard library. Configure an MCP host with a stdio server entry like this, substituting the absolute path to this checkout.

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

Ask questions in the connected host. Its language model chooses tools, combines results, and carries context into follow-up questions such as “What was the score?”

| Question or follow-up | Tool and arguments |
|---|---|
| When did Flamengo last play Corinthians? | `find_matches(team="Flamengo", opponent="Corinthians", limit=1)` |
| Which side won more of those games? | `statistics(team="Flamengo", opponent="Corinthians")` |
| Which competitions has Palmeiras played in? | `statistics(team="Palmeiras")`, read `competitions` |
| Who scored the most team goals in Série A in 2023? | `statistics(competition_name="Serie A", season=2023, rank_by="goals_for", limit=1)` |
| Who were the top Brazilian forwards at Grêmio in FIFA? | `find_players(nationality="Brazil", team="Grêmio", position="forwards")` |
| How did scoring change between two seasons? | Call `statistics` for each season and compare `goals_per_match` |
| Show the 2018 Libertadores bracket | Page through `find_matches(competition_name="Libertadores", season=2018)` and group knockout legs by stage and opponent |

All tools return a total and support limit/offset pagination. Dates are inclusive. Match results retain source basenames and include stadium or extended statistics where available. Missing scores appear as null and are excluded from calculated records. Win rates are percentages.

Standings represent recorded results with three points for a win, followed by wins, goal difference and goals scored as tiebreakers. Source coverage varies by season. Official sanctions, individual goalscorers and penalty shootouts are unavailable. The FIFA file represents a historical snapshot, and some clubs have no listed players. Derby searches cover selected traditional rivalries.

For overlapping Série A seasons the dedicated fixture list determines league membership. Other sources enrich fixtures by club pairing and season. For other competitions extended data can match a fixture within one calendar day to accommodate kickoff time differences. A source filter also exposes unmatched extended records. Cup finals use the final recorded numbered round when complete, or the last reciprocal pair of legs in the 2021–2023 extended results.

Run the executable behavior scenarios with `python3 -m unittest -v`.
