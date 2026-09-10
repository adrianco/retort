# Brazilian Soccer MCP Server

A Python 3.10+ offline knowledge graph over the six supplied Kaggle CSVs. No
third-party packages, database service, API keys, or network access are required.
All Python modules live in this directory.

```sh
python server.py --check       # ingestion report, coverage, licenses and diagnostics
python server.py               # MCP over stdin/stdout
python -m unittest -v          # fixtures, real-data scenarios and protocol tests
python -m compileall -q soccer.py server.py sample_queries.py test_soccer.py
```

The data path defaults to `data/kaggle/` **relative to the code**, independent of
working directory. Override with `python server.py --data-dir /path/to/csvs`.
Missing required files fail startup clearly. Invalid rows are reported by file and
line in `coverage`; unknown dates and unplayed scores remain queryable as nulls.

## Connect an LLM

Configure a stdio-capable MCP client with the absolute paths on your machine:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/absolute/path/to/python",
      "args": ["/absolute/path/to/this/directory/server.py"]
    }
  }
}
```

The connected LLM interprets natural language, calls the typed tools, and formats
answers. It also maintains conversational context for follow-ups such as “What
was the score?” The server itself is a deterministic data service, not an LLM or
a keyword-based question parser. No live LLM is needed to run the tests.

The server implements the [MCP stdio transport](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports),
initialization, version negotiation, ping, tools, and resources. Supported versions:
`2024-11-05`, `2025-03-26`, `2025-06-18`; unknown versions negotiate `2025-06-18`.
Send `notifications/initialized` after initialization. Requests and responses are
one JSON-RPC object per line; logs go only to stderr. Tool schemas reject unknown
arguments, wrong types and invalid pagination. Operational input errors are tool
results with `isError: true`; protocol errors use JSON-RPC errors.

## Query interface

| Tool | Purpose |
|---|---|
| `matches(filters, limit=50, offset=0)` | Fixtures/results, latest first, across all five match files |
| `team_stats(team, filters)` | W/D/L, goals, points, win rate, home/away and competition splits |
| `head_to_head(team, opponent, filters, limit=50)` | Full aggregate record and paginated recent fixtures |
| `players(name, nationality, club, position, min_rating, limit, offset)` | FIFA snapshot, ratings descending, all source attributes |
| `standings(competition, season, venue="either", source="")` | Calculated league table with completeness diagnostic and optional source filter |
| `analysis(filters, limit=10)` | Goal averages, biggest wins, team goals and home/away rankings |
| `compare_seasons(seasons, competition, team)` | Aggregate or team-specific trends |
| `team_info(team, season)` | Cross-file match record, competitions, historical player roster |
| `competition_info(competition, season)` | Stage-grouped results, available bracket information |
| `graph(entity, limit=50, offset=0)` | Paginated graph relationships by entity ID or team name |
| `match_detail(match_id)` | Complete original source rows, conflicts and extended statistics |
| `coverage()` | Source row counts, dates/seasons, licenses, deduplication and rejection diagnostics |

`filters` accepts `team`, `opponent`, `venue` (`home`, `away`, `either`),
`competition`, `season`, `start_date`, `end_date`, `stage`, `source` (CSV filename),
and `derbies`. Date bounds are inclusive. `opponent` and home/away venue require
`team`. Stages match exactly: `final` does not match `semifinals`. Competition
aliases include `Serie A`, `Brasileirão`, and `Libertadores`.

Pagination returns `total`, `items`, `limit`, `offset`, and `next_offset`. Limits
are 1–1000; follow `next_offset` to retrieve all matches or players. Aggregates
always use all matching records, independent of displayed match pagination.
Win rates are percentages. Empty collections return total zero; a zero-match
average/rate is zero, accompanied by the match count.

Player search is accent-insensitive; nationality accepts `Brazil` or `Brazilian`.
Club aliases match canonical clubs; partial club searches work when no exact team
exists. Positions accept FIFA codes or `forward`, `midfielder`, `defender`, and
`goalkeeper` (also plural). Missing players return an empty result, not a fabricated
profile. In particular, there are no Flamengo or São Paulo club records in this FIFA snapshot.

Resources `soccer://coverage` and `soccer://guide` expose the dataset manifest and
LLM answer instructions. `graph` links teams to home/away matches, matches to
competitions and seasons, and players to clubs using `PLAYS_FOR_SNAPSHOT` edges.
Match IDs are deterministic hashes; player IDs use the FIFA ID. Match detail
retains every contributing original row and file/line attribution.

Python example:

