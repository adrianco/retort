# Brazilian Soccer MCP Server (Go)

An [MCP](https://modelcontextprotocol.io) server that exposes a queryable
knowledge base of Brazilian soccer — matches, teams, players, competitions and
statistics — built from the bundled Kaggle datasets. An LLM host connects to it
over stdio and calls its tools to answer natural-language questions.

The original specification is in [`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md)
(mirrored in `TASK.md`).

## What was built

- **Pure-Go, zero external dependencies.** The MCP protocol (JSON-RPC 2.0 over
  stdio, newline-delimited framing) is implemented directly on the standard
  library, so the server builds and runs with nothing but a Go toolchain.
- **All six CSV datasets are loaded and queryable**, unified into a single
  in-memory model with per-source loaders that handle the different column
  layouts, date formats (`YYYY-MM-DD`, `DD/MM/YYYY`, with/without time), goal
  encodings (`1` vs `1.0`), a UTF-8 BOM on the FIFA header, and UTF-8 accented
  Portuguese text.
- **Robust team-name handling.** Names appear with state suffixes
  (`Palmeiras-SP`), country suffixes (`Barcelona-EQU`), parenthetical notes
  (`Nacional (URU)`) and accents (`Grêmio`, `São Paulo`). Identity keys fold
  accents and casing but **keep** the state/country suffix, because it
  disambiguates clubs that share a base name (Atlético-MG, Atlético-GO and
  Athletico-PR can all play the same season). User queries match loosely
  (`"flamengo"` finds `Flamengo-RJ`).
- **Correct cross-source de-duplication.** The Brasileirão Série A appears in
  three files (and Copa do Brasil in two) with inconsistent spellings between
  them. Instead of trying to reconcile spellings, the loader picks a single
  authoritative source per `(competition, season)`, so every season comes from
  one internally consistent file. This produces exact figures — e.g. the 2019
  Série A table reproduces the known result: **Flamengo champion, 90 pts,
  28-6-4**.

## MCP tools

| Tool | Purpose |
|------|---------|
| `search_matches` | Find matches by team, opponent, competition, season, venue and/or date range |
| `head_to_head` | All-time W/D/L record and goals between two teams |
| `team_stats` | A team's record (matches, W/D/L, goals, points, win rate), filterable by season/competition/venue |
| `search_players` | FIFA player search by name, nationality, club, position and minimum overall rating |
| `competition_standings` | League table for a competition + season, computed from results |
| `competition_stats` | Aggregates: match count, avg goals/match, home-win rate, biggest wins |
| `list_competitions` | Competitions available and dataset size |

These cover the five capability areas in the spec: match, team, player,
competition and statistical queries.

## Layout

```
cmd/server/         main: load data, serve MCP on stdio
internal/soccer/    domain model, CSV loaders, name normalization, queries, formatting
internal/mcpserver/ JSON-RPC 2.0 protocol, method router, tool definitions
data/kaggle/        the six provided CSV files
```

Every source file begins with a context block comment describing its role.

## Build, test, run

```bash
go build ./...          # build everything
go test ./...           # run the BDD (Given/When/Then) test suite
go run ./cmd/server     # start the MCP server (reads data/kaggle by default)
```

The data directory can be overridden with the `-data` flag or the
`SOCCER_DATA_DIR` environment variable:

```bash
go run ./cmd/server -data /path/to/data/kaggle
```

Diagnostics go to stderr; stdout carries only the JSON-RPC stream.

### Example session

```bash
printf '%s\n' \
 '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
 '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"competition_standings","arguments":{"competition":"Brasileirão","season":2019,"limit":5}}}' \
 | go run ./cmd/server
```

returns the 2019 Série A table led by Flamengo on 90 points.

### Connecting from an MCP client

Configure the host to launch the built binary over stdio, e.g.:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/path/to/server",
      "args": ["-data", "/path/to/data/kaggle"]
    }
  }
}
```

## Testing approach

Tests are written in BDD Given/When/Then style (`internal/soccer/*_test.go`,
`internal/mcpserver/*_test.go`):

- Normalization scenarios run without data and pin down suffix-aware matching.
- Query scenarios run against the **real** datasets and assert known-good
  numbers (the 2019 Série A gold-standard season, head-to-head consistency,
  top-rated Brazilian = Neymar, etc.).
- Protocol scenarios verify the `initialize` handshake, `tools/list`,
  `tools/call` (including error results for missing arguments) and a full
  line-delimited stdio round trip.

## Data sources & licenses

| File | Source | License |
|------|--------|---------|
| `Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`, `Libertadores_Matches.csv` | [Kaggle: jogos-do-campeonato-brasileiro](https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro) | CC BY 4.0 |
| `BR-Football-Dataset.csv` | [Kaggle: brazilian-football-matches](https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches) | CC0 Public Domain |
| `novo_campeonato_brasileiro.csv` | [Kaggle: campeonato-brasileiro-2003-a-2019](https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019) | CC BY 4.0 |
| `fifa_data.csv` | [Kaggle: fifa-players-data](https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data) | Apache 2.0 |

The FIFA player dataset is FIFA-19 era, which licenses some Brazilian clubs
(Grêmio, Santos, Internacional, Fluminense, …) but not others (Flamengo,
Palmeiras, Corinthians, São Paulo).
