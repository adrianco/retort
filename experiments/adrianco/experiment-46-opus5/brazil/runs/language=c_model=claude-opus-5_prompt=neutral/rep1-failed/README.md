# Brazilian Soccer MCP Server

An MCP (Model Context Protocol) server, written in C11 with no third-party
dependencies, that turns the six provided Kaggle CSV datasets into a queryable
knowledge graph of Brazilian football and exposes it to an LLM as twelve tools.

Implemented from the specification in [`TASK.md`](TASK.md)
(= [`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md)).

```
$ make && ./brsoccer-mcp --demo
brsoccer-mcp: loaded 16750 matches, 18207 players, 474 clubs from data/kaggle in 0.133s
...
29 questions answered in 12.4 ms total (0.43 ms average).
```

---

## Quick start

```sh
make            # build ./brsoccer-mcp and ./run_tests   (cc, C11, no deps)
make test       # BDD suite (67 scenarios) + end-to-end stdio protocol test
make demo       # answer the 29 benchmark questions from the specification
./brsoccer-mcp  # speak MCP (JSON-RPC 2.0) on stdin/stdout
```

One-off tool calls from the shell, handy for exploring:

```sh
./brsoccer-mcp --call league_table '{"season":2019}'
./brsoccer-mcp --call head_to_head '{"team_a":"Flamengo","team_b":"Fluminense"}'
./brsoccer-mcp --call search_players '{"nationality":"Brazil","limit":5}'
./brsoccer-mcp --list-tools
```

### Connecting an LLM

The server speaks the MCP stdio transport (newline-delimited JSON-RPC 2.0,
protocol versions `2025-06-18`, `2025-03-26` and `2024-11-05`). For Claude
Desktop / Claude Code, add:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/absolute/path/to/brsoccer-mcp",
      "args": ["--data-dir", "/absolute/path/to/data/kaggle"]
    }
  }
}
```

The data directory defaults to `./data/kaggle` (or `$BRSOCCER_DATA`). Loading
happens once at start-up; stdout carries protocol traffic only, diagnostics go
to stderr.

---

## The tools

| Tool | Answers questions like |
|------|------------------------|
| `search_matches` | "Show me all Flamengo vs Fluminense matches", "What did Palmeiras play in 2023?", "Find all Copa do Brasil finals" |
| `head_to_head` | "Compare Palmeiras and Santos head-to-head" |
| `team_stats` | "What is Corinthians' home record in 2022?" |
| `league_table` | "Who won the 2019 Brasileirão?", "Which teams were relegated in 2020?" |
| `team_rankings` | "Which team scored the most goals in Serie A 2023?", "Which team has the best away record?" |
| `biggest_wins` | "Show me the biggest wins in the dataset" |
| `competition_stats` | "What's the average goals per match?", "Compare the 2018 and 2019 seasons" |
| `search_players` | "Find all Brazilian players", "Show me all forwards from Cruzeiro" |
| `player_profile` | "Who is Gabriel Jesus?" |
| `club_squad` | "Which players play for Grêmio?" |
| `list_teams` | "What competitions has Palmeiras played in?" |
| `dataset_info` | "What is actually in this data?" |

Filters shared by the match tools: `team`, `opponent`, `venue` (home/away),
`competition`, `season`, `season_from`/`season_to`, `date_from`/`date_to`
(accept `YYYY`, `YYYY-MM` or `YYYY-MM-DD`), `stage`, `round`, `limit`, `order`.

Sample output:

```
$ ./brsoccer-mcp --call team_stats '{"team":"Corinthians","season":2022,"venue":"home","competition":"Serie A"}'
Corinthians home record (Brasileirão Série A 2022, home matches)
Overall:
- Matches: 19
- Wins: 12, Draws: 4, Losses: 3
- Goals For: 24, Goals Against: 11 (diff +13)
- Points: 40, Win rate: 63.2%
- Clean sheets: 10, goals per match: 1.84
- Biggest win: 2022-04-16: Corinthians 3-0 Avaí (Brasileirão Série A, Round 2, 2022)
- Heaviest defeat: 2022-10-26: Corinthians 0-2 Fluminense (Brasileirão Série A, Round 34, 2022)
```

---

## What the implementation does

### One graph out of six files

```
      Brasileirao_Matches.csv        -.
      novo_campeonato_brasileiro.csv  |
      BR-Football-Dataset.csv         +--> Match[]  --(home/away)--> Team[]
      Brazilian_Cup_Matches.csv       |                                ^
      Libertadores_Matches.csv       -'                                |
      fifa_data.csv ------------------> Player[] --(club)--------------'
```

The files overlap heavily — Série A 2014-2019 appears in three of them — so
records are de-duplicated on (competition, home, away, ±7 days) and then
**merged**: the Brasileirão file contributes the round number, the historical
file the stadium, and BR-Football the shots, corners and attacks *for the same
match*. 24,000 raw rows become **16,750 distinct matches**, ~3,900 of which
carry data from more than one file. `search_matches` with `"detail": true`
cites the files each answer came from.

Deliberate decisions worth knowing about:

- **Season, not calendar year.** `BR-Football-Dataset.csv` has no season
  column. Brazilian seasons never start before March, so a January/February
  fixture belongs to the previous season — that is what puts the COVID-shifted
  2020 programme (which finished in February 2021) back where it belongs.
- **Cup stages are derived.** `Brazilian_Cup_Matches.csv` numbers its rounds
  but does not name them. The last round of a season is only labelled *final*
  when it actually has at most two legs, so seasons the dataset only covers
  partially (2021 stops after the round of 16) keep plain `round N` labels
  instead of inventing a final.
- **Champions are only claimed from complete seasons.** The 2023 Série A is
  three fixtures short in the source data — enough to change the top of the
  table — so `league_table` reports the gap rather than crowning anybody.

### Club names

The spec's "team name variations" problem is handled by a normalisation
pipeline (`src/teams.c`) rather than a lookup table that would have to grow
with the data:

1. fold accents, case and punctuation (`São Paulo-SP` → `sao paulo sp`),
2. glue runs of single letters (`A.b.c.` → `abc`),
3. peel a trailing region code — a Brazilian state (`-MG`, ` - MG`) or a
   CONMEBOL country (`(URU)`, `-PAR`),
4. drop club-form noise (`EC`, `FC`, `Sport Club`, `Futebol`, `de`, `da`),
5. apply an alias table for the ~110 cases that cannot be derived
   (`Athletico` ≡ `Atletico Paranaense` ≡ `Atlético-PR`).

A club's identity is **(base name, region)**, which keeps Vitória-BA apart from
Vitória-ES and the three Botafogos apart from each other, while a region-less
spelling is merged into its regioned sibling when that sibling is unique (so
`Avai` joins `Avai-SC` with no hand-written rule). Where two clubs still share
a name, the one with more matches keeps the plain display name and the others
are qualified: `Botafogo` and `Botafogo (PB)`.

The same resolver joins the FIFA `Club` column to the match data — including
`Ceará Sporting Club` → Ceará and `América FC (Minas Gerais)` → América
Mineiro — while an exclusion list stops `Club América` (Mexico), `Inter`
(Italy) and `Vitória Guimarães` (Portugal) from being mistaken for Brazilian
clubs. 300 of the 18,207 players are joined to 15 Brazilian clubs; the FIFA 19
snapshot simply does not license the rest, and the tools say so instead of
returning nothing.

### Everything else

Queries are linear scans over in-memory arrays: no index to invalidate, and the
whole 29-question benchmark runs in ~12 ms (loading the 22 MB of CSV takes
~130 ms). The spec's budgets are simple lookups < 2 s and aggregates < 5 s;
the slowest tool call measured is 2 ms.

---

## Layout

```
src/
  util.c/h      allocation, growable buffers, timing
  strutil.c/h   UTF-8 decoding and diacritic folding
  csv.c/h       RFC 4180 reader (BOM, CRLF, quoted commas, in-place unescape)
  date.c/h      ISO / ISO+time / Brazilian d/m/Y parsing, partial-date bounds
  teams.c/h     club identity: normalisation, aliases, coalescing, resolution
  data.c/h      loading, de-duplication, cross-file merging, player join
  query.c/h     match filters, records, head-to-head, tables, rankings, aggregates
  tools.c/h     the twelve MCP tools and their JSON Schemas
  json.c/h      JSON parser and writer for the wire format
  mcp.c/h       JSON-RPC 2.0 / MCP over stdio
  main.c        server, --demo, --call, --list-tools
tests/
  bdd.h         Given/When/Then macros
  run_tests.c   harness + entry point (loads the dataset once)
  test_*.c      strutil, csv, date, json, teams, data, query, mcp suites
  mcp_stdio_test.sh  end-to-end protocol test against the real binary
features/       the same scenarios as readable Gherkin
```

Every source file opens with a context block comment explaining what it is for
and why it is shaped the way it is.

---

## Tests

```sh
make test              # everything
./run_tests            # the C suites only
./run_tests teams data # a subset (strutil csv date json teams data query mcp)
```

67 scenarios / 601 assertions, written as executable Gherkin — each scenario
prints its Given/When/Then as it runs, and a failure names the file, line and
the values that differed. Coverage:

- **parsing**: quoted commas, doubled quotes, CRLF, BOM, short rows, `NA`/`nan`,
  three date formats, invalid dates, partial-date range bounds;
- **names**: every spelling family in the data, plus the traps (same name,
  different state) that must *not* be merged;
- **data**: all six files load with their documented row counts, overlapping
  seasons merge to ~380 matches per Série A season, merged records carry the
  columns each file contributed, players join to the right clubs;
- **queries**: the spec's own Gherkin scenarios, plus results checked against
  independently known facts — the 2019 Brasileirão table (Flamengo 90 pts,
  Cruzeiro/CSA/Chapecoense/Avaí relegated), Palmeiras' 81-point 2022, the 2019
  Copa do Brasil final, the 2018 Libertadores final, internal consistency
  (points = 3W+D, league goals for = goals against);
- **protocol**: handshake, version negotiation, tool catalogue schemas, text
  content, `isError` for bad arguments, JSON-RPC error codes, notifications
  going unanswered *whatever method they name*, exact echoing of large integer
  ids, rejection of non-JSON numerics and escaped NULs, every tool callable;
- **performance**: latency assertions for the spec's 2 s / 5 s budgets.

The suite also runs clean under `-fsanitize=address,undefined`.

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

### Coverage and limits

| Competition | Matches | Seasons |
|-------------|---------|---------|
| Brasileirão Série A | 8,405 | 2003-2023 |
| Brasileirão Série B | 3,677 | 2014-2023 |
| Brasileirão Série C | 1,807 | 2014-2023 |
| Copa do Brasil | 1,606 | 2012-2023 |
| Copa Libertadores | 1,255 | 2013-2022 |
| FIFA players | 18,207 | one snapshot (FIFA 19) |

The optional live sources the specification mentions (API-Football,
TheSportsDB, Wikipedia) are deliberately not used: the server stays offline,
deterministic and dependency-free, which is also what makes the test suite able
to assert exact numbers.

What these files **cannot** answer, and what the server therefore refuses to
guess at: goal scorers, line-ups, referees and attendances are not in the data,
so there are no top-scorer tools; shot and corner counts only start in mid-2016;
the FIFA snapshot is a single point in time and only licenses 15 Brazilian
clubs. `dataset_info` states all of this up front so the LLM does not have to
discover it by getting an empty answer.
