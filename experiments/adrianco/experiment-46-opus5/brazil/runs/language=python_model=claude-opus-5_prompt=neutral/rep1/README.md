# Brazilian Soccer MCP Server

An MCP (Model Context Protocol) server that answers natural-language questions
about Brazilian football. It loads the six Kaggle CSVs in `data/kaggle` into an
in-memory knowledge graph — clubs, players, matches, competitions, seasons — and
exposes 21 query tools plus 2 resources over stdio.

Specification: [`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md)
(also mirrored as `TASK.md`).

```
$ python -m brazilian_soccer.demo "Who won the 2019"
2019 Brasileirão Série A Final Standings (calculated from 380 matches in the dataset):

 1. Flamengo - 90 pts (28W, 6D, 4L) GF 86 GA 37 GD +49 - Champion
 2. Santos - 74 pts (22W, 8D, 8L) GF 60 GA 33 GD +27 - Libertadores
 3. Palmeiras - 74 pts (21W, 11D, 6L) GF 61 GA 32 GD +29 - Libertadores
 ...
17. Cruzeiro - 36 pts (7W, 15D, 16L) GF 27 GA 46 GD -19 - Relegated
```

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"              # or: pip install -r requirements-dev.txt

python -m brazilian_soccer.demo      # answer 28 sample questions
python -m brazilian_soccer.server    # run the MCP server on stdio
pytest                               # 244 tests, ~4s
```

`make install`, `make test`, `make demo` and `make serve` do the same things.

Requires Python 3.10+ and `mcp>=1.2`. Nothing else: the CSV loading, the
knowledge graph and the query layer are pure standard library, so there is no
compiled dependency to build. The query tests run even without the MCP SDK
installed — the three modules that drive the protocol skip themselves.

### Connecting an MCP client

Claude Desktop (`claude_desktop_config.json`) or any other MCP client:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/path/to/repo/.venv/bin/python",
      "args": ["-m", "brazilian_soccer.server"],
      "cwd": "/path/to/repo"
    }
  }
}
```

The CSVs are looked up in `$BRAZILIAN_SOCCER_DATA_DIR`, then in the `data/kaggle`
of this checkout, then in `./data/kaggle` — so the server also finds its data
when the package itself is installed into `site-packages`.

## What was built

| Module | Responsibility |
|---|---|
| `normalization.py` | Team-name parsing, curated club table, date/score/competition parsing |
| `teams.py` | Two-pass registry: every raw spelling → one canonical club; fuzzy user lookup |
| `loader.py` | Reads the six CSVs (stdlib `csv`), de-duplicates and merges overlapping records |
| `models.py` | `Team`, `Match`, `Player`, `TeamRecord` (points, goal difference, win rate) |
| `graph.py` | Node/edge store + indexes; process-wide cached `load_graph()` |
| `queries.py` | The query API — matches, teams, players, competitions, statistics |
| `formatting.py` | Renders results as the text layouts shown in the specification |
| `server.py` | FastMCP server: 21 tools, 2 resources |
| `demo.py` | 28 sample questions mapped to tool calls (used by the test-suite too) |

Loaded graph: **1,003 clubs, 16,782 matches, 18,207 players — 36,182 nodes and
103,300 edges**, covering 2003-03-29 to 2023-12-07. Start-up takes ~0.5s; every
query then runs from memory (simple lookups are sub-millisecond).

### Competitions covered

| Competition | Matches | Seasons |
|---|---|---|
| Brasileirão Série A | 8,404 | 2003–2023 |
| Brasileirão Série B | 3,677 | 2014–2023 |
| Brasileirão Série C | 1,795 | 2014–2023 |
| Copa do Brasil | 1,657 | 2012–2023 |
| Copa Libertadores | 1,249 | 2013–2022 |

## The knowledge graph

```
(match)  -[:HOME_TEAM]->      (team)
(match)  -[:AWAY_TEAM]->      (team)
(match)  -[:IN_COMPETITION]-> (competition)
(match)  -[:IN_SEASON]->      (season)
(player) -[:PLAYS_FOR]->      (team)
(player) -[:FROM_COUNTRY]->   (country)
```

Players and matches meet at the *same* team nodes, which is what makes
cross-file questions work: "who plays for Internacional, and how has
Internacional done?" walks `player → team → matches`.

The store is plain Python — no database to install or seed. At this size
(36k nodes) an in-memory graph with sorted adjacency lists answers everything
faster than a round-trip to an external store would, and it keeps the demo a
single `pip install` away from running.

## MCP tools

**Matches** — `search_matches`, `last_meeting`, `head_to_head`, `derbies`
**Teams** — `team_statistics`, `team_profile`, `compare_teams`, `home_away_split`, `find_teams`
**Players** — `search_players`, `player_profile`, `club_squad`, `players_by_club`
**Competitions** — `standings`, `competition_summary`, `knockout_bracket`, `list_competitions`
**Statistics** — `biggest_wins`, `team_rankings`, `compare_seasons`, `dataset_statistics`
**Resources** — `soccer://overview`, `soccer://teams`

Every tool returns formatted text (the structured dicts behind them live in
`queries.py`), and bad input is answered rather than raised — asking about
"Sporting Lisbon" returns *"No team matching 'Sporting Lisbon' in the dataset"*
instead of an error the model has to interpret.

## Data problems and how they are handled

The interesting work was reconciling six files that disagree with each other.

