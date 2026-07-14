# Brazilian Soccer MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io) server, written in
Rust, that provides a natural-language-friendly knowledge interface over
Brazilian soccer datasets (matches, teams, players, competitions and aggregate
statistics). It loads the provided Kaggle CSV files into memory and exposes a
set of MCP tools that an LLM client can call to answer questions.

The specification implemented here is in
[`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md) /
[`TASK.md`](TASK.md).

## Quick start

```bash
# Build
cargo build --release

# Run the test suite (BDD-style Given/When/Then scenarios over the real data)
cargo test

# Print answers to a batch of sample questions
cargo run --release -- selftest

# Run one tool directly from the CLI
cargo run --release -- call standings '{"season":2019}'
cargo run --release -- call search_players '{"name":"Neymar"}'

# Run as an MCP server on stdio (default with no arguments)
cargo run --release
```

By default the data is read from `data/kaggle/`. Override with the
`SOCCER_DATA_DIR` environment variable.

## Using it as an MCP server

The binary speaks JSON-RPC 2.0 over stdio using newline-delimited messages
(the MCP stdio transport). Register it with any MCP-capable client, e.g. for
Claude Desktop / Claude Code `mcpServers` config:

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

It implements `initialize`, `tools/list`, `tools/call` and `ping`.

## Tools

| Tool | Purpose |
|------|---------|
| `search_matches` | Find matches by team, opponent, competition, season and date range. With two teams, adds a head-to-head summary. |
| `head_to_head` | Head-to-head record and recent meetings between two teams. |
| `team_stats` | Win/draw/loss record, goals for/against, points and win rate, filterable by season, competition and venue (home/away/all). |
| `standings` | League table for a season, computed from match results (3pts win / 1pt draw, Brazilian tiebreakers). |
| `competition_stats` | Average goals per match, home/draw/away win rates, biggest victories, top scoring teams. |
| `search_players` | Search FIFA players by name, nationality, club, position and minimum rating. |
| `top_players` | Highest-rated players for a nationality/club/position, plus a per-club breakdown. |
| `list_datasets` | Summary of loaded datasets and row counts. |

### Example

`standings {"season": 2019}` →

```
2019 Brasileirão Série A standings (calculated from 380 matches):
 1. Flamengo - 90 pts (28W 6D 4L, GF 86 GA 37 GD +49) - Champion
 2. Santos - 74 pts (22W 8D 8L, GF 60 GA 33 GD +27)
 3. Palmeiras - 74 pts (21W 11D 6L, GF 61 GA 32 GD +29)
 ...
```

(This matches the real-world 2019 Brasileirão final table.)

## How it works

### Data unification
Five match CSVs with different schemas (Brasileirão, Copa do Brasil,
Libertadores, the 2003–2019 historical set, and an extended-stats set) are
parsed into a single `Match` model, and the FIFA CSV into a `Player` model.
Dates are normalized to ISO `YYYY-MM-DD` from the three encodings present
(ISO, ISO-with-time, and Brazilian `DD/MM/YYYY`). Everything is UTF-8.

### Team name normalization (`src/normalize.rs`)
The datasets name the same club many ways: `Palmeiras-SP`, `Palmeiras`,
`São Paulo` vs `Sao Paulo`, `Vasco Da Gama RJ` vs `Vasco da Gama-RJ`,
`Nacional (URU)`. Naively stripping the state suffix is wrong because some
clubs are *only* distinguished by it — `Atlético-MG` (Mineiro) and
`Athletico-PR` (Paranaense) are different clubs. So each name is resolved
through a curated alias table to a canonical club, with a suffix-preserving
fallback for clubs outside the table.

### De-duplication
The same real match appears in several files. Because the extended-stats file
records some matches a day off (timezone shift), matches are de-duplicated on
`competition + season + home + away + score` (not date), which merges
duplicates without collapsing the home and away legs of a fixture. This is what
makes the computed standings exact.

## Data limitations (honest notes)
- The FIFA 19 player dataset omits several big Brazilian clubs that were
  unlicensed at the time (Flamengo, Palmeiras, Corinthians, São Paulo), so
  player searches for those clubs / their players (e.g. Gabriel Barbosa) return
  no results. Santos, Grêmio, Internacional, Cruzeiro, etc. are present.
- The extended-stats file also covers Série B/C; the `Brasileirão` competition
  filter resolves to Série A unless you ask for `Série B`/`Série C` explicitly.

## Project layout
```
src/
  main.rs        CLI entry: stdio server (default), `selftest`, `call <tool>`
  lib.rs         library crate root
  mcp.rs         JSON-RPC 2.0 / MCP transport and tool dispatch + schemas
  data.rs        CSV loading and the in-memory Dataset (+ dedup)
  model.rs       Match and Player data structures
  normalize.rs   team/club canonicalization and competition resolution
  queries.rs     all query/analysis functions (formatted answers)
tests/
  bdd.rs         Given/When/Then behaviour tests over the real datasets
```

## Data Sources

Kaggle data can't be downloaded without an account, so these freely available
(with attribution) datasets are included under `data/kaggle/`:

https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro
- License: Attribution 4.0 International (CC BY 4.0)
- `data/kaggle/Brasileirao_Matches.csv`
- `data/kaggle/Brazilian_Cup_Matches.csv`
- `data/kaggle/Libertadores_Matches.csv`

https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches
- License: CC0 Public Domain
- `data/kaggle/BR-Football-Dataset.csv`

https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019
- License: Attribution 4.0 International (CC BY 4.0)
- `data/kaggle/novo_campeonato_brasileiro.csv`

https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data
- License: Apache 2.0
- `data/kaggle/fifa_data.csv`
