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

## Run the Python implementation

Requires Python 3.10 or newer. There are **no runtime dependencies**, credentials,
external services, or data downloads.

```bash
python server.py
# Or use an explicit data location:
python server.py --data-dir /absolute/path/to/data/kaggle
```

The process reads newline-delimited JSON-RPC from stdin and writes only protocol
responses to stdout. Startup failures go to stderr. It loads the data once and
exits when stdin closes. It serves the stable MCP `2025-11-25` protocol with
negotiation for `2025-06-18`, `2025-03-26`, and `2024-11-05`.

Configure an MCP-capable LLM client with absolute paths, for example:

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

The **client LLM interprets natural language**, chooses tools, and formats the
answer. This server performs deterministic data queries; it does not require or
embed an LLM. Conversation context stays in the client: after “When did Flamengo
last play Corinthians?”, use `search_matches` with both teams and `limit: 1`;
for “What was the score?”, reuse that result or call `get_match` with its ID.

Protocol implementation references:
[tools](https://modelcontextprotocol.io/specification/2025-11-25/server/tools),
[lifecycle](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle),
and [schema](https://modelcontextprotocol.io/specification/2025-11-25/schema).
The server implements initialize, initialized notifications, ping, tools/list,
and tools/call. Tools return readable text plus JSON and `structuredContent`.
All tools are read-only and validate their arguments; no arbitrary code or SQL
execution is exposed. Unsupported methods return JSON-RPC errors.

## Available tools

| Tool | Use |
|---|---|
| `search_matches` | Team/opponent, home/away, competition, season, inclusive dates, stage, source; newest first |
| `get_match` | Full match, extended statistics, original CSV rows and source lines |
| `team_statistics` | Wins/draws/losses, goals, points, home/away and competition breakdowns; FIFA players |
| `head_to_head` | Both teams' records and latest meeting |
| `search_players` | Name substring, nationality, club, position group, minimum rating; all FIFA attributes |
| `standings` | Calculated league table, coverage check, leader and relegation candidates |
| `competition_bracket` | Observed stages, paired teams, match legs and aggregate scores |
| `statistics` | Goals/game, home wins, largest margins, team goals and home/away win-rate rankings |
| `season_trends` | Compare up to 30 seasons, optionally for one team |
| `derbies` | Curated Brazilian rivalries |
| `competitions` | Available seasons and match counts, optionally for one team |
| `graph_neighbors` | Team, match, opponent, competition and historical player relationships |
| `data_status` | Source coverage, rejected rows, conflicts, counts and limitations |

Call `tools/list` for complete JSON input schemas. Optional arguments should be
omitted, not set to null. Seasons are integer years. Search results paginate with
`limit` (1–500), `offset`, `total`, and `next_offset`. Continue until
`next_offset` is null when answering requests for all records. `stage: "final"`
selects finals, not semifinals. Dates accept ISO, Brazilian dates and timestamps.
Players support position groups `forward`, `midfielder`, `defender`, `goalkeeper`
and individual FIFA position codes. Extended numeric statistics retain missing
values as null. Individual player goal totals are unavailable in these sources;
FIFA Finishing/Overall ratings must never be presented as goals scored.

[28 sample natural-language questions and tool calls](sample_questions.json)
are executed by the test suite. Questions about absent players or incomplete
seasons legitimately produce empty results or qualified calculated answers.

## Data model and interpretation

The in-memory graph uses stable `team:`, `match:`, `player:` and `competition:`
IDs. Edges include `PLAYED_HOME`, `PLAYED_AWAY`, `IN_COMPETITION` and
`PLAYS_FOR_SNAPSHOT`. Queries use an index of matches by normalized team.
Accents, case, common full names and state suffixes normalize across sources;
known homonyms such as América-MG/RN and Botafogo-RJ/PB/SP remain distinct.
Aliases are deliberately curated rather than fuzzy guesses. Unrecognized team
variants may remain separate entities.

Match identity is competition, calendar date and ordered home/away teams.
Records from different sources with identical teams/scores within one day also
merge, accommodating observed midnight date shifts. All source rows survive in
`get_match`. Priority is Brasileirão, Brazilian Cup, Libertadores, historical
Brasileirão, then extended statistics. Conflicting scores use the first source
and are reported by `data_status`; later sources enrich statistics and missing
metadata. Authoritative season fields survive merging, including 2020 matches
played in 2021. Extended-only records derive their season from calendar year.

All 42,161 rows across the six provided files load, including 18,207 players.
The Libertadores row with unknown date, season and score remains queryable
with null fields. Invalid rows are reported, not silently discarded. Missing
scores do not become 0–0 draws. Source filtering selects canonical matches
containing evidence from that source; raw values remain accessible separately.

Copa do Brasil numeric stage mapping follows the observed dataset conventions:
final round 6 in 2012, 8 in 2013–15, 7 in 2016, 8 in 2017–20, and 7 from 2021.
The provided 2021 cup source stops at the round of 16: it does not establish a
final. Extended-only cup matches with no stage remain `unknown stage`.
Brackets present observed ties; penalty winners and advancement are not guessed.

Standings use 3 points/win and 1/draw, sorted by points, wins, goal difference,
goals scored, then alphabetical order. They do not apply disciplinary deductions
or official remaining tie-breaks. The 2019 table reproduces Flamengo's 90 points
and 38 matches. Completeness requires every ordered team pair exactly once in
a Brasileirão season of 20/22/24 teams and every team having all results.
Only complete Brasileirão tables from 2006 onward return bottom-four relegation
**candidates**, not official decisions. Other seasons and formats need separate
rules. All results describe the dataset, not live soccer; missing coverage must
not be presented as a complete schedule or final official table. Historical
FIFA club membership is not evidence that a player appeared in a particular match.

## Test and build

```bash
python -m unittest -v
python -m py_compile soccer.py server.py test_soccer.py build.py
python build.py
python dist/brazilian-soccer-mcp.pyz --data-dir "$PWD/data/kaggle"
```

The tests cover hand-calculated outcomes, duplicate/conflicting sources,
normalization, all six files, season attribution, finals, graph endpoints,
missing data, pagination, invalid input, protocol lifecycle, a stdio subprocess,
and the sample questions. Full-data performance tests require combined simple
lookups under 2 seconds and an aggregate query under 5 seconds after loading.

The zipapp contains Python code only and builds without downloading anything.
Pass `--data-dir` when running it. Optional wheel packaging is available using
`python -m pip wheel . --no-deps --wheel-dir dist` in an environment with
setuptools and wheel installed (or access to PyPI). When installing elsewhere, retain the
six CSVs and pass `--data-dir /absolute/path/to/data/kaggle` to the installed
`brazilian-soccer-mcp` command. Wheel packaging requires setuptools and wheel; the standard-library zipapp
build and running directly from this directory require no installation.
