# Brazilian Soccer MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io) server, written in
Rust, that exposes a knowledge-graph query interface over the provided Brazilian
soccer datasets. An LLM connects to it over stdio and can answer natural-language
questions about matches, teams, players, competitions and statistics by calling
the server's tools.

This implements the specification in
[`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md) (identical to
`TASK.md`).

---

## What was built

A self-contained Rust crate (no database server, no network dependency) that:

1. **Loads all six CSV datasets** at startup into an in-memory knowledge graph
   (~16,000 de-duplicated matches and 18,207 players).
2. **Normalizes the messy data** — team-name variants, multiple date formats and
   UTF-8 Portuguese text — so the same club is recognised across files.
3. **Answers the five query categories** from the spec (match, team, player,
   competition and statistical queries) through nine MCP tools.
4. **Computes aggregates on demand** — league standings, head-to-head records,
   win/loss/goal statistics — directly from match results.

The 2019 Brasileirão standings produced by the server match the historical
record exactly (Flamengo champion, 90 pts, 28W–6D–4L; Santos and Palmeiras on
74), which is used as a correctness check in the test suite.

### Architecture

```
normalize  →  model  →  loader  →  db (query engine)  →  mcp (JSON-RPC)  →  main (stdio)
```

| File | Responsibility |
|------|----------------|
| `src/normalize.rs` | Team-name canonicalisation, accent stripping, date-independent matching keys |
| `src/model.rs`     | Core types: `Match`, `Player`, `Outcome` |
| `src/loader.rs`    | One tolerant parser per CSV schema; date/number normalisation |
| `src/db.rs`        | In-memory graph + query engine (matches, records, standings, stats, player search) |
| `src/mcp.rs`       | MCP/JSON-RPC 2.0 protocol and tool definitions; formats human-readable answers |
| `src/main.rs`      | Loads data, runs the stdio JSON-RPC loop |
| `tests/`           | Unit tests (per module) + `tests/integration.rs` against the real datasets |

Every source file opens with a context block comment describing its role.

---

## Building and running

```bash
# Build
cargo build --release

# Quick self-test: load the data and print a competition summary
cargo run --release -- --selftest

# Run as an MCP server over stdio (default data dir: ./data/kaggle)
cargo run --release
# or with an explicit data directory:
cargo run --release -- /path/to/data/kaggle
```

Diagnostics are written to **stderr**; the JSON-RPC protocol uses **stdout**
only, so the streams never interfere.

### Connecting an MCP client

Example client configuration (e.g. Claude Desktop `mcpServers` block):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/absolute/path/to/target/release/brazilian-soccer-mcp",
      "args": ["/absolute/path/to/data/kaggle"]
    }
  }
}
```

### Talking to it by hand

The server reads one JSON-RPC request per line and writes one response per line:

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"standings","arguments":{"season":2019,"limit":5}}}' \
  | cargo run --release 2>/dev/null
```

---

## Tools

| Tool | Purpose | Key arguments |
|------|---------|---------------|
| `find_matches` | List matches by team, opponent, competition, season or date range (newest first); adds head-to-head when two teams are given | `team`, `opponent`, `competition`, `season`, `date_from`, `date_to`, `venue`, `limit` |
| `head_to_head` | All-time record between two teams | `team_a`, `team_b` |
| `team_record` | Win/draw/loss + goals, optionally by season/competition/venue | `team`, `season`, `competition`, `venue` |
| `standings` | League table for a competition + season, computed from results | `competition`, `season`, `limit` |
| `search_players` | FIFA player search by name/nationality/club/position/rating | `name`, `nationality`, `club`, `position`, `min_overall`, `limit` |
| `league_stats` | Avg goals per match, home/away win rates over a scope | `competition`, `season`, `team` |
| `biggest_wins` | Largest-margin victories in a scope | `competition`, `season`, `team`, `limit` |
| `team_competitions` | Which competitions a team appears in, with counts | `team` |
| `list_competitions` | All loaded competitions, season ranges and match counts | — |

Team names are matched leniently: `"Palmeiras"`, `"Palmeiras-SP"`,
`"São Paulo"`, `"Sao Paulo"` and `"Atletico Mineiro"` all resolve correctly.

### Example answers

```
Brasileirão Série A 2019 Final Standings (calculated from matches):
 1. Flamengo - 90 pts (28W, 6D, 4L), GF 86 GA 37 (GD +49)
 2. Palmeiras - 74 pts (21W, 11D, 6L), GF 61 GA 32 (GD +29)
 3. Santos - 74 pts (22W, 8D, 8L), GF 60 GA 33 (GD +27)
 ...

Palmeiras vs Santos — head-to-head (40 matches):
- Palmeiras wins: 17
- Santos wins: 15
- Draws: 8
- Goals: Palmeiras 58 - 52 Santos
```

---

## Data handling decisions

The datasets overlap and use inconsistent conventions. The notable choices:

- **Team-name normalisation.** Names are reduced to an accent-free, lower-case
  matching key. A trailing state code is dropped for unambiguous clubs
  (`Flamengo-RJ` → `flamengo`) but **kept** for clubs that share a name across
  states (`Atlético-MG`, `Atlético-GO` and `Atlético-PR` stay distinct, since
  they play in the same season). Long-form spellings used by one dataset are
  reconciled with the short forms used by another via a small alias table
  (`"Atletico Mineiro"` = `"Atletico-MG"`, `"Vasco Da Gama RJ"` = `"Vasco"`).

- **Cross-file de-duplication.** The Série A and Copa do Brasil seasons appear in
  several files. Matches are de-duplicated by competition, season, date, teams
  and score, so a standings query counts each fixture once. The authoritative
  dedicated files are used for Série A and Copa do Brasil; `BR-Football-Dataset.csv`
  contributes the divisions unique to it — **Série B** and **Série C** — along
  with the extended shot/corner statistics it carries.

- **Dates.** ISO (`2012-05-19 18:30:00`), date-only (`2023-09-24`) and Brazilian
  (`29/03/2003`) formats are all normalised to `YYYY-MM-DD`.

- **Tolerant loading.** A malformed row is skipped rather than aborting the
  import; a missing file is reported but does not stop the server.

> **Note on the FIFA player data:** this is a FIFA 19-era export. It contains
> many Brazilian players and several Brazilian clubs (Santos, Grêmio,
> Internacional, Cruzeiro, Atlético Mineiro, …) but, due to licensing, omits some
> big clubs (e.g. Flamengo, Palmeiras) and players. Searches for absent
> entries correctly return "No players found".

---

## Testing

```bash
cargo test
```

28 tests cover normalisation, date/number parsing, the query engine and the MCP
protocol. The integration tests run against the real datasets in `data/kaggle`
and assert known facts (2019 champion, derby head-to-heads, top Brazilian
players, realistic goal averages). If the data directory is absent, the
data-dependent tests skip gracefully so the suite still builds and runs
anywhere.

`cargo clippy` is clean (no warnings).

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
