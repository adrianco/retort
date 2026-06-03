# Brazilian Soccer MCP Server (Java)

An [MCP](https://modelcontextprotocol.io) server that answers natural-language-style
questions about Brazilian soccer — players, teams, matches, competitions and
statistics — over the Kaggle datasets shipped in `data/kaggle/`.

It implements the specification in
[`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md): match search,
team statistics, head-to-head records, computed league standings, player search
and aggregate statistics, all exposed as MCP tools over a JSON-RPC / stdio
transport so any MCP-capable LLM client can call them.

## What was built

- **Language / build:** Java 17, Maven. Produces a single runnable uber-jar.
- **Zero runtime services:** all data is loaded into memory from the CSV files at
  startup; no database is required. (Jackson is the only runtime dependency, used
  for JSON-RPC.)
- **MCP protocol layer** (`server/McpServer.java`): handles `initialize`,
  `notifications/initialized`, `ping`, `tools/list` and `tools/call` as
  newline-delimited JSON-RPC 2.0 over stdio.
- **Query engine** (`query/SoccerQueries.java`): all the analytical logic over a
  unified in-memory model.
- **Data layer** (`data/`): a dependency-free CSV reader, multi-format date/number
  parsing, team-name normalization and cross-source de-duplication.
- **Tests** (`src/test/java`): 31 BDD (Given/When/Then) tests with JUnit 5,
  exercising the real shipped datasets.

### Architecture

```
data/kaggle/*.csv
      │  CsvReader (UTF-8, BOM, quoted commas)
      ▼
SoccerData ──► List<Match>, List<Player>      (loading, labelling, de-dup)
      │
      ▼
SoccerQueries  (search / stats / standings / players)
      │
      ▼
SoccerTools  ──►  McpServer  ──►  stdio (JSON-RPC / MCP)
```

Every source file begins with a context block comment describing its role.

## Build & test

```bash
mvn clean test       # run the 31 BDD tests
mvn -DskipTests package   # build target/brazilian-soccer-mcp.jar
```

## Run

```bash
java -jar target/brazilian-soccer-mcp.jar [dataDir]
```

`dataDir` defaults to `./data` (the folder containing `kaggle/`); it can also be
set with the `BRAZIL_SOCCER_DATA` environment variable. Diagnostic logs go to
**stderr** so they never corrupt the JSON-RPC stream on stdout.

### Using it from an MCP client

Example client configuration (e.g. Claude Desktop `mcpServers` entry):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "java",
      "args": [
        "-jar", "/absolute/path/to/target/brazilian-soccer-mcp.jar",
        "/absolute/path/to/data"
      ]
    }
  }
}
```

### Quick manual smoke test

```bash
printf '%s\n' \
 '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05"}}' \
 '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
 '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"standings","arguments":{"season":2019}}}' \
 | java -jar target/brazilian-soccer-mcp.jar
```

## Tools

| Tool | Purpose |
|------|---------|
| `search_matches` | Matches by team, competition, season and/or date range |
| `matches_between` | All matches between two teams + head-to-head summary |
| `head_to_head` | Head-to-head record between two teams |
| `team_stats` | Wins/draws/losses, goals, win rate (by season/competition/venue) |
| `standings` | Computed final league table for a season (incl. relegation zone) |
| `search_players` | FIFA player search by (partial) name |
| `find_players` | Players by nationality / club / position, ranked by rating |
| `average_goals` | Average goals per match (optionally filtered) |
| `biggest_wins` | Largest-margin victories |
| `list_competitions` | Competitions and season ranges available |

### Example questions answered

- "Show me all Flamengo vs Fluminense matches" → `matches_between`
- "What is Corinthians' home record in 2019?" → `team_stats` (`venue: home`)
- "Who won the 2019 Brasileirão?" → `standings` (Flamengo, 90 pts — historically correct)
- "Who are the top Brazilian players?" → `find_players` (`nationality: Brazil`)
- "Compare Palmeiras and Santos head-to-head" → `head_to_head`
- "What's the average goals per match in the Brasileirão?" → `average_goals`

## Data quality handling

The datasets overlap heavily and spell clubs inconsistently. The implementation
addresses the issues the spec calls out:

- **Team-name variations** (`Palmeiras-SP` / `Palmeiras`, `Nacional (URU)`,
  `Atlético Mineiro` / `Atletico-MG`, full club names): normalized to a stable
  key that *retains* the state/country code (so `Atlético-MG` is never conflated
  with `Atlético-GO`) while tolerant word-containment matching still lets a bare
  "Palmeiras" or "Corinthians" find the coded / full-name forms.
- **Multiple date formats** (`2012-05-19 18:30:00`, `2023-09-24`, `29/03/2003`)
  and **float-encoded scores** (`1.0`) are parsed uniformly.
- **UTF-8 / accents / BOM** are handled by the CSV reader.
- **Overlapping sources**: Série A appears in three files. Matches are
  de-duplicated with a naming-tolerant key (date + team first-token + score) so
  head-to-head and statistics are not double-counted. League **standings** are
  computed from the single most complete, consistently-named source for that
  season to avoid phantom teams.

### Known limitations

- The FIFA player dataset (≈2019) only includes the licensed subset of Brazilian
  clubs (e.g. Santos, Grêmio, Internacional are present; Flamengo, Palmeiras and
  Corinthians appear as their players' national entries but not as club squads).
- Full-name spellings that share no first token with the coded form of the same
  club (rare) are not unified.
- No top-scorer data: the datasets contain no goal-scorer information, so that
  optional capability is not provided.

## Datasets

Kaggle data (downloaded with attribution; see licenses below) lives in `data/kaggle/`:

- https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro — CC BY 4.0
  - `Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`, `Libertadores_Matches.csv`
- https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches — CC0 Public Domain
  - `BR-Football-Dataset.csv`
- https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019 — CC BY 4.0
  - `novo_campeonato_brasileiro.csv`
- https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data — Apache 2.0
  - `fifa_data.csv`
