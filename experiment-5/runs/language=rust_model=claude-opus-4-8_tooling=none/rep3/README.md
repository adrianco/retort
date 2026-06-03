# Brazilian Soccer MCP Server (Rust)

A [Model Context Protocol](https://modelcontextprotocol.io) server, written in
Rust, that exposes a knowledge-graph–style query interface over the provided
Brazilian-soccer datasets. It lets an MCP-capable LLM answer natural-language
questions about matches, teams, players, competitions and aggregate statistics.

This implements the specification in
[`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md) /
[`TASK.md`](TASK.md).

## Quick start

```bash
# Build
cargo build --release

# Run the BDD test suite (Given/When/Then scenarios)
cargo test

# Smoke-test against the real CSVs without an MCP client
cargo run -- --selftest

# Run as an MCP stdio server (default data dir: ./data/kaggle)
cargo run --release
#   or point it at the data explicitly:
SOCCER_DATA_DIR=/path/to/data/kaggle cargo run --release
#   or:
cargo run --release -- /path/to/data/kaggle
```

The server speaks line-delimited JSON-RPC 2.0 over stdio (the standard MCP
stdio transport). All diagnostics go to **stderr** so they never corrupt the
JSON-RPC stream on stdout.

### Wiring into an MCP client

Add an entry like this to your client's MCP server configuration:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/abs/path/to/target/release/brazilian-soccer-mcp",
      "env": { "SOCCER_DATA_DIR": "/abs/path/to/data/kaggle" }
    }
  }
}
```

## Tools exposed

| Tool | Purpose | Key arguments |
|------|---------|---------------|
| `search_matches` | Find matches by team / opponent / competition / season / date range | `team`, `opponent`, `competition`, `season`, `date_from`, `date_to`, `limit` |
| `head_to_head` | Win/draw/goal record + recent meetings between two teams | `team_a`, `team_b` |
| `team_stats` | Aggregated record (W/D/L, goals, win rate), filterable | `team`, `season`, `competition`, `venue` (home/away/any) |
| `search_players` | Search FIFA players | `name`, `nationality`, `club`, `position`, `min_overall`, `limit` |
| `standings` | League table computed from match results (3pts win / 1 draw) | `season`, `competition` |
| `biggest_wins` | Largest-margin victories | `competition`, `season`, `limit` |
| `average_goals` | Avg goals/match, home/away win rates | `competition`, `season` |
| `data_summary` | Overview of everything loaded | — |

These cover all five required capability categories in the spec (Match, Team,
Player, Competition and Statistical-Analysis queries) and answer well over the
20 sample questions listed there. Example, calling `standings` for 2019:

```
Brasileirão 2019 standings (computed from matches):
 1. Flamengo-RJ - 90 pts (28W, 6D, 4L) GF 86 GA 37 (GD +49)
 2. Palmeiras-SP - 74 pts (21W, 11D, 6L) GF 61 GA 32 (GD +29)
 3. Santos-SP - 74 pts (22W, 8D, 8L) GF 60 GA 33 (GD +27)
 ...
```

## Architecture

The crate is split into a library (used by both the binary and the tests) and a
thin binary entry point. Every source file opens with a detailed context-block
comment describing its role.

```
src/
  model.rs      Domain types: Match, Player, Competition
  normalize.rs  Team-name + date normalization (the matching core)
  loader.rs     CSV parsers, one per source file
  store.rs      In-memory store + the query engine
  format.rs     Renders query results as human-readable answers
  mcp.rs        JSON-RPC 2.0 stdio MCP server + tool dispatch
  lib.rs        Library root wiring the modules together
  main.rs       Binary: load data, then serve over stdio (or --selftest)
tests/
  bdd.rs        Given/When/Then behaviour tests (fixture + real-data)
```

Pipeline: `loader` → `model` → `normalize` → `store` → `format` → `mcp`.

## Data-quality handling

The datasets are messy and overlapping; the spec calls this out explicitly. Key
decisions made to keep answers correct:

- **Team names keep their state/country suffix as identity.** `normalize_team`
  folds accents, lower-cases and unifies suffix punctuation but *keeps* the
  suffix, because `Atlético-MG` (Mineiro) and `Atlético-PR` (Paranaense) are
  **different clubs** — stripping the suffix would merge them and corrupt
  standings. Loose user queries still resolve: a bare `"Flamengo"` matches the
  key `flamengo-rj` via substring/base-name matching (`team_matches`).
- **Multiple date & score encodings** are normalized on load: ISO,
  ISO-with-time and Brazilian `DD/MM/YYYY` dates → canonical `YYYY-MM-DD`; goals
  given as ints, floats (`"1.0"`) or quoted strings are all parsed.
- **Cross-source de-duplication.** The five match files overlap heavily (the
  same Brasileirão game can appear in three of them). Exact-fixture duplicates
  (same date, base team names and score) are collapsed on load, taking the raw
  row count from ~23.8k down to ~19.6k. This stops head-to-head and statistics
  from double-counting.
- **Standings use a single, most-complete source per competition+season.**
  Because the overlapping files use slightly different names/dates that can't
  always be reconciled, a league table is computed from whichever source file
  most completely covers that season — guaranteeing exactly one row per fixture
  and a correct 20-team table (e.g. 2019 reproduces the spec's example exactly).
- **UTF-8 / Portuguese accents** are handled throughout.

## Testing

Tests follow BDD Given-When-Then structure (mirroring the Gherkin scenarios in
the spec). They run against a small deterministic in-memory fixture for exact
assertions, plus real-data smoke tests that load `data/kaggle/` when present and
verify the full pipeline (loaders, queries and MCP dispatch). The real-data
tests are skipped gracefully if the CSVs are absent.

```bash
cargo test          # 31 tests
cargo clippy        # clean
```

## Data sources & licenses

Datasets live in `data/kaggle/` (pre-downloaded; Kaggle requires an account):

| File | Source | License |
|------|--------|---------|
| `Brasileirao_Matches.csv` | [jogos-do-campeonato-brasileiro](https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro) | CC BY 4.0 |
| `Brazilian_Cup_Matches.csv` | same | CC BY 4.0 |
| `Libertadores_Matches.csv` | same | CC BY 4.0 |
| `BR-Football-Dataset.csv` | [brazilian-football-matches](https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches) | CC0 |
| `novo_campeonato_brasileiro.csv` | [campeonato-brasileiro-2003-a-2019](https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019) | CC BY 4.0 |
| `fifa_data.csv` | [fifa-players-data](https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data) | Apache 2.0 |

> Note: the FIFA snapshot does not license every Brazilian club (e.g. Flamengo
> is absent), and its Brazilian-league player names are anonymized — both are
> properties of the source data, not the server.
