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

## Run the Python MCP server

Python 3.10+; no third-party packages, credentials, network calls or database setup required.
All implementation and test files live in this directory.

```sh
python server.py
# Optional dataset location:
python server.py --data-dir /absolute/path/to/data/kaggle
python -m unittest -v
python -m compileall -q soccer.py server.py test_soccer.py
```

Configure an MCP-capable LLM client with absolute paths:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/absolute/path/to/python",
      "args": ["/absolute/path/to/server.py"]
    }
  }
}
```

The client LLM interprets natural language, calls the advertised tools, and formats
answers from their JSON results. Conversational follow-ups such as “What was the
score?” use the client's conversation context. This server does not embed an LLM
or claim to parse arbitrary natural language itself. The newline-delimited UTF-8
JSON-RPC transport follows the [MCP stdio specification](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports).
It supports initialize, ping, tools/list, tools/call and notifications; protocol
versions 2024-11-05, 2025-03-26 and 2025-06-18 are negotiated. Standard output is
reserved for protocol messages. EOF terminates the process.

## Tools and examples

- `search_matches`: team/opponent, venue, competition, season, date range, stage,
  source filename, traditional derbies, newest-first ordering and pagination.
- `search_players`: name substring, nationality, normalized club, position or
  `forwards`; results sorted by FIFA overall rating, with all original attributes.
- `team_info`: record, competitions and FIFA club snapshot.
- `head_to_head`: team record against an opponent and paginated results.
- `standings`: points, wins/draws/losses, goals, goal difference and win percentage.
  Venue filters support home/away comparisons. The client can rank goals_for or
  win_rate when the question requests those metrics instead of points.
- `statistics`: average goals, home win rate, biggest victories.
- `trends`: season-by-season aggregates.
- `bracket`: cup fixtures grouped by recorded stage or round.
- `graph`: explicit team/player/match/competition nodes and relationship edges.
- `top_scorers`: explains unavailable individual scoring information.
- `coverage`: row counts, ingestion issues and dataset date bounds.

`test_soccer.py` contains 24 executable natural-language question/tool mappings,
including the task's lookups, relationship queries and analytical examples. For
example, “When did Flamengo last play Corinthians?” maps to:

```json
{"name":"search_matches","arguments":{"team":"Flamengo","opponent":"Corinthians","latest":true,"limit":1}}
```

List results include total/offset/results; request subsequent offsets to retrieve
all matches or players. Default page size is 50 and maximum is 500. Python callers
can import `SoccerGraph` from `soccer.py` and use the same methods directly.

## Data interpretation

All six CSV files are read at startup, including 18,207 FIFA players. Match sources
are processed in specification order. Team matching removes accents and state
suffixes where unambiguous and applies explicit aliases; ambiguous América and
Atlético state identities are preserved. This is a curated alias set, not fuzzy
entity resolution for every international club spelling.

Duplicate fixtures share normalized date, home team, away team and competition.
Cross-source fixtures one day apart also merge when season and score agree,
accounting for midnight/time-zone differences. First-source values take precedence;
original rows and filenames remain in `source_rows` and `sources`. Conflicting
scores and malformed rows are reported by `coverage`. Adjacent-day merging is a
heuristic; original source dates remain available for auditing. Missing files fail
startup rather than silently yielding an incomplete database.

This is a historical, noncommercial demo. FIFA clubs and ratings are snapshots,
not current rosters. Missing scores are excluded from aggregates. Standings use
points, wins, goal difference and goals scored, with alphabetical ordering for
remaining ties. These are calculated records, not authoritative champions or
relegation decisions: coverage, deductions, historical rules and all tie-breakers
are not guaranteed. Copa do Brasil numeric final rounds are inferred as the
highest observed round within each season. Brackets expose recorded fixtures,
without guessing advancement, penalties or missing legs. The derby list is a
curated subset. Individual scorers cannot be derived from team scores or FIFA
ratings. No optional live APIs are used.

Tests verify source coverage, filters, UTF-8/name/date normalization, pagination,
record consistency, duplicate reconciliation against the 2019 league results,
graph relationships, missing-data responses, protocol errors and stdio operation.
They also enforce the specified query-time budgets for all sample tool calls.
Source attribution and licenses are listed above; raw data is preserved.
