# Brazilian Soccer MCP Server (Clojure)

An [MCP](https://modelcontextprotocol.io) server that turns the six Kaggle datasets in
`data/kaggle` into a queryable knowledge graph of Brazilian football: **16,762 matches**
(Brasileirão Série A/B/C 2003–2023, Copa do Brasil 2012–2023, Copa Libertadores 2013–2022),
**378 clubs** and the **18,207 player** FIFA 19 snapshot.

The specification implemented here is [TASK.md](TASK.md) (same content as
`brazilian-soccer-mcp-guide.md`).

```
$ clojure -M:cli call standings competition=brasileirao season=2019

Brasileirão Série A 2019 - table calculated from 380 matches in the dataset
#    Team                         P   W   D   L   GF   GA   GD   Pts
1    Flamengo                    38  28   6   4   86   37  +49    90  <- champion (by points)
2    Santos                      38  22   8   8   60   33  +27    74
3    Palmeiras                   38  21  11   6   61   32  +29    74
...
17   Cruzeiro                    38   7  15  16   27   46  -19    36  <- relegation zone
```

## Quick start

Requires Java 11+ and the [Clojure CLI](https://clojure.org/guides/install_clojure).

```bash
clojure -M:test                 # full test suite (42 tests, 527 assertions)
clojure -M:cli demo             # answer all 32 sample questions from the spec
clojure -M:cli tools            # list the MCP tools and their arguments
clojure -M:cli call search_matches team=Flamengo opponent=Fluminense limit=5
clojure -M:mcp                  # run the MCP server on stdio
```

`clojure -X:test` and `make test` run the same suite.

> **macOS note.** `/usr/bin/java` is a stub that only finds JDKs registered under
> `/Library/Java/JavaVirtualMachines` or `~/Library/Java/JavaVirtualMachines`. A JDK
> installed by Homebrew is keg-only and lands in neither, so `clojure` reports *"Unable to
> locate a Java Runtime"* despite Java being installed. Register it once with
>
> ```bash
> mkdir -p ~/Library/Java/JavaVirtualMachines
> ln -sfn /opt/homebrew/opt/openjdk/libexec/openjdk.jdk ~/Library/Java/JavaVirtualMachines/openjdk.jdk
> ```
>
> or set `JAVA_HOME=/opt/homebrew/opt/openjdk`. `make test` applies this fallback itself.

### Connecting an MCP client

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "clojure",
      "args": ["-M:mcp"],
      "cwd": "/absolute/path/to/this/repo"
    }
  }
}
```

The data directory defaults to `data/kaggle`; override it with the `SOCCER_DATA_DIR`
environment variable or by passing a path: `clojure -M:mcp /some/other/dir`.

## Tools

| Tool | Answers |
|------|---------|
| `search_matches` | "Show me all Flamengo vs Fluminense matches", "What matches did Palmeiras play in 2023?", "When did Flamengo last play Corinthians?" |
| `head_to_head` | "Compare Palmeiras and Santos head-to-head" |
| `team_stats` | "What is Corinthians' home record in 2022?" |
| `team_profile` | "What competitions has Palmeiras played in?" |
| `team_rankings` | "Which team has the best home record?", "Which team scored the most goals in Série A 2023?" |
| `standings` | "Who won the 2019 Brasileirão?", "Which teams were relegated in 2020?" |
| `competition_stats` | "What's the average goals per match in the Brasileirão?", "Compare the 2018 and 2019 seasons" |
| `biggest_wins` | "Show me the biggest wins in the dataset" |
| `list_finals` | "Find all Copa do Brasil finals", "Show the 2018 Libertadores final" |
| `find_derbies` | "Show me all derbies in 2023" |
| `search_players` | "Find all Brazilian players", "Show me all forwards at Fluminense" |
| `player_profile` | "Who is Neymar?" |
| `club_squad` | "Which players play for Grêmio?", "Which Brazilian clubs have squads?" |
| `list_teams` | "Which clubs in the data are called Atlético?" |
| `dataset_info` | "What data is loaded and where does it come from?" |

Tool failures come back as MCP tool errors (not protocol errors) carrying a readable
message, so the model can recover: asking for `"Atletico"` answers *"matches several clubs:
Atlético Mineiro, Athletico Paranaense, Atlético Goianiense … please be more specific"*.

## How it works

```
src/brazilian_soccer/
  names.clj    normalisation of club names -> canonical ids ("atletico|mg")
  data.clj     CSV loading, de-duplication/merging, indexing, player linking
  query.clj    pure queries: matches, records, head-to-head, tables, rankings, players
  format.clj   rendering of results as the text an LLM reads
  tools.clj    MCP tool catalogue: JSON schema + handler per capability
  mcp.clj      JSON-RPC 2.0 over newline-delimited stdio
  server.clj   `clojure -M:mcp` entry point
  cli.clj      `clojure -M:cli` entry point for humans
