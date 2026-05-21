# Brazilian Soccer MCP Server

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server, written
in Go, that answers natural-language questions about Brazilian soccer — players,
teams, matches and competitions — over the bundled Kaggle datasets.

The full requirements are in `brazilian-soccer-mcp-guide.md` / `TASK.md`.

## What was built

A self-contained Go program (no external dependencies) that:

- Loads all six provided CSV datasets into an in-memory store.
- Reconciles the messy real-world data: differing column layouts, three date
  formats, UTF-8 accents, and team names written several ways
  (`Palmeiras-SP`, `Palmeiras`, `América - MG`, `Nacional (URU)`).
- De-duplicates fixtures that appear in more than one dataset by designating a
  single authoritative source per competition and season, so aggregate
  statistics are never double-counted.
- Speaks MCP over stdio (newline-delimited JSON-RPC 2.0) and exposes seven tools.

### MCP tools

| Tool | Purpose |
|------|---------|
| `search_matches` | Find matches by team, opponent, competition, season or date range |
| `team_stats` | Win/draw/loss record, goals and win rate for a team (optionally by season/competition/venue) |
| `head_to_head` | All-time head-to-head record between two teams |
| `search_players` | Search the FIFA player database by name, nationality, club, position or rating |
| `competition_standings` | League table calculated from match results (3pts win / 1pt draw) |
| `competition_stats` | Average goals per match, home-win rate and biggest victories |
| `list_competitions` | Competitions, season coverage and dataset sizes |

## Build and run

```sh
go build -o brazilian-soccer-mcp .
./brazilian-soccer-mcp            # serves MCP on stdin/stdout, logs to stderr
./brazilian-soccer-mcp -data DIR  # override the dataset directory
```

The server reads JSON-RPC requests from stdin and writes responses to stdout.
Example session:

```jsonl
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}
{"jsonrpc":"2.0","id":2,"method":"tools/list"}
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"competition_standings","arguments":{"competition":"Brasileirão","season":2019}}}
```

To connect it to an MCP client (e.g. Claude Desktop), register it as a stdio
server pointing at the built binary.

## Tests

BDD-style Given/When/Then scenarios covering loading, normalization, every
query and the MCP transport:

```sh
go test ./...
```

## Source layout

| File | Responsibility |
|------|----------------|
| `main.go` | Entry point: load data, serve MCP over stdio |
| `mcp.go` | JSON-RPC 2.0 / MCP protocol transport |
| `tools.go` | MCP tool definitions, schemas and response formatting |
| `query.go` | Pure query/aggregation logic (search, records, standings, stats) |
| `loader.go` | CSV parsing and cross-dataset de-duplication |
| `normalize.go` | Team-name normalization (accents, suffixes, country codes) |
| `model.go` | Core data types |

## Data notes

- Brasileirão Série A is sourced from `novo_campeonato_brasileiro.csv` for
  2003–2019 and `Brasileirao_Matches.csv` for 2020–2022; `BR-Football-Dataset.csv`
  additionally provides Série B and Série C.
- The FIFA dataset (FIFA 19) does not include some clubs that were unlicensed
  at the time — notably Flamengo, Palmeiras, Corinthians and São Paulo — so club
  searches for those return no players. Many other Brazilian clubs (Santos,
  Grêmio, Internacional, Cruzeiro, Fluminense, …) are present.

## Data sources

Pre-downloaded into `data/kaggle/` (Kaggle requires an account to download):

- https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro — CC BY 4.0
  (`Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`, `Libertadores_Matches.csv`)
- https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches — CC0 Public Domain
  (`BR-Football-Dataset.csv`)
- https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019 — CC BY 4.0
  (`novo_campeonato_brasileiro.csv`)
- https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data — Apache 2.0
  (`fifa_data.csv`)
