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

## Running the Python server

Python 3.10+; no external dependencies or network access required.

```sh
python3 server.py
python3 -m unittest -v
python3 -m py_compile soccer.py server.py test_soccer.py
```

Configure your MCP client with absolute paths:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "python3",
      "args": ["/absolute/path/to/server.py", "--data-dir", "/absolute/path/to/data/kaggle"]
    }
  }
}
```

The server implements UTF-8 newline-delimited JSON-RPC over stdio, initialization,
version negotiation, ping, tool discovery and tool calls following the
[MCP specification](https://modelcontextprotocol.io/specification/2025-11-25).
Stdout is reserved for protocol messages. All tools are read-only. The attached
LLM interprets natural-language questions, calls tools, and formats answers;
no API key, embedded LLM or brittle free-text parser is required. Follow-up
questions such as “What was the score?” use the client's conversation context.

Available tools: `search_matches`, `search_players`, `team_statistics`,
`head_to_head`, `standings`, `analysis`, `team_profile`, `trends`,
`competition_results`, `top_scorers`, `coverage`, and `neighbors`.
Tool discovery provides parameter schemas. Search tools paginate with `limit`
(1–500) and `offset`, returning a total count. Matches are newest first and
players are ordered by overall rating. `venue` is home, away or either.
Dates accept ISO dates/timestamps and DD/MM/YYYY. Position filters accept FIFA
codes or forward/midfielder/defender/goalkeeper.

`test_soccer.py:EXAMPLES` contains 23 executable question-to-tool examples.
To answer “Which team scored most?”, sort the returned standings by `goals_for`;
for best home/away record, request the appropriate venue and compare win rates.
`trends` provides per-season comparisons. `team_profile` joins match history
and FIFA club membership. `neighbors` exposes graph edges between teams,
players, matches and competitions. Match IDs are deterministic for an unchanged
dataset, not durable identifiers across dataset updates.

## Data handling and limits

All six original CSVs are loaded on startup. Accents, common full names and
Brazilian state suffixes are normalized. Ambiguous América/Atlético state
identifiers are retained. Aliases are explicit and extensible in `soccer.py`;
unknown names are preserved rather than fuzzy-matched to a different club.

Match identity uses competition, date, home and away teams. Identical-score
matches within one day are merged only across distinct sources with one
candidate, accounting for observed local/UTC date differences. Raw rows and
source filenames remain attached. Source priority follows the file order in
`FILES`: dedicated competition data, extended statistics, then historical
results. Conflicting scores are exposed, not averaged; missing scores may be
filled from another source. Numeric rounds are preserved. Unknown dates,
scores and seasons stay null; unplayed matches do not affect statistics.
`coverage` reports counts, conflicts and malformed rows. Missing files fail
startup clearly. No data is downloaded or written by the server.

Standings use three points per win and one per draw; ties sort by wins, goal
difference, goals scored, then name. These are dataset-derived tables, not
certified official standings: coverage, deductions, historical rules and
multi-group formats may differ. Bottom places do not prove relegation.
Copa do Brasil numeric rounds are not assumed to encode finals; use recorded
round filters and grouped fixtures. Libertadores has textual stages including
`final`. Knockout progression and penalty winners cannot reliably be inferred.
Individual scoring events are absent, so top scorer queries explicitly report
unavailability. FIFA clubs/attributes reflect a historical snapshot, not current
rosters. Source attribution and licenses are listed above. Intended for demo
and non-commercial use.
