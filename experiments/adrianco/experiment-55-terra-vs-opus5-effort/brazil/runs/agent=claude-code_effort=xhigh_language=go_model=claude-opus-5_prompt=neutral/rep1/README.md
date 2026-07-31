# Brazilian Soccer MCP Server

An [MCP](https://modelcontextprotocol.io) server, written in Go, that turns the six
Kaggle datasets in `data/kaggle/` into one queryable knowledge graph and exposes it
to an LLM as 15 tools, 5 resources and 3 prompt templates.

It answers questions such as *"Who won the 2019 Brasileirão?"*, *"What is Corinthians'
home record in 2022?"*, *"Show me all Flamengo vs Fluminense matches"*, *"Which team
has the best away record?"* and *"Find all Brazilian players"* — see
[Sample questions](#sample-questions).

```
$ go run . -quiet -call standings -args '{"season":2019}'
2019 Brasileirão Série A standings (calculated from matches)
Champion: Flamengo

#   Team                       P   W   D   L   GF   GA    GD  Pts
1   Flamengo                  38  28   6   4   86   37   +49   90 - Champion
2   Santos                    38  22   8   8   60   33   +27   74
3   Palmeiras                 38  21  11   6   61   32   +29   74
...
17  Cruzeiro                  38   7  15  16   27   46   -19   36 - Relegated
```

---

## Quick start

```bash
go build ./...          # no network needed: dependencies are vendored
go test ./...           # 122 tests including 34 BDD scenarios
go run . -demo          # answer a set of sample questions and print them
go run . -list-tools    # print the tool catalogue with JSON schemas
go run .                # run as an MCP server over stdio (what a client launches)
go run . -http :8080    # run as an MCP server over streamable HTTP
```

`-call` runs a single tool from the shell, which is the quickest way to explore:

```bash
go run . -quiet -call head_to_head   -args '{"team_a":"Grêmio","team_b":"Internacional"}'
go run . -quiet -call team_stats     -args '{"team":"Corinthians","competition":"Serie A","season":2022,"venue":"home"}'
go run . -quiet -call search_players -args '{"nationality":"Brazil","group_by_club":true,"limit":5}'
go run . -quiet -call dataset_info   -args '{}'
```

### Connecting it to Claude

Claude Code:

```bash
claude mcp add brazilian-soccer -- go run . -quiet     # from this directory
# or, after `go build -o brazilian-soccer-mcp .`
claude mcp add brazilian-soccer -- /full/path/brazilian-soccer-mcp -quiet -data /full/path/data/kaggle
```

Claude Desktop (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/full/path/brazilian-soccer-mcp",
      "args": ["-quiet", "-data", "/full/path/data/kaggle"]
    }
  }
}
```

Startup loads all six CSVs in about 120 ms and holds them in memory; every query after
that takes microseconds to a few milliseconds.

---

## What was built

### Architecture

```
main.go                      CLI: stdio server, HTTP server, -call, -demo, -list-tools
internal/soccer/             the knowledge graph and query engine (no MCP types)
  model.go                   Competition, Team, Match, Player, MatchStats, SourceInfo
  names.go                   team-name normalisation: accents, state/country suffixes, aliases
  loader.go                  one reader per CSV, season inference, load report
  graph.go                   registry, indexes, cross-source de-duplication, resolution
  matches.go                 MatchFilter, match search, head-to-head
  teams.go                   Record accumulator, team stats, team profile, club directory
  competitions.go            standings, champions, cup brackets, season summaries
  players.go                 FIFA player search and profiles
  analytics.go               leaderboards, aggregate statistics, derby table
  format.go                  the human-readable rendering of every result
internal/mcpserver/          the MCP layer, built on the official Go SDK
  server.go                  server wiring, resources, prompts, instructions
  tools.go                   the 15 tools: arguments, schemas, handlers
