# Brazilian Soccer MCP Server

A Go, stdio-based [Model Context Protocol](https://modelcontextprotocol.io/) server for the six Brazilian soccer CSV datasets included in this repository. It loads the data once at startup, normalizes the incompatible source schemas, and exposes deterministic MCP tools for an LLM client.

## What it supports

- Match search by team, home/away venue, opponent, competition, dataset source, season, round/stage, and inclusive date range.
- Accent-, punctuation-, alias-, and state-suffix-aware team matching, including forms such as `São Paulo FC`, `Sao Paulo-SP`, and `Sport Club Corinthians Paulista`.
- Nullable scores and dates for scheduled/postponed rows; they are returned by match search but never silently counted as 0–0 in analytics.
- Team records, home/away splits, goals, points, head-to-head comparisons, and calculated league standings.
- Aggregate scoring statistics, biggest wins, top-scoring teams, best home/away records, and clearly labelled derived relegation candidates.
- FIFA player search by name, nationality, club, position, position group, rating, and provided numeric attributes.
- Competition/source discovery, a documented traditional-derby lookup, and a convenience `ask_soccer_question` tool for common natural-language requests.

The server exposes both structured tools and resources over newline-delimited JSON-RPC 2.0 on stdin/stdout. Startup messages go only to stderr, so stdout remains valid MCP transport.

## Run it

Requires Go 1.26 or newer.

```sh
go test ./...
go run . -data-dir ./data/kaggle
```

For an MCP client, run the built binary with its working directory set to this repository, or pass an absolute `-data-dir` path. The MCP lifecycle supports `initialize`, `ping`, `tools/list`, `tools/call`, `resources/list`, and `resources/read`.

Example JSON-RPC requests:

```json
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{}}}
{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"search_matches","arguments":{"team":"Flamengo","opponent":"Fluminense","competition":"Brasileirão","limit":20}}}
```

## MCP tools

| Tool | Purpose |
| --- | --- |
| `search_matches` | Search every supplied match dataset while retaining `source_file` provenance. |
| `get_team_statistics` | Get a team's deduplicated completed-match record and home/away splits. |
| `compare_teams` | Compare two team records and their head-to-head results. |
| `search_players` | Search the FIFA player snapshot and skill attributes. |
| `get_competition_standings` | Calculate a Brasileirão Série A/B/C table for a season. |
| `analyze_statistics` | Request summaries, head-to-head, biggest wins, scoring leaders, venue records, or derived relegation candidates. |
| `list_competitions` | Discover available competitions, seasons, datasets, and row counts. |
| `list_derbies` | Find matches from the server's documented traditional-rivalry list. |
| `ask_soccer_question` | Deterministically handle common natural-language question forms. |

`search_players.position_group` accepts `forwards`, `midfielders`, `defenders`, or `goalkeepers`.

## Data handling choices

- The five match files are normalized to one model, and `fifa_data.csv` is loaded as player data. The FIFA BOM and optional fields are handled safely.
- Calculations conservatively deduplicate overlapping rows by competition, season, date, normalized teams, and final score while preferring the dedicated competition files over historical/extended copies. Direct match search deliberately preserves each source row and identifies its source.
- Standings use 3 points for a win and 1 for a draw, then sort by points, goal difference, goals scored, wins, and team name.
- Copa do Brasil and Libertadores are not treated as league tables. The data does not contain enough aggregate/tie-break information to invent a full knockout bracket.
- Top scorers cannot be calculated because no source includes player goal events. The server reports this rather than fabricating player statistics.
- FIFA club values are a snapshot, not a historical match-season roster.

## Verification

The BDD-style Go tests cover:

- loading and querying all six CSV files;
- UTF-8/BOM, Brazilian/ISO date, numeric/unknown score, and team-alias handling;
- match search, team records, standings, head-to-head, player filters, source overlap, and aggregate statistics;
- MCP initialization, tool discovery/calls, resources, and JSON-RPC error behavior;
- 20 supported natural-language question forms;
- concurrent reads and the specified <2 s lookup / <5 s aggregate latency gates against the supplied datasets.
