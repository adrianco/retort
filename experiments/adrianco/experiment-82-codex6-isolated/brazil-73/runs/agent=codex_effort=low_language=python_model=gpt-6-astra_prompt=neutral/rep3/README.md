# Brazilian Soccer MCP Server

An offline Python 3.10+ MCP server for demo/non-commercial exploration of the six bundled Kaggle CSV files. No dependencies, API keys, network access, or database service are required.

```sh
python server.py
python -m unittest -v
python -m py_compile soccer.py server.py test_soccer.py
```

`server.py` reads newline-delimited JSON-RPC from stdin and writes only protocol responses to stdout. Set `--data-dir /path/to/csvs` to use another dataset directory; the default is relative to the code, independent of the working directory. Missing files and invalid rows produce a clear startup error on stderr.

Configure an MCP-capable LLM client using absolute paths:

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

The connected LLM interprets natural-language questions, composes tool calls, and formats answers. The server supplies structured evidence; it does not require a second LLM or attempt to parse arbitrary English itself. For a follow-up such as “What was the score?”, the client retains the preceding match in conversation context.

## Tools

| Tool | Purpose |
|---|---|
| `search_matches` | Team/opponent, home/away, inclusive date range, competition, season, exact stage/round, source, traditional derbies |
| `team_stats` | Played, W/D/L, goals, points, win percentage, competition breakdown and FIFA roster |
| `head_to_head` | Both orientations, records and latest meeting |
| `search_players` | Name substring, nationality, normalized club, position/forwards, minimum rating; highest rating first; full original attributes |
| `standings` | Calculated league ranking, optionally home/away only |
| `competition_results` | Season fixtures and stage groups for schedules/bracket exploration |
| `analysis` | Goal averages, home win rate, biggest wins, team rankings and season trends |
| `graph_neighbors` | Traverse team, player, match and competition entities |
| `coverage` | All source row counts, competition coverage, conflicts and caveats |

Paginated tools return `items`, `total`, `offset`, and `next_offset`. Follow `next_offset` until null to retrieve every result. Default page size is 50; maximum is 500. Match results are newest first and include original source records, statistics, source filenames and row numbers. Player attributes preserve the complete FIFA record.

Graph IDs use `team:flamengo`, `player:158023`, `match:1`, and `competition:Copa Libertadores`. Match IDs are stable for the same files/load order, but are not permanent identifiers across dataset updates. Edges connect teams to matches, competitions and roster members, players to clubs, and fixtures to their participants and competition.

Python usage:

```python
from soccer import SoccerGraph

graph = SoccerGraph()
print(graph.head_to_head("Palmeiras", "Santos"))
print(graph.team_stats("Corinthians", season=2022, venue="home"))
print(graph.search_players(nationality="Brazil", limit=10))
print(graph.standings("Brasileirão", 2019))
```

## Data semantics

Accents, case, state suffixes and known full-name aliases are normalized. State distinctions for names such as América and Botafogo are retained; the alias dictionary is explicit and extensible, not fuzzy matching that silently conflates unrelated clubs. Unknown names are preserved.

Sources load in this priority order: Brasileirão, Brazilian Cup, Libertadores, historical league, extended statistics, FIFA. Fixtures with the same competition/date/home/away merge. Across different sources, matching teams and scores within one calendar day also merge to accommodate timezone discrepancies. Original rows remain attached. First-source scores and season take precedence; score conflicts appear in `coverage`. Extended statistics enrich the fixture. This conservative heuristic can leave larger date discrepancies unmerged; aggregates are dataset results, not certified official records.

Missing scores are null and excluded from played-game statistics. The undated, unscored Libertadores final is retained with an empty date and null season. Extended-only fixtures infer seasons from calendar years; pandemic seasons may cross calendar years. Date range filters operate on the canonical date.

Tables rank by points, wins, goal difference, goals scored, then normalized name. Official remaining tiebreakers, disciplinary deductions and completeness cannot be guaranteed. Série C may have a group structure; a combined calculated table is not its official standings. Champion/relegation questions should identify dataset leaders/bottom teams and include these qualifications. Cup tables are rejected in favor of stage-grouped results. Cup CSV round numbers are retained because their stage mapping changes across seasons; an empty search for `stage="final"` in Copa do Brasil does **not** establish that no final occurred. Libertadores has actual stage labels. Penalty shootouts and advancement are not inferred. Individual top scorers cannot be calculated because no goal-event data exists.

FIFA clubs, ages, ratings and attributes describe the historical snapshot, not current rosters or match-time participation. Name searches return only actual matching records (e.g. an absent or abbreviated Gabriel Barbosa entry is not fabricated). Derbies use a documented-in-code curated list, not an exhaustive definition of rivalries.

## Sample questions

The 24 question-to-tool scenarios in `test_soccer.py` exercise lookup, relationship and analytical use cases. Additional examples and client interpretation:

- “Who scored most as a team in Série A 2023?” → `standings`, sort the returned teams by `goals_for`, noting partial coverage.
- “Compare 2018 and 2019” → `analysis`, compare those two entries in `seasons`.
- “Which competitions has Palmeiras played in?” → keys of `team_stats.by_competition` or `graph_neighbors`.
- “Show the 2018 Libertadores bracket” → paginate `competition_results` and group by stage; do not invent shootout winners.
- “Find all Copa do Brasil finals” → explain the numeric-round limitation using `competition_results`; do not label the highest observed round as a final without additional evidence.

Tests cover every input CSV, row provenance conservation, normalization, date parsing, missing data, exact arithmetic, pagination, stages, graph relationships, validation, protocol framing, subprocess operation and 24 example question routes. Each lookup is checked against the 2-second target and aggregate queries against 5 seconds after loading. The known 2019 Flamengo record (38 played, 28 wins, 90 points) is a regression check against duplicate counting.

## Attribution and protocol

- [Ricardo Mattos match datasets](https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro): CC BY 4.0; Brasileirão, Brazilian Cup, Libertadores.
- [Brazilian football matches](https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches): CC0; extended statistics.
- [Historical Brasileirão](https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019): CC BY 4.0.
- [FIFA player data](https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data): Apache 2.0.

Normalization and duplicate merging are modifications to these datasets; original CSV files are unchanged. Attribution/license descriptions follow TASK.md.

The stdio implementation follows the [MCP transport specification](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports) and [tool specification](https://modelcontextprotocol.io/specification/2025-06-18/server/tools). It supports initialization negotiation for 2024-11-05, 2025-03-26 and 2025-06-18, notifications, ping, tool discovery and tool calls. It advertises only tools; no HTTP transport is provided.