**Team names.** `Palmeiras-SP`, `Palmeiras`, `Palmeiras - SP` and `SE Palmeiras`
are one club; `Santa Cruz - PE`, `- RN` and `- RS` are three. Names are parsed
into a slug plus a state/country code, a curated table resolves the clubs whose
spellings collide (`Atlético-MG` vs `Athletico-PR` vs `Atlético-GO`, all written
as "Atlético" somewhere), and the remainder are grouped generically: one state
seen for a slug means the state-less spellings merge into it; several states
means the state stays part of the identity.

**Duplicate matches.** 23,954 match rows across five files collapse to 16,782
unique matches. Série A 2014–2019 appears in three files at once; without
merging, every table would count those seasons three times. Two records are the
same fixture when the competition and both teams match and the dates are close;
the merged match keeps the round from one file, the stadium from another and the
shot counts from a third.

**Seasons that cross the new year.** The pandemic-hit 2020 Série A finished in
February 2021, and one source records only a date. Early-year league matches are
attributed to the previous season, which is why the 2020 relegation places come
out right (Vasco, Goiás, Coritiba, Botafogo).

**Cup rounds without names.** The Copa do Brasil file numbers its rounds. Round
sizes identify them: the last round of a season has two legs (the final), the
one before four (semifinals), and so on — so `stage="final"` returns finals, not
semifinals.

**Mislabelled rows.** A couple of state-league matches are filed under "Serie A".
Teams with a fraction of the matches everyone else played are dropped from a
league table and reported (`Excluded as mislabelled in the source data: ...`).
One cup row names the same club as home and away; it is dropped at load time
rather than counted twice for that club.

**Honesty about gaps.** The 2023 Série A is three matches short in the source
data, and those matches decide the title, so no champion is declared for 2023 —
the answer says how many fixtures are missing. Likewise, the FIFA file is a
single-season snapshot with several Brazilian clubs unlicensed (and pseudonymous
player names at the licensed ones); asking for a player it does not contain
returns "not in the dataset" plus similar names, never a different player passed
off as the right one.

Validated against reality: every Série A champion from 2003 to 2022 computed
from the match data matches the real champion. Relegation matches too, except
where an off-field ruling overrode the results — the tables put Fluminense down
in 2003 and 2013, where in reality a court case and Portuguesa's points
deduction saved them. That is the expected behaviour for a table calculated
purely from match results, and the output always says it was.

## Required capabilities, and where each one lives

| Capability (from the specification) | Tool → query function | Test |
|---|---|---|
| MCP server exposing tools/handlers | `server.py` — FastMCP, 21 tools + 2 resources | `test_server.py`, `test_stdio_integration.py` |
| Loads the datasets in `data/kaggle` | `loader.load_dataset` (all six CSVs) | `test_loader.py::TestRealDataCoverage` |
| Matches by team (home, away, either) | `search_matches` → `queries.search_matches(team=…, venue=…)` | `TestSearchMatches::test_matches_between_two_teams`, `…::test_filter_by_competition_and_venue` |
| Matches by date range / season | `search_matches(season=…, date_from=…, date_to=…)` | `TestSearchMatches::test_matches_for_a_team_in_a_season`, `…::test_filter_by_date_range` |
| Matches by competition | `search_matches(competition=…)`, `knockout_bracket` | `TestSearchMatches::test_cup_finals_are_not_confused_with_semifinals` |
| Team record: W/D/L, goals for/against | `team_statistics` → `queries.team_stats` | `test_team_queries.py::TestTeamStatistics` |
| Player search by name | `player_profile`, `search_players(name=…)` | `TestPlayerSearch::test_search_by_name`, `TestPlayerProfile` |
| Players by nationality/club, with ratings | `search_players`, `club_squad`, `players_by_club` | `TestPlayerSearch::test_all_brazilian_players`, `…::test_players_at_a_brazilian_club` |
| Season standings from match results | `standings` → `queries.standings` | `test_competition_queries.py::TestStandings` |
| Aggregate statistics | `dataset_statistics`, `biggest_wins`, `team_rankings`, `compare_seasons` | `test_statistics.py` |
| Head-to-head between two teams | `head_to_head`, `compare_teams`, `last_meeting` | `test_match_queries.py::TestHeadToHead`, `::TestLastMeeting` |
| Automated tests over the query layer | 244 pytest tests | `pytest` |

## Tests

244 tests, BDD Given/When/Then scenarios written as pytest tests
(`pytest` runs in ~4s):

| File | Covers |
|---|---|
| `tests/features/brazilian_soccer.feature` | Gherkin contract, each scenario mapped to its test |
| `test_normalization.py` | Name/date/score/competition parsing rules |
| `test_team_registry.py` | Name variants, namesakes, fuzzy user lookup |
| `test_loader.py` | Cross-file merging, season derivation, cup stages, coverage |
| `test_graph.py` | Nodes, edges, indexes, caching |
| `test_match_queries.py` | Match search, head-to-head, derbies |
| `test_team_queries.py` | Team records, comparisons, rankings |
| `test_player_queries.py` | Player search, profiles, squads, cross-file links |
| `test_competition_queries.py` | Standings against the real 2019/2020 tables, brackets |
| `test_statistics.py` | Aggregates, biggest wins, season comparison |
| `test_server.py` | Tool registration, schemas, error handling |
| `test_stdio_integration.py` | A real client driving the server over stdio |
| `test_sample_questions.py` | All 28 sample questions answered, each < 2s |
| `test_performance.py` | Spec budgets: lookups < 2s, aggregates < 5s |

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

Demo / non-commercial use. All statistics are calculated from these datasets and
should be described as such rather than as official records.
