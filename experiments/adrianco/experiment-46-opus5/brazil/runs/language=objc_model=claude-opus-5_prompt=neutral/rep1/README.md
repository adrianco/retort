# Brazilian Soccer MCP Server

An MCP (Model Context Protocol) server that answers natural-language questions
about Brazilian football, backed by an in-memory knowledge graph built from the
six Kaggle datasets in `data/kaggle/`.

Written in Objective-C against Foundation, with no third-party dependencies.

```
make build     compile the server and the test runner
make test      run the behaviour suite against data/kaggle
make run       start the MCP server on stdio
```

## Quick look

The server is normally launched by an MCP client, but it will also answer a
single tool call from the shell, which is the fastest way to see what it does:

```console
$ ./build/brazilian-soccer-mcp --call standings '{"season":2019}'
2019 Brasileirão Série A standings (calculated from 380 matches):
 1. Flamengo - 90 pts (28W, 6D, 4L) 86-37, GD +49 - Champion
 2. Santos - 74 pts (22W, 8D, 8L) 60-33, GD +27
 3. Palmeiras - 74 pts (21W, 11D, 6L) 61-32, GD +29
...
17. Cruzeiro - 36 pts (7W, 15D, 16L) 27-46, GD -19 - Relegated

$ ./build/brazilian-soccer-mcp --call head_to_head '{"team_a":"Flamengo","team_b":"Fluminense","limit":2}'
Flamengo vs Fluminense (Fla-Flu derby):
- 2023-11-11: Flamengo 1-1 Fluminense (Brasileirão Série A 2023)
- 2023-07-16: Fluminense 0-0 Flamengo (Brasileirão Série A 2023)
… (42 more matches in dataset)

Head-to-head in dataset: Flamengo 18 wins, Fluminense 14 wins, 12 draws
```

`--list-tools` prints the catalogue; `--data DIR` points at a different copy of
the CSVs.

