# Brazilian Soccer MCP Server

A dependency-free Python 3.10+ server for querying the six supplied Kaggle datasets. It provides a local knowledge graph of teams, matches, players, competitions and seasons, with typed, traversable relationships and source provenance.

Run from this directory:

```sh
python3 server.py
```

The process reads newline-delimited MCP JSON-RPC from stdin and writes responses to stdout. It is intended to be launched by an MCP-capable LLM client, which interprets natural-language questions and calls the structured tools. No API keys, internet access, external database, or separate model are required by the server. It does not implement its own natural-language model.

Example client configuration (replace the absolute path):

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

Data defaults to `data/kaggle` relative to the code, independent of the working directory. Override with `--data-dir /path/to/csvs`. All six files are required; a missing file fails startup rather than silently reducing coverage.

The stdio implementation supports the initialize/tools lifecycle through revision 2025-11-25, with protocol negotiation, tool discovery, schema validation, JSON-RPC errors, tool execution errors, notifications and ping. Reference: [MCP tools specification](https://modelcontextprotocol.io/specification/2025-11-25/server/tools).

## Tools

| Tool | Purpose |
|---|---|
| `search_matches` | Team, opponent, home/away, inclusive date range, competition, season, stage and source filters; newest first |
| `team_statistics` | W/D/L, goals, points, win percentage, breakdown by competition |
| `head_to_head` | Record from the first team's perspective |
| `search_players` | Name substring, nationality, canonical club, position or position group, minimum rating; highest rated first |
| `standings` | Calculated season standings, optional home/away records |
| `analysis` | Goals per match, home/away outcomes, biggest wins, seasonal comparisons and team trends |
| `team_profile` | Match statistics, competitions and FIFA club members together |
| `competition_bracket` | Fixtures grouped by available stage/round |
| `derbies` | Matches from a curated set of traditional rivalries |
| `graph_neighbors` | Paginated traversal of typed graph relationships |
| `coverage` | File row counts, competition date ranges, import conflicts and limitations |

Paged tools return `total`, `items`, and `next_offset`. Pass the returned offset for the next page. Default page size is 50, maximum 500. Statistics operate on the full selection, not a result page. Match results include original source rows and extended statistics. Players include all original FIFA attributes. Tool responses contain JSON text suitable for the connected LLM to turn into readable answers.

`sample_questions.json` contains 27 natural-language questions and corresponding tool calls, all exercised by tests. For "most goals", sort the returned standings by `goals_for`; for "best win rate", compare `win_rate`. Follow-up context such as "What was the score?" belongs to the connected LLM; the server does not mix conversational state between clients.

Python usage:

```python
from soccer import SoccerGraph

graph = SoccerGraph()
print(graph.head_to_head('Palmeiras-SP', 'Santos'))
print(graph.team_statistics('Corinthians', season=2022, venue='home'))
print(graph.search_players(nationality='Brazil', position='forwards', limit=10))
print(graph.standings('Serie A', 2019))
```

## Data handling and limits

- UTF-8/BOM, accent-insensitive matching, ISO dates, Brazilian dates and timestamps are supported. Explicit aliases normalize common full names. State suffixes are retained for ambiguous clubs such as América-MG/América-RN and Botafogo-PB. Unknown aliases are not guessed.
- Fixtures merge by competition, calendar date and ordered canonical teams. Across different files, a one-day difference also merges when scores agree or one score is missing, to reconcile time zones. Original dates remain in provenance. Same-source adjacent fixtures remain distinct. This is a documented reconciliation heuristic, not a universal fixture identity rule.
- Source priority follows TASK.md order: league, cup, Libertadores, extended statistics, historical league. Missing scores are filled from later sources; conflicting known scores retain the first value and are reported by `coverage`. Raw rows preserve alternatives for inspection. Statistics omit unplayed games; unknown dates/scores remain null and queryable.
- League tables use points, wins, goal difference and goals scored, with alphabetical ordering for unresolved ties. These are calculated standings, not official disciplinary or tie-break rulings. A completeness flag checks double-round-robin match counts. Incomplete datasets must not be presented as final standings. Champion claims require checking completeness and relevant rules; relegation is not inferred because historical formats and administrative decisions vary.
- Cup rounds differ by season. A final is inferred only when the highest numbered round in that season contains exactly two fixtures involving the same two teams. `stage_inferred` marks this. Stage labels missing from the extended file cannot reliably be recovered, so final searches may be incomplete. Brackets expose stage-grouped fixtures without inventing progression or penalty winners.
- The FIFA database is a historical snapshot, not current rosters. A missing player/club is an empty result, not proof of real-world absence. Individual top scorers cannot be calculated: the files contain team score totals, not goal events.
- Optional live APIs are deliberately not required. Coverage only represents the supplied historical files. Some source discrepancies and unusual club spellings remain visible rather than being silently fabricated.

## Verification

```sh
python3 -m compileall -q soccer.py server.py test_soccer.py
python3 -m unittest -v
```

Tests cover all six files without lost rows, date/name normalization, source reconciliation, independent known 2019 league totals, filters, aggregate conservation, head-to-head symmetry, players, graph links, cup fixtures, pagination, invalid inputs, missing data, 27 question/tool scenarios, response-time budgets, and a real stdio subprocess handshake and query. No third-party test runner is needed.

## Dataset attribution

For demo/non-commercial use as requested by TASK.md; dataset licenses are retained independently of this code.

| Files | Source | License |
|---|---|---|
| Brasileirão, Copa do Brasil, Libertadores | [Ricardo Mattos: jogos do campeonato brasileiro](https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro) | CC BY 4.0 |
| BR-Football-Dataset.csv | [cuecacuela: Brazilian football matches](https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches) | CC0 |
| novo_campeonato_brasileiro.csv | [macedojleo: campeonato brasileiro 2003–2019](https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019) | CC BY 4.0 |
| fifa_data.csv | [youssefelbadry10: FIFA players data](https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data) | Apache 2.0 |

Attributions/licenses above follow the supplied specification. Data transformations are normalization, fixture reconciliation and calculated aggregates; source records are preserved.
