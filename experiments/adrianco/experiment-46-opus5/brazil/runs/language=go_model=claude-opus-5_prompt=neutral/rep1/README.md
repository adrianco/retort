# Brazilian Soccer MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io) server, written in Go, that turns six
Kaggle CSV files into a queryable knowledge graph of Brazilian football and exposes it to an LLM as
18 tools.

Implements the specification in [brazilian-soccer-mcp-guide.md](brazilian-soccer-mcp-guide.md).

```
$ go run . -check
Clubs:   387
Matches: 16731
Players: 18207
Edges:   50493
```

## Quick start

```bash
go test ./...                       # run the BDD suite (~5s, no network needed)
go run . -check                     # load the datasets and print a coverage report
go run . -list-tools                # list the 18 MCP tools
go run .                            # serve MCP over stdio

# ask a question directly (real MCP round trip over an in-memory transport)
go run . -quiet -tool competition_standings -args '{"season":2019}'
go run . -quiet -tool head_to_head -args '{"team_a":"Gremio","team_b":"Internacional"}'
```

Register it with an MCP host, e.g. in Claude Desktop's `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/path/to/brazilian-soccer-mcp",
      "env": { "BRAZILIAN_SOCCER_DATA": "/path/to/data/kaggle" }
    }
  }
}
```

The data directory is found automatically when the binary runs anywhere inside this repository;
`BRAZILIAN_SOCCER_DATA` or `-data` override it.

## What it does

The five match datasets and one player dataset are loaded into an in-memory graph:

```
   Club ──home_of / away_of──▶ Match ──part_of──▶ Competition + Season
   Club ◀──plays_for────────── Player                  │
                                 └──played_at──▶ Stadium
```

Nothing is pre-aggregated. Standings, records, head-to-head summaries and averages are all
computed from the match edges when a tool is called, so every number traces back to source rows.

### The interesting part: making the data usable

The raw files disagree with each other constantly, and most of the implementation is about
reconciling them.

**Team names.** The same club is spelled `Palmeiras-SP`, `Palmeiras - SP`, `Palmeiras` and
`SE Palmeiras` across the files; there are abbreviations (`C.r.b. - AL`), legal names
(`Vitoria F. C. - ES`), editorial asides (`Boavista Sport Club (antigo Esporte Clube Barreira) - RJ`)
and country markers (`Nacional (URU)`). `internal/soccer/normalize.go` reduces any spelling to a
`(base name, region)` pair — accent-folded, punctuation-free, with the state or country code kept
*separate* rather than discarded. That separation matters: `Flamengo - PI` is not Flamengo, and
`Santos - AP` is not Santos. A curated table in `internal/soccer/clubs.go` then pins down the
identities that no string rule can derive (`Vasco` = `Vasco da Gama-RJ`, `Athletico` =
`Atlético-PR`, `Sport Club do Recife` = `Sport-PE`).

**Duplicate fixtures.** Série A 2012–2019 appears in *three* of the five match files. Without
de-duplication, Palmeiras play 95 matches in 2015 and every table is nonsense. Fixtures are merged
on competition + season + home club + away club, additively: the first source owns the score, later
sources contribute what it lacked (stadium names from the historical file, shot and corner counts
from BR-Football). Two rows from the *same* file are never merged — `novo_campeonato_brasileiro.csv`
lists Botafogo as home for both 2009 Botafogo–Flamengo meetings, and folding those together would
silently delete a match.

**Source defects.** `BR-Football-Dataset.csv` has no season column, so its season is derived from
the football calendar rather than the calendar year — otherwise the 111 Série A matches played in
January and February 2021 (the COVID-delayed 2020 season) become a phantom second half of 2021. It
also labels 2021 Série B fixtures as Série A, so once a competition season has a primary source,
later sources may only corroborate its fixtures, never introduce clubs that were not in that
division. 42 rows are rejected on those grounds, and the count is reported by `list_datasets`.

**Correctness check.** The test suite asserts the calculated tables against independently known
football history: all 20 Brasileirão champions from 2003 to 2022, their exact points totals, and
the relegated clubs. Every season from 2006 to 2022 contains exactly 380 fixtures with every club
on 38 matches; 2003–2005 correctly hold 552, 552 and 462 for their 24-, 24- and 22-club formats.

## Tools

| Tool | Answers questions like |
|------|------------------------|
| `find_matches` | "What matches did Palmeiras play in 2022?", "Find all Copa do Brasil finals" |
| `match_details` | "What were the shots and corners in that match?" |
| `find_derbies` | "Show me all derbies in 2023" |
| `search_teams` | "Which clubs are called Atlético?" |
| `team_profile` | "What competitions has Palmeiras played in?" |
| `team_stats` | "What is Corinthians' home record in 2022?" |
| `head_to_head` | "Show me all Flamengo vs Fluminense matches" |
| `search_players` | "Find all Brazilian players", "Show me all forwards from Santos" |
| `player_profile` | "Who is Neymar?" |
| `club_squad` | "Who are the highest-rated players at Grêmio?" |
| `list_competitions` | "What competitions and seasons are available?" |
| `competition_standings` | "Who won the 2019 Brasileirão?", "Which teams were relegated in 2020?" |
| `competition_stats` | "What's the average goals per match in the Brasileirão?" |
| `compare_seasons` | "Compare the 2018 and 2019 seasons" |
| `team_leaderboard` | "Which team has the best away record?", "Who scored the most goals in 2023?" |
| `notable_matches` | "Show me the biggest wins in the dataset" |
| `graph_summary` | "How big is the knowledge graph?" |
| `list_datasets` | "Where does this data come from?" |

Two resources, `brazilian-soccer://datasets` and `brazilian-soccer://graph`, expose provenance and
graph shape as JSON.

