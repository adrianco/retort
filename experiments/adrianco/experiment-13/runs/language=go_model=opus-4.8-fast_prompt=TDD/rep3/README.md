# Brazilian Soccer MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io) server, written in Go,
that exposes a knowledge interface over Brazilian soccer data (matches, teams,
players and competitions). An MCP-capable LLM can call its tools to answer
natural-language questions such as *"Who won the 2019 Brasileirão?"*,
*"What is Corinthians' home record in 2022?"* or *"Find the top Brazilian forwards."*

The full specification is in [`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md).

## What was built

The implementation was developed test-first (TDD) and is organised into three layers:

| Package | Responsibility |
|---------|----------------|
| `internal/soccer` | Domain model, CSV loaders (one per source layout), team-name normalization & canonicalization, cross-file deduplication, and the query engine (match search, head-to-head, team records, standings, player search, statistics). |
| `internal/mcpserver` | The six MCP tools, argument coercion, answer formatting, and a JSON-RPC 2.0 server over a newline-delimited stdio transport. |
| `cmd/server` | Entry point: loads the datasets and serves MCP on stdin/stdout. |

### MCP tools

| Tool | Purpose |
|------|---------|
| `search_matches` | Find matches by team, opponent, competition, season or date range. |
| `head_to_head` | All-time head-to-head record between two teams. |
| `team_record` | A team's W/D/L, goals and win-rate, filterable by season/competition/venue. |
| `standings` | League table for a season/competition, computed from match results. |
| `search_players` | Search the FIFA player database by name, nationality, club or position. |
| `match_statistics` | Average goals/match, home-win rate and the biggest victories. |

## Data handling

The six CSV datasets (see attribution below) use inconsistent conventions, which
the loader normalizes:

- **Team-name variations** — state suffixes (`Palmeiras-SP`), country codes
  (`Nacional (URU)`), accents (`Grêmio`), space-separated state codes
  (`Botafogo RJ`) and long forms (`Vasco da Gama`, `Atlético Mineiro`). Names are
  cleaned, and the well-known top-flight clubs are canonicalized to a single
  identity so they match and aggregate consistently. The two Atléticos (MG/PR)
  are kept distinct.
- **Multiple date formats** — `2012-05-19 18:30:00`, `2023-09-24` and
  `29/03/2003` are all parsed.
- **UTF-8 / BOM** — accents are preserved for display; a leading byte-order mark
  on the FIFA file is stripped.
- **Cross-file overlap** — the same Brasileirão fixture can appear in up to three
  files (the historical file, the modern file, and the extended-statistics file
  labelled "Serie A"). These are **deduplicated on load**, so standings,
  head-to-head and statistics are not multiplied. As a check, the computed 2019
  Brasileirão table reproduces the real result (Flamengo champions, 90 pts from
  38 games).

> Note: entity resolution covers the major clubs that recur across datasets;
> obscure lower-division clubs with very different spellings may not fully merge.

## Build & run

```bash
go build ./...
go test ./...                 # unit + integration tests
go run ./cmd/server           # serves MCP on stdio (data dir defaults to data/kaggle)
go run ./cmd/server -data path/to/csvs
```

Diagnostics go to stderr; the JSON-RPC stream is stdout only.

### Quick manual check

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"standings","arguments":{"season":2019}}}' \
  | go run ./cmd/server
```

### Configuring an MCP client

Point any MCP client at the built binary over stdio, for example:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/path/to/brazilian-soccer-mcp",
      "args": ["-data", "/path/to/data/kaggle"]
    }
  }
}
```

## Testing approach

Every behavior was specified by a failing unit test before implementation
(red → green → refactor). Coverage includes per-format CSV parsing, name
normalization/canonicalization, deduplication, each query, the tool dispatch
layer, and the JSON-RPC protocol, plus an integration test that loads the real
bundled datasets and validates representative queries.

## Data Sources

Kaggle data can't be downloaded without an account so these (freely available
with attribution) data sets have been downloaded for use here:

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
