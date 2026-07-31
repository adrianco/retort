# Brazilian Soccer MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io) server that turns six
Kaggle datasets into a queryable knowledge graph of Brazilian club football, so an
LLM can answer natural-language questions about matches, teams, players and
competitions.

Implements the specification in [`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md).

**No third-party dependencies.** The knowledge graph, the query engine and the MCP
JSON-RPC transport are all built on the Python standard library. `pytest` is only
needed to run the tests.

```
$ python -m brazilian_soccer.cli call standings season=2019

2019 Campeonato Brasileiro Série A standings (calculated from 380 matches)

 #  Team                      P   W   D   L  GF  GA   GD  Pts
--  -----------------------  --  --  --  --  --  --  ---  ---
 1  Flamengo - Champion      38  28   6   4  86  37  +49   90
 2  Santos                   38  22   8   8  60  33  +27   74
 3  Palmeiras                38  21  11   6  61  32  +29   74
...
17  Cruzeiro - Relegated     38   7  15  16  27  46  -19   36
18  CSA - Relegated          38   8   8  22  24  58  -34   32
19  Chapecoense - Relegated  38   7  11  20  31  52  -21   32
20  Avaí - Relegated         38   3  11  24  18  62  -44   20
```

---

## Quick start

```bash
# 1. Check everything loads (no install needed)
python -m brazilian_soccer.server --self-test

# 2. Ask the specification's sample questions
python -m brazilian_soccer.cli demo

# 3. Call a single tool
python -m brazilian_soccer.cli call head_to_head team_a=Flamengo team_b=Fluminense
python -m brazilian_soccer.cli --json call team_stats team=Corinthians season=2022 venue=home

# 4. Run the tests
pip install -e ".[dev]" && pytest
```

### Register with an MCP client

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "python",
      "args": ["-m", "brazilian_soccer.server"],
      "cwd": "/path/to/this/repository"
    }
  }
}
```

The data directory is found automatically (`./data/kaggle`); override it with
`--data-dir` or the `BR_SOCCER_DATA` environment variable.

---

## What was built

### Architecture

```
                     data/kaggle/*.csv   (6 files, 42,161 rows)
                              |
   normalization.py  ---------+           text / date / number cleaning
   clubs.py          ---------+           canonical club registry + resolver
   competitions.py   ---------+           competition slugs and aliases
                              v
   loaders.py        one reader per file -> Match / Player objects
                              v
   graph.py          KnowledgeGraph: dedupe, merge, index
                              |
                Team --played--> Match --part of--> Competition
                   \                                   (season)
                    +--squad member--> Player
                              v
   queries.py        16 query functions returning JSON-ready dicts
   formatting.py     the same results rendered as readable answers
                              v
   tools.py          MCP tool schemas + dispatch + error envelopes
   server.py         JSON-RPC 2.0 over stdio        cli.py  shell client
```

Every source file opens with a context block comment explaining what it owns and
why it exists.

### The three problems worth solving

**1. Overlapping datasets.** The same Série A fixture appears in up to three of the
provided files. Concatenating them would double every goal total and produce
nonsense standings. `graph.py` matches fixtures on `(competition, home, away)` —
exact for a double round robin, where an ordered pair meets once per season — and
merges them into one `Match` carrying the union of all columns: the round number
from `Brasileirao_Matches.csv`, the stadium from `novo_campeonato_brasileiro.csv`,
and the corner/shot/attack counts from `BR-Football-Dataset.csv`.

```
23,954 match rows  ->  16,878 unique fixtures  (7,074 duplicate rows folded in)
```

The result is verifiable: every Série A season from 2006 to 2022 contains exactly
380 fixtures, 2003–2004 contain 552 (24 clubs) and 2005 contains 462 (22 clubs).

**2. Team-name variations.** Ten spellings of one club across five files:

```
$ python -m brazilian_soccer.cli call resolve_team name=Atletico-PR

'Atletico-PR' resolves to Athletico Paranaense (PR)
- Canonical id: athletico-pr
- Matches in data: 904 (2003-2023)
- Spellings seen in source files: Athletico, Athletico Paranaense,
  Athletico Paranaense - PR, Athletico-PR, Atletico - PR, Atletico Paranaense,
  Atletico-PR, Atlético - PR, Atlético Paranaense - PR, Atlético-PR
```

`clubs.py` resolves names in layers: strip accents and punctuation, peel off the
state suffix, look up `(base, state)` in a curated registry of 190 clubs, then the
bare base, then retry after dropping filler tokens (`EC`, `FC`, `Esporte Clube`,
`Sporting Club`), and finally fall back to a generated slug so the ~250 minor Copa
do Brasil clubs stay queryable.

Crucially it also keeps clubs *apart* where a naive normaliser would merge them:
Botafogo-RJ / Botafogo-SP / Botafogo-PB, the three Atléticos (MG, PR, GO),
Bragantino-SP vs Bragantino-PA, Grêmio vs Grêmio Prudente, and `FC Barcelona`
(FIFA) vs `Barcelona-EQU` (Libertadores). Where a bare name really is ambiguous the
most prominent club wins and the alternatives are reported back.

Player-to-club joins are checked against the data rather than a hand-written
exclusion list: a FIFA club that shares a slug with a club in the match datasets but
whose squad is mostly *not* Brazilian cannot be the Brazilian club, so Portugal's
Boavista FC never gets joined onto Boavista-RJ.

**3. Honest answers about missing data.** Every result carries a `notes` list.
FIFA 19 only licensed 15 Brazilian clubs, so `club_squad` for Flamengo returns an
empty squad *and says why*, instead of implying the club has no players. No dataset
has a goalscorer column, so `competition_stats` states that top-scorer questions are
unanswerable rather than inventing an answer.

### Data quirks handled

| Quirk | Handling |
|---|---|
| ISO, `DD/MM/YYYY`, `"2012-05-19 18:30:00"` and `"Jul 1, 2004"` dates | `parse_date` tries every format, returns `None` for `NA`/`-` |
| Scores written `2`, `2.0`, `-`, `NA` | `parse_int` tolerates all sentinels |
| The 2020 Série A finished in February 2021 | BR-Football rows inherit the season of the fixture they merge with; unmatched league rows in Jan–Mar count as the previous season |
| Copa do Brasil's `round` column means a different stage each edition (the final is round 6 in 2012, round 8 in 2017, and 2021 stops at round 4) | Stage derived from the number of fixtures in the round: 2 = Final, 4 = Semifinals, 8 = Quarterfinals, 16 = Round of 16 |
| `"Bragantino - PA"` listed against itself twice | Dropped as invalid, counted in the build report |
| A Brasília FC fixture mislabelled Série A 2015 | Kept in the data, excluded from the standings table with an explanation |
| Botafogo hosted Flamengo twice in 2009 | Preserved as two fixtures (different rounds) — rows inside one file are only merged when dated within two days |
| `A.b.c. - RN` vs `ABC - RN` | Dotted initialisms are glued back together before matching |
| UTF-8 accents and cedillas throughout | All files read as `utf-8-sig`; accents folded only for comparison, never for display |

---

## The 16 tools

| Tool | Answers questions like |
|---|---|
| `find_matches` | "What matches did Palmeiras play in 2023?", "Find all Copa do Brasil finals" |
| `head_to_head` | "Show me all Flamengo vs Fluminense matches", "When did Flamengo last play Corinthians?" |
| `team_stats` | "What is Corinthians' home record in 2022?" |
| `team_profile` | "What competitions has Palmeiras played in?" |
| `standings` | "Who won the 2019 Brasileirão?", "Which teams were relegated in 2020?" |
| `team_rankings` | "Which team has the best away record?", "Which team scored the most goals in Serie A 2023?" |
| `competition_stats` | "What's the average goals per match in the Brasileirão?" |
| `biggest_wins` | "Show me the biggest wins in the dataset" |
| `compare_seasons` | "Compare the 2018 and 2019 seasons" |
| `find_derbies` | "Show me all derbies in 2023" |
| `search_players` | "Find all Brazilian players", "Show me all forwards from Santos" |
| `player_profile` | "Who is Gabriel Jesus?" |
| `club_squad` | "Which players play for Grêmio?" |
| `brazilian_players_by_club` | "Who are the top Brazilian players?" |
| `resolve_team` | "Is 'Atlético' Mineiro, Paranaense or Goianiense?" |
| `dataset_summary` | "What data do you actually have?" |

Every tool returns both a rendered text answer and `structuredContent` with the raw
result. User-fixable problems (unknown club, unavailable season, bad enum value)
come back as `isError` tool results carrying a suggestion, never as protocol
failures.

The server also exposes the six source files as MCP **resources** and two ready-made
**prompts** (`season-review`, `derby-report`), and negotiates protocol versions
`2025-06-18`, `2025-03-26` and `2024-11-05`.

---

## Data coverage

| Competition | Matches | Seasons | Clubs |
|---|---|---|---|
| Campeonato Brasileiro Série A | 8,404 | 2003–2023 | 46 |
| Campeonato Brasileiro Série B | 3,677 | 2014–2023 | 62 |
| Campeonato Brasileiro Série C | 1,807 | 2014–2023 | 78 |
| Copa do Brasil | 1,735 | 2012–2023 | 345 |
| Copa Libertadores | 1,255 | 2013–2022 | 106 |
| **Total** | **16,878 unique fixtures** | | **445 clubs** |

Plus 18,207 FIFA 19 players (827 Brazilian) joined to the clubs that appear in the
match data.

Correctness spot-check — the champion computed from the raw match results matches
the historical record for **every Série A season from 2003 to 2022** (asserted in
`tests/bdd/test_competition_queries.py`), and the 2019 table reproduces the
specification's example exactly: Flamengo 90 pts (28W 6D 4L), Santos 74,
Palmeiras 74.

---

## Testing

BDD scenarios in Given/When/Then form, backed by plain `pytest`:

```
tests/features/*.feature        Gherkin specifications (6 features)
tests/gwt.py                    a small Given/When/Then harness
tests/bdd/                      one test per scenario, against the real data
tests/test_normalization.py     text, date and number parsing
tests/test_clubs.py             name resolution: what must merge, what must not
tests/test_loaders.py           all six CSVs load; row counts pinned to the spec
tests/test_graph.py             deduplication, merging, indexes
tests/test_tools.py             tool schemas, argument coercion, error envelopes
tests/test_answer_shapes.py     rendered answers match the spec's example formats
tests/test_mcp_server.py        protocol, plus a real subprocess round-trip
tests/test_sample_questions.py  every sample question in the specification
tests/test_performance.py       the specification's 2 s / 5 s budgets
tests/test_cli.py               the shell client and the demo run
tests/test_feature_coverage.py  every .feature scenario still has a test
```

```bash
$ pytest
390 passed in 3.8s
```

Measured against the specification's success criteria:

- [x] Search and return match data from all six CSV files
- [x] Search and return player data
- [x] Calculate statistics (wins, losses, goals, points, win rates)
- [x] Compare teams head-to-head
- [x] Handle team name variations correctly
- [x] Return properly formatted responses
- [x] Simple lookups < 2 s — measured in single-digit milliseconds
- [x] Aggregate queries < 5 s — the slowest (all competitions, all seasons) is ~10 ms
- [x] No timeout errors
- [x] All 6 CSV files loadable and queryable
- [x] At least 20 sample questions answerable — 26, in `cli.py:DEMO_QUESTIONS`
- [x] Cross-file queries work — `brazilian_players_by_club` joins players to matches

The whole graph is built once at server start (~0.4 s) and every query is an index
lookup, which is why the response budgets are met by three orders of magnitude.

---

## Data Sources

Kaggle data can't be downloaded without an account so these (freely available with
attribution) data sets have been downloaded for use here:

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

brazilian-soccer-mcp-guide.md
