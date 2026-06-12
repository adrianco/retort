# Brazilian Soccer MCP Server

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server, written in Go,
that exposes a knowledge graph over Brazilian soccer datasets (matches, teams, players, and
competitions) as a set of tools an LLM can call to answer natural-language questions.

It implements the specification in [`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md)
(also in [`TASK.md`](TASK.md)).

## What it does

The server loads the six provided Kaggle CSV datasets at start-up, unifies them into a single
in-memory model of matches and players, and answers domain queries over the standard MCP
JSON-RPC interface (`initialize`, `tools/list`, `tools/call`) on the stdio transport.

### Tools

| Tool | Purpose | Key arguments |
|------|---------|---------------|
| `find_matches` | Find matches by team, opponent, competition, season, or date range; reports head-to-head when two teams are given | `team`, `opponent`, `home_team`, `away_team`, `competition`, `season`, `start_date`, `end_date`, `limit` |
| `get_team_stats` | A team's record: wins/draws/losses, goals for/against, win rate; filterable by competition, season, and venue | `team`, `competition`, `season`, `venue` (`home`/`away`/`all`) |
| `compare_teams` | Head-to-head between two teams with the list of matches | `team1`, `team2` |
| `search_players` | Search FIFA players by name, nationality, club, or position, sorted by overall rating | `name`, `nationality`, `club`, `position`, `min_overall`, `limit` |
| `get_standings` | League table calculated from match results (3 pts win, 1 pt draw) | `competition`, `season` |
| `league_statistics` | Aggregate stats: matches, avg goals/match, home win rate, biggest victories | `competition`, `season` |

These cover the five capability categories in the spec: match, team, player, competition, and
statistical-analysis queries.

## Running

```bash
go build -o brazilian-soccer-mcp .
./brazilian-soccer-mcp -data data/kaggle
```

The server speaks newline-delimited JSON-RPC 2.0 on stdin/stdout (the MCP stdio transport);
all logs go to stderr. `-data` defaults to `data/kaggle`.

### Example session

```jsonc
// → request
{"jsonrpc":"2.0","id":1,"method":"initialize"}
{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"get_standings","arguments":{"competition":"Brasileirão","season":2019}}}
```

```
1. Flamengo-RJ - 100 pts (31W, 7D, 4L, GF 99, GA 44, GD +55) - Champion
2. Palmeiras-SP - 82 pts (23W, 13D, 6L, GF 66, GA 35, GD +31)
3. Santos-SP - 81 pts (24W, 9D, 9L, GF 65, GA 35, GD +30)
...
```

To wire it into an MCP-capable client (e.g. Claude Desktop), register it as a stdio server
running the built binary with `-data` pointing at this repo's `data/kaggle`.

## Design

```
main.go            stdio JSON-RPC loop (transport)
mcp/               MCP protocol: JSON-RPC types, server dispatch, tool definitions
  protocol.go      wire types and error codes
  server.go        Server.Handle — the single request→response entry point
  tools.go         the six tools and their domain-language formatting
  schema.go        input-schema helpers and tolerant argument extraction
soccer/            the domain (no MCP knowledge)
  model.go         Match/Player types; team-name normalization
  load.go          per-file CSV loaders + dedup
  store.go         in-memory store and all domain queries
acceptance/        black-box acceptance tests (drive the server via JSON-RPC only)
```

### Data handling

The datasets disagree on naming, dates, and encoding; the loaders reconcile them:

- **Team names** — A trailing state/country code (`Palmeiras-SP`, `Nacional (URU)`, `América - MG`)
  is parsed off and, when a dataset instead carries the state in its own column, re-attached, so
  the same club resolves to one canonical identity (`Flamengo` + state `RJ` ≡ `Flamengo-RJ`).
  Crucially the code is **kept** in the identity, so distinct clubs that share a base name
  (`Atlético-MG` vs `Atlético-PR`) are not merged. User queries remain forgiving: matching is
  accent- and suffix-insensitive, so "Sao Paulo" finds "São Paulo-SP".
- **Dates** — ISO (`2023-09-24`), ISO+time (`2012-05-19 18:30:00`), and Brazilian `DD/MM/YYYY`
  are all parsed; output is normalized to ISO.
- **Encoding** — UTF-8 throughout, including stripping a leading byte-order mark from headers.
- **Deduplication** — The same fixture appears in more than one source file. Since within a
  competition and season an ordered (home, away) pairing occurs at most once, that tuple is used
  to drop cross-file duplicates so standings and statistics aren't double-counted.

### Known data-quality limitation

The two Brasileirão sources occasionally record the *same* fixture with home and away swapped or
on conflicting dates. Those few cases survive deduplication, so a calculated season can show a
handful of games more than the real 38-round total. Champions and overall ordering remain
correct; this is inherent to merging overlapping community datasets and is surfaced rather than
hidden.

## Development & tests

Built with the Go standard library only — no external dependencies.

```bash
go test ./...
```

The work followed **Acceptance Test-Driven Development**: every requirement in the spec was first
captured as an executable acceptance test that drives the system *only* through the public MCP
protocol (no back-door access to internals), and the implementation was written until those tests
passed, with finer-grained unit tests underneath.

- `acceptance/acceptance_test.go` — scenario tests, each starting a fresh server over its own
  isolated fixture data (atomic and independent), asserting on answers in domain language.
- `acceptance/realdata_test.go` — the same protocol exercised against the full real datasets,
  proving all six files load and concrete sample questions are answered.
- `main_test.go` — end-to-end round-trip over the actual stdio transport.
- `soccer/soccer_test.go` — unit tests for normalization, date parsing, and each query.

## Data Sources

Kaggle data can't be downloaded without an account, so these (freely available with attribution)
datasets are included under `data/kaggle/`:

https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro
- License: Attribution 4.0 International (CC BY 4.0)
- `data/kaggle/Brasileirao_Matches.csv`
- `data/kaggle/Brazilian_Cup_Matches.csv`
- `data/kaggle/Libertadores_Matches.csv`

https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches
- License: CC0: Public Domain
- `data/kaggle/BR-Football-Dataset.csv`

https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019
- License: World Bank - Attribution 4.0 International (CC BY 4.0)
- `data/kaggle/novo_campeonato_brasileiro.csv`

https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data
- License: Apache 2.0
- `data/kaggle/fifa_data.csv`
