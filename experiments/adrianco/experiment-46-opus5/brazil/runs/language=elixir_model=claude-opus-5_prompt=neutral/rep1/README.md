# Brazilian Soccer MCP Server

An [MCP](https://modelcontextprotocol.io) server, written in Elixir, that turns the six Kaggle CSV
files in `data/kaggle/` into one queryable knowledge graph of Brazilian football — matches, clubs,
competitions and players — and exposes it to an LLM as 24 tools.

```
$ mix soccer.demo
Q21 [Competition queries] Who won the 2019 Brasileirão?
tool: competition_champion %{"competition" => "Brasileirão", "season" => 2019}
------------------------------------------------------------------------------
Brasileirão 2019: Flamengo
- 90 points from 38 matches (28W, 6D, 4L), goals 86-37
- Runner-up: Santos
Table computed from the match results in the dataset (3 points per win); points
deductions and other sanctions are not represented.
```

## Specification
brazilian-soccer-mcp-guide.md (the same content as `TASK.md`)

---

## Quick start

```bash
mix deps.get
mix test          # 205 tests, ~2s once the graph cache is warm
mix soccer.demo   # answers the 32 sample questions from the specification
mix soccer.server # runs the MCP server on stdio
```

Connect an MCP client (Claude Desktop, Claude Code, any stdio MCP client):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "mix",
      "args": ["soccer.server"],
      "cwd": "/path/to/this/repo"
    }
  }
}
```

Or build a standalone binary that needs only Erlang:

```bash
mix escript.build
./brazilian_soccer_mcp                                          # MCP server on stdio
./brazilian_soccer_mcp --list-tools
./brazilian_soccer_mcp --tool head_to_head --args '{"team_a":"Grêmio","team_b":"Internacional"}'
```

---

## What it does

### The knowledge graph

| Node | Count | Notes |
|------|-------|-------|
| Matches | 16,738 | de-duplicated from 23,954 CSV rows |
| Teams | 398 | canonical clubs, with every spelling found in the data |
| Players | 18,207 | FIFA database, linked to Brazilian club nodes |
| Competitions | 5 | Série A, Série B, Série C, Copa do Brasil, Libertadores |

Edges: match → home team / away team, player → club, plus adjacency indexes
(`team → matches`, `competition/season → matches`, `club → players`) so queries never scan
everything.

| Competition | Matches | Seasons |
|-------------|---------|---------|
| Campeonato Brasileiro Série A | 8,403 | 2003–2023 |
| Campeonato Brasileiro Série B | 3,677 | 2014–2023 |
| Campeonato Brasileiro Série C | 1,746 | 2014–2023 |
| Copa do Brasil | 1,657 | 2012–2023 |
| Copa Libertadores | 1,255 | 2013–2022 |

### The tools

| Category | Tools |
|----------|-------|
| Matches | `search_matches`, `head_to_head`, `last_meeting`, `find_derbies` |
| Teams | `team_stats`, `team_profile`, `compare_teams`, `team_rankings`, `resolve_team_name` |
| Players | `search_players`, `player_profile`, `club_squad`, `players_by_nationality` |
| Competitions | `list_competitions`, `league_standings`, `competition_champion`, `cup_bracket`, `competition_summary` |
| Statistics | `match_statistics`, `biggest_wins`, `highest_scoring_matches`, `compare_seasons`, `home_advantage` |
| Meta | `list_datasets` |

Every call returns human-readable text (what the model quotes back) *and* `structuredContent`
with the same result as JSON. The server also publishes four MCP resources:
`brazilian-soccer://datasets`, `://competitions`, `://teams` and `://sample-questions`.

---

## The interesting parts

### 1. One club, many spellings

The datasets spell the same club as `Palmeiras-SP`, `Palmeiras`, `Palmeiras - SP`;
`Atlético - MG` and `Atletico Mineiro`; `Sport-PE`, `Sport Recife` and `Sport Club do Recife`;
`Nacional (URU)` and `Nacional AM`.

`BrazilianSoccer.Names` folds accents, strips punctuation, pulls out the state/country qualifier,
drops club-type words (`EC`, `FC`, `Esporte Clube`, …) and applies a small alias table, producing a
`base` plus an optional qualifier. Whether the qualifier survives into the club id is decided *from
the corpus*: `palmeiras` is unique so its id is `palmeiras`, while Botafogo appears in three
states so the ids are `botafogo-rj`, `botafogo-sp` and `botafogo-pb` — and a bare "Botafogo"
resolves to the Rio club.

The state columns in the CSVs are deliberately **not** used for identity:
`novo_campeonato_brasileiro.csv` files Vitória (Salvador, Bahia) under `ES` in some rows, which
would split the club in two.

### 2. Matches that appear in three files at once

