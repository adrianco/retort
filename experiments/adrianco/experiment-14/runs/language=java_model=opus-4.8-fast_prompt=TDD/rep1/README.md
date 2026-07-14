# Brazilian Soccer MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io) server, written in Java, that
exposes a knowledge graph over Brazilian soccer datasets (matches, teams, competitions and
FIFA players) as a set of LLM-callable tools. Connect it to any MCP-capable client (e.g.
Claude Desktop) to answer natural-language questions about Brazilian football.

It implements the specification in [`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md)
(mirror: [`TASK.md`](TASK.md)).

## What was built

The server loads the six provided Kaggle CSV files into an in-memory knowledge base and
serves JSON-RPC 2.0 over stdio. It was developed **test-first (TDD)**; every behaviour is
covered by a unit test (90 tests), plus integration tests that run against the real data.

### MCP tools

| Tool | Answers questions like |
|------|------------------------|
| `find_matches` | "Show me all Flamengo vs Fluminense matches", "What matches did Palmeiras play in 2023?" (filter by team, opponent, competition, season, date range, home/away) |
| `head_to_head` | "Compare Palmeiras and Santos head-to-head" (wins/draws + recent meetings) |
| `team_record` | "What is Corinthians' home record in 2022?" (W/D/L, goals, points, win rate) |
| `competition_standings` | "Who won the 2019 Brasileirão?", "Which teams were relegated?" (table computed from results) |
| `search_players` | "Find all Brazilian players", "Highest-rated players at Grêmio", "Forwards with rating ≥ 80" |
| `match_statistics` | "Average goals per match", "Home win rate", "Biggest wins" |
| `list_competitions` | What data is loaded |

### Data handling

The datasets are messy, so the loader normalizes them (each concern is its own tested unit):

- **Team-name variations** — `Palmeiras-SP`, `Palmeiras`, `Nacional (URU)` and `América - MG`
  all normalize to a canonical key. Distinct clubs that share a base name are kept apart
  (Atlético-MG ≠ Atlético-PR ≠ Atlético-GO), while hyphen and full-name spellings of the
  *same* club unify (`Atletico-MG` = `Atlético Mineiro`, `Athletico-PR` = `Atletico Paranaense`).
- **Multiple date formats** — ISO (`2023-09-24`), ISO date-time (`2012-05-19 18:30:00`) and
  Brazilian (`29/03/2003`).
- **UTF-8 / accents / BOM** — handled throughout (`São Paulo`, `Grêmio`); a query for
  `Gremio` matches the club `Grêmio`.
- **Cross-file de-duplication** — the same fixture appears in several files under different
  competition labels (e.g. `Brasileirão` vs `Serie A`) and sometimes with a timezone-induced
  off-by-one date. These are merged (same teams + score within ±1 day), preventing
  double-counted standings and statistics. ~24,000 raw rows collapse to ~18,700 unique fixtures.
- **`Série A` ≡ `Brasileirão`** — the top-flight league is treated as one competition across
  the differently-labelled files (without pulling in Série B / Série C).

## Architecture

```
csv/      CsvParser, Dates              — raw text → fields, tolerant date parsing
model/    Match, Player, TeamNames      — domain entities + name normalization
data/     DataLoader, DataStore, Matches— CSV layouts → entities, dedup, directory load
query/    SoccerDatabase + queries      — the in-memory query engine and result types
mcp/      McpServer, StdioTransport,    — JSON-RPC/MCP protocol, tool catalogue,
          SoccerTools, Main               argument parsing and response formatting
```

Every source file carries a header comment block describing its purpose and place in the
system.

## Build & test

Requires JDK 21+ and Maven.

```bash
mvn test          # run the full test suite (unit + real-data integration)
mvn package       # build target/brazilian-soccer-mcp.jar (self-contained, runnable)
```

## Run

The server speaks newline-delimited JSON-RPC over stdin/stdout. Diagnostics go to stderr.

```bash
java -jar target/brazilian-soccer-mcp.jar [data-dir]
# data-dir defaults to ./data/kaggle, or set BRSOCCER_DATA_DIR
```

Quick manual check:

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"competition_standings","arguments":{"competition":"Brasileirão","season":2019,"limit":5}}}' \
  | java -jar target/brazilian-soccer-mcp.jar
```

### Use from an MCP client (e.g. Claude Desktop)

Add to your MCP client configuration:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "java",
      "args": ["-jar", "/absolute/path/to/target/brazilian-soccer-mcp.jar"],
      "env": { "BRSOCCER_DATA_DIR": "/absolute/path/to/data/kaggle" }
    }
  }
}
```

## Data Sources

Kaggle data can't be downloaded without an account, so these (freely available with
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

### Data coverage notes

- The provided `Brasileirao_Matches.csv` covers up to 2022; the 2023 top-flight season is
  present only in the `BR-Football-Dataset.csv` (labelled `Serie A`), which the server treats
  as the Brasileirão. Some seasons in that file are slightly incomplete, so a few computed
  standings (e.g. 2023) may differ marginally from the official table; fully-sourced seasons
  such as 2019 reproduce the official champion (Flamengo).
- The FIFA player snapshot omits some clubs that were unlicensed in that edition (e.g.
  Flamengo, Palmeiras, Corinthians) and individual players such as Gabriel Barbosa, so player
  queries scoped to those clubs return no results. Many Brazilian clubs (Grêmio, Santos,
  Fluminense, Internacional, Cruzeiro, …) and 800+ Brazilian players are present and queryable.