Every tool returns both a human-readable text block and typed structured content; the JSON schemas
are derived from the Go argument structs, so they cannot drift from the handlers. Errors are
actionable — an unknown club suggests `search_teams`, an unavailable season lists the ones that
exist, an ambiguous name lists the candidates.

### Example

```
$ go run . -quiet -tool team_stats -args '{"team":"Corinthians","season":2022,"competition":"Serie A","venue":"home"}'
Corinthians (SP) in Brasileirão Série A 2022 (home matches only):
- Matches: 19
- Wins: 12, Draws: 4, Losses: 3
- Goals For: 24, Goals Against: 11 (GD +13)
- Points: 40 (70.2% of available)
- Win rate: 63.2%

Biggest win:  2022-04-16: Corinthians 3-0 Avaí (Brasileirão Série A 2022 Round 2)
Biggest loss: 2022-10-26: Corinthians 0-2 Fluminense (Brasileirão Série A 2022 Round 34)
Data range: 2022-04-16 to 2022-11-13
```

## Coverage

| Competition | Seasons | Notes |
|-------------|---------|-------|
| Brasileirão Série A | 2003–2023 | complete except 2023 (377 of 380 fixtures in the source) |
| Brasileirão Série B | 2014–2023 | single source, some seasons incomplete |
| Brasileirão Série C | 2014–2023 | single source, variable format |
| Copa do Brasil | 2012–2023 | |
| Copa Libertadores | 2013–2022 | includes CONMEBOL opponents |
| FIFA players | FIFA 19 snapshot | 18,207 players, 827 Brazilians |

### Honest limitations

- **The FIFA dataset only licenses 15 Brazilian clubs** (Grêmio, Atlético Mineiro, Cruzeiro,
  Fluminense, Santos, Internacional, América Mineiro, Botafogo, Bahia, Paraná, Athletico
  Paranaense, Vitória, Sport Recife, Chapecoense, Ceará). Flamengo, Palmeiras, Corinthians, São
  Paulo and Vasco have no squads. `club_squad` says so and lists what is available instead of
  returning a bare empty result. Within those 15 clubs, FIFA 19 also substitutes fictional names
  for players it has no licence for, so squad names there are not real.
- **Série B and C come from one source only**, so the primary/secondary cross-check that fixes
  Série A cannot be applied and a few seasons are short or long.
- **Copa do Brasil** involves hundreds of small clubs whose names differ enough between the two
  sources that some fixtures are counted twice; season totals run a few percent above the cup file.
- **No goalscorer data.** None of the datasets records who scored, so "top scorer" questions can
  only be answered at club level (`team_leaderboard` with `metric=goals_for`).
- **~100 fixtures have `NA` scores.** They are kept as fixtures but excluded from records, and the
  count is reported alongside every affected record.

## Layout

```
main.go                      process entry point: stdio server, -check, -list-tools, -tool
internal/soccer/
  model.go                   graph node and edge types
  normalize.go               name/date normalization, accent folding, region parsing
  clubs.go                   curated club identity table, rivalries, FIFA club links
  loader.go                  one reader per CSV file
  resolver.go                two-pass raw-spelling to club-node resolution
  graph.go                   graph assembly, de-duplication, indexes
  query.go                   club lookup and match filtering
  stats.go                   records, standings, aggregates, leaderboards
  players.go                 player search
  format.go                  human-readable rendering
internal/mcpserver/          MCP tool and resource registration
internal/bdd/                Given/When/Then test harness
```

Every file opens with a context comment explaining what it does and why the non-obvious decisions
were made.

## Tests

`go test ./...` runs the whole suite in about five seconds with no network access. It is written as
Gherkin-style scenarios (`internal/bdd`), so `go test ./... -v` reads like a feature file:

```
Feature: Competition Queries
  Scenario: Who won the 2019 Brasileirao
    Given the match data is loaded
    When I request the 2019 Série A standings
    Then Flamengo are champions with 90 points from 28 wins
    And the table is ordered by points then wins then goal difference
```

Coverage:

- **Data quality** — name variations, accents, abbreviations, all four date formats, missing values.
- **Loading** — all six files, plus a synthetic `fstest.MapFS` dataset that pins the merge contract
  without touching the 22 MB of real CSVs.
- **Identity** — 40+ spellings resolve to the right club; homonyms from different states stay apart.
- **De-duplication** — fixture counts per season, source lists, unique ids.
- **The five capability areas** — the specification's own scenarios, asserted against known football
  history.
- **MCP protocol** — a real client session: initialize, tools/list, schema validation, structured
  content agreeing with the text, resources, and six kinds of actionable error.
- **29 sample questions** from the specification, each timed against its latency budget
  (2s simple / 5s aggregate; all answer in single-digit milliseconds).
- **CLI** — dataset discovery, `-check`, `-list-tools`, `-tool`, and bad input.

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

The only runtime dependencies are the official MCP Go SDK
(`github.com/modelcontextprotocol/go-sdk`) and `golang.org/x/text` for Unicode normalization.
