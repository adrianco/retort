# Brazilian Soccer MCP Server

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server,
written in Go, that answers natural-language questions about Brazilian soccer —
players, teams, matches, competitions and statistics — over the bundled Kaggle
datasets. It implements the specification in
[`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md) /
[`TASK.md`](TASK.md).

The server loads all six CSV datasets into an in-memory **knowledge graph** at
startup and speaks the MCP **stdio transport** (newline-delimited JSON-RPC 2.0)
so it can be plugged into any MCP-compatible LLM client. It has **no external
dependencies** (standard library only) and **no database** to run — it is a
single self-contained binary.

---

## Quick start

```bash
# Build
go build -o brazilian-soccer-mcp .

# Run (auto-detects ./data/kaggle, or pass -data)
./brazilian-soccer-mcp
./brazilian-soccer-mcp -data /path/to/data/kaggle
```

Diagnostics (dataset load summary, "ready" banner) are written to **stderr** so
they never corrupt the JSON-RPC stream on stdout.

### Talking to it directly

The transport is line-delimited JSON-RPC, so you can drive it from a shell:

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"standings","arguments":{"season":2019,"limit":5}}}' \
  | ./brazilian-soccer-mcp
```

### Registering with an MCP client (e.g. Claude Desktop)

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

---

## Tools

| Tool | Purpose | Key arguments |
|------|---------|---------------|
| `search_matches` | Find matches by team, opponent, competition, season, date range | `team`, `opponent`, `competition`, `season`, `date_from`, `date_to`, `limit` |
| `head_to_head` | All-competition head-to-head record between two teams | `team_a`, `team_b`, `limit` |
| `team_stats` | A team's W/D/L, goals and win rate (optionally home/away) | `team`, `season`, `competition`, `venue` |
| `standings` | League table computed from match results | `competition`, `season`, `limit` |
| `search_players` | FIFA players by name, nationality, club, position, rating | `name`, `nationality`, `club`, `position`, `min_overall`, `limit` |
| `competition_stats` | Aggregate stats: avg goals, home-win rate, biggest wins | `competition`, `season`, `top_wins` |
| `list_metadata` | Discover available teams, competitions and seasons | – |

These cover all five required capability categories in the spec: match,
team, player, competition and statistical-analysis queries.

### Example: 2019 Brasileirão standings

```
2019 Brasileirão Série A Final Standings (calculated from matches):
1. Flamengo - 90 pts (28W, 6D, 4L, GD +49) - Champion
2. Santos - 74 pts (22W, 8D, 8L, GD +27)
3. Palmeiras - 74 pts (21W, 11D, 6L, GD +29)
...
20. Avaí - 20 pts (3W, 11D, 24L, GD -44)
```

(Matches the historical result and the figure cited in the specification.)

---

## How the data is handled

The datasets are messy and overlapping; the loader normalizes them into one
coherent graph. The non-obvious parts:

- **Team-name normalization.** Names appear with state suffixes
  (`Palmeiras-SP`), without (`Palmeiras`), accented (`São Paulo`) and
  unaccented (`Sao Paulo`). A canonical key (accent-, suffix- and
  punctuation-stripped) unifies these.
- **Ambiguous clubs.** Some abbreviations denote *different* clubs by state —
  `Atletico-MG`, `Atletico-GO`, `Atletico-PR`. The loader detects bases that
  occur with several states (each above a noise threshold) and keeps the state
  as part of the identity for those, while leaving unique clubs (`Flamengo`)
  un-suffixed. This prevents distinct clubs from being merged in standings.
- **Overlapping datasets / no double counting.** Several files cover the same
  fixtures (`Brasileirao_Matches.csv`, `novo_campeonato_brasileiro.csv` and
  `BR-Football-Dataset.csv` all include Brasileirão 2019). Matches are
  fixture-deduplicated, and a **source-priority "primary" set** picks one
  authoritative source per (competition, season) so aggregate statistics and
  standings are computed exactly once. (A full Brasileirão season correctly
  yields 380 matches / 38 games per team.)
- **Multiple date formats.** ISO (`2023-09-24`), with time
  (`2012-05-19 18:30:00`) and Brazilian (`29/03/2003`) are all parsed.
- **UTF-8.** Portuguese accents and the FIFA file's byte-order mark are handled.

---

## Project layout

```
main.go                      # entry point: load data, serve MCP over stdio
internal/soccer/             # knowledge graph + query layer (no I/O beyond CSV)
  model.go                   #   Match / Player domain types
  normalize.go               #   team-name + date normalization
  loader.go                  #   CSV loaders for all six datasets
  graph.go                   #   in-memory graph, dedup, ambiguity, primary set
  queries.go                 #   match/team/player/competition queries
  format.go                  #   spec answer-format rendering
  datadir.go                 #   locate data/kaggle
internal/mcp/                # MCP JSON-RPC server
  protocol.go                #   JSON-RPC + MCP envelope types
  server.go                  #   stdio dispatch loop
  tools.go                   #   tool catalog + dispatch to queries
```

Every source file begins with a context comment describing its role.

---

## Testing

Tests follow a BDD **Given/When/Then** style and run against the real bundled
datasets.

```bash
go test ./...
```

Coverage includes:

- **Normalization** — suffix/accent unification, state extraction, all date
  formats.
- **Query layer** — match search (including two-team and competition/season
  filters), head-to-head consistency, team records, the 2019 standings (20
  teams × 38 games, Flamengo champion on 90 pts), distinct-Atléticos
  non-merging, player search by name/nationality/club, competition statistics
  and the no-double-counting invariant.
- **MCP protocol** — `initialize` handshake, notification handling, `tools/list`,
  `tools/call` for several tools, and error handling for unknown
  methods/tools.

---

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