features/*.feature           BDD acceptance criteria in Gherkin
bdd/                         Gherkin parser, step registry and the World the steps drive
```

The split matters: `internal/soccer` knows nothing about MCP, so the query engine is
testable on its own, and `internal/mcpserver` only maps arguments and renders results.

### The hard part: one club, five spellings

The five match files each name clubs differently, and merging them wrongly is the
difference between a correct answer and a plausible lie:

| File | Spelling |
|---|---|
| `Brasileirao_Matches.csv` | `Palmeiras-SP`, `Athletico-PR` |
| `Brazilian_Cup_Matches.csv` | `América - MG`, `Boavista Sport Club (antigo Esporte Clube Barreira) - RJ` |
| `BR-Football-Dataset.csv` | `America MG`, `Vasco Da Gama RJ` |
| `novo_campeonato_brasileiro.csv` | `Grêmio`, `Athletico-PR` |
| `Libertadores_Matches.csv` | `Nacional (URU)`, `Barcelona-EQU`, `Athletico` |
| `fifa_data.csv` | `América FC (Minas Gerais)`, `Sport Club do Recife` |

`names.go` splits a raw name into `(base, state, country)`: it folds accents to ASCII,
pulls `(URU)` and `(Minas Gerais)` out of parentheses, peels a trailing `-SP` / ` - MG` /
` PB` when the token really is a UF or country code, strips generic club words
(`Fortaleza EC` → `fortaleza`, `Ceará Sporting Club` → `ceara`), and then applies a
curated alias table for renames and long official names (`Athletico Paranaense` and
`Atlético-PR` are the same club; `Sport Club do Recife` is `Sport-PE`).

`graph.go` then decides identity across *all* files at once. A base seen with exactly
one state becomes one club and bare spellings join it — that is how `Palmeiras`,
`Palmeiras-SP` and `Palmeiras - SP` become one node. A base seen with several states
stays several clubs, so **Atlético-MG and Athletico-PR, América-MG and América-RN,
Botafogo-RJ and Botafogo-PB never merge**. Bare spellings of a contested base are
resolved through a curated default (`Flamengo` means the Rio club, not Flamengo-PI).

Two collisions needed evidence rather than names to settle: the Libertadores file writes
`River Plate` and `Peñarol` for the Argentine and Uruguayan giants while the Copa do
Brasil file has a `River Plate - SE` from Sergipe and a `Penarol - AM` from Amazonas, so
those names carry an explicit default country. The FIFA join has the same problem in
reverse — `FC Barcelona` shares a base with the Ecuadorian `Barcelona-EQU` — so a squad
only links to a Brazilian club when the squad really is mostly Brazilian, and to a
foreign club only on a full-name match. Nicknames (`Timão`, `Galo`, `Verdão`, `Mengão`,
`Furacão`) are registered as extra lookup keys.

The result is checked by tests: 10 clubs must unify across every file that names them,
and 7 pairs of similarly named clubs must stay apart.

### The other hard part: the same match in three files

Série A 2014–2019 appears in `Brasileirao_Matches.csv`, `novo_campeonato_brasileiro.csv`
**and** `BR-Football-Dataset.csv`. Without handling that, "average goals per match" would
be computed over triple-counted fixtures.

Each row gets a fixture key of `competition | season | home | away`. Within a group the
file with explicit season and round numbers wins and becomes the *primary* row; the
losing rows attach to it and donate the columns only they have — the stadium from the
historic file, the shots, attacks and corners from BR-Football. Every query runs over
the primary view, and `search_matches` has an `include_duplicates` flag for inspecting
the raw rows. This is asserted by test: every Série A season from 2006 to 2022 must hold
exactly 380 fixtures, 2003 must hold 552 (24 clubs) and 2005 must hold 462 (22 clubs).

`BR-Football-Dataset.csv` has no season column, only a date. League seasons run
April–December, except the pandemic-shifted 2020 season which finished in February 2021,
so January and February league matches are assigned to the previous season while cups
keep the calendar year.

### Answers the data cannot support are refused, not invented

- **Penalty shoot-outs.** The 2013 Libertadores final and the 2015 and 2017 Copa do
  Brasil finals ended level on aggregate. `champions` reports *"decided on penalties,
  which the datasets do not record"* rather than picking a winner.
- **Incomplete seasons.** The 2023 Série A data stops three matches short, so the table
  is labelled a partial standing and the leader is not called champion.
- **Goalscorers.** No file records who scored, so `competition_summary` says so and
  reports per-team scoring instead.
- **Unlicensed clubs.** FIFA 19 licenses only 15 Brazilian clubs, so asking for
  Flamengo's squad returns an explanation and the list of clubs that *are* covered.
- **Unplayed fixtures.** 82 Brasileirão rows and 16 Copa do Brasil rows carry `NA`
  scores; they are skipped and counted in `dataset_info` rather than treated as 0-0.
- **Unknown clubs.** "Real Madrid" produces an error naming the closest known clubs, not
  an empty list.

### Verification against reality

The tests assert facts that exist outside this code, so a regression in the loader, the
normaliser or the de-duplication shows up as a wrong football result:

- 2019 Série A: Flamengo champion on 90 points (28W 6D 4L); Santos second and Palmeiras
  third, both on 74 — which only comes out right because the CBF tie-break is wins
  before goal difference; Cruzeiro, CSA, Chapecoense and Avaí relegated.
- 2020 Série A: Flamengo champion; Vasco, Goiás, Coritiba and Botafogo relegated.
- Fourteen consecutive league champions from 2009 to 2022.
- Libertadores winners 2014–2020 and Copa do Brasil winners 2012–2020, each derived from
  the final rather than looked up.
- The 2018 Libertadores final: River Plate beat Boca Juniors 5–3 on aggregate.

---

## Tools

| Tool | What it answers |
|---|---|
| `search_matches` | Matches by club, opponent, competition, season, date range, round, stage or venue |
| `head_to_head` | Full record between two clubs, with home/away splits, biggest wins and form |
| `team_stats` | Win/draw/loss, goals, points, clean sheets and form; filter by competition, season, home/away |
| `team_profile` | Cross-dataset club overview: name variants, competitions, titles, rivalries, stadiums, squad |
| `list_teams` | Browse or search the club directory; resolves ambiguous names like "Atlético" |
| `search_players` | FIFA database by name, nationality, club, position, rating, age; optional per-club breakdown |
| `player_profile` | One player's ratings, physical data, contract, best attributes and club link |
| `standings` | League table computed from results, with champion and relegation zones |
| `champions` | Winners per season, cups resolved from the final on aggregate |
| `competition_bracket` | Knockout bracket with two-legged ties aggregated |
| `competition_summary` | Season headline numbers; several seasons produce a comparison |
| `team_rankings` | Rank clubs by wins, points, win rate, goals, defence, clean sheets, goal difference |
| `aggregate_stats` | Goals per match, home advantage, biggest wins, highest scoring matches |
| `list_derbies` | Brazil's traditional derbies with their records, filterable by season |
| `dataset_info` | Provenance, licences, row counts, seasons and known gaps |

Every tool returns **both** a rendered text answer (for the model to quote) and a
structured JSON payload conforming to a declared output schema (for the client to
compute with).

**Resources:** `soccer://datasets`, `soccer://teams`, `soccer://competitions`,
`soccer://sample-questions`, `soccer://tools` — browsable views a client can read
without calling a tool.

**Prompts:** `club_report`, `season_review`, `compare_clubs` — templates that tell the
model which tools to combine for a full analysis.

---

## Sample questions

| Question | Tool | Arguments |
|---|---|---|
| Show me all Flamengo vs Fluminense matches | `head_to_head` | `team_a=Flamengo, team_b=Fluminense` |
| What matches did Palmeiras play in 2023? | `search_matches` | `team=Palmeiras, season=2023` |
| Find all Copa do Brasil finals | `search_matches` | `competition=Copa do Brasil, stage=final` |
| When did Flamengo last play Corinthians? | `head_to_head` | `team_a=Flamengo, team_b=Corinthians, limit=1` |
| Every match played at the Maracanã | `search_matches` | `venue=Maracanã` |
| What is Corinthians' home record in 2022? | `team_stats` | `team=Corinthians, competition=Serie A, season=2022, venue=home` |
| Which team scored the most goals in Série A 2023? | `team_rankings` | `metric=most_goals_scored, competition=Serie A, season=2023` |
| Compare Palmeiras and Santos head-to-head | `head_to_head` | `team_a=Palmeiras, team_b=Santos` |
| What competitions has Palmeiras played in? | `team_profile` | `team=Palmeiras` |
| Which team has the best away record? | `team_rankings` | `metric=best_win_rate, venue=away, min_matches=100` |
| Find all Brazilian players in the dataset | `search_players` | `nationality=Brazil, group_by_club=true` |
| Who are the highest-rated players at Fluminense? | `search_players` | `club=Fluminense` |
| Show me all forwards from Santos | `search_players` | `club=Santos, position=forward` |
| Who is Neymar? | `player_profile` | `name=Neymar` |
| Which players play for Grêmio? | `team_profile` | `team=Grêmio` |
| Who won the 2019 Brasileirão? | `standings` | `competition=Serie A, season=2019` |
| Which teams were relegated in 2020? | `standings` | `competition=Serie A, season=2020` |
| Show the 2018 Copa Libertadores bracket | `competition_bracket` | `competition=Libertadores, season=2018` |
| List every Copa do Brasil winner | `champions` | `competition=Copa do Brasil` |
| Summarise the 2021 Série B season | `competition_summary` | `competition=Serie B, seasons=[2021]` |
| What's the average goals per match in the Brasileirão? | `aggregate_stats` | `competition=Serie A` |
| Show me the biggest wins in the dataset | `aggregate_stats` | `top=10` |
| Compare the 2018 and 2019 seasons | `competition_summary` | `competition=Serie A, seasons=[2018,2019]` |
| Show me all derbies in 2023 | `list_derbies` | `season=2023` |
| How big is the home advantage? | `aggregate_stats` | — |
| Where does this data come from? | `dataset_info` | — |
| Which clubs are called Atlético? | `list_teams` | `query=atletico` |

All 27 run as an acceptance test (`TestSampleQuestions`), against the specification's
"at least 20 sample questions" criterion. `go run . -demo` prints worked answers to a
dozen of them.

---

## Testing

The specification asks for BDD, so the acceptance criteria are written as Gherkin in
`features/` and executed against a **live MCP session** — in-memory transports, full
JSON-RPC round trip — so a passing scenario proves the argument schema, handler,
formatter and protocol encoding all work, not just the Go functions underneath.

```gherkin
Scenario: Find matches between two teams
  Given the Brazilian soccer knowledge graph is loaded
  And the MCP server is connected
  When I search for matches between "Flamengo" and "Fluminense"
  Then I should receive at least 30 matches
  And each match should have a date, a score and a competition
  And the answer should include a head-to-head record
```

`bdd/gherkin.go` parses the files and `bdd/steps_test.go` binds each sentence to a tool
call. A sentence with no step definition fails the run, and a step definition no
scenario uses is reported, so the English and the Go cannot drift apart.

```bash
go test ./...                      # everything
go test ./bdd/ -v                  # the 34 BDD scenarios, named in the output
go test ./internal/soccer/ -run TestStandings2019MatchesHistory -v
go test -race ./...
```

| Suite | Covers |
|---|---|
| `internal/soccer/names_test.go` | accent folding, suffix peeling, aliases, argument parsers |
| `internal/soccer/graph_test.go` | file coverage, name unification, distinct clubs, de-duplication, cross-source enrichment, FIFA linkage |
| `internal/soccer/queries_test.go` | standings, champions and brackets against real history; filters; player search; performance budgets |
| `internal/mcpserver/server_test.go` | initialize, tools/list, every tool over the protocol, error messages, resources, prompts, concurrency, the 27 sample questions |
| `bdd/steps_test.go` | the Gherkin acceptance criteria |
| `main_test.go` | the CLI entry points |

Performance is asserted rather than assumed: simple lookups must answer within 2 seconds
and aggregates within 5 (they take microseconds and low milliseconds respectively).

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

### What ends up in the graph

| | |
|---|---|
| Clubs | 415 |
| Unique fixtures | 16,821 (from 23,852 source rows) |
| Players | 18,207, of whom 827 are Brazilian |
| Série A | 2003–2023 |
| Série B and C | 2014–2023 |
| Copa do Brasil | 2012–2023 |
| Copa Libertadores | 2013–2022 |
| Clubs with FIFA squads | 36 (15 Brazilian, the rest South American) |
| Load time | ~120 ms |

Run `dataset_info` for the live version of this table, including per-file row counts and
the reason for every skipped row.

---

## Specification

The requirements this implements are in `brazilian-soccer-mcp-guide.md` (also copied to
`TASK.md`). Against its success criteria:

- ✅ All 6 CSV files load and are queryable
- ✅ Match, team, player, competition and statistical queries
- ✅ Statistics: wins, losses, goals, head-to-head, home/away, standings, aggregates
- ✅ Team name variations handled, verified by test in both directions
- ✅ Formatted responses matching the specification's example layouts
- ✅ Cross-file queries (player + match data, and clubs joined across five match files)
- ✅ 27 sample questions answered, all as an automated test
- ✅ Simple lookups well under 2 s, aggregates well under 5 s, no timeouts
- ✅ BDD scenarios in Gherkin

Dependencies: the official
[`github.com/modelcontextprotocol/go-sdk`](https://github.com/modelcontextprotocol/go-sdk)
only, vendored so the build needs no network. Everything else is the standard library.
