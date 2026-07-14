# Brazilian Soccer MCP Server

An [MCP](https://modelcontextprotocol.io) server, written in Go, that turns the
bundled Kaggle datasets into a queryable knowledge graph for Brazilian soccer.
It lets an LLM answer natural-language questions about matches, teams, players,
competitions and statistics.

The full specification is in [`TASK.md`](TASK.md) /
[`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md).

## What was built

A self-contained MCP server (Go standard library only, no external
dependencies) that:

- Loads all six provided CSV datasets (~24,000 raw match rows + 18,207 FIFA
  players) into memory.
- Normalizes the messy real-world data: accents (`São Paulo` ≈ `Sao Paulo`),
  state/country suffixes (`Palmeiras-SP`, `Nacional (URU)`, `Vasco da Gama RJ`),
  multiple date formats (`2012-05-19 18:30:00`, `2023-09-24`, `29/03/2003`) and
  competition aliases (`Serie A` → `Brasileirão Série A`).
- Keeps clubs that share a base name but play in different states apart
  (`Atlético-MG` vs `Atlético-PR` vs `Atlético-GO`).
- Deduplicates matches that appear in several overlapping datasets, keeping one
  canonical source per competition/season so standings and statistics are not
  double-counted.
- Speaks JSON-RPC 2.0 over stdio (`initialize`, `tools/list`, `tools/call`,
  `ping`).

### Source layout

| File | Responsibility |
|------|----------------|
| `main.go` | Entry point and the stdio JSON-RPC serve loop |
| `protocol.go` | MCP / JSON-RPC request handling |
| `tools.go` | The seven MCP tools: schemas, argument parsing, answer formatting |
| `query.go` | Query layer (matches, head-to-head, stats, standings, players) |
| `load.go` | Per-dataset CSV loaders and cross-source deduplication |
| `normalize.go` | Team-name, competition and date normalization |
| `model.go` | `Match`, `Player` and `DB` data models |
| `*_test.go` | BDD (Given/When/Then) test scenarios |

## Build and run

```sh
go build -o soccer-mcp .      # build
go test ./...                 # run the BDD test suite
./soccer-mcp                  # run the MCP server (reads/writes stdio)
```

The data directory defaults to `data/kaggle`. Override it with the `-data`
flag or the `SOCCER_DATA_DIR` environment variable:

```sh
./soccer-mcp -data /path/to/csvs
```

### Connecting from an MCP client

Register the built binary as a stdio MCP server. Example client config:

```json
{
  "mcpServers": {
    "brazilian-soccer": { "command": "/absolute/path/to/soccer-mcp" }
  }
}
```

### Talking to it directly

```sh
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize"}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"competition_standings","arguments":{"competition":"Brasileirão","season":2019}}}' \
  | ./soccer-mcp
```

## Tools

| Tool | Purpose |
|------|---------|
| `find_matches` | Find matches by team, opponent, competition, season, venue or date range |
| `head_to_head` | Head-to-head record between two teams |
| `team_stats` | A team's wins/draws/losses/goals/points, optionally by season and venue |
| `competition_standings` | League table for a competition + season, computed from results |
| `match_statistics` | Aggregate stats: avg goals, home/away win rates, biggest wins |
| `search_players` | Search FIFA players by name, nationality, club, position or rating |
| `list_competitions` | Competitions in the dataset with match counts and season ranges |

## Testing

Tests follow a BDD Given/When/Then structure (`TestScenario_*`) covering
normalization, dataset loading and deduplication, every query type, and the MCP
protocol end-to-end. They run against the real bundled CSV files.

```sh
go test -v ./...
```

## Data sources

Kaggle data cannot be downloaded without an account, so these freely available
datasets (used with attribution) are included under `data/kaggle/`:

- https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro — CC BY 4.0
  - `Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`, `Libertadores_Matches.csv`
- https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches — CC0 Public Domain
  - `BR-Football-Dataset.csv`
- https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019 — CC BY 4.0
  - `novo_campeonato_brasileiro.csv`
- https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data — Apache 2.0
  - `fifa_data.csv`

### Data notes

- The FIFA player dataset (FIFA 19 era) includes only a limited set of licensed
  Brazilian clubs, so some clubs (e.g. Flamengo) have no player entries.
- `BR-Football-Dataset.csv` is the only source with extended stats (shots,
  corners) and is the sole source for Série B/C and the 2023 season.
- For competitions/seasons present in multiple files, the dedicated league
  files take precedence over the broader datasets.