### Connecting an MCP client

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/absolute/path/to/build/brazilian-soccer-mcp",
      "args": ["--data", "/absolute/path/to/data/kaggle"]
    }
  }
}
```

The transport is newline-delimited JSON-RPC 2.0 on stdio. `initialize`,
`notifications/initialized`, `ping`, `tools/list` and `tools/call` are
implemented, and protocol versions `2025-06-18`, `2025-03-26` and `2024-11-05`
are negotiated.

## What it holds

16,765 distinct fixtures reconciled from 23,952 CSV rows, 978 clubs and 18,207
players, loaded in about a quarter of a second.

| Competition | Fixtures | Seasons |
|---|---|---|
| Brasileirão Série A | 8,403 | 2003–2023 |
| Brasileirão Série B | 3,677 | 2014–2023 |
| Brasileirão Série C | 1,807 | 2014–2023 |
| Copa do Brasil | 1,623 | 2012–2023 |
| Copa Libertadores | 1,255 | 2013–2022 |

## The two problems worth knowing about

Most of the work in this server is not querying — it is making six
disagreeing files describe one world.

### The files overlap, and they contradict each other

The 2012–2019 Brasileirão seasons appear in three of the five match files.
Concatenating them would report the 2019 title race three times and give
Flamengo 270 points. But the files cannot simply be matched on date, because
they disagree: `Brasileirao_Matches.csv` dates the 2019 Athletico–Flamengo
fixture to 13 October and `novo_campeonato_brasileiro.csv` dates it to 18 May,
five months apart.

Reconciliation therefore leans on the competition format. A Brasileirão season
is a double round-robin, so an ordered pair of clubs meets exactly once — which
means two rows with the same competition, season, home club and away club are
the same match whatever their dates say. Cup competitions get no such guarantee,
so their rows are paired individually by score agreement and date proximity, and
Série C is treated as a cup despite its name because its group and knockout
phases really do let a pair meet twice (Brusque and Amazonas met in May and again
in October 2023).

A second pass repairs season disagreements: `BR-Football-Dataset.csv` has no
season column at all, so a Copa do Brasil final played in March 2021 is inferred
as season 2021 while the cup file correctly files it under 2020, and the two
have to be folded together afterwards.

The result: exactly 380 fixtures for each complete Brasileirão season, with the
union of every file's detail — round numbers from one, stadiums from another,
shot and corner counts from a third.

### The same club is spelled seven different ways

Athletico Paranaense appears as `Atletico-PR`, `Athletico-PR`, `Athletico`,
`Athletico Paranaense` and `Atlético Paranaense`. Get the normalisation too
loose and Atlético-MG, Atlético-GO and Athletico-PR merge into one
20,000-goal super-club; too tight and Flamengo's record splits across four
half-clubs.

Names are folded (diacritics stripped, punctuation reduced to spaces), a
trailing region code is peeled off, connectives (`de`, `da`, `do`) and
club-type abbreviations (`FC`, `EC`, `Clube`) are shed, and the resulting
`(base, region)` pair is looked up in a hand-seeded table of ~90 real clubs.
Everything not in that table — mostly the ~400 sides that appear once in a Copa
do Brasil first round — gets an auto-created node.

Two traps that the table exists to handle:

- **`SC` is both Santa Catarina and Sport Club; `AC` is both Acre and Atlético
  Clube.** Reading them as states silently moved Amiens SC to Santa Catarina and
  Wolfsberger AC to Acre, and — because a state code implies Brazil — filed
  their squads under Brazilian football. A punctuated suffix (`Avaí - SC`) is
  always a state; an unpunctuated one is only a state if we already know a club
  of that name there.
- **FIFA club names collide with Brazilian ones.** `Boavista FC` is the Porto
  club, not Boavista-RJ of the Copa do Brasil; `Club América` is Mexican, not
  América Mineiro. Both are seeded explicitly.

## Design

```
src/
  BSCommon            competition and source vocabulary
  BSTextUtil          accent folding, edit distance
  BSDateUtil          yyyymmdd dates, four input formats, no time zones
  BSCSVParser         streaming RFC 4180 reader, lazy field materialisation
  BSClub              club node
  BSClubRegistry      name normalisation and the seeded club table
  BSMatch             match node, with cross-source merge
  BSPlayer            player node, skills in a fixed byte array
  BSDataLoader        one adapter per CSV file
  BSKnowledgeGraph    reconciliation and indexing
  BSQuery             declarative match filter and index selection
  BSAnalytics         records, league tables, head-to-head, aggregates
  BSTools             the 17 MCP tools
  BSToolSupport       argument coercion, JSON Schema, text rendering
  BSMCPServer         JSON-RPC 2.0 over stdio
```

Dates are plain `yyyymmdd` integers rather than `NSDate`, so no time-zone shift
can move a fixture across a season boundary. The CSV reader materialises a field
into an `NSString` only when a caller asks for it, which matters for the FIFA
file's 18,207 × 89 grid. Every index is stored most-recent-first, so listing
queries need no sort.

### Tools

| | |
|---|---|
| `search_matches` | by team, opponent, competition, season, date range, venue, round, stage |
| `head_to_head` | full record between two clubs, with the derby name |
| `team_record` | W/D/L, goals, points, win rate for any slice |
| `team_profile` | everything the graph knows about one club |
| `compare_teams` | side-by-side records plus head-to-head |
| `standings` | league table computed from results, CBF tie-breaks |
| `season_summary` | champion, relegated, top scorers, headline statistics |
| `competition_info` | coverage and participants |
| `match_statistics` | goals per match, home advantage, scoreline distribution |
| `biggest_wins` | ranked by winning margin |
| `team_rankings` | by points, wins, goals, goal difference or win rate |
| `find_derbies` | matches between traditional rivals |
| `search_players` | by name, nationality, club, position, rating, age |
| `player_profile` | full FIFA record, plus the club's match record |
| `club_squad` | squad and match record together — the cross-file view |
| `list_teams` | browse and disambiguate club names |
| `dataset_info` | coverage, licences and limitations |

League tables are computed, not looked up, so the tie-break order is the CBF's:
points, then **wins**, then goal difference. That is why 2019 comes out with
Santos second on 74 points and Palmeiras third on the same 74 — Santos won 22
matches to Palmeiras' 21, even though Palmeiras had the better goal difference.

## Answering honestly

Several questions the specification asks cannot be answered from these files,
and the server says so rather than inventing an answer.

- **"Who is Gabriel Barbosa?"** `fifa_data.csv` is a FIFA 19 export, and he is
  not in it. The name search will happily fuzzy-match him to an unrelated
  player called *Gabriel*, so `player_profile` checks whether the best hit
  actually contains the requested name and reports a miss when it does not.
- **"Which players play for Flamengo?"** FIFA 19 shipped without licences for
  Flamengo, Palmeiras, Corinthians, São Paulo and Vasco. The answer explains
  that, and lists the Brazilian clubs that *do* have squads, instead of
  returning an empty list that reads as "this club has no players".
- **Top scorers.** No source records goalscorers, so the question is only
  answerable per team. `dataset_info` states this.
- **Incomplete seasons.** `standings` reports `season_complete`, and names a
  champion only when the fixtures amount to a finished round-robin. 2009 (one
  fixture short) and 2023 (three short) are correctly reported as incomplete.

Failed lookups come back as tool results with `isError` set — not as JSON-RPC
errors — so the model can recover conversationally. Name resolution has a
deliberate confidence gap: a close match is acted on, a weak one is offered as a
suggestion rather than silently substituted.

```console
$ ./build/brazilian-soccer-mcp --call team_record '{"team":"Gremiu"}'
Grêmio record: ...                       # confident, so resolved