Série A 2014–2019 is in three of the source files. Matches are grouped by
`{competition, season, home, away}` and merged, so nothing is counted twice, while each file's
extra columns survive the merge: the round from `Brasileirao_Matches.csv`, the stadium from
`novo_campeonato_brasileiro.csv`, and shots/corners/attacks from `BR-Football-Dataset.csv`.

Cups can repeat a pairing within a season, so there the merge only collapses dates within one day
of each other — `BR-Football-Dataset.csv` timestamps night kick-offs in UTC and lands them on the
following day.

After merging, Série A holds exactly 380 matches for almost every season since 2006, which is the
sanity check that the club canonicalisation actually worked (`test/data/graph_test.exs`).

### 3. Deriving what the data does not state

No file records who won anything, so:

* **League champions and relegation** come from a table computed from results (3 points per win,
  ordered by points, wins, goal difference, goals for).
* **Cup champions** come from the final, on aggregate over both legs. When the aggregate is level
  the answer says the shoot-out is not in the data rather than guessing — the 2013 Libertadores
  (Atlético Mineiro vs Olimpia) is exactly that case.
* **Copa do Brasil stages** are derived from the bracket's shape: a round with 2 matches is the
  final, 4 the semi-finals, 8 the quarter-finals, 16 the round of 16. Only the last rounds of a
  season are labelled, and only exact counts count, so a season the files cover partially (2021)
  does not get a fake final.

### 4. Saying what the data cannot answer

* The 2009 files are one match short, so the 2009 table warns that it may differ from the official
  one instead of quietly promoting the wrong champion.
* The FIFA 19 export does not license Flamengo, Palmeiras, Corinthians, São Paulo or Vasco.
  `club_squad` for those clubs explains exactly that and lists the clubs that *do* have players,
  rather than answering "not found".
* Matches with no score in the data (the 2022 Libertadores final) are shown as
  `[result not in dataset]`.

### 5. Speed

The graph is built once and kept in `:persistent_term`, so queries read it with no copying. The
parsed graph is also memoised on disk (keyed by size + mtime of every CSV), which turns a ~1.6 s
cold build into a ~160 ms start. The specification's budget is < 2 s for simple lookups and < 5 s
for aggregates; `test/performance_test.exs` asserts it — in practice lookups are ~1 ms and the
heaviest aggregate ~100 ms.

---

## Layout

```
lib/brazilian_soccer/
  names.ex             club name normalisation and canonical ids
  dates.ex             ISO / Brazilian / timestamp date parsing
  model.ex             Competition, Team, Match, Player nodes
  config.ex            where the CSVs and the cache live
  repo.ex              load once, cache on disk, hand out the graph
  format.ex            results -> the text an LLM reads back
  sample_questions.ex  the question catalogue (demo, MCP resource, acceptance test)
  cli.ex               escript entry point
  data/
    csv.ex             RFC4180 reader (BOM, ragged rows, UTF-8)
    loader.ex          one reader per source file -> a common raw shape
    graph.ex           canonicalise, de-duplicate, index
  query/
    filters.ex         argument coercion shared by every query
    matches.ex         search, head-to-head, derbies
    teams.ex           records, profiles, comparisons, rankings
    competitions.ex    standings, champions, brackets, summaries
    players.ex         player search, profiles, squads
    stats.ex           aggregates, biggest wins, season comparisons
  mcp/
    tools.ex           the tool catalogue (schema + query + formatter)
    server.ex          JSON-RPC 2.0 method handling (pure functions)
    stdio.ex           newline delimited JSON transport
    json.ex            structs/atoms/dates -> JSON-encodable data
```

---

## Tests

`mix test` — 205 tests, BDD style: each file is a `Feature`, each `describe` a `Scenario`, each
test a `Given / When / Then` sentence.

| File | Covers |
|------|--------|
| `test/names_test.exs` | accents, suffixes, aliases, ambiguity resolution |
| `test/dates_test.exs` | every date format and every junk value in the data |
| `test/data/csv_test.exs` | quoted fields, BOM, ragged rows, cell coercion |
| `test/data/loader_test.exs` | all six files, per-file column mapping, season spill-over |
| `test/data/graph_test.exs` | canonicalisation, de-duplication, stages, player links |
| `test/query/*_test.exs` | the five query categories from the specification |
| `test/format_test.exs` | answers match the shapes in the specification |
| `test/mcp/server_test.exs` | initialize, tools/list, tools/call, resources, batches, errors |
| `test/mcp/stdio_test.exs` | line protocol plus a real `mix soccer.server` session over pipes |
| `test/sample_questions_test.exs` | all 32 sample questions answer, with spot-checked facts |
| `test/performance_test.exs` | the specification's 2 s / 5 s budgets |
| `test/repo_test.exs` | lazy loading and the on-disk cache |

Optional configuration: `BRAZILIAN_SOCCER_DATA_DIR` (where the CSVs live) and
`BRAZILIAN_SOCCER_CACHE` (cache path, or `false` to disable caching).

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
