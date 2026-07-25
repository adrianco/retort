# Brazilian Soccer MCP Server

An [MCP](https://modelcontextprotocol.io) server that turns six Kaggle datasets of
Brazilian football into a queryable knowledge graph an LLM can ask questions of:
matches, clubs, competitions, league tables and FIFA player data.

Implemented in **C11 with no third-party dependencies** — the CSV reader, JSON
parser/serialiser, hash maps and the JSON-RPC/MCP transport are all in `src/`.

```
$ make && ./bin/brsoccer-mcp --call standings '{"season":2019}'

2019 Brasileirão Série A - table calculated from match results (3 points for a win)

  #  Club                        P    W    D    L    GF   GA   GD   Pts
  -- --------------------------- ---- ---- ---- ---- ---- ---- ---- ----
   1 Flamengo                      38   28    6    4   86   37  +49   90   <- champion
   2 Santos                        38   22    8    8   60   33  +27   74
   3 Palmeiras                     38   21   11    6   61   32  +29   74
   ...
  17 Cruzeiro                      38    7   15   16   27   46  -19   36   <- relegated

380 matches used, 20 clubs.
Champion: Flamengo with 90 points.
```

---

## Quick start

```bash
make                # build bin/brsoccer-mcp
make test           # build and run the BDD test suite (93 scenarios, 460 checks)
make demo           # answer the 28 sample questions from the specification
make serve          # run the MCP server on stdio
```

Requires only a C11 compiler and `make`.

### Using it from an MCP client

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/absolute/path/to/bin/brsoccer-mcp",
      "args": ["--data", "/absolute/path/to/data/kaggle"]
    }
  }
}
```

The server speaks JSON-RPC 2.0 over newline-delimited stdio and implements
`initialize`, `notifications/initialized`, `ping`, `tools/list` and `tools/call`.
Data is loaded before the transport starts (~0.05 s) and all diagnostics go to
stderr, so stdout carries protocol messages only.

### Using it from the shell

```bash
./bin/brsoccer-mcp --list-tools
./bin/brsoccer-mcp --info
./bin/brsoccer-mcp --call head_to_head '{"team_a":"Flamengo","team_b":"Fluminense"}'
./bin/brsoccer-mcp --call search_players '{"nationality":"Brazil","limit":10}'
./bin/brsoccer-mcp --demo
```

---

## The tools

Fourteen read-only tools covering the five capability groups in the specification.
Each returns a prose answer plus a `structuredContent` object carrying the same
figures in machine-readable form.

| Tool | Answers questions like |
|------|------------------------|
| `search_matches` | "Show me all Flamengo vs Fluminense matches", "Find all Copa do Brasil finals", "Show me all derbies in 2023" |
| `head_to_head` | "Compare Palmeiras and Santos head-to-head", "When did Flamengo last play Corinthians?" |
| `team_stats` | "What is Corinthians' home record in 2022?" |
| `team_profile` | "What competitions has Palmeiras played in?" |
| `standings` | "Who won the 2019 Brasileirão?", "Which teams were relegated in 2020?" |
| `rank_teams` | "Which team scored the most goals in Série A 2023?", "Which team has the best away record?" |
| `competition_stats` | "What's the average goals per match in the Brasileirão?" |
| `biggest_wins` | "Show me the biggest wins in the dataset" |
| `search_players` | "Find all Brazilian players", "Show me all forwards at Brazilian clubs" |
| `player_profile` | "Who is Neymar?" |
| `club_squads` | "Which Brazilian clubs have the best FIFA squads?" |
| `compare_seasons` | "Compare the 2018 and 2019 seasons" |
| `list_teams` | "Which clubs are called Atlético?" |
| `dataset_info` | "What data is available, and what are its limits?" |

Arguments are forgiving, because the caller is a language model working from a user's
phrasing: competitions accept `brasileirao`, `Série A` or `serie_a`; clubs accept
`flamengo`, `Flamengo-RJ` or `CR Flamengo`; numbers may arrive as strings. When a club
name is unknown or ambiguous the error names the closest candidates, so the model can
retry without another round trip.

---

## How it works

```
src/util.c    buffers, string arena, hash map, UTF-8 accent folding, dates
src/csv.c     RFC 4180 reader (quotes, embedded commas/newlines, CRLF, BOM)
src/json.c    JSON parser (depth-limited) and streaming writer
src/teams.c   club identity: normalisation, alias table, fuzzy lookup
src/db.c      loading, cross-file de-duplication, indexing
src/query.c   filtering, records, head-to-head, league tables, rankings
src/format.c  text and JSON rendering
src/tools.c   the fourteen MCP tools
src/mcp.c     JSON-RPC 2.0 / MCP over stdio
```

Every file opens with a context block explaining what it does and why.

### Club names — the hard part

The datasets name the same club up to a dozen ways, and name *different* clubs the
same way:

```
Flamengo-RJ   Flamengo - RJ   Flamengo            -> one club (Rio)
Flamengo - PI                 Flamengo do Piauí   -> a different club
Atletico-MG   Atlético - MG   Atletico Mineiro    -> one club
Atletico-GO   Atlético - GO   Atletico Goianiense -> a different club
Vasco         Vasco da Gama-RJ                    -> one club
River Plate                   River Plate-URU     -> two different clubs
```

Getting this wrong is not cosmetic: de-duplication, head-to-head records and league
tables all key on club identity. The resolution pipeline in `src/teams.c` is explicit
and unit-tested:

1. split off a trailing state/country code — `Atlético - MG` → (Atlético, MG)
2. drop parenthetical asides — `Boavista Sport Club (antigo …)` → `Boavista Sport Club`
3. fold to accent-free lowercase ASCII — `Grêmio` → `gremio`
4. collapse initialisms — `C.r.b.` → `crb`
5. strip corporate affixes — `Fortaleza EC` → `fortaleza`
6. apply a hand-curated alias table — `vasco` → `vasco da gama`/RJ
7. canonical key = `<base>|<state>`

Clubs that appear without a state and have exactly one Brazilian counterpart are then
merged automatically, which mops up the long tail of Série C clubs that no hand-written
alias would cover. 397 canonical clubs result; `list_teams` reports how many source
spellings were merged into each.

### The overlap problem

Three files describe the same competition:

| File | Coverage |
|------|----------|
| `Brasileirao_Matches.csv` | Série A 2012–2022, round numbers |
| `novo_campeonato_brasileiro.csv` | Série A 2003–2019, stadiums |
| `BR-Football-Dataset.csv` | Série A/B/C + Copa do Brasil 2014–2023, shots and corners |

Loading them naively double-counts eight seasons of Série A and most of the Copa do
Brasil, silently corrupting every table and average. So fixtures are grouped by
(competition, home, away, season) and merged when their dates fall within a day of each
other — chained along the group, because the same match is dated 28, 29 and 30 July
2019 in the three files. Merging is **additive**: the round number from one file, the
stadium from another and the shot counts from a third end up on one record, which
remembers which files it came from.

Two further wrinkles the loader handles:

- **Season ≠ year.** The 2020 Brasileirão ran to February 2021, so league matches
  played in January–March belong to the previous season. Without that rule the 2021
  season appears to have 491 matches and 2020 only 264.
- **Unplayed fixtures.** `Brasileirao_Matches.csv` records `NA` scores for the tail of
  2022; those rows carry the *scheduled* date, so they are matched against the file
  that has the result over a wider window and take its date along with the score.

42,161 source rows become **16,779 unique matches**, with 7,175 duplicates merged.

### Correctness

League tables are computed from results (3 points for a win; ordered by points, wins,
goal difference, then goals for — the Brasileirão's own criteria). The test suite
asserts them against the published final standings:

| Season | Champion | Points |
|--------|----------|--------|
| 2016 | Palmeiras | 80 |
| 2017 | Corinthians | 72 |
| 2018 | Palmeiras | 80 |
| 2019 | Flamengo | 90 (28W 6D 4L) |
| 2020 | Flamengo | 71 |
| 2021 | Atlético Mineiro | 84 |
| 2022 | Palmeiras | 81 |

Every Série A season from 2006 onward reconciles to exactly 380 matches, 2003–2004 to
552 (24 clubs) and 2005 to 462 (22 clubs).

### Honesty about the data

The server never fills a gap with a guess:

- there is **no goalscorer, card or lineup data** in any of these files, so "who was
  top scorer" is reported as unanswerable rather than approximated;
- the FIFA file is a **2019 snapshot** licensing only fifteen Brazilian clubs — asking
  for Flamengo's players returns "no players matched" *and* lists the clubs that do
  have squads;
- an incomplete season (2023 is missing three fixtures) is flagged as partial and no
  champion is declared;
- stray rows in the sources (a "Série B" fixture between two clubs that never played in
  that competition) are excluded from tables and reported, not silently averaged in.

---

## Testing

BDD, in Given/When/Then form. The `.feature` files in `tests/features/` are the
readable specification; the C suites execute them.

```
tests/features/*.feature   match, team, competition, player, protocol and
                           data-quality scenarios in Gherkin
tests/test_util.c          folding, dates, buffers, hash map
tests/test_csv.c           quoting, CRLF, BOM, short rows, the real files
tests/test_json.c          parse/serialise round trips, malformed input, depth limit
tests/test_teams.c         normalisation, aliases, homonyms, lookup
tests/test_db.c            loading, de-duplication, indexing, cross-file links
tests/test_query.c         records, head-to-head, tables vs the record books, timing
tests/test_mcp.c           handshake, discovery, tool calls, JSON-RPC error codes
tests/test_questions.c     all 28 sample questions end to end, plus timings
```

```
$ make test
...
 93 scenarios, 460 checks, 0 failures
```

The suite also runs clean under AddressSanitizer and UndefinedBehaviorSanitizer:

```bash
make clean
make CFLAGS="-std=c11 -Wall -Wextra -g -O1 -Isrc -fsanitize=address,undefined" test
```

### Measured against the specification's success criteria

| Criterion | Result |
|-----------|--------|
| Search and return match data from all provided CSV files | ✅ all six load; 16,779 merged matches |
| Search and return player data | ✅ 18,207 players |
| Calculate basic statistics | ✅ records, splits, tables, rankings |
| Compare teams head-to-head | ✅ `head_to_head`, symmetric and consistent |
| Handle team name variations | ✅ 7-step pipeline + alias table, unit-tested |
| Return properly formatted responses | ✅ text + `structuredContent` |
| Simple lookups < 2 s | ✅ ~0.1 ms |
| Aggregate queries < 5 s | ✅ ~0.5 ms per league table |
| No timeout errors | ✅ 28 questions in ~13 ms total |
| All 6 CSV files loadable and queryable | ✅ |
| At least 20 sample questions answerable | ✅ 27 of 28 answered from the data; the 28th ("Who is Gabriel Barbosa?") correctly reports that he is absent from the FIFA 19 snapshot and offers the closest names |
| Cross-file queries work | ✅ FIFA squads linked to match-data clubs |

---

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

## Specification

[brazilian-soccer-mcp-guide.md](brazilian-soccer-mcp-guide.md)
