# Brazilian Soccer MCP Server

An MCP (Model Context Protocol) server in C++17 that turns six Kaggle CSV files
of Brazilian football into a queryable knowledge graph. An LLM host connects
over stdio and asks questions about matches, clubs, players, competitions and
aggregate statistics; every answer is computed from the raw results, not from a
pre-baked table.

Implements the specification in [TASK.md](TASK.md) (also
`brazilian-soccer-mcp-guide.md`).

## Quick start

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j
ctest --test-dir build --output-on-failure     # 117 BDD scenarios
```

```bash
./build/bsmcp --summary                        # what got loaded
./build/bsmcp --list-tools                     # the tool catalogue
./build/bsmcp --tool standings --args '{"competition":"serie a","season":2019}'
./build/bsmcp                                  # speak MCP on stdin/stdout
```

There are no third-party dependencies: JSON, CSV, UTF-8 handling and the test
harness are all in `src/` and `tests/`.

### Registering with an MCP host

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/absolute/path/to/build/bsmcp",
      "args": ["--data-dir", "/absolute/path/to/data/kaggle"]
    }
  }
}
```

The data directory is resolved from `--data-dir`, then `$BSMCP_DATA_DIR`, then
`./data/kaggle` walking a few levels up, then the path baked in at build time —
so the binary works from any working directory.

## What the server exposes

Fourteen tools, covering the five capability groups of the specification.

| Group | Tools |
|---|---|
| Match queries | `search_matches`, `head_to_head` |
| Team queries | `team_stats`, `team_profile`, `list_teams` |
| Player queries | `search_players`, `player_profile`, `team_squad` |
| Competition queries | `standings`, `competition_bracket`, `list_competitions` |
| Statistical analysis | `competition_stats`, `compare_seasons` |
| Provenance | `dataset_summary` |

Each tool returns both a prose answer (what the model reads back to the user)
and a `structuredContent` JSON mirror of the same facts.

Sample output:

```
$ ./build/bsmcp --tool standings --args '{"competition":"serie a","season":2019}'
2019 Brasileirão Série A (computed from 380 matches, source: Brasileirao_Matches.csv)
  # Club                      P   W   D   L   GF   GA   GD  Pts
  1 Flamengo                 38  28   6   4   86   37  +49   90  Champion
  2 Santos                   38  22   8   8   60   33  +27   74
  3 Palmeiras                38  21  11   6   61   32  +29   74
 ...
 17 Cruzeiro                 38   7  15  16   27   46  -19   36  Relegated

Champion: Flamengo with 90 points.
Relegated (bottom four): Cruzeiro, CSA, Chapecoense, Avaí
```

That table matches the real 2019 final standings row for row, including the
wins tie-break that puts Santos ahead of Palmeiras on 74 points.

## What is loaded

All six files, ~24k match rows and 18,207 players, in about 0.25 s.

| File | Rows | Covers |
|---|---|---|
| `Brasileirao_Matches.csv` | 4,180 | Série A 2012–2022 |
| `Brazilian_Cup_Matches.csv` | 1,337 | Copa do Brasil 2012–2021 |
| `Libertadores_Matches.csv` | 1,255 | Libertadores 2013–2022 |
| `BR-Football-Dataset.csv` | 10,296 | Série A/B/C + Copa do Brasil 2014–2023, with shots and corners |
| `novo_campeonato_brasileiro.csv` | 6,886 | Série A 2003–2019, with stadiums |
| `fifa_data.csv` | 18,207 | FIFA player ratings snapshot |

Merged coverage: **Série A 2003–2023**, **Copa do Brasil 2012–2023**,
**Libertadores 2013–2022**, plus Série B and C from 2014.

## Design notes

### Club identity is the hard part

The same club is spelled five different ways across the corpus:

```
Brasileirao_Matches.csv       "Atletico-MG"            (+ a state column)
novo_campeonato_brasileiro    "Atlético-MG"            (+ UF columns)
Brazilian_Cup_Matches.csv     "Atlético Mineiro - MG"
Libertadores_Matches.csv      "Atlético-MG"            (foreign: "Nacional (URU)")
BR-Football-Dataset.csv       "Atletico Mineiro"       (no state at all)
fifa_data.csv                 "Atlético Mineiro"
```

`src/team_registry.cpp` resolves a raw name by peeling a trailing region tag,
folding accents/case/punctuation, stripping club-type noise (`FC`, `EC`,
`Sport Club`, `Futebol`), and finally consulting an explicit alias table for the
clubs whose long and short forms differ materially.

Identity is `(base name, state)`, not just the base name, because different
clubs share names: **Flamengo-RJ vs Flamengo-PI**, **Atlético MG/PR/GO**,
**Operário MS/MT/PR**, and three different **River Plate**s (Argentina, Uruguay,
Sergipe). The registry is built in two passes — observe every spelling, then
decide which base names are ambiguous — so that an unqualified "Flamengo"
resolves to the club that dominates the data (RJ) rather than to a coin flip.

