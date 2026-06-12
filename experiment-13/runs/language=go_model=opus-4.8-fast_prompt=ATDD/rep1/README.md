# Brazilian Soccer MCP Server

An [MCP](https://modelcontextprotocol.io) (Model Context Protocol) server, written
in Go, that answers natural-language questions about Brazilian soccer — matches,
teams, players, competitions and statistics — by querying the bundled Kaggle
datasets. It speaks JSON-RPC 2.0 over stdio, so any MCP-capable LLM client can
connect to it.

See `brazilian-soccer-mcp-guide.md` / `TASK.md` for the full specification.

## Quick start

```bash
# Build
go build -o bsmcp ./cmd/bsmcp

# Run the MCP server over stdio (reads CSVs from ./data/kaggle by default)
./bsmcp -data data
```

The process reads MCP/JSON-RPC requests from stdin and writes responses to
stdout. Example handshake + query:

```jsonc
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05"}}
{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}
{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"find_matches","arguments":{"team":"Flamengo","opponent":"Fluminense"}}}
```

To register with an MCP client (e.g. Claude Desktop), point it at the built
binary with `-data <path-to>/data`.

## Tools

Each tool returns a JSON document (as MCP text content) using problem-domain
field names. The seven tools cover every capability category in the spec:

| Tool | Purpose | Key arguments |
|------|---------|---------------|
| `find_matches` | Find matches by team, opponent, competition, season, venue or date range. Returns a head-to-head summary when two teams are given. | `team`, `opponent`, `competition`, `season`, `venue` (home/away/either), `start_date`, `end_date`, `limit` |
| `get_team_stats` | A team's W/D/L record, goals for/against, points and win rate. | `team` (required), `competition`, `season`, `venue` |
| `head_to_head` | Compare two teams across all competitions. | `team_a`, `team_b` |
| `search_players` | Search FIFA players by name, nationality, club or position (sorted by rating). | `name`, `nationality`, `club`, `position`, `limit` |
| `get_standings` | League table for a competition + season, calculated from results (position 1 = champion). | `competition`, `season` |
| `league_stats` | Aggregate stats: total goals, avg goals/match, home/away/draw split, home-win rate, biggest wins. | `competition`, `season` |
| `team_rankings` | Rank teams by a metric (`goals_for`, `goals_against`, `wins`, `points`, `win_rate`, …), optionally by venue — e.g. "best home/away record". | `competition`, `season`, `metric`, `venue`, `limit` |

Competitions are normalised to `Brasileirao`, `Copa do Brasil`, `Libertadores`
(plus `Serie B`/`Serie C` where present).

## Design notes

The implementation directly addresses the spec's data-quality challenges:

- **Team-name variations** — names are normalised (accent-folded, lower-cased,
  state/country suffixes stripped) into a matching key, so `"Flamengo"`,
  `"Flamengo-RJ"` and `"Grêmio"`/`"Gremio"` all resolve consistently. The state
  suffix is *retained in the identity key* so genuinely different clubs that
  share a base name (Atlético-MG vs Atlético-GO vs Athletico-PR) stay distinct,
  and display names are disambiguated as `Atletico (MG)` only when needed.
- **Date formats** — ISO (`2023-09-24`), datetime (`2012-05-19 18:30:00`) and
  Brazilian (`29/03/2003`) formats are all parsed.
- **UTF-8 / accents** — handled throughout; searches are accent-insensitive.
- **Overlapping datasets** — several files cover the same Brasileirão seasons.
  To avoid double-counting, a single authoritative source is used per
  (competition, season), chosen by file priority. Seasons a higher-priority file
  does not cover still load from the others (e.g. pre-2012 Brasileirão from the
  historical file, and Serie B/C from the extended dataset). This yields correct
  tables — e.g. the 2019 Brasileirão computes as Flamengo champion, 90 pts,
  20 teams, 38 games each, matching reality.

### Architecture

```
cmd/bsmcp/main.go      – binary entry point (stdio transport)
app.go, tools.go       – wires the data Store to the seven MCP tools
internal/mcp/          – minimal JSON-RPC 2.0 / MCP protocol server
internal/store/        – CSV loaders, team/date normalisation, query engine
acceptance_test.go     – executable acceptance spec (drives the server via MCP)
e2e_test.go            – end-to-end test over the real compiled binary + stdio
internal/store/*_test  – unit tests for the internals
```

### Development methodology

Built with executable Acceptance Test-Driven Development. `acceptance_test.go`
is an executable specification: every requirement is a scenario driven purely
through the public MCP protocol (initialize → `tools/call`), each starting from a
fresh server seeded with its own controlled fixture CSVs, asserting on *what* the
system reports in domain language. Finer-grained unit tests under
`internal/store` drove the internals.

```bash
go test ./...            # all tests
go test -race ./...      # with the race detector
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
