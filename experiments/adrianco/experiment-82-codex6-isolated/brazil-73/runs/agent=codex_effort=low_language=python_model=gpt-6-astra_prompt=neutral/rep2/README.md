# Brazilian Soccer MCP Server

An offline Python knowledge graph over all six bundled CSV datasets. It exposes ten read-only MCP tools for an LLM to answer soccer questions. Requires Python 3.10 or newer; no packages, database, API credentials, or network access are required.

Run from this directory:

```sh
python3 server.py
```

The server reads newline-delimited MCP JSON-RPC on stdin and writes responses on stdout. It waits silently for a client. Data is loaded once at startup; errors go to stderr. Dataset paths default to `data/kaggle` beside the code, independent of the client's working directory. Override with `--data-dir /path/to/csvs` (all six files are required).

Configure an MCP host with absolute paths:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/absolute/path/to/python3",
      "args": ["/absolute/path/to/server.py"]
    }
  }
}
```

The implementation follows the MCP [stdio transport](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports) and [tool interface](https://modelcontextprotocol.io/specification/2025-06-18/server/tools), with protocol version `2025-06-18`. The host must initialize and send `notifications/initialized` before calling tools. This is a tools-only stdio server; HTTP, resources, prompts and subscriptions are not advertised.

Natural-language interpretation and conversation context belong to the connected LLM. For example, “When did Flamengo last play Corinthians?” maps to `search_matches(team="Flamengo", opponent="Corinthians", limit=1)`. The host can answer “What was the score?” from that result. There is no separate keyword-based natural-language parser or bundled LLM. Structured results and readable JSON text are both returned, allowing the host to produce prose answers.

| Tool | Purpose |
|---|---|
| `search_matches` | Team/opponent, home/away, inclusive dates, competition, season, stage, derby or source filters; latest first |
| `team_statistics` | Wins/draws/losses, goals, points, win percentage, competition breakdown and snapshot players |
| `head_to_head` | Symmetric team records and latest fixture across both venue orientations |
| `search_players` | Name substring, nationality, club, position and minimum rating; highest rating first |
| `standings` | Calculated Serie A/Serie B tables, leader, completeness and relegation candidates |
| `bracket` | Cup fixtures grouped by recorded stage/round |
| `analysis` | Goals per match, venue win rates, ranked team records, highest-scoring teams and biggest wins |
| `season_comparison` | Competition or team trends over selected seasons |
| `graph_neighbors` | Traverse team/match/competition and player/club relationships |
| `dataset_info` | Source counts, coverage, missing results and score conflicts |

`search_matches`, `search_players` and `graph_neighbors` return `total`, `items`, `offset` and `next_offset`. Follow `next_offset` until null to retrieve everything; limits range from 1–500. Aggregates always use all matching records, regardless of list limits. Win rates are percentages. Match scores are integers or null. `analysis.team_records` ranks by win rate then points; sample sizes are included. `highest_scoring_teams` ranks by goals for. All tools are described by discoverable JSON schemas, and invalid calls return explicit errors.

Python callers can use the same service directly:

```python
from soccer import SoccerGraph

graph = SoccerGraph()
print(graph.head_to_head("Palmeiras", "Santos"))
print(graph.standings("Brasileirão", 2019)["table"][0])
```

The latter returns Flamengo with 90 points, 28 wins, 6 draws, 4 losses, 86 goals for and 37 against. The tests also verify complete 2018 and 2020 Serie A seasons.

[Sample questions](sample_questions.json) contains 26 natural-language questions and their corresponding tool arguments, covering all query categories. These mappings are exercised by the test suite. Some questions legitimately return no data; for example, this FIFA snapshot contains neither Flamengo nor São Paulo squads, and a full-name player search may not match an abbreviated FIFA name. Use shorter name fragments when appropriate. Empty results must not be interpreted as proof that a player or team does not exist.

Data handling and limits:

- UTF-8 text, accent-insensitive comparisons, state suffixes and common full-name aliases are supported. Ambiguous clubs such as América-MG/América-RN, Botafogo-SP/Botafogo-RJ and Flamengo-PI/Flamengo-RJ remain distinct. The alias table is explicit and extendable; it is not an exhaustive football entity resolver.
- An in-memory graph indexes canonical teams to fixtures. Matches have stable IDs and edges to teams and competitions; FIFA IDs identify player nodes with snapshot club edges. `graph_neighbors` supports paginated traversal. All original match rows, including extended statistics and stadium data, remain in `sources`; player attributes preserve the original FIFA columns.
- Exact duplicate fixture identities merge across files. A cross-source difference of at most one calendar day also merges when only one candidate exists and scores agree or are missing. This handles evening matches represented on the next UTC day. Distinct same-source dates are not collapsed by this heuristic. Files load in the order listed in `soccer.FILES`: dedicated competition files take precedence, then historical results, then extended statistics. Missing scores can be filled; conflicting known scores are reported by `dataset_info`.
- A merged fixture inherits the primary source's season, preserving seasons that extend into the next year, such as 2020. Extended-only rows have no season column and therefore use calendar year. Dates differing by more than one day and unknown aliases can still leave duplicates. Coverage and quality notes should accompany conclusions.
- Undated fixtures are retained and sorted last, and excluded by date-range filters. Missing scores are null and excluded from played-match statistics. CSV errors report the source and line rather than silently discarding data.
- League standings use 3/1/0 points and sort by points, wins, goal difference, goals for, then name. They do not model official deductions, disciplinary rules or head-to-head tie-breakers. Complete double-round-robin coverage requires exactly one played match per ordered team pair. A calculated leader is not an authoritative champion. Four relegation candidates are shown only for complete seasons from 2006 onward; earlier formats need external rules.
- Cup brackets group recorded fixtures; advancement and champions are not invented. The primary Copa do Brasil file uses numerical rounds: 7 through 2016 and 8 from 2017 are treated as finals. Extended-only fixtures lack round data and cannot be reliably selected as finals. Semifinals are never included by substring matching. Serie C group standings are not flattened into a fictitious league table.
- No supplied file records individual goal scorers, so top-scorer requests explicitly report unavailable data. Penalty shootouts and aggregate tie-breakers are unavailable. Player clubs are historical FIFA affiliations, not current squads or match-day lineups. Derby detection uses a curated, non-exhaustive rivalry list.

Run verification:

```sh
python3 -m unittest -v
python3 -m py_compile soccer.py server.py test_soccer.py
```

Given/When/Then scenarios cover all six sources and row preservation, normalization, date parsing, merged fixtures, missing results, known standings, player filters, cross-file graph queries, pagination, validation, 26 sample questions and an actual MCP stdio subprocess. Performance checks enforce under 2 seconds for a loaded lookup and under 5 seconds for a full aggregate query. Startup loads the data once; performance depends on host hardware.

Data attribution (demo/non-commercial purpose as specified in `TASK.md`):

| Files | Source | License declared in task |
|---|---|---|
| `Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`, `Libertadores_Matches.csv` | [Ricardo Mattos, Brazilian match data](https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro) | CC BY 4.0 |
| `BR-Football-Dataset.csv` | [cuecacuela, Brazilian football matches](https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches) | CC0 Public Domain |
| `novo_campeonato_brasileiro.csv` | [macedojleo, Campeonato Brasileiro 2003–2019](https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019) | CC BY 4.0 |
| `fifa_data.csv` | [youssefelbadry10, FIFA players data](https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data) | Apache 2.0 |

Original CSV files are unmodified. Normalization and merged query representations are generated in memory by this implementation.