$ ./build/brazilian-soccer-mcp --call team_record '{"team":"Palmeirense"}'
No club called "Palmeirense" is in the dataset.
Did you mean: Palmeiras, Figueirense, Campinense, Juazeirense, CD Feirense?

$ ./build/brazilian-soccer-mcp --call team_record '{"team":"Manchester City"}'
Manchester City has no matches in this dataset. It is known here only because
players in the FIFA database are signed to it; the match data covers the
Brasileirão Série A/B/C, the Copa do Brasil and the Copa Libertadores.
```

One nicety worth calling out: *"Find all Copa do Brasil finals"* is a listed
sample question, but the cup file numbers its rounds 1–8 and never writes the
word "final", while the Libertadores labels stages textually — where a substring
match for `final` would also catch *quarterfinals* and *semifinals*. Asking
`search_matches` for finals is therefore handled semantically: an exact stage
match where stages are labelled, and the last round played that season where
they are numbered.

## Tests

`make test` runs 86 Given/When/Then scenarios and 318 assertions in a few
seconds. The specification asks for BDD scenarios, and its two worked examples
appear verbatim in `tests/BSTestQueries.m`.

```
Feature: Competition Queries

  Scenario: Compute the 2019 Brasileirão final standings
    Given the 2019 season's 380 matches
    When  I compute the table with the CBF tie-break order
    Then  20 clubs are classified ✓
    Then  the season is recognised as complete ✓
    Then  Flamengo are champions, as they were ✓
    Then  Flamengo finished on 90 points ✓
    And   the tie on 74 points is broken by wins, not goal difference
    Then  Santos are second on 22 wins ✓
    Then  Palmeiras are third on 21 wins, despite a better goal difference ✓
```

Coverage: CSV/date/text primitives against the exact malformations in the
bundled files; name normalisation in both directions (variants unify, distinct
clubs stay apart); loading and reconciliation; queries and analytics; the MCP
protocol including all four error paths; the specification's sample questions;
and the performance budgets.

Figures are asserted against the historical record where one exists — Flamengo's
90 points in 2019, the four clubs actually relegated that season, Corinthians'
10W-8D-1L home record in 2022, and the champions of every complete season — so
that a reconciliation regression cannot pass unnoticed.

Performance, measured by the suite: cold start under 10s (actual ≈0.25s), three
simple lookups within the 2s budget, four full-dataset aggregates within 5s.

## Data sources

Kaggle data can't be downloaded without an account, so these (freely available
with attribution) datasets have been downloaded for use here:

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

`brazilian-soccer-mcp-guide.md` (identical to `TASK.md`).