```

Everything is parsed once at start-up (~0.7 s) into immutable indexed maps, so no query
touches the disk. Each file opens with a context comment explaining its role.

### Three problems the data poses, and what the code does about them

**1. The same club is written a dozen ways.** `Atletico-MG`, `Atlético - MG`,
`Atlético Mineiro - MG` and `Atletico Mineiro` are one club; `Atlético-MG`, `Athletico-PR`
and `Atlético-GO` are three. Names are folded (accents, case, punctuation), the state or
country suffix is split off, club decorations (`EC`, `FC`, `Esporte Clube`, …) are dropped,
curated aliases handle what rules cannot, and a missing region is filled from a curated
default or inferred from the corpus. The result is a canonical id such as `atletico|mg` or
`nacional|uru`. `list_teams` shows every spelling behind each club.

**2. The files overlap.** Série A 2014–2019 appears in *three* of them. Counting a season
twice would multiply every league table, so records of the same fixture are merged into one:
a league fixture is identified by competition + season + home + away (the files disagree
about kick-off dates and occasionally about scores), cup fixtures additionally need a
matching score or a date within two days, and duplicates *within* one file need both. The
merge is additive — the round comes from `Brasileirao_Matches.csv`, the stadium from
`novo_campeonato_brasileiro.csv`, shots and corners from `BR-Football-Dataset.csv`, and the
82 fixtures that were scraped before they were played get their score from another file.

**3. Some rows are simply wrong.** `BR-Football-Dataset.csv` has no season column (it is
derived from the date, allowing for the COVID-shifted 2020 and 2021 seasons that ran into
the following February) and files a handful of state-championship games under
"Serie A"/"Serie B"; in a complete national season every club plays 38 matches, so clubs
with fewer than five are dropped from that season. One Libertadores row has neither season
nor score and is discarded. Fixtures with no score anywhere are kept, flagged, and excluded
from every statistic.

The check that all of this works: **de-duplicated seasons are exact double round-robins**
(380 matches for every 20-club season, 552 for 2003–2004, 462 for 2005) and the calculated
tables reproduce the published ones — Flamengo 90 points in 2019, Palmeiras 80 in 2018 and
81 in 2022, Corinthians 72 in 2017, Cruzeiro 100 in 2003, and exactly Vasco, Goiás, Coritiba
and Botafogo relegated in 2020.

### Honest limits

* **No goalscorer data exists in any of the six files**, so individual top scorers cannot be
  derived. `competition_stats` says so and reports team totals instead.
* **FIFA 19 does not license the Brazilian league.** Only 15 Brazilian clubs appear (Grêmio,
  Cruzeiro, Internacional, Fluminense, Santos, Botafogo, Bahia, Vitória, Paraná,
  Chapecoense, Ceará, Sport, Atlético Mineiro, Athletico Paranaense, América-MG) and their
  players carry EA's generated placeholder names — the ratings describe the squad, the names
  are not real players. Brazilian internationals appear under their real names at their
  European clubs (Neymar 92, Casemiro 88, Coutinho 88, Marcelo 88…). Asking for Flamengo's
  players returns an empty result *with an explanation*, not a wrong answer.
* **Standings are calculated from match results**, 3 points per win, ranked on points, wins,
  goal difference then goals for. Points deductions and court rulings (2003 Fluminense, for
  example) are not in the data, so a computed table can differ from the official one.
* Copa do Brasil rounds are numbered, not named; the final is taken as the last round of a
  season and only when that round holds one or two matches. Seasons whose data stops earlier
  are reported as such rather than guessed at.

## Tests

```
clojure -M:test        # or: clojure -X:test, make test
```

| Namespace | Covers |
|-----------|--------|
| `names_test` | accents, state/country suffixes, club decorations, ambiguous bases |
| `data_test` | date formats, all six files, round-robin completeness, merge behaviour, published tables |
| `features_test` | Given/When/Then scenarios for the five capability groups in the spec |
| `tools_test` | tool schemas, argument coercion, error messages, answer formats |
| `mcp_test` | initialize / notifications / tools list / tools call / JSON-RPC errors / full stdio session |
| `samples_test` | every sample question in `resources/sample_questions.edn` answers with the expected content |
| `performance_test` | simple lookups < 2 s, aggregates < 5 s, no degradation over repeated calls |

BDD scenarios use a small Gherkin-flavoured DSL (`test/brazilian_soccer/bdd.clj`) that
expands to `clojure.test`, so a failure reads like the specification it came from:

```clojure
(scenario "Find matches between two teams"
  (given "the match data is loaded" [db (test-db)]
    (when* "I search for matches between Flamengo and Fluminense"
      [result (q/find-matches db {...})]
      (then "I should receive a list of matches" (seq result))
      (and* "each match should have date, scores and a competition"
        (every? #(and (:date %) (:home-goals %) (:competition-name %)) result)))))
```

`resources/sample_questions.edn` is the single source for both `clojure -M:cli demo` and the
acceptance test, so the demo cannot drift from what is verified.

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