```python
from soccer import SoccerGraph

g = SoccerGraph()
print(g.head_to_head("Flamengo-RJ", "Fluminense"))
print(g.team_stats("Corinthians", {"venue": "home", "season": 2022}))
print(g.players(nationality="Brazil", position="forward", limit=10))
print(g.standings("Serie A", 2019)["table"][:3])
# Flamengo 90 points, Santos 74, Palmeiras 74; 380 matches, 20 teams.
```

## Data quality and limits

* Accents, common full club names and state suffixes normalize to shared entities.
  Ambiguous clubs keep state distinctions (e.g. Botafogo-PB vs Botafogo-RJ).
  Aliases are deliberately explicit and extensible in `CLUBS`/`ALIASES`.
* Match identity uses competition, calendar date and ordered home/away teams.
  Duplicates combine source records and extended corners/attacks/shots. A unique
  adjacent-day match is also merged when scores, teams, competition and season
  agree, accommodating late kickoffs recorded on different calendar days. An
  explicit season overrides the extended file's inferred calendar year, including
  the 2020 season's games played in early 2021. Same-source adjacent fixtures and
  reversed legs are kept separate. Raw dates are preserved, not globally shifted.
* Priority for score conflicts follows `SOURCES` order: dedicated competition
  files, extended statistics, then historical data. Conflicting scores remain in
  match detail and coverage diagnostics. This is an auditable reconciliation
  policy, not a claim that every conflicting result has been independently verified.
* The historical adapter corrects its Bahia/BH and Vitória/ES state anomalies
  within that Série A source. Original rows are preserved; these corrections do
  not merge distinct Vitória-ES cup entities.
* Extended records without an explicit season infer it from their date and expose
  `season_inferred`. There are remaining source anomalies and incomplete seasons:
  for example, the union includes extra Série A records in 2014/2016 and only 377
  in 2023. The `complete_double_round_robin` check examines every directed team
  pairing, not merely a count. Use source filters to inspect disagreements.
  Source filters select matches with that provenance; merged fields still follow
  the reconciliation policy. Inspect `match_detail` for a source's original values.
* Tables sort by points, wins, goal difference and goals scored, then name for
  deterministic display. No sanctions, disciplinary tie-breakers or official
  relegation rules are available. Report dataset leaders/bottom places without
  presenting them as independently verified champions/relegated teams. Série C
  standings are rejected because its group/phase structure is absent.
* Cup rounds vary by season. Finals are explicitly marked **inferred** only when
  the highest numbered round has two teams and one or two legs. Unlabeled extended
  cup matches cannot always be classified. Libertadores stages come from the CSV.
  Stage-grouped results are available, but penalty shootouts and reliable bracket
  advancement are not. Neither match-level individual scorers nor top-scorer
  rankings can be inferred from team scores or FIFA ratings.
* FIFA ratings/club memberships are a historical snapshot, not current rosters.
  Missing dates/scores remain null. An undated Libertadores final is retained and
  excluded from date-constrained queries and played-match aggregates.
* Derbies use the explicit traditional-rivalry list in `RIVALRIES`; it is not an
  exhaustive list of every regional rivalry.

## Examples and validation

[sample_queries.py](sample_queries.py) contains **27 natural-language questions**
and corresponding executable tool calls across all requested categories. Tests
exercise every mapping through MCP. When a question needs unavailable data, the
LLM should state the limitation: for example, return stage-grouped results for a
bracket request, or a historical-snapshot empty result for a missing player.

`test_soccer.py` includes Given/When/Then-style fixture scenarios with independently
specified expected W/D/L, goals, averages and deduplication outcomes. Real-data
checks account for every row in all six files, verify the calculated 2019 table,
exercise filters/players/derbies, and enforce the task's <2-second simple-query
and <5-second aggregate-query targets. A subprocess test covers real stdio
initialization and tool invocation from a different working directory.

## Dataset attribution

Demo/non-commercial project; retain each upstream dataset's license and attribution.

| Files | Source | License recorded by the supplied specification |
|---|---|---|
| `Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`, `Libertadores_Matches.csv` | [Ricardo Mattos: Jogos do Campeonato Brasileiro](https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro) | CC BY 4.0 |
| `BR-Football-Dataset.csv` | [Brazilian Football Matches](https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches) | CC0 |
| `novo_campeonato_brasileiro.csv` | [Campeonato Brasileiro 2003–2019](https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019) | CC BY 4.0 |
| `fifa_data.csv` | [FIFA Players Data](https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data) | Apache 2.0 |

See [TASK.md](TASK.md) for the supplied requirements.