Ambiguity in the other direction is handled too: `Central SC` and `River AC`
end in what look like state codes but are really *Sport Club* and *Atlético
Clube*, so those spellings are pinned by alias before the suffix peeler runs.

### Overlapping sources are de-duplicated

Série A 2014–2019 appears in **three** files and Copa do Brasil in two. Left
alone, an average or a league table would count those seasons two or three
times. For every `(competition, season)` the loader elects one *primary*
source — the file with the most matches, ties broken by a fixed preference —
and all aggregates count only primary rows:

```
Série A 2003-2011  ->  novo_campeonato_brasileiro.csv
Série A 2012-2022  ->  Brasileirao_Matches.csv
Série A 2023       ->  BR-Football-Dataset.csv
```

Every tool takes `sources: "all"` to opt back into the full row set.

### Answers state their limits

The corpus has real gaps, and the server says so rather than papering over them:

* 82 Brasileirão fixtures carry `NA` scores (the 2022 file was scraped
  mid-season). Those fixtures are listed by `search_matches` but excluded from
  records, and `team_stats` and `standings` report how many were skipped.
* A final level on aggregate went to penalties, which the corpus does not
  record — `competition_bracket` says "decided on penalties" instead of naming
  a champion it cannot know.
* `fifa_data.csv` licenses only a subset of Brazilian clubs, so `team_squad`
  for Flamengo explains that an empty squad is missing data, not an empty club,
  and points at the clubs that do have squads.
* The corpus has no goalscorer data, so there is no top-scorer tool; only
  team-level scoring is inferable.

### Layout

```
src/
  json.{hpp,cpp}              minimal JSON DOM, parser and serializer
  csv.{hpp,cpp}               RFC 4180 reader (BOM, CRLF, embedded newlines)
  text_utils.{hpp,cpp}        UTF-8 folding, accent stripping, date parsing
  team_registry.{hpp,cpp}     club identity resolution
  model.hpp                   Match, Player, SourceInfo records
  dataset.{hpp,cpp}           CSV ingestion, indexes, primary-source election
  query_engine.{hpp,cpp}      tool catalogue, filters, shared formatting
  query_tools_*.cpp           the fourteen tool bodies, grouped by capability
  mcp_server.{hpp,cpp}        JSON-RPC 2.0 / MCP over stdio
  main.cpp                    entry point and CLI modes
tests/
  bdd.hpp                     Given/When/Then harness
  test_*.cpp                  117 scenarios
```

## Testing

Behaviour-driven scenarios, written Given/When/Then, run as one ctest target:

```
Feature: Competition queries
  [PASS] Compute the 2019 Brasileirão final standings from match results
  [PASS] Name the clubs relegated in a season
  [PASS] Say so honestly when a final was decided on penalties
  ...
117 scenarios passed, 0 failed, 117 total
```

The two Gherkin scenarios quoted in the specification ("Find matches between
two teams", "Get team statistics") are implemented verbatim in
`tests/test_match_queries.cpp` and `tests/test_team_queries.cpp`.

Coverage by area:

| File | Focus |
|---|---|
| `test_json.cpp` | JSON round-trips, `\u` escapes, UTF-8, malformed input |
| `test_csv.cpp` | Quoting styles, BOM, CRLF, ragged rows |
| `test_text_utils.cpp` | Accent folding, the three date formats, `NA` handling |
| `test_team_registry.cpp` | Name variants, same-name clubs, false-suffix traps |
| `test_dataset.cpp` | Row counts, coverage, de-duplication, cross-file links |
| `test_match_queries.cpp` | Search, filters, head-to-head, derbies, error paths |
| `test_team_queries.cpp` | Records, home/away splits, per-competition breakdown |
| `test_player_queries.cpp` | Player search, profiles, squads, unlicensed clubs |
| `test_competition_queries.cpp` | Standings vs. the real 2019 table, brackets, champions |
| `test_statistics.cpp` | Averages, outcome splits, season comparison, provenance |
| `test_mcp_protocol.cpp` | Handshake, `tools/list`, `tools/call`, JSON-RPC errors |
| `test_performance.cpp` | The 2 s / 5 s budgets from the specification |
| `test_sample_questions.cpp` | 28 natural-language questions end to end |

Measured on the shipped data: corpus loads in ~0.25 s, the slowest simple
lookup is ~3 ms and the slowest whole-corpus aggregate ~4 ms — three orders of
magnitude inside the specification's budgets, because everything is answered
from memory.

## Data sources

Kaggle data can't be downloaded without an account so these (freely available
with attribution) data sets have been downloaded for use here:

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
