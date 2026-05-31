# Brazilian Soccer MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io) server, written in Go,
that exposes a knowledge-graph-style query interface over Brazilian soccer data
(matches, teams, competitions, and FIFA players). It lets an LLM answer natural
language questions such as *"Who won the 2019 Brasileirão?"*, *"Compare Flamengo
and Fluminense head-to-head"*, or *"Find the top Brazilian players"*.

This implements the specification in [`TASK.md`](TASK.md) /
[`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md).

## What was built

- A self-contained MCP server over the **stdio JSON-RPC 2.0** transport,
  implemented with **only the Go standard library** (no external dependencies),
  so it builds and runs fully offline.
- An in-memory data layer that loads and unifies all six provided CSV datasets.
- A transport-independent query engine providing match, team, player,
  competition, and statistical analysis queries.
- BDD-style (Given/When/Then) tests covering normalization, loading,
  the query engine, and the MCP protocol end-to-end.

## Architecture

```
main.go                     process entry point; loads data, serves MCP over stdio
internal/data/              domain model + CSV loaders + team-name normalization
  model.go                  unified Match / Player / Database types
  normalize.go              team-name normalization & matching
  loader.go                 per-file CSV parsers + cross-file de-duplication
internal/query/             analytical engine (independent of transport)
  engine.go                 match search, head-to-head, team stats, standings, etc.
  format.go                 human-readable answer formatting
internal/mcp/               MCP server
  protocol.go               JSON-RPC 2.0 stdio framing & dispatch
  tools.go                  tool definitions + handlers + lifecycle methods
```

Every source file begins with a context block comment describing its role.

## Data handling

The six CSV files overlap heavily and use inconsistent conventions; the loader
addresses the data-quality issues called out in the spec:

- **Team name variations** — names are normalized (lower-cased, accents folded,
  state/country suffixes stripped) so `Flamengo`, `Flamengo-RJ`, and
  `São Paulo`/`Sao Paulo` match. Clubs that differ only by state
  (`Atlético-MG` vs `Athletico-PR`) are kept distinct for standings.
- **Multiple date formats** — ISO, ISO-with-time, and Brazilian `DD/MM/YYYY`
  are all parsed.
- **Mixed numeric formats** — goals appear as ints, floats (`2.0`), and quoted
  strings; all are handled.
- **UTF-8 & BOM** — Portuguese accents are preserved; the BOM in the FIFA header
  is stripped.
- **De-duplication** — the same season appears in several files (e.g. Série A
  2019 is in three of them). For each `(competition, season)` the loader keeps
  only the single most complete source, so standings and aggregate statistics
  are not double-counted.

## MCP tools

| Tool | Purpose |
|------|---------|
| `search_matches` | Find matches by team, opponent, competition, season, venue, or date range |
| `head_to_head` | All-time record between two teams |
| `team_stats` | A team's W/D/L, goals, points and win rate (optionally by season/competition/venue) |
| `standings` | League table for a competition + season, computed from results |
| `competition_stats` | Match count, average goals, home/away/draw rates, biggest wins |
| `search_players` | Search FIFA players by name, nationality, club, position, min rating |
| `list_competitions` | List competitions available in the loaded data |

## Build & run

```sh
go build -o brazilian-soccer-mcp .
./brazilian-soccer-mcp                 # loads ./data/kaggle by default
./brazilian-soccer-mcp -data /path/to/csvs
```

The dataset directory can also be set via the `BRAZIL_SOCCER_DATA` environment
variable.

### Example MCP client configuration

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/absolute/path/to/brazilian-soccer-mcp",
      "args": ["-data", "/absolute/path/to/data/kaggle"]
    }
  }
}
```

### Manual smoke test (pipe JSON-RPC on stdin)

```sh
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"standings","arguments":{"competition":"Brasileirão","season":2019,"limit":5}}}' \
  | ./brazilian-soccer-mcp
```

## Tests

```sh
go test ./...
```

Tests use the Given/When/Then BDD structure. The query-engine and MCP tests run
against small synthetic datasets for determinism, plus integration tests that
load the real CSVs and assert well-known facts (e.g. Flamengo won the 2019
Brasileirão with 90 points). Integration tests skip gracefully if the data
directory is absent.

## Data sources

Kaggle data can't be downloaded without an account, so these freely available
(with attribution) datasets are included under `data/kaggle/`:

- https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro — CC BY 4.0
  - `Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`, `Libertadores_Matches.csv`
- https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches — CC0 Public Domain
  - `BR-Football-Dataset.csv`
- https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019 — CC BY 4.0
  - `novo_campeonato_brasileiro.csv`
- https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data — Apache 2.0
  - `fifa_data.csv`
