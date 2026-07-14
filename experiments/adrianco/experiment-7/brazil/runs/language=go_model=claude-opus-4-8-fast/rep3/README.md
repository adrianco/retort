# Brazilian Soccer MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io) server, written in Go,
that turns six Kaggle Brazilian-soccer datasets into a queryable knowledge graph.
An LLM host (Claude Desktop, etc.) connects over the MCP **stdio** transport and
calls the server's tools to answer natural-language questions about matches,
teams, players, competitions and statistics.

The implementation follows [`TASK.md`](TASK.md) (a copy of
[`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md)).

## Quick start

```bash
go test ./...            # run the BDD test suite
go build -o soccer-mcp . # build the self-contained server (data is embedded)
./soccer-mcp             # speaks MCP JSON-RPC on stdin/stdout
```

The datasets in `data/kaggle/` are compiled into the binary with `go:embed`, so
the server runs from any working directory with no external files. To use a
refreshed copy of the CSVs instead, pass `-data <dir>`.

### Registering with an MCP host

```json
{
  "mcpServers": {
    "brazilian-soccer": { "command": "/absolute/path/to/soccer-mcp" }
  }
}
```

### Trying it from the shell

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"competition_standings","arguments":{"competition":"Brasileirão","season":2019,"limit":5}}}' \
  | ./soccer-mcp
```

## Tools

| Tool | Purpose |
|------|---------|
| `search_matches` | Find fixtures by team, opponent, competition, season and/or date range. |
| `head_to_head` | Wins/draws/goals and the match list between two teams. |
| `team_stats` | A team's W/D/L, goals, points and win rate, scoped by season/competition/venue. |
| `search_players` | FIFA players by name, nationality, club, position and rating. |
| `competition_standings` | A league table computed from match results. |
| `league_statistics` | `summary`, `biggest_wins`, `best_home`, `best_away`, `best_overall`, `top_scoring`. |
| `list_competitions` | Discover the competitions and seasons present in the data. |

Example — the 2019 Brasileirão table (matches the figures in the spec):

```
1. Flamengo — 90 pts (28W 6D 4L, GD +49) — Champion
2. Palmeiras — 74 pts (21W 11D 6L, GD +29)
3. Santos — 74 pts (22W 8D 8L, GD +27)
```

## Architecture

```
main.go        entry point: loads embedded data, registers tools, serves stdio
embed.go       go:embed of data/kaggle/*.csv
tools.go       MCP tool definitions, JSON-Schema args, result formatting
internal/mcp/  minimal MCP JSON-RPC 2.0 server over the stdio transport (stdlib only)
internal/soccer/
  normalize.go team-name canonicalization & accent-insensitive matching
  model.go     unified Match / Player / DB domain types
  loader.go    CSV parsing + per-(competition,season) source selection
  query.go     match / team / player / standings queries
  stats.go     aggregate statistics (goals, biggest wins, best records, coverage)
  format.go    human-readable rendering of results
```

There are **no third-party dependencies** — only the Go standard library.

## Data handling notes

The datasets are messy and overlapping; the loader addresses each issue called
out in the specification:

- **Team-name variations** — `Palmeiras-SP`, `América - MG`, `Nacional (URU)`
  and `São Paulo` are normalized to canonical names, and matching is
  case- and accent-insensitive (`Sao Paulo` ≡ `São Paulo-SP`).
- **Overlapping datasets** — the same fixture appears in up to three files, which
  also disagree on spelling. For each `(competition, season)` the loader keeps
  matches from a **single authoritative source** (the file with the most
  *scored* matches), so tables are never double-counted and a club is never split
  into spelling variants. This matters in practice: the 2022 Brasileirão rows in
  one file have blank scores, so the scored file is chosen automatically.
- **Date formats** — ISO (`2023-09-24`), Brazilian (`29/03/2003`) and
  timestamped (`2012-05-19 18:30:00`) dates are all parsed.
- **Numeric quirks** — quoted and float-formatted goals (`"2"`, `1.0`) are
  handled, and the UTF-8 BOM on the FIFA header is stripped.

## Datasets

| File | Competition / content | License |
|------|-----------------------|---------|
| `Brasileirao_Matches.csv` | Brasileirão Série A | CC BY 4.0 |
| `Brazilian_Cup_Matches.csv` | Copa do Brasil | CC BY 4.0 |
| `Libertadores_Matches.csv` | Copa Libertadores | CC BY 4.0 |
| `novo_campeonato_brasileiro.csv` | Brasileirão 2003–2019 | CC BY 4.0 |
| `BR-Football-Dataset.csv` | Série A/B/C + Copa do Brasil w/ extended stats | CC0 |
| `fifa_data.csv` | FIFA player database (18,207 players) | Apache 2.0 |

Sources are listed in the [data attribution section](#data-attribution) below.
After loading and de-duplication the knowledge graph holds ~16,800 matches across
five competitions (2003–2023) and 18,207 players.

> Note on FIFA coverage: the FIFA-19 player file does not include every Brazilian
> club (e.g. Flamengo, Palmeiras and Corinthians are absent for licensing
> reasons), while Grêmio, Santos and Fluminense are present. Player-by-club
> queries reflect what the dataset contains.

## Testing

Tests follow the spec's BDD (Given/When/Then) approach:

- `internal/soccer/soccer_test.go` loads the real datasets and asserts on match,
  team, player, standings, head-to-head and statistics scenarios — including
  historically verifiable facts (2019 champion Flamengo, 2022 champion Palmeiras).
- `internal/mcp/server_test.go` drives the JSON-RPC transport end to end
  (initialize handshake, `tools/list`, `tools/call`, error handling).

```bash
go test ./...
```

## Data attribution

- https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro — CC BY 4.0
- https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches — CC0 Public Domain
- https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019 — CC BY 4.0
- https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data — Apache 2.0
