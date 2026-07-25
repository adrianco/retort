# Brazilian Soccer MCP Server (Swift)

An MCP (Model Context Protocol) server that turns the bundled Kaggle datasets into a
queryable knowledge graph of Brazilian soccer: **16,787 matches**, **406 clubs**,
**18,207 players**, five competitions, seasons **2003-2023**.

It is written in Swift with **no external dependencies** — CSV parsing, the knowledge
graph, the query engine and the JSON-RPC 2.0 / MCP layer are all in this repository.
The whole dataset loads in **0.29 s** (release build) and every query answers in
milliseconds.

Specification implemented: [`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md)
(the same document is in `TASK.md`).

---

## Quick start

```bash
swift build -c release                              # build
.build/release/brazilian-soccer-mcp --check         # load the data and print a summary
./run-tests.sh                                      # 73 BDD tests
```

Ask a question straight from the shell (`--ask` runs a single tool call):

```bash
.build/release/brazilian-soccer-mcp --ask competition_table '{"competition":"brasileirao","season":2019}'
.build/release/brazilian-soccer-mcp --ask head_to_head '{"team_a":"Flamengo","team_b":"Fluminense"}'
.build/release/brazilian-soccer-mcp --ask search_players '{"nationality":"Brazil","limit":5}'
```

```
2019 Brasileirão Série A standings (calculated from matches, final):
Pos Team                       Pts  P   W   D   L   GF  GA  GD
  1 Flamengo                    90  38  28   6   4  86  37 +49
  2 Santos                      74  38  22   8   8  60  33 +27
  3 Palmeiras                   74  38  21  11   6  61  32 +29
...
Champion: Flamengo
Relegation zone (bottom four): 17. Cruzeiro, 18. CSA, 19. Chapecoense, 20. Avaí
```

### Connecting an LLM

The server speaks MCP over stdio (newline delimited JSON-RPC 2.0), so it drops into any
MCP client — Claude Desktop, Claude Code, etc.:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/absolute/path/to/.build/release/brazilian-soccer-mcp",
      "args": ["--data", "/absolute/path/to/data/kaggle"]
    }
  }
}
```

`--data` is optional: the server also honours `$BRAZILIAN_SOCCER_DATA` and searches the
working directory and its ancestors for `data/kaggle`.

---

## What the server exposes

### Tools (15)

| Tool | Answers questions like |
|---|---|
| `search_matches` | "What matches did Palmeiras play in 2023?" — filter by team, opponent, competition, season, date range, stage, home/away |
| `head_to_head` | "Show me all Flamengo vs Fluminense matches" — every meeting plus the win/draw/goal record |
| `team_record` | "What is Corinthians' home record in 2022?" |
| `team_profile` | "What competitions has Palmeiras played in?" — record, home/away split, linked players |
| `find_team` | "Which clubs does the data know as *Atletico*?" |
| `team_rankings` | "Which team has the best away record?" — points, wins, win rate, goals for/against, goal difference |
| `competition_table` | "Who won the 2019 Brasileirão?" / "Which teams were relegated in 2020?" — standings calculated from results |
| `list_competitions` | "What competitions and seasons are available?" |
| `competition_stats` | "What's the average goals per match?" — goals, home advantage, biggest and highest scoring matches |
| `biggest_victories` | "Show me the biggest wins in the dataset" |
| `search_players` | "Find all Brazilian players" / "Show me all forwards from Santos" |
| `player_profile` | "Who is Casemiro?" |
| `club_player_summary` | "Brazilian players at Brazilian clubs" — squad size and average rating per club |
| `graph_neighbors` | "What is connected to Grêmio in the graph?" — `COMPETED_IN`, `PLAYED`, `PLAYS_FOR` edges |
| `dataset_overview` | "What data is loaded?" — files, row counts, merge results |

### Resources

`soccer://dataset/overview`, `soccer://competitions`, `soccer://teams`,
`soccer://sample-questions` (a table of example questions and the call that answers each).

### Prompts

`team_report`, `season_review`, `rivalry_analysis` — ready-made instructions that drive
the tools above.

---

## Architecture

```
Sources/BrazilianSoccerKit/
  Support/   CSVParser (byte level, RFC-4180), JSONValue, TextUtils (accent folding)
  Model/     Competition, Team, Match, Player, SimpleDate
  Data/      DataLocator, TeamRegistry (name canonicalisation), DataSetLoader (+ de-duplication)
  Graph/     KnowledgeGraph — nodes, indexes, team lookup
  Query/     match search, head-to-head, records, league tables, aggregates, player search
  Format/    human/LLM readable rendering
  MCP/       MCPServer (JSON-RPC), SoccerMCPServer (tool catalogue), StdioTransport
Sources/brazilian-soccer-mcp/main.swift    CLI + stdio server
Tests/BrazilianSoccerKitTests/             73 Given/When/Then scenarios
Features/                                  the same scenarios in Gherkin, for reading
```

The graph is:

```
(Team)   -[:PLAYED {competition, season, score}]-> (Team)
(Team)   -[:COMPETED_IN]->                         (Competition)
(Player) -[:PLAYS_FOR]->                           (Team)
```

Everything is loaded once into immutable, `Sendable` value types with pre-built indexes
(by team, by pair, by competition, by club, by nationality), so no query has to scan the
full match list.

---

## Data handling

The five match files describe overlapping fixtures using five different naming
conventions, so most of the work is reconciliation.

**Team name normalisation** (`TeamRegistry`) — a name is resolved in three steps: peel off
a region tag (`-SP`, ` - MG`, ` SP`, `(URU)`), fold the rest into an accent/punctuation
free key with club-type words removed (`Sport Club do Recife` → `sport recife`), then look
that key up in a curated catalogue of ~290 clubs. The region matters: `Atletico-MG`,
`Atletico-PR` and `Atletico-GO` share one key but are three different clubs, while
`Flamengo`, `Flamengo-RJ` and `CR Flamengo` are one. A bare `Atletico` is reported as
ambiguous with candidates rather than guessed.

**De-duplication** — Série A 2012-2019 appears in three files. Records are merged on
(competition, season, home, away) with a 45 day date tolerance; fields missing from the
winning record are filled from the duplicates, so a Brasileirão fixture picks up its
stadium from `novo_campeonato_brasileiro.csv`, its corner and shot counts from
`BR-Football-Dataset.csv`, and — for rows the primary file records as `NA` — its score.
Every season from 2013 to 2019 comes out as exactly one 20 team, 380 match double round
robin (verified in the tests).

**Season attribution** — `BR-Football-Dataset.csv` has no season column. League matches
played in January-March are attributed to the previous season, which keeps the
COVID-delayed 2020 Brasileirão (it finished in February 2021) intact instead of splitting
it across two phantom seasons.

**Missing scores** — `NA` and `-` become `nil`, not `0`. Such fixtures are excluded from
every statistic and only appear when `include_unplayed` is set.

**Dates and encoding** — `2023-09-24`, `2012-05-19 18:30:00` and `29/03/2003` all parse;
all text is handled as UTF-8 and displayed with its accents (`São Paulo`, `Grêmio`, `Avaí`).

### Known data limitations (source, not code)

* `fifa_data.csv` is a FIFA 19 export: it omits unlicensed Brazilian clubs (Flamengo,
  Palmeiras, Corinthians, São Paulo) and pseudonymises players at the Brazilian clubs it
  does include. `search_players` says so instead of returning a silent empty list.
* `BR-Football-Dataset.csv` labels one 2016 Campeonato Brasiliense match (Brasília FC vs
  CA Taguatinga) as "Serie A". The row is kept, but such outliers are listed under
  *"Not ranked — too few matches for this season (source data anomaly)"* rather than
  polluting the table.
* `novo_campeonato_brasileiro.csv` contradicts itself on Vitória's state (BA in 217 rows,
  ES in 179). A region embedded in the name is treated as authoritative while a separate
  UF column is only a hint, so Vitória stays one club.
