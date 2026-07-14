# Brazilian Soccer MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io) server, written in Java,
that exposes a natural-language-friendly query interface over a corpus of Brazilian
soccer data (matches, teams, competitions and FIFA players). It implements the
specification in [`TASK.md`](TASK.md) / [`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md).

The server speaks JSON-RPC 2.0 over **stdio**, so it can be plugged into any MCP
client (Claude Desktop, the MCP Inspector, etc.).

---

## What was built

A self-contained MCP server that, on startup, loads all six bundled CSV datasets
(~42k rows) into memory as a unified model and answers tool calls with formatted
text responses. No external services or network access are required.

### Tools exposed

| Tool | Purpose | Key arguments |
|------|---------|---------------|
| `search_matches` | Find matches by team / opponent / competition / season / date range | `team`, `opponent`, `competition`, `season`, `date_from`, `date_to`, `limit` |
| `team_record` | Win/draw/loss & goal record for a team | `team` (req), `season`, `competition`, `venue` (all/home/away) |
| `head_to_head` | Compare two teams head-to-head | `team1` (req), `team2` (req), `season`, `competition` |
| `search_players` | Search the FIFA player database | `name`, `nationality`, `club`, `position`, `min_overall`, `limit` |
| `competition_standings` | League table calculated from match results | `competition` (req), `season` (req), `limit` |
| `league_stats` | Avg goals/match, home/away/draw rates, biggest wins | `competition`, `season`, `limit` |
| `top_scoring_teams` | Teams ranked by goals scored | `competition`, `season`, `limit` |

These cover all five capability categories in the spec (Match, Team, Player,
Competition and Statistical Analysis queries).

---

## Build & run

Requirements: **JDK 17+** and **Maven 3.9+**.

```bash
# Build, run the test suite, and produce a runnable fat jar
mvn package

# Start the MCP server (reads JSON-RPC requests on stdin, writes responses on stdout;
# diagnostics go to stderr). Auto-detects ./data/kaggle.
java -jar target/brazilian-soccer-mcp.jar
```

The data directory is auto-detected as `./data/kaggle` but can be overridden:

```bash
java -Dsoccer.data.dir=/path/to/kaggle -jar target/brazilian-soccer-mcp.jar
# or
SOCCER_DATA_DIR=/path/to/kaggle java -jar target/brazilian-soccer-mcp.jar
```

### Quick manual check

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"competition_standings","arguments":{"competition":"Brasileirão","season":2019,"limit":5}}}' \
  | java -jar target/brazilian-soccer-mcp.jar
```

produces (abridged):

```
 1. Flamengo-RJ   90 pts (28W  6D  4L) GF:86 GA:37 GD:+49  - Champion
 2. Palmeiras-SP  74 pts (21W 11D  6L) GF:61 GA:32 GD:+29
 3. Santos-SP     74 pts (22W  8D  8L) GF:60 GA:33 GD:+27
 ...
```

### Using it from an MCP client

Add an entry like the following to your client's MCP server configuration
(adjust the absolute paths):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "java",
      "args": ["-jar", "/absolute/path/to/target/brazilian-soccer-mcp.jar"]
    }
  }
}
```

---

## Architecture

```
src/main/java/com/brazilsoccer/mcp/
  model/      Match, Player                     – immutable unified records
  data/       Csv                               – dependency-free CSV reader
              TeamNames                          – name normalization / match keys
              Competitions                       – competition canonicalization
              DataStore                          – loads & de-duplicates all CSVs
  query/      MatchService, TeamService,         – the five query capabilities
              PlayerService, CompetitionService,
              StatsService, TeamRecord
  server/     SoccerTools                        – MCP tool declarations + formatting
              McpServer                          – JSON-RPC 2.0 / stdio transport
              Main                               – entry point
```

Every match, regardless of its source file, is normalized into a single `Match`
shape so the query layer treats all competitions uniformly. The whole corpus fits
in memory, so queries are linear scans and comfortably meet the spec's latency
targets (simple lookups and aggregates both complete in well under a second).

### Notable data-handling decisions

These address the spec's "Data Quality Notes":

- **Team-name variations.** The `-SP`/`-RJ`/`-MG` suffixes are *kept*, not
  stripped, because they disambiguate genuinely different clubs that share a base
  name (Atlético-**MG** vs Atlético-**GO** vs Atlético-**PR**; América-**MG** vs
  América-**RN**). A user query like `"Flamengo"` still matches the stored key
  `flamengorj` via accent-insensitive substring matching (`TeamNames` +
  `MatchService.keyMatches`).
- **Accents / UTF-8.** All files are read as UTF-8 (BOM-aware), display names keep
  their accents, and match keys are accent-folded so `"Sao Paulo"` finds
  `"São Paulo-SP"`.
- **Date formats.** ISO (`2023-09-24`), ISO-with-time (`2012-05-19 18:30:00`) and
  Brazilian (`29/03/2003`) formats are all parsed.
- **Competition naming.** `Competitions` canonicalizes synonyms so `"Brasileirão"`,
  `"Serie A"` and `"Campeonato Brasileiro"` mean the top flight — crucially
  **without** also matching `"Brasileirão Série B"` (which would otherwise leak the
  second-division champion into the Série A table).
- **Cross-file de-duplication.** The Brasileirão appears in three overlapping files
  (`Brasileirao_Matches.csv` 2012–2022, `novo_campeonato_brasileiro.csv` 2003–2019,
  `BR-Football-Dataset.csv` Série A 2014–2023). Pooling them would double- or
  triple-count fixtures. `DataStore.deduplicate` groups matches by
  *(canonical competition, season)* and keeps only the single source file that
  contributed the most rows for that group, giving one authoritative copy of each
  season while preserving full coverage. The raw, non-deduplicated set is still
  available via `DataStore.allMatches()`.

### Known data limitations

- The bundled **FIFA 19** player dataset does not include the (then-unlicensed)
  clubs **Flamengo, Palmeiras, Corinthians and São Paulo**, so club searches for
  those return no players. Other Brazilian clubs (Santos, Grêmio, Internacional,
  Fluminense, Cruzeiro, Atlético Mineiro, …) are present, as are Brazilian players
  worldwide via the `nationality` filter.
- Some single-season snapshots contain a few unplayed fixtures with `NA` scores
  (e.g. parts of the 2022 Brasileirão); these are loaded but excluded from
  win/draw/loss and goal tallies.

---

## Tests

BDD-style (Given/When/Then) tests written with JUnit 5 live under
`src/test/java/com/brazilsoccer/mcp/` and run as part of `mvn package`:

- `DataLoadingTest` – all six CSVs load; UTF-8 / scores / dates parse; de-dup works.
- `TeamNamesTest` – name normalization, sibling-club disambiguation, query matching.
- `CompetitionsTest` – competition canonicalization; Série B does not leak into Série A.
- `QueryServicesTest` – the five query capabilities against real data and known facts
  (e.g. Flamengo won the 2019 Brasileirão with ~90 pts; head-to-head tallies are consistent).
- `McpServerTest` – the MCP protocol surface: `initialize`, `tools/list`, `tools/call`,
  error handling, notifications, and a full stdio round-trip.

```bash
mvn test
```

---

## Data Sources

The following freely-available datasets (downloaded from Kaggle, with attribution)
are bundled under `data/kaggle/`:

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

## Specification

See [`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md) /
[`TASK.md`](TASK.md) for the full requirements this server implements.
