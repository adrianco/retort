# Brazilian Soccer MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io) server (Java 21, MCP Java SDK 2.0)
that turns six Kaggle datasets about Brazilian soccer into an in-memory knowledge graph and
exposes it to an LLM as 15 tools: matches, clubs, players, competitions and statistics.

Specification: [TASK.md](TASK.md) / [brazilian-soccer-mcp-guide.md](brazilian-soccer-mcp-guide.md).

```
$ mvn package
$ java -jar target/brazilian-soccer-mcp.jar --call competition_summary competition=serie_a season=2019
2019 Brasileirão Série A summary:
- Matches in dataset: 380 (380 with a known score)
- Clubs: 20
- Goals per match: 2.31
- Home wins: 48.4%, draws: 25.8%, away wins: 25.8%
- Champion: Flamengo (runner-up: Santos)
  league table computed from 380 of the 380 matches of a full double round robin
...
```

## Quick start

```bash
mvn package                                   # build + run all tests (154 of them)
java -jar target/brazilian-soccer-mcp.jar     # speak MCP over stdio
java -jar target/brazilian-soccer-mcp.jar --list-tools
java -jar target/brazilian-soccer-mcp.jar --call head_to_head team_a=Flamengo team_b=Fluminense
java -jar target/brazilian-soccer-mcp.jar --data /path/to/csvs   # or $BRAZIL_SOCCER_DATA_DIR
```

