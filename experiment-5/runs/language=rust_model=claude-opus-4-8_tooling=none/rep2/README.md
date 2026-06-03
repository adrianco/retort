# Brazilian Soccer MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io) (MCP) server, written
in Rust, that exposes a knowledge graph over six Brazilian-soccer datasets so an
LLM can answer natural-language questions about matches, teams, players,
competitions and statistics.

It implements the specification in [`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md)
/ [`TASK.md`](TASK.md).

## Quick start

```bash
# Build (uses only serde, serde_json and csv)
cargo build --release

# Run the MCP server (reads ./data/kaggle, speaks JSON-RPC 2.0 over stdio)
./target/release/brazilian-soccer-mcp

# Smoke-test without an MCP client: loads the data and prints sample answers
./target/release/brazilian-soccer-mcp --self-test

# Run the BDD + unit test suite
cargo test
```

The data directory defaults to `./data/kaggle` and can be overridden with the
`SOCCER_DATA_DIR` environment variable.

## Connecting to an MCP client

The server uses the standard MCP **stdio transport**: newline-delimited JSON-RPC
2.0 messages on stdin/stdout (all logging goes to stderr). Example client config:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/absolute/path/to/target/release/brazilian-soccer-mcp",
      "env": { "SOCCER_DATA_DIR": "/absolute/path/to/data/kaggle" }
    }
  }
}
```

It responds to `initialize`, `tools/list`, `tools/call`, `ping` and the
`notifications/initialized` notification.

## Tools

| Tool | Purpose | Key arguments |
|------|---------|---------------|
| `search_matches` | Find matches by team / opponent / competition / season / venue / date range | `team`, `opponent`, `competition`, `season`, `venue`, `date_from`, `date_to`, `include_extended`, `limit` |
| `head_to_head` | Match list + W/D/L record between two teams | `team_a`, `team_b` |
| `team_record` | W/D/L, goals, points and win-rate for a team | `team`, `season`, `competition`, `venue` |
| `standings` | League table calculated from results (3pts/win) | `season` (required), `competition` |
| `search_players` | FIFA players by name / nationality / club / position / rating | `name`, `nationality`, `club`, `position`, `min_overall`, `limit` |
| `player_profile` | Detailed profile for the best name match ("Who is X?") | `name` |
| `competition_stats` | Aggregate stats: avg goals, home/away/draw rates, biggest wins | `competition`, `season` |
| `players_by_club` | Players of a nationality grouped by club | `nationality`, `min_overall` |

These cover all five capability areas in the spec (match, team, player and
competition queries plus statistical analysis) and answer the 20+ sample
questions.

Example — the calculated 2019 Brasileirão table reproduces the real result:

```
2019 Brasileirão Final Standings (calculated from matches):
 1. Flamengo-RJ  - 90 pts (28W, 6D, 4L) - Champion
 2. Palmeiras-SP - 74 pts (21W, 11D, 6L)
 3. Santos-SP    - 74 pts (22W, 8D, 8L)
 ...
```

## Architecture

The crate is split into a library (exercised by the tests) and a thin binary:

| Module | Responsibility |
|--------|----------------|
| `src/normalize.rs` | Team-name canonicalization, multi-format date parsing, goal parsing, competition aliasing |
| `src/models.rs` | `Match` and `Player` domain types |
| `src/data.rs` | CSV loaders → in-memory `Database`; overlap resolution |
| `src/query.rs` | Pure analytical functions (search, records, standings, stats) |
| `src/format.rs` | Render results into the spec's text answer formats |
| `src/mcp.rs` | JSON-RPC 2.0 / MCP protocol surface and tool catalog |
| `src/main.rs` | Loads data once, runs the stdio transport loop |

## Data handling notes

The provided datasets are messy and overlapping; the implementation addresses
each of the spec's "Data Quality Notes":

- **Team-name variations** — names are folded (accents removed), lower-cased and
  reduced to alphanumeric tokens. The state/country code is **kept as a token**
  (`atletico mg` ≠ `atletico go`) so genuinely different clubs that share a base
  name are not conflated, while a bare query like "Flamengo" still matches
  "Flamengo-RJ" via substring matching.
- **Date formats** — ISO (`2023-09-24`), ISO+time (`2012-05-19 18:30:00`) and
  Brazilian (`29/03/2003`) are all parsed.
- **UTF-8 / encoding** — Portuguese accents and the BOM on `fifa_data.csv` are
  handled.
- **Overlapping sources** — Brasileirão seasons 2012–2019 appear in both
  `Brasileirao_Matches.csv` and `novo_campeonato_brasileiro.csv` (and again as
  "Serie A" in `BR-Football-Dataset.csv`). The two curated files disagree on a
  few spellings and kickoff dates, so they cannot be merged row-by-row. At load
  time each `(competition, season)` is assigned to a single authoritative
  source (most complete, curated over historical), which yields exact league
  tables (e.g. 2019 = 20 clubs × 38 games).
- **Extended dataset** — `BR-Football-Dataset.csv` overlaps the curated files
  with divergent dates/scores/names, so it is **searchable** (via
  `include_extended`) but excluded from aggregates by default to avoid
  double-counting.

## Testing

`cargo test` runs:

- **Unit tests** (`src/normalize.rs`) for normalization, date/goal parsing and
  competition aliasing.
- **BDD scenarios** (`tests/bdd.rs`) in Given/When/Then style against the real
  datasets, covering match/team/player/competition/statistical queries, data-
  quality handling and the MCP protocol handshake + tool calls.

All queries run well within the spec's performance budget (full load + queries
complete in well under a second).

## Data sources

Pre-downloaded Kaggle datasets in `data/kaggle/` (see attributions below):

| File | Description | License |
|------|-------------|---------|
| `Brasileirao_Matches.csv` | Brasileirão Série A (2012–2022) | CC BY 4.0 |
| `Brazilian_Cup_Matches.csv` | Copa do Brasil | CC BY 4.0 |
| `Libertadores_Matches.csv` | Copa Libertadores | CC BY 4.0 |
| `BR-Football-Dataset.csv` | Extended match stats (Serie A/B/C, Copa) | CC0 |
| `novo_campeonato_brasileiro.csv` | Historical Brasileirão (2003–2019) | CC BY 4.0 |
| `fifa_data.csv` | FIFA player database (~18k players) | Apache 2.0 |

- https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro (CC BY 4.0)
- https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches (CC0)
- https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019 (CC BY 4.0)
- https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data (Apache 2.0)
