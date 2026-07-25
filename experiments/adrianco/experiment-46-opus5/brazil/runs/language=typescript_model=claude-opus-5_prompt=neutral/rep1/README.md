# Brazilian Soccer MCP Server

An [MCP](https://modelcontextprotocol.io) server that exposes a knowledge graph over Brazilian
soccer, built from the six Kaggle datasets in `data/kaggle/`. It answers natural-language questions
about matches, teams, players, competitions and statistics by giving an LLM 17 focused, read-only
tools instead of raw CSV access.

Implemented in TypeScript against `@modelcontextprotocol/sdk`. No database and no network access:
the corpus is ~11 MB of CSV, parsed into memory in about 300 ms at startup.

```
$ npm run ask -- competition_standings '{"season":2019}'
2019 Brasileirão Série A Final Standings (calculated from matches):
1. Flamengo - 90 pts (28W, 6D, 4L) GF 86 GA 37 +49 - Champion
2. Santos - 74 pts (22W, 8D, 8L) GF 60 GA 33 +27
3. Palmeiras - 74 pts (21W, 11D, 6L) GF 61 GA 32 +29
...
17. Cruzeiro - 36 pts (7W, 15D, 16L) GF 27 GA 46 -19 - Relegated
```

---

## Quick start

```bash
npm install
npm run verify        # typecheck + build + tests
npm start             # run the MCP server over stdio
```

Ad-hoc queries without an MCP client:

```bash
npm run ask -- --list
npm run ask -- head_to_head '{"teamA":"Flamengo","teamB":"Fluminense","limit":5}'
npm run ask -- search_players '{"nationality":"Brazil","minOverall":85}'
npm run ask -- team_stats '{"team":"Corinthians","season":2022,"competition":"serie-a","venue":"home"}'
```

### Connecting an MCP client

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "node",
      "args": ["/absolute/path/to/dist/index.js"]
    }
  }
}
```

The data directory is found by walking up from the running module until `data/kaggle` appears; set
`BRAZILIAN_SOCCER_DATA_DIR` to override.

---

## What the graph contains

| | |
|---|---|
| Source rows read | 23 950 match rows + 18 207 player rows |
| Merged fixtures | **16 795** (duplicate reports of the same match collapsed) |
| Teams | 396 |
| Players | 18 207 |
| Rows dropped as unusable | 4 |
| Load time | ~300 ms |

| Competition | Matches | Seasons |
|---|---|---|
| Brasileirão Série A | 8 403 | 2003–2023 |
| Brasileirão Série B | 3 677 | 2014–2023 |
| Brasileirão Série C | 1 807 | 2014–2023 |
| Copa do Brasil | 1 654 | 2012–2023 |
| Copa Libertadores | 1 254 | 2013–2022 |

Nodes are competitions, seasons, teams, matches, players and stadiums. Edges are the relationships
the CSVs imply — a team *played* a match, a match *belongs to* a competition-season, a player is
*contracted to* a club — and they are what makes cross-file questions ("what is Internacional's
squad, and how has the club done in the matches?") answerable at all.

---

## Tools

| Tool | Answers questions like |
|---|---|
| `dataset_info` | What is in this dataset? |
| `list_seasons` | Which seasons of the Copa do Brasil are covered? |
| `list_teams` | Which clubs played in Série A in 2019? |
| `search_matches` | Show me all Flamengo vs Fluminense matches. Find all Copa do Brasil finals. |
| `head_to_head` | When did Flamengo last play Corinthians? Compare Palmeiras and Santos. |
| `find_derbies` | Show me all the derbies played in 2023. |
| `team_stats` | What is Corinthians' home record in 2022? |
| `team_profile` | What competitions has Palmeiras played in? |
| `team_rankings` | Which team scored the most goals in Série A 2023? Best away record? |
| `search_players` | Find all Brazilian players. Show me all forwards from Santos. |
| `player_profile` | Who is Alisson? |
| `club_squad` | Which Brazilian clubs have squads, and how strong are they? |
| `competition_standings` | Who won the 2019 Brasileirão? Who was relegated in 2020? |
| `competition_bracket` | Show the 2018 Copa Libertadores bracket. |
| `match_statistics` | What's the average goals per match in the Brasileirão? |
| `record_extremes` | Show me the biggest wins in the dataset. |
| `compare_seasons` | Compare the 2018 and 2019 seasons. |

Every tool returns both a formatted text block for the model to read and a `structuredContent`
payload for programmatic use. All are marked `readOnlyHint`.

---

## How the hard parts were solved

### The source files overlap, so the rows have to be merged

Série A 2014–2019 is described by **three** of the five match files at once, and
`BR-Football-Dataset.csv` additionally contains duplicate rows within itself (Série A 2021 has 491
rows for a 380-match season). Counting raw rows would inflate every aggregate by up to 3×.

Rows are grouped by competition and ordered team pair, then merged, with the merge rule chosen per
competition:

- **Série A and Série B** are straight double round-robins, so an ordered pair meets exactly once
  per season. The season joins the key, and rows up to 45 days apart merge — enough to absorb a
  postponement, short enough to keep the two legs apart when a source mistakenly files both under
  the same home team (`novo_campeonato_brasileiro.csv` does this for Botafogo–Flamengo in 2009).
- **Série C, Copa do Brasil and Libertadores** can legitimately pair the same two teams twice with
  the same home side, so those are keyed on the pair alone and split by a 5-day window.

Within a cluster, a row that recorded a score outranks one that did not, and the competition-specific
files outrank the broad scrape. Lower-priority sources only ever fill gaps — the stadium name comes
from `novo_campeonato_brasileiro.csv`, the shot and corner counts from `BR-Football-Dataset.csv`, the
round number from `Brasileirao_Matches.csv`, all on the same merged match, which records its
`sources`.

The result validates against history: Série A comes out at 552 matches for 2003 and 2004 (24 teams),
462 for 2005 (22 teams) and 380 from 2006 on (20 teams); the champion is correct for every season
from 2003 to 2022; and the 2019 table reproduces the real final standings exactly, points and all
four relegation places included.

Cup rounds are labelled relative to each season's own last round rather than a fixed number, because
the Copa do Brasil ran six rounds in 2012 and seven in 2016 — anchoring on "round 8 is the final"
hid both those finals entirely and shifted every other label by one.

### The same club is spelled five different ways

```
Brasileirao_Matches.csv          "Atletico-PR"   "Sao Paulo-SP"   "Vasco da Gama-RJ"
novo_campeonato_brasileiro.csv   "Athletico-PR"  "São Paulo"      "Vasco"
BR-Football-Dataset.csv          "Athletico Paranaense"           "Vasco Da Gama RJ"
Brazilian_Cup_Matches.csv        "América - MG"  "Boavista Sport Club (antigo …) - RJ"
Libertadores_Matches.csv         "Athletico"     "Nacional (URU)" "Guaraní-PAR"
fifa_data.csv                    "Atlético Paranaense"  "Sport Club do Recife"
```

`src/domain/teams.ts` resolves these in two layers. A structural parse peels off state suffixes
(`-MG`, ` - MG`, ` MG`), country codes (`(URU)`, `-PAR`) and club-type noise (`EC`, `FC`,
`Sporting Club`, `Esporte Clube`, and the Portuguese articles left behind), then folds accents and
case. A curated table then pins the clubs where structure alone is ambiguous — above all the
homonyms where the state is the *only* difference between two real clubs:

| Bare name goes to | Distinct clubs kept apart |
|---|---|
| Botafogo → Botafogo-RJ | Botafogo-SP, Botafogo-PB |
| América → América-MG | América-RN |
| Atlético → Atlético-MG | Atlético-GO, Athletico-PR |
| Nacional → Nacional (URU) | Nacional (PAR) |

Names the table does not cover still get a stable canonical id from the structural parse, so
lower-division and South American clubs stay queryable without being enumerated. User queries go
through the same machinery plus a fuzzy fallback; when nothing resolves, the error names the closest
candidates rather than returning an empty list.

### Three date formats, one calendar

`2023-09-24`, `2012-05-19 18:30:00` and `29/03/2003` all normalise to `YYYY-MM-DD` plus an optional
kick-off time. Dates are never round-tripped through a `Date`: these are Brazilian calendar dates,
and a UTC conversion moves evening kick-offs across midnight. Impossible dates (`2023-02-30`,
`2019-02-29`) are rejected rather than silently coerced. User-supplied bounds accept either format,
and an unparseable one raises an explicit error instead of being quietly dropped.

`BR-Football-Dataset.csv` has no season column, only a date. Brazilian league seasons normally run
May–December, so the year is the season — except 2020, which the pandemic pushed into February 2021.
League matches played January–March are therefore assigned to the previous season; cups genuinely
start in February, so the rule is applied to the leagues only.

### Standings are inferred, and say so

No source file contains a table. Standings replay the season's results (3 points for a win, 1 for a
draw; ties broken by wins, then goal difference, then goals scored). The champion and the four
relegation places are consequently *inferences*, so the result carries a `complete` flag, and every
standings answer states in its text that it was calculated from matches rather than quoted from an
official table. A partial season says how many of the expected matches it actually holds.

Cup winners are decided on aggregate. Away goals and penalty shoot-outs are not in the data, so a
level tie yields *no* winner and an explanatory note rather than a guess.

### Joining players to matches without inventing links

The FIFA file is worldwide and has no league or country column, and club names collide across
continents: Mexico's Club América reduces to the same name as América-MG, Portugal's Boavista to
Rio's, and "FC Barcelona" to the Ecuadorian Barcelona that plays the Libertadores. Two filters keep
the join honest — a club is only offered for linking if its squad's most common nationality is
Brazil, and it is only linked if the team registry curates it as a club in a Brazilian state. That
yields 15 Brazilian clubs and 300 players linked to match history, with no false pairs. Every other
club remains fully searchable by its raw label.

---

## Known limitations

These are properties of the source data, surfaced rather than papered over:

- **FIFA coverage.** The FIFA edition in `fifa_data.csv` licensed only 15 Brazilian clubs. Flamengo,
  Palmeiras, Corinthians, São Paulo and Vasco have no squad in it; `search_players` says so
  explicitly instead of returning a bare empty list. The licensed Brazilian squads also carry
  fictional player names, an artefact of that edition.
- **Player names.** `Gabriel Barbosa` is absent from this FIFA edition. `player_profile` returns the
  closest match but labels it as inexact and lists the alternatives.
- **Implausible source rows are rejected.** Two rows are dropped and counted as skipped: a Copa do
  Brasil fixture listing "Bragantino - PA" as both home and away, and a Campeonato Brasiliense match
  that `BR-Football-Dataset.csv` tags as Série A and dates to January 2016. The national divisions
  do not play in January, and left in place that single row added two clubs that have never played
  in the division to the 2015 table and suppressed its champion and relegation places.
- **Genuinely missing data is not invented.** Série A 2023 holds 377 of 380 fixtures because
  `BR-Football-Dataset.csv` is incomplete, so that season reports as partial and names no champion —
  its top row is *not* the real 2023 winner. The 2021 Libertadores final is absent from the source,
  and the 2022 final is present but carries no date, season or score.
- **Cup ties level on aggregate have no winner.** Away goals and penalty shoot-outs are not in the
  data. Some level finals in this era were decided on away goals and some on penalties, and nothing
  in the files distinguishes them, so the 2017 Copa do Brasil final reports as undecidable rather
  than guessing.
- **Lower-division name collisions.** Disambiguation is curated for the clubs that reach Série A and
  the Libertadores. Two lower-tier clubs sharing a base name and a state can still conflate, and a
  club whose name ends in a two-letter initialism that collides with a state code may still split.
- **No goalscorers.** None of the files record who scored, so "top scorers" is not answerable and no
  tool pretends otherwise.
- **Tiebreakers and points deductions.** The CBF's official tiebreakers continue past goals scored
  into head-to-head and disciplinary records, which the data lacks; ties that deep are broken by
  name for determinism. Administrative points deductions are also absent, so 2013 shows the correct
  on-field table rather than the official one that relegated Portuguesa.

---

## Testing

```bash
npm test
```

Four layers:

**BDD feature files** (`tests/features/*.feature`, 75 scenarios) — the specification asks for
Gherkin, so the `.feature` files are the actual test definitions, executed by a small parser and
step registry in `tests/support/`. Steps drive the real MCP tool handlers, so a passing scenario is
evidence about the shipped server.

```gherkin
Scenario: Find matches between two teams
  Given the match data is loaded
  When I call "search_matches" with {"team":"Flamengo","opponent":"Fluminense","limit":50}
  Then the call should succeed
  And the field "total" should be at least 15
  And every item in "matches" should involve "flamengo-rj"
```

**Historical invariants** (`tests/unit/graph.test.ts`) — assertions checkable against the real
history of Brazilian football, so a regression in loading or merging shows up as a *historically
wrong* number rather than an opaque count change: season shapes for 2003–2021, the 2019 title race
and relegation places, the 2016–2018 champions, goals-for equalling goals-against across each table.

**Unit tests** — the CSV reader (quoting, CRLF, BOM, accents), date parsing (three formats, leap
years, invalid dates), team resolution (both merges and splits, in both directions), the merge rules
(one case per rule, on synthetic rows), and the tool contract (documentation, validation, error
messages).

**Integration** — `tests/mcp.test.ts` drives the server with a real SDK client over an in-memory
transport, covering the manifest a client actually sees, JSON-Schema generation, and error results.
`tests/sampleQuestions.test.ts` runs 28 of the specification's own sample questions end to end.
`tests/performance.test.ts` enforces the specified budget: simple lookups under 2 s, aggregates
under 5 s — the actual figures are sub-millisecond.

---

## Layout

```
src/
  util/         CSV reader, accent-folding and fuzzy name matching
  domain/       Entities, multi-format date parsing, team identity resolution
  data/         Per-file CSV readers, fixture merging, data directory discovery
  graph/        In-memory knowledge graph and its indexes
  query/        Match selection, team records, standings, player search, statistics
  format/       Text rendering for the model to read back
  tools/        Tool definitions (Zod schema + pure handler)
  server.ts     MCP wiring
  index.ts      stdio entry point
  cli/ask.ts    CLI over the same handlers
tests/
  features/     Gherkin scenarios
  support/      Gherkin parser and step definitions
  unit/         Focused tests per module
```

Tools are declared independently of the transport — each is a Zod schema plus a pure
`(graph, input) → { text, data }` function — so the tests exercise the same code path a client does.

---

## Data sources and licences

Kaggle data cannot be downloaded without an account, so these freely available datasets were
downloaded in advance and are included here with attribution:

- https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro — CC BY 4.0
  - `data/kaggle/Brasileirao_Matches.csv`
  - `data/kaggle/Brazilian_Cup_Matches.csv`
  - `data/kaggle/Libertadores_Matches.csv`
- https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches — CC0 Public Domain
  - `data/kaggle/BR-Football-Dataset.csv`
- https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019 — CC BY 4.0
  - `data/kaggle/novo_campeonato_brasileiro.csv`
- https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data — Apache 2.0
  - `data/kaggle/fifa_data.csv`

The specification this implements is in [`TASK.md`](TASK.md) (also `brazilian-soccer-mcp-guide.md`).
For demo and non-commercial use.
