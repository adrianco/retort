# Brazilian Soccer MCP Server

A self-contained [Model Context Protocol](https://modelcontextprotocol.io) (MCP)
server, written in Go, that exposes a knowledge interface over bundled Brazilian
football datasets. It lets an MCP-capable LLM answer natural-language questions
about matches, teams, players and competitions (Brasileirão, Copa do Brasil and
Copa Libertadores) plus the FIFA player database.

The full requirements are in [`TASK.md`](TASK.md) /
[`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md).

## Quick start

```bash
# Build (datasets are embedded into the binary)
go build -o bsmcp .

# The server speaks JSON-RPC 2.0 over stdio. Try it by hand:
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
  '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"standings","arguments":{"competition":"Brasileirão Série A","season":2019}}}' \
  | ./bsmcp
```

### Registering with an MCP client

Point any MCP client (e.g. Claude Desktop) at the built binary:

```json
{
  "mcpServers": {
    "brazilian-soccer": { "command": "/absolute/path/to/bsmcp" }
  }
}
```

The CSV datasets are embedded with `go:embed`, so the binary runs from any
directory with no external files. To load refreshed CSVs from disk instead, set
`SOCCER_DATA_DIR` to a directory containing the same file names.

## Tools

| Tool | Purpose | Key arguments |
|------|---------|---------------|
| `search_matches` | Find matches by team, opponent, venue, competition, season or date range | `team`, `opponent`, `venue`, `competition`, `season`, `date_from`, `date_to`, `limit` |
| `head_to_head` | All-time record between two teams | `team_a`, `team_b`, `limit` |
| `team_stats` | A team's W/D/L and goals, optionally by competition/season/venue | `team`, `competition`, `season`, `venue` |
| `search_players` | Search FIFA players by name/nationality/club/position/rating | `name`, `nationality`, `club`, `position`, `min_overall`, `sort_by`, `limit` |
| `players_by_club` | Player counts and average rating grouped by club | `nationality`, `limit` |
| `standings` | League table for a competition+season (3pts/win) | `competition`, `season`, `limit` |
| `competition_stats` | Avg goals/match, home-win rate, biggest victories | `competition`, `season`, `top_wins` |
| `list_competitions` | Competitions available in the data | — |
| `list_seasons` | Seasons available (optionally per competition) | `competition` |

These cover all five capability categories in the spec — match, team, player,
competition and statistical queries — and answer the sample questions such as
"Who won the 2019 Brasileirão?", "Compare Flamengo and Fluminense head-to-head",
"Find all Brazilian players" and "What's the average goals per match?".

## How it works

```
main.go                 stdio entry point; embeds data/kaggle/*.csv
internal/mcp/           dependency-free JSON-RPC 2.0 / MCP stdio server
internal/soccer/        data model, CSV loader and query engine
internal/app/           wires the query engine to MCP tools
```

The implementation has **no third-party dependencies** — only the Go standard
library.

### Data handling

The six CSV files use different layouts, encodings and naming conventions, which
the loader reconciles:

- **Team-name normalization.** Names appear with a state suffix
  (`Palmeiras-SP`), without one (`Palmeiras`), spaced (`América - MG`) or with a
  country code (`Nacional (URU)`). Matching folds accents and strips suffixes so
  `Sao Paulo` finds `São Paulo`, while a *suffixed* query like `Atlético-MG`
  stays distinct from `Atlético-GO`. Display names keep the suffix to tell
  same-named clubs apart.
- **Date formats.** ISO (`2023-09-24`), ISO-with-time
  (`2012-05-19 18:30:00`) and Brazilian (`29/03/2003`) are all parsed.
- **UTF-8 / BOM.** Headers are BOM-trimmed and Portuguese accents preserved.
- **Overlapping datasets.** The Brasileirão appears in three files. To avoid
  double-counting, each `(competition, season)` is served by a single
  highest-priority source (official single-competition files outrank the broad
  BR-Football set), so calculated standings match reality — e.g. the 2019
  Brasileirão correctly returns Flamengo champions on 90 points.

> Note: standings/statistics are computed purely from the matches present in the
> provided data. A few seasons in the source files are partial (e.g. the 2022
> Brasileirão stops mid-season), so totals reflect the available rows.

## Testing

Behaviour-driven (Given/When/Then) tests cover normalization, every query type,
the MCP protocol and end-to-end tool calls against the real datasets:

```bash
go test ./...
```

## Data sources & licenses

See the dataset attributions in [`TASK.md`](TASK.md). Datasets live under
`data/kaggle/` and are bundled for demo / non-commercial use.