* One Libertadores row (`datetime = NA`, score `-`) carries no usable data and is skipped;
  the loader reports skipped rows in `dataset_overview`.
* `fifa_data.csv` has no league or country column for clubs, so a handful of foreign
  namesakes link to the Brazilian club of the same name (Portugal's Boavista FC to
  Boavista-RJ, Mexico's Club América to América-MG). Filtering by
  `nationality: "Brazil"` — the case the specification asks for — is unaffected.

---

## Testing

73 scenarios written Given/When/Then (`Tests/BrazilianSoccerKitTests`, mirrored in
readable Gherkin under `Features/`):

| Feature | Covers |
|---|---|
| `DataLoadingFeatureTests` | all six files load, row counts, de-duplication, season attribution, encoding, date formats |
| `TeamNameNormalizationFeatureTests` | suffixes, accents, long forms, namesakes, CONMEBOL tags, ambiguity |
| `CSVParsingFeatureTests` | quoted commas, doubled quotes, BOM, CRLF, embedded newlines, `NA` |
| `MatchQueryFeatureTests` | team/opponent/competition/season/date/stage/venue filters, last meeting |
| `TeamQueryFeatureTests` | records, home-away splits, head-to-head symmetry, rankings, profiles, graph traversal |
| `CompetitionQueryFeatureTests` | 2019 standings, 2020 relegation, internal consistency, competition name resolution |
| `PlayerQueryFeatureTests` | nationality/name/club/position/rating filters, cross-file club links |
| `StatisticalAnalysisFeatureTests` | goals per match, home advantage, biggest wins, season comparison |
| `MCPProtocolFeatureTests` | initialize, notifications, tools/list, tools/call, resources, prompts, error codes |
| `SampleQuestionsFeatureTests` | 27 natural language questions answered end to end through the MCP layer |
| `PerformanceFeatureTests` | simple lookups < 2 s, aggregates < 5 s, 50 repeated queries < 5 s |

```bash
./run-tests.sh                 # or: swift test
```

> `swift test` needs XCTest, which ships with Xcode and **not** with the Command Line
> Tools. If `xcode-select -p` points at `/Library/Developer/CommandLineTools`, plain
> `swift test` fails with *"no such module 'XCTest'"*. `run-tests.sh` detects that and
> points `DEVELOPER_DIR` at an installed Xcode.

Measured here: data load 0.29 s (release), 73 tests in 2.5 s, every tool call in single
digit milliseconds.

---

## Specification checklist

| Requirement | Status |
|---|---|
| Search and return match data from all provided CSV files | ✅ all five match files, merged |
| Search and return player data | ✅ `search_players`, `player_profile` |
| Calculate basic statistics (wins, losses, goals) | ✅ `team_record`, `competition_table` |
| Compare teams head-to-head | ✅ `head_to_head` |
| Handle team name variations correctly | ✅ `TeamRegistry` + dedicated tests |
| Return properly formatted responses | ✅ output follows the examples in the spec |
| Simple lookups < 2 s, aggregates < 5 s, no timeouts | ✅ `PerformanceFeatureTests` |
| All 6 CSV files loadable and queryable | ✅ `dataset_overview` |
| At least 20 sample questions answerable | ✅ 27 in `SampleQuestionsFeatureTests` |
| Cross-file queries (player + match data) | ✅ `club_player_summary`, `team_profile` |
| BDD test scenarios | ✅ 73 Given/When/Then scenarios + `Features/*.feature` |

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

Demo / non-commercial use.
