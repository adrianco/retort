# Brazilian Soccer MCP Server

A Model Context Protocol server, written in Go, that turns six Kaggle datasets
into a queryable knowledge graph of Brazilian club football and exposes it to an
LLM as 14 natural-language-shaped tools.

Implements [`TASK.md`](TASK.md) (also mirrored as `brazilian-soccer-mcp-guide.md`).

## Quick start

```sh
go build -o brazilian-soccer-mcp .
./brazilian-soccer-mcp -check      # load the data, print a report, exit
./brazilian-soccer-mcp             # serve MCP on stdio
```

Register it with an MCP client (Claude Code shown; adjust paths as needed):

```sh
claude mcp add brazilian-soccer -- /abs/path/to/brazilian-soccer-mcp -data /abs/path/to/data/kaggle
```

The data directory defaults to `./data/kaggle` and can be set with `-data` or
the `SOCCER_DATA_DIR` environment variable.

## What gets loaded

```
rows_per_file        BR-Football-Dataset.csv         10296
                     novo_campeonato_brasileiro.csv   6886
                     Brasileirao_Matches.csv          4098
                     Brazilian_Cup_Matches.csv        1319
                     Libertadores_Matches.csv         1253
                     fifa_data.csv                   18207
raw match rows       23852
merged duplicates     7075
unique matches       16777
clubs                  408
load time              ~100 ms
```

| Competition | Seasons |
|---|---|
| Brasileirão Série A | 2003–2023 |
| Brasileirão Série B | 2014–2023 |
| Brasileirão Série C | 2014–2023 |
| Copa do Brasil | 2012–2023 |
| Copa Libertadores | 2013–2022 |

Everything is held in memory and never mutated after start-up, so queries are
pointer walks rather than file scans and the graph is safe for concurrent use.

## Tools

| Tool | Answers |
|---|---|
| `find_matches` | "Show me all Flamengo vs Fluminense matches", "What matches did Palmeiras play in 2023?", "Find all Copa do Brasil finals" |
| `team_statistics` | "What is Corinthians' home record in 2022?" |
| `head_to_head` | "How do Grêmio and Internacional compare in the Grenal?" |
| `compare_teams` | "Compare Palmeiras and Santos head-to-head" |
| `search_teams` | "What competitions has Palmeiras played in?", disambiguating club names |
| `find_players` | "Find all Brazilian players", "Show me all forwards from Santos" |
| `club_squad` | "Which players play for Internacional?" |
| `brazilian_club_ratings` | "Brazilian players at Brazilian clubs" (player × match cross-file join) |
| `league_standings` | "Who won the 2019 Brasileirão?", "Which teams were relegated in 2020?" |
| `competition_stats` | "What's the average goals per match?", "Show me the biggest wins" |
| `team_leaderboard` | "Which team scored the most goals in Série A 2023?", "Which team has the best away record?" |
| `compare_seasons` | "Compare the 2018 and 2019 seasons" |
| `find_derbies` | "Show me all derbies in 2023" |
| `dataset_info` | "What data do you actually have?" |

Every tool returns both a prose block an LLM can quote directly and a structured
JSON payload for post-processing.

## How the data problems were solved

The specification's "Data Quality Notes" turn out to understate the mess. Four
problems needed real work.

### 1. Team name normalisation

The same club is spelled up to six ways across files: `Flamengo`,
`Flamengo-RJ`, `Flamengo - RJ`, `CR Flamengo`, `Clube de Regatas do Flamengo`.
`internal/normalize` strips, in order: quotes, parenthesised country/state tags
(`Nacional (URU)`, `América FC (Minas Gerais)`), trailing state codes, accents,
punctuation, and club-type words (`Esporte Clube`, `Sport Club`, `FC`, `EC`,
dangling `do`/`da`/`de`).

The hard part is not over-merging. `Atlético-MG` and `Athletico-PR` are
different clubs whose names normalise identically; so are `Flamengo-RJ` and
`Flamengo-PI`, `Botafogo-RJ` and `Botafogo-PB`, `Santos-SP` and `Santos-AP`. So
base names known to be shared keep their state code in the canonical ID, and an
alias table pins down the roughly 60 clubs that appear both with and without a
state suffix. `TestResolveCollapsesSpellings` and
`TestResolveKeepsDistinctClubsApart` guard both directions.

### 2. Cross-file deduplication

The five match files overlap heavily — 2019 Série A appears in three of them.
Loading them naively triples that season and makes every computed table
nonsense. 7,075 of 23,852 rows are duplicates.

The datasets also disagree about dates by a day (late kick-offs recorded in
different time zones), so a date-based key would miss those. Instead, league
fixtures key on `competition + season + home + away`: a double round robin plays
each ordered pair exactly once per season, which makes the key exact regardless
of date. Knockout competitions can replay a pairing, so those add the month.
Merging fills gaps rather than overwriting, so a match ends up with the round
number from one file, the stadium from another and the shot counts from a third.

The proof this works: the calculated 2019 Série A table is exactly the real one
— 380 matches, Flamengo champions on 90 points (28W 6D 4L, 86 goals), Santos and
Palmeiras on 74, Cruzeiro/CSA/Chapecoense/Avaí relegated.

### 3. Copa do Brasil round numbering

