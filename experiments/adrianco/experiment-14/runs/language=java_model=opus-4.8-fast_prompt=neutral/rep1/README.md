# Brazilian Soccer MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io) server, written in Java, that
exposes a knowledge graph over Brazilian soccer datasets. It lets an LLM answer natural-language
questions about matches, teams, players and competitions — Brasileirão, Copa do Brasil, Copa
Libertadores and more — by calling well-defined MCP tools.

The full requirements are in [`TASK.md`](TASK.md) (a.k.a. `brazilian-soccer-mcp-guide.md`).

---

## What was built

An in-memory knowledge graph is loaded once at startup from the six bundled CSV files
(`data/kaggle/`), unifying their different schemas, team-name spellings and date formats. A
JSON-RPC 2.0 server speaks the MCP stdio transport and dispatches tool calls to a query engine
that computes results live from match data.

```
stdin/stdout (JSON-RPC 2.0)
        │
   McpServer ── Tools (catalogue + formatting)
        │
   QueryService (matches / teams / players / standings / stats)
        │
   KnowledgeGraph (Match + Player models, indexed)
        │
   CsvReader  ←  data/kaggle/*.csv
```

| Layer | Class | Responsibility |
|-------|-------|----------------|
| Transport | `server/McpServer` | JSON-RPC 2.0 over stdio: `initialize`, `tools/list`, `tools/call`, `ping`, notifications |
| Tools | `server/Tools` | MCP tool catalogue (input schemas) + dispatch + human-readable formatting |
| Query | `query/QueryService` | All five capability categories, computed from the data |
| Data | `data/KnowledgeGraph` | Loads all CSVs into unified `Match`/`Player` models with indexes |
| Util | `util/CsvReader`, `util/TeamNames` | RFC-4180 CSV parsing; club-name normalization |
| Entry | `server/Main` | Loads data, starts the server (`--selftest` for a smoke check) |

Every source file carries a context-block comment describing its purpose and role.

### Data loaded

| File | Rows loaded | Mapped competition |
|------|------------:|--------------------|
| `Brasileirao_Matches.csv` | 4,180 | Brasileirão Série A |
| `Brazilian_Cup_Matches.csv` | 1,337 | Copa do Brasil |
| `Libertadores_Matches.csv` | 1,255 | Copa Libertadores |
| `BR-Football-Dataset.csv` | 10,296 | Serie A / B / C, Copa do Brasil (per `tournament`) |
| `novo_campeonato_brasileiro.csv` | 6,886 | Brasileirão (histórico 2003–2019) |
| `fifa_data.csv` | 18,207 players | — |

≈ 24,000 matches and 18,207 players, loaded in ~300 ms.

### Data-quality handling

- **Team-name variations** — `TeamNames` strips state/country suffixes (`Palmeiras-SP` → `Palmeiras`,
  `Nacional (URU)`), folds accents (`Grêmio` → `gremio`), and applies aliases for long legal names
  (`Sport Club Corinthians Paulista` → `corinthians`). Crucially it **keeps** the state code for
  clubs that share a base name, so `Atlético-MG`, `Atlético-PR` and `Atlético-GO` stay distinct
  (this is what makes the computed league tables correct).
- **Date formats** — ISO (`2023-09-24`), ISO-with-time (`2012-05-19 18:30:00`) and Brazilian
  (`29/03/2003`) are all parsed.
- **Character encoding** — all files are read as UTF-8, including a BOM on `fifa_data.csv`.

---

## MCP tools

| Tool | Purpose |
|------|---------|
| `search_matches` | Matches by team / opponent / home / away / competition / season / date range |
| `head_to_head` | Aggregate record between two teams across all competitions |
| `team_record` | Win/draw/loss & goals for a team, scoped by season / competition / home-away |
| `search_players` | FIFA players by name / nationality / club / position / min overall |
| `standings` | League table for a competition + season, computed from results (3/1/0) |
| `match_statistics` | Match count, total & average goals, home/away/draw rates |
| `biggest_wins` | Largest-margin victories, optionally filtered |
| `best_records` | Teams ranked by win rate (all/home/away) |
| `list_competitions` | What competitions and how much data are available |

---

## Build & run

Requires JDK 17+ and Maven.

```bash
mvn package                 # compile, test, build the runnable fat-jar
java -jar target/brazilian-soccer-mcp.jar          # start the MCP server (stdio)
java -jar target/brazilian-soccer-mcp.jar --selftest   # quick smoke check, no MCP client needed
```

The data directory is resolved from (in order): a CLI argument, the `BRAZIL_SOCCER_DATA`
environment variable, then `./data/kaggle`.

### Register with an MCP client

Example `claude_desktop_config.json` (or any MCP client) entry:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "java",
      "args": ["-jar", "/absolute/path/to/target/brazilian-soccer-mcp.jar"],
      "env": { "BRAZIL_SOCCER_DATA": "/absolute/path/to/data/kaggle" }
    }
  }
}
```

### Talking to it directly

```bash
printf '%s\n' \
 '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
 '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"standings","arguments":{"competition":"Brasileirão Série A","season":2019}}}' \
 | java -jar target/brazilian-soccer-mcp.jar
```

returns the 2019 Brasileirão table with **Flamengo champions on 90 points** — matching the worked
example in the spec.

---

## Example questions it answers

- *"Show me all Flamengo vs Fluminense matches"* → `search_matches` (team + opponent, with a head-to-head summary)
- *"What is Corinthians' home record in 2022?"* → `team_record`
- *"Who won the 2019 Brasileirão?"* → `standings`
- *"Find all Brazilian players"* / *"Who are the highest-rated players at Flamengo?"* → `search_players`
- *"What's the average goals per match in the Brasileirão?"* → `match_statistics`
- *"Which team has the best home record?"* → `best_records`
- *"Show me the biggest wins in the dataset"* → `biggest_wins`

---

## Tests

35 JUnit 5 tests run against the real datasets:

```bash
mvn test
```

They cover club-name normalization (including the ambiguous-Atlético case), loading of all six
files, every query category (the headline test reproduces the spec's 2019 Flamengo-90-points
table), and the full MCP JSON-RPC protocol surface (handshake, `tools/list`, `tools/call`,
notifications, error envelopes).

---

## Data Sources

Kaggle data can't be downloaded without an account, so these (freely available with attribution)
datasets have been downloaded for use here:

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
