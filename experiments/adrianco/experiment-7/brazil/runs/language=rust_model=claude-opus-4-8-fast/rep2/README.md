# Brazilian Soccer MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io) server, written in
Rust, that exposes a queryable knowledge interface over six Brazilian-soccer
datasets. It lets an LLM answer natural-language questions about matches, teams,
players, competitions, and aggregate statistics by calling well-typed tools.

This implements the specification in
[`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md) (mirrored in
`TASK.md`).

## What was built

* **In-memory data layer** (`src/data.rs`) that loads all six CSV files into a
  unified `Match` / `Player` model. Each file has a different schema, so every
  source gets its own tolerant loader (rows with unparseable scores are skipped
  rather than aborting the load). Goals stored as floats (`1.0`) and integers
  (`1`) are both handled.
* **Normalization + entity resolution** (`src/normalize.rs`):
  * Accent folding (`Grêmio` ≡ `Gremio`), case folding, and UTF-8 throughout.
  * Multiple date formats normalized to ISO `YYYY-MM-DD`
    (`2012-05-19 18:30:00`, `29/03/2003`, `2023-09-24`).
  * A **data-derived `Canonicalizer`** that resolves the same club spelled
    differently across sources (`Flamengo` / `Flamengo-RJ`,
    `Vasco` / `Vasco da Gama-RJ` / `Vasco Da Gama RJ`, `EC Bahia` / `Bahia-BA`)
    onto one identity — while keeping genuinely different clubs that share a
    stem apart (`Atlético-MG` vs `Athletico-PR`, `América-MG` vs `América-RN`).
    It keeps a trailing 2-letter state code only when a stem is ambiguous
    (appears with several states) *and* never appears in bare form.
* **Cross-source de-duplication**: the Brasileirão appears in three overlapping
  files; fixtures are de-duplicated by (date, canonical home, canonical away) so
  aggregates aren't inflated (~5,400 duplicate fixtures removed).
* **Query engine** (`src/queries.rs`) implementing the five capability
  categories from the spec, each returning ready-to-display text.
* **MCP server** (`src/mcp.rs`) speaking JSON-RPC 2.0 over newline-delimited
  stdio: `initialize`, `tools/list`, `tools/call`, `ping`, and notifications.

Every source file begins with a context block comment describing its role.

## Tools

| Tool | Purpose |
|------|---------|
| `search_matches` | Matches by team / opponent / competition / season (head-to-head appended when two teams given) |
| `team_stats` | W/D/L, goals for/against, win rate, optionally by season / competition / venue |
| `head_to_head` | Wins, draws and goals between two teams |
| `competition_standings` | League table for a season, calculated from results (3pts/win) |
| `league_statistics` | Avg goals/match, home/away win rate, draw rate |
| `biggest_wins` | Largest-margin victories matching a filter |
| `list_competitions` | Competitions with match counts and season ranges |
| `search_players` | FIFA players by name / nationality / club / position |

## Build & test

```sh
cargo build --release
cargo test            # 7 unit + 20 BDD (Given/When/Then) integration tests
```

The BDD suite (`tests/bdd.rs`) runs against the real CSVs in `data/kaggle/` and
mirrors the spec's Gherkin scenarios across all five capability categories plus
the MCP protocol layer.

## Running

The binary loads the data once and then serves MCP over stdio:

```sh
# Diagnostic summary (loads data, prints competitions, exits):
cargo run --release -- --check

# Run the MCP server (data dir defaults to ./data/kaggle):
cargo run --release
cargo run --release -- /path/to/data/kaggle      # or set BR_SOCCER_DATA_DIR
```

### Example MCP client session

```sh
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"competition_standings","arguments":{"competition":"Brasileirão","season":2019}}}' \
  | ./target/release/brazilian-soccer-mcp
```

### Connecting to an MCP client (e.g. Claude Desktop)

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

## Sample questions it can answer

Matches: *"Show me all Flamengo vs Fluminense matches"*, *"What matches did
Palmeiras play in 2019?"* · Teams: *"What is Corinthians' home record in 2022?"*,
*"Compare Palmeiras and Santos head-to-head"* · Competitions: *"Who won the 2019
Brasileirão?"*, *"What competitions are in the data?"* · Stats: *"What's the
average goals per match in the Brasileirão?"*, *"Show me the biggest wins"* ·
Players: *"Who is Neymar?"*, *"Find Brazilian players at Santos"*, *"Highest-rated
goalkeepers"*.

## Notes & limitations

* **Standings are calculated from match results** and clearly labelled as such.
  Because the three Brasileirão sources occasionally disagree on a fixture's
  exact calendar date (kickoff/timezone differences), a small fraction of
  fixtures survive de-duplication, so a season's match count can sit slightly
  above the official total. The champion and ordering remain correct (e.g. 2019
  → Flamengo).
* The **FIFA dataset (FIFA 19)** only licenses a subset of Brazilian clubs
  (Santos, Grêmio, Cruzeiro, Internacional, Fluminense, Botafogo, Bahia, the
  Atléticos, Chapecoense, etc.). Clubs such as Flamengo, Palmeiras, Corinthians
  and São Paulo are not in it, so player queries for those return no results —
  this reflects the source data, not a bug.

## Project layout

```
src/normalize.rs   accent/date normalization + Canonicalizer (entity resolution)
src/data.rs        CSV loaders, unified model, de-duplication
src/queries.rs     query engine (one method per capability)
src/mcp.rs         JSON-RPC 2.0 / MCP dispatch + stdio loop
src/main.rs        entry point (load data, serve stdio)
tests/bdd.rs       Given/When/Then integration tests
```

## Data sources & licenses

Kaggle data can't be downloaded without an account, so these (freely available,
with attribution) datasets are included under `data/kaggle/`:

* https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro
  — License: Attribution 4.0 International (CC BY 4.0)
  — `Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`, `Libertadores_Matches.csv`
* https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches
  — License: CC0 Public Domain — `BR-Football-Dataset.csv`
* https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019
  — License: Attribution 4.0 International (CC BY 4.0) — `novo_campeonato_brasileiro.csv`
* https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data
  — License: Apache 2.0 — `fifa_data.csv`

| File | Competition | Rows |
|------|-------------|------|
| `Brasileirao_Matches.csv` | Brasileirão Série A | 4,180 |
| `Brazilian_Cup_Matches.csv` | Copa do Brasil | 1,337 |
| `Libertadores_Matches.csv` | Copa Libertadores | 1,255 |
| `BR-Football-Dataset.csv` | Série A/B/C, Copa do Brasil (extended stats) | 10,296 |
| `novo_campeonato_brasileiro.csv` | Brasileirão Série A 2003–2019 | 6,886 |
| `fifa_data.csv` | FIFA player attributes | 18,207 |

This project is for demo / non-commercial use, per the specification.
