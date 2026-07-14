# Brazilian Soccer MCP with spec and basic data sets

## Specification
brazilian-soccer-mcp-guide.md (also `TASK.md`)

## Implementation

A self-contained **Model Context Protocol (MCP) server written in Go** that
answers natural-language questions about Brazilian soccer by loading the bundled
Kaggle CSVs into memory and exposing query tools over JSON-RPC 2.0 (stdio).
It has **no external dependencies** — only the Go standard library — so it builds
and runs anywhere with a Go toolchain.

### Build & run

```bash
go build -o brsoccer .      # build the server
./brsoccer                  # serve MCP over stdin/stdout (data dir: ./data/kaggle)
./brsoccer /path/to/data    # or point at a different data directory
go test ./...               # run the full test suite
```

The server speaks newline-delimited JSON-RPC. Example handshake + query:

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"standings","arguments":{"season":2019}}}' \
  | ./brsoccer
```

### MCP tools

| Tool | Purpose | Example question |
|------|---------|------------------|
| `search_matches` | Find matches by team / opponent / competition / season / source | "Show me all Flamengo vs Fluminense matches" |
| `team_record` | Win/draw/loss record, goals, win rate (home/away/all) | "What is Corinthians' home record in 2022?" |
| `head_to_head` | All-competition head-to-head between two teams | "Compare Palmeiras and Santos head-to-head" |
| `standings` | League table for a competition + season (3 pts/win) | "Who won the 2019 Brasileirão?" |
| `search_players` | Search FIFA players by name / nationality / club / position | "Who are the top Brazilian players?" |
| `competition_stats` | Avg goals per match, home/away win rates, biggest wins | "What's the average goals per match in the Brasileirão?" |

### How it works

- **Loader** (`loader.go`) — each of the five match CSVs and the FIFA player CSV
  has its own column layout, date format and naming convention, so each gets a
  dedicated parser mapping rows into a unified `Match` / `Player` model. Handles
  the UTF-8 BOM in `fifa_data.csv` and float-encoded goals (`1.0`).
- **Normalization** (`normalize.go`) — team names are reduced to a canonical key
  (lowercase, accent-free, state/country suffix and parentheticals stripped) so
  `Flamengo-RJ`, `Flamengo` and `São Paulo` all match consistently. Dates are
  parsed across ISO, ISO+time, and Brazilian `DD/MM/YYYY` formats.
- **Query engine** (`query.go`) — match search, team records, head-to-head,
  season standings, player search and aggregate statistics. Standings group by
  display name within a single source so same-named clubs from different states
  (Atlético-MG vs Atlético-PR) stay distinct and overlapping Brasileirão files
  are not double-counted.
- **MCP layer** (`mcp.go`, `tools.go`, `format.go`) — JSON-RPC dispatch, the
  tool catalog with JSON-Schema argument definitions, and human-readable
  rendering of results for the LLM.

Loads ~24k matches and ~18k players in well under a second; all queries respond
in milliseconds.

### Testing

Built test-first (TDD). The suite (`*_test.go`) covers normalization, date
parsing, CSV loading (asserting exact per-file row counts), every query against
known ground-truth facts (e.g. Flamengo were 2019 Brasileirão champions with 90
points and 28 wins), the full MCP JSON-RPC protocol surface, and the stdio
transport loop — ~87% statement coverage.

### Known data limitations

- Stripping state suffixes for cross-file matching merges distinct same-named
  clubs (the three Atléticos) in *cross-source* aggregates; per-season standings
  avoid this by keeping the suffix within a single source.
- This FIFA edition does not license every Brazilian club (e.g. Flamengo is
  absent), so some club-level player queries return no rows.
- All-competition head-to-head counts every dataset row, so overlapping
  Brasileirão files may count a 2012–2019 league meeting more than once.

## Data Sources
Kaggle data can't be downloaded without an account so these (freely available with attribution) data sets have been downloaded for use here:

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
