# Brazilian Soccer MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io) server, written in Go,
that exposes a knowledge graph over Brazilian soccer data (Brasileirão, Copa do
Brasil, Copa Libertadores match results plus the FIFA player database). An LLM
client such as Claude Desktop connects to it over stdio and can answer natural
language questions about players, teams, matches and competitions.

The full specification is in [`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md)
(mirrored in `TASK.md`).

## What was built

- A standard-library-only MCP server speaking **JSON-RPC 2.0 over stdio** (the
  transport MCP clients expect). No third-party dependencies.
- A CSV loader that ingests all **six bundled datasets**, normalizes the wildly
  inconsistent team names, dates and number formats, and merges them into one
  in-memory knowledge graph.
- A query engine covering every capability in the spec, surfaced as **7 MCP
  tools**.
- A test suite (`go test ./...`) with unit tests over synthetic fixtures and an
  integration test that validates results against the real bundled data.

## Quick start

```bash
# Build
go build -o brazilian-soccer-mcp .

# Run (reads data/kaggle by default; override with -data or $BRMCP_DATA)
./brazilian-soccer-mcp

# Run the tests
go test ./...
```

The server reads JSON-RPC requests from stdin and writes responses to stdout;
all diagnostics go to stderr so they never corrupt the protocol stream.

### Connecting from Claude Desktop

Add to `claude_desktop_config.json`:

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

### Try it from the shell

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"standings","arguments":{"season":2019}}}' \
  | ./brazilian-soccer-mcp
```

## Tools

| Tool | Purpose | Example question |
|------|---------|------------------|
| `search_matches` | Find matches by team, opponent, competition, season, date range | "What matches did Palmeiras play in 2023?" |
| `head_to_head` | Aggregate record + match list between two teams | "Compare Palmeiras and Santos head-to-head" |
| `team_record` | Win/draw/loss, goals and points for a team (filterable by season, competition, home/away) | "What is Corinthians' home record in 2022?" |
| `standings` | League table for a competition + season, computed from results | "Who won the 2019 Brasileirão?" |
| `search_players` | FIFA players by name, nationality, club, position, min rating | "Who are the highest-rated Brazilian players?" |
| `competition_stats` | Match count, total/average goals, home-win rate, biggest wins | "What's the average goals per match in the Brasileirão?" |
| `list_competitions` | Discover available competitions and dataset size | — |

Each tool returns a formatted text block designed to be dropped straight into an
LLM answer (see the answer formats in the spec).

## Design notes

### Team-name normalization
The datasets name the same club many different ways — `Palmeiras-SP`,
`Palmeiras`, `América - MG`, `Nacional (URU)`, `Sport Club Corinthians
Paulista`. Every name is reduced to a canonical **lookup key** (lower-cased,
accent-folded — `São Paulo` → `sao paulo`, `Grêmio` → `gremio` — and stripped of
state/country suffixes and punctuation). Queries match on this key with
bidirectional substring containment, so a search for `Corinthians` also matches
`Sport Club Corinthians Paulista`.

### Multiple formats
Dates are parsed from ISO (`2023-09-24`), datetime (`2012-05-19 18:30:00`) and
Brazilian (`29/03/2003`) forms. Goal counts may be quoted (`"2"`) or float-encoded
(`2.0`). UTF-8 BOMs in CSV headers are stripped.

### Cross-source de-duplication (important for correctness)
Brasileirão Série A 2019, for example, appears in **three** of the source files,
and a naive merge double- or triple-counts every match (producing a "90-point"
season with 120 points). Because the files spell team names differently,
per-fixture de-duplication is unreliable. Instead, for each
`(competition, season)` pair the loader keeps matches from a **single
authoritative source** — the richest one that covers that pair — with the broad
`BR-Football-Dataset.csv` used as a fallback for seasons and divisions
(Série B/C) the dedicated files don't reach. This yields a clean, non-overlapping
fixture set: the integration test confirms 2019 Série A has exactly 380 matches
and Flamengo as champions on 90 points (28W 6D 4L), matching reality.

## Project layout

```
main.go                     # CLI entry point + stdio wiring
internal/mcp/               # MCP / JSON-RPC server (transport-agnostic)
  jsonrpc.go                #   wire types
  server.go                 #   method dispatch (initialize, tools/list, tools/call)
  tools.go                  #   tool definitions + arg parsing
internal/soccer/            # knowledge graph + query engine
  model.go                  #   types
  normalize.go              #   team-name / competition normalization
  load.go                   #   CSV loaders + coverage de-duplication
  query.go                  #   search, standings, records, stats
  format.go                 #   human-readable answer formatting
data/kaggle/                # bundled datasets (see below)
```

## Data Sources

Kaggle data can't be downloaded without an account, so these (freely available
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

> **Data note:** the FIFA player dataset is a ~2019 snapshot with anonymized
> player names for some clubs and does not include every Brazilian league club
> (e.g. Flamengo is absent), so a few of the spec's example player lookups
> return no results. This is a limitation of the source data, not the server.