Register it with an MCP client (Claude Desktop / Claude Code `mcp.json`):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "java",
      "args": ["-jar", "/absolute/path/to/target/brazilian-soccer-mcp.jar"],
      "env": { "BRAZIL_SOCCER_DATA_DIR": "/absolute/path/to/data/kaggle" }
    }
  }
}
```

`stdout` carries the JSON-RPC stream only; all logging goes to `stderr`.

## Tools

| Tool | Answers questions like |
|------|------------------------|
| `dataset_info` | "What data can I query?" - files, licences, competitions, seasons, graph size |
| `search_matches` | "Show me all Flamengo vs Fluminense matches", "What did Palmeiras play in 2023?" |
| `head_to_head` | "Compare Palmeiras and Santos head-to-head" |
| `find_derbies` | "Show me all derbies in 2019" |
| `team_stats` | "What is Corinthians' home record in 2022?" |
| `team_competitions` | "What competitions has Palmeiras played in?" |
| `list_teams` | "Which clubs are called Atlético?" - name disambiguation |
| `standings` | "Who won the 2019 Brasileirão?", "Which teams were relegated in 2020?" |
| `competition_summary` | "Who won the 2019 Copa do Brasil?" (final decided on aggregate) |
| `compare_seasons` | "Compare the 2018 and 2019 seasons" |
| `search_players` | "Find all Brazilian players", "Show me all forwards from Santos" |
| `player_profile` | "Who is Neymar?" |
| `player_club_summary` | "Brazilian players at Brazilian clubs" |
| `player_club_report` | cross-file: player → his club → that club's match record |
| `statistics` | "Average goals per match?", "Best home record?", "Biggest wins?" |

Answers are plain text formatted for an LLM to read, following the examples in the specification.

## How it works

```
data/kaggle/*.csv ──► DataLoader ──► KnowledgeGraph ──► query services ──► ToolRegistry ──► MCP (stdio)
                        │                 │
                    TeamRegistry      adjacency indexes
                (name normalisation)  (club, competition+season, club→players)
```

* **Nodes**: `Team` (1,010 clubs), `Match` (16,733), `Player` (18,207), `Competition` (5).
* **Edges**: `HOME_TEAM` / `AWAY_TEAM` (match ↔ club), `PART_OF` (match → competition),
  `PLAYS_FOR` (player → club) - ~68,000 relationships, materialised as adjacency indexes so a
  club lookup is a hash lookup and a full season table touches only 380 matches.
* **Load time**: ~0.6 s for all six files; the graph is immutable afterwards.

### Team name normalisation

The files spell the same club in up to eleven ways. `TeamNameNormalizer` strips accents,
punctuation, parenthetical remarks and legal-form noise (`EC`, `FC`, `Esporte Clube`, `do/da/de`),
peels off the trailing state (UF) or country code and applies a curated alias table
(`Athletico Paranaense` → `atletico`/PR). `TeamRegistry` then decides **from the data** whether a
base name needs its state to be unique:

* `atletico` occurs with MG, PR and GO → three nodes (`atletico-mg`, `atletico-pr`, `atletico-go`);
* `palmeiras` only ever occurs with SP → one node (`palmeiras`);
* spellings without a state attach to the most frequent state of that base name.

So `Flamengo`, `Flamengo-RJ` and `Flamengo - RJ` are one club, while Botafogo-RJ, Botafogo-SP and
Botafogo-PB stay apart, and `Flamengo do Piauí` never merges with Flamengo.

### Merging overlapping datasets

Série A 2014-2019 appears in three of the files, so ~7,200 of the 23,953 raw rows describe a
fixture that is already known. The loader merges them on
`(competition, season, home club, away club)` (plus a date window for knockout ties) and enriches
the surviving record with whatever each source adds - round number, stadium, shots, corners,
half-time result. Without this, every aggregate (season tables, goals per match, head-to-head
records) would be inflated. Score disagreements between sources are counted and reported by
`dataset_info` (70 fixtures; the first source wins).

Other data quirks handled: three date formats (`2023-09-24`, `2012-05-19 18:30:00`, `29/03/2003`),
`NA` / `-` placeholders, a UTF-8 BOM in `fifa_data.csv`, quoted fields containing commas, and the
2020 season that ran into February 2021 (league matches played in January-March belong to the
previous season).

### Coverage

| Competition | Seasons | Matches |
|-------------|---------|---------|
| Brasileirão Série A | 2003-2023 | 8,403 |
| Brasileirão Série B | 2014-2023 | 3,677 |
| Brasileirão Série C | 2014-2023 | 1,746 |
| Copa do Brasil | 2012-2023 | 1,653 |
| Copa Libertadores | 2013-2022 | 1,254 |

Champions and relegation zones are **computed from the results**, not hard coded: the 2019 Série A
table comes out as Flamengo 90, Santos 74, Palmeiras 74 with Cruzeiro, CSA, Chapecoense and Avaí
in the bottom four, and the 2019 Copa do Brasil final is resolved on aggregate to Athletico
Paranaense.

Known limits, reported by the server itself rather than guessed at: the datasets contain no goal
scorer data (no individual top-scorer answers), and the FIFA player file only licenses 15 Brazilian
clubs - asking for Flamengo players returns the list of clubs that *are* covered.

## Tests

`mvn test` runs 154 tests in about 4 seconds:

* **BDD (Cucumber / Gherkin)** - `src/test/resources/features`, 88 scenarios in Given/When/Then
  form over the real datasets:
  `match_queries`, `team_queries`, `player_queries`, `competition_queries`,
  `statistical_analysis`, `data_quality` and `sample_questions` (29 natural-language questions with
  the tool an LLM would pick and the fact its answer must contain).
* **Protocol** - `McpProtocolTest` starts the server on in-memory pipes and drives it with hand
  written JSON-RPC: `initialize`, `tools/list`, `tools/call`, error results, UTF-8 round trip.
* **Unit** - CSV parsing quirks, date parsing, name normalisation (33 cases), graph construction,
  de-duplication, known season tables, tool schemas and argument validation.
* **Performance** - the budget from the specification: simple lookups < 2 s, aggregations < 5 s
  (actual: single-digit milliseconds after the one-off load).

## Layout

```
src/main/java/com/brazilsoccer/mcp/
  BrazilianSoccerMcpServer.java   entry point (stdio server + CLI)
  McpServerFactory.java           adapts the tool catalogue to the MCP Java SDK
  data/DataLoader.java            reads and merges the six CSV files
  graph/                          TeamNameNormalizer, TeamRegistry, KnowledgeGraph
  model/                          Team, Match, Player, Competition, MatchStats
  query/                          match, team, player, competition and statistics services
  tools/                          the 15 tools, their JSON schemas and argument handling
  format/Formatters.java          text rendering of matches, records and tables
  util/                           CSV reader, date parsing, text helpers
```

## Data sources

Kaggle data can't be downloaded without an account, so these (freely available with attribution)
data sets have been downloaded into `data/kaggle/`:

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