The `round` column is a bare integer whose meaning shifts between seasons
because the competition was restructured: the final is round 6 in 2012, round 7
in 2016 and round 8 from 2017. A fixed lookup table is wrong for most seasons.
`labelCupStages` instead names stages backwards from the last round of each
season, and only when that season actually reached a two-legged final — 2021 in
this file stops at the round of 16 and is left as numbered rounds. The
recovered finals check out against the real champions (Palmeiras 2012, Flamengo
2013, Atlético Mineiro 2014, Palmeiras 2015, Grêmio 2016, Cruzeiro 2017/2018).

### 4. Unplayable fixtures

102 rows carry `NA` scores — the abandoned Chapecoense fixtures of 2016 and
postponed 2022 matches. Counting them as 0-0 would corrupt every table, so they
are skipped and the count is reported by `dataset_info` rather than silently
dropped.

## Known data limitations

These are properties of the provided datasets, surfaced rather than papered
over. The server's MCP instructions tell the model about them.

- **No goalscorer data anywhere.** No file records who scored, so "top scorers"
  is genuinely unanswerable. The server says so rather than guessing.
- **The FIFA file is a FIFA 19 snapshot** with attributes but no appearances,
  and it omits unlicensed clubs — Flamengo, Palmeiras, Corinthians and São Paulo
  have no players in it. `club_squad` returns an explicit no-data error for
  those rather than an empty squad that reads like "this club has no players".
  Grêmio, Santos, Internacional, Cruzeiro, Atlético Mineiro, Bahia, Vitória,
  Chapecoense, Ceará, Botafogo, Fluminense and others are present.
- **Player names at those clubs are FIFA's pseudonyms.** Where EA lacked player
  licences it invented names, so Grêmio's top-rated player reads as "Ronaldo
  Cabrais". The ratings are real, the names at Brazilian clubs frequently are
  not. Players at licensed European clubs (Neymar, Alisson, Casemiro) are named
  correctly.
- **`brazilian_club_ratings` requires three players per club by default.** A few
  foreign Libertadores opponents (Santos Laguna, Universidad de Chile) appear in
  both datasets with one Brazilian on the books, and would otherwise top a
  ranking by average rating.
- **Standings are calculated, not official**, using three points per win and CBF
  tie-breaks (points, wins, goal difference, goals for). They agree with the
  real tables for the complete seasons tested, but a season the data does not
  fully cover is flagged as incomplete rather than presented as final.
- **Série A 2023 has no round numbers**, because only BR-Football-Dataset covers
  it and that file has no round column.

## Layout

```
main.go                       stdio entry point, -check mode
internal/normalize/           club name canonicalisation
internal/soccer/
  model.go                    Match, Team, Player, Record
  load.go                     CSV parsing, date/number tolerance, cup stages
  graph.go                    dedup, merge, indexes, team resolution
  matches.go                  match search, head-to-head
  teams.go                    team records, comparison
  standings.go                league tables, competition name resolution
  players.go                  FIFA search, squads, player×match join
  stats.go                    aggregates, leaderboards, derbies
internal/mcpserver/
  server.go                   MCP tool definitions and schemas
  render.go                   prose formatting of results
```

## Testing

BDD-style Given/When/Then scenarios, as the specification asks for. Rather than
adding a Cucumber runner, each scenario is a Go subtest whose steps are recorded
and replayed on failure, so a failure reads like the feature file it came from:

```
--- FAIL: TestFeatureCompetitionQueries/who_won_the_2019_Brasileirao
    Scenario: who won the 2019 Brasileirao
      Given the match data is loaded
      When I calculate the 2019 Brasileirao standings
      Then the season is complete: 20 teams and 380 matches
      And Flamengo are champions on 90 points
```

```sh
go test ./...           # all suites
go test -race ./...     # concurrency
go test -v ./internal/soccer/ -run TestFeature   # read the scenarios
```

Coverage:

- `internal/normalize` — name collapsing and, equally, non-collapsing of
  distinct clubs; state/country tag splitting; UTF-8 folding.
- `internal/soccer` — all five specification capability areas as scenarios, plus
  loader unit tests for the three date formats, `NA`/float/quoted numbers, the
  UTF-8 BOM, ragged rows, the dedup key, merge semantics and cup stage naming.
  Standings are checked against the known-correct 2019 and 2020 seasons, and
  internal consistency (goals for equals goals against across a table, W+D+L
  equals matches played, points follow the three-point rule) is verified across
  several seasons.
- `internal/mcpserver` — drives the server through a **real MCP client over an
  in-memory transport**, so the handshake, generated JSON schemas and argument
  marshalling are all exercised. 24 sample questions from the specification are
  run end to end and asserted on the prose the model would receive; error paths,
  near-miss club suggestions, name-variation equivalence, concurrent calls and
  the 2s/5s latency budgets are covered too.

## Specification checklist

| Requirement | Status |
|---|---|
| Search and return match data from all provided CSV files | ✅ all five match files, deduplicated |
| Search and return player data | ✅ `find_players`, `club_squad` |
| Calculate basic statistics (wins, losses, goals) | ✅ `team_statistics`, `competition_stats` |
| Compare teams head-to-head | ✅ `head_to_head`, `compare_teams` |
| Handle team name variations | ✅ `internal/normalize`, tested both directions |
| Return properly formatted responses | ✅ prose + structured JSON per tool |
| Simple lookups < 2 s | ✅ sub-millisecond; asserted in tests |
| Aggregate queries < 5 s | ✅ single-digit milliseconds; asserted in tests |
| All 6 CSV files loadable and queryable | ✅ |
| At least 20 sample questions answerable | ✅ 24 run end to end through MCP |
| Cross-file queries (player + match) | ✅ `brazilian_club_ratings`, `club_squad` |

## Data Sources

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
