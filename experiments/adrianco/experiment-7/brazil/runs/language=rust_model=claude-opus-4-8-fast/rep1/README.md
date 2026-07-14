# Brazilian Soccer MCP Server (Rust)

A [Model Context Protocol](https://modelcontextprotocol.io) server, written in
Rust, that exposes a natural-language-friendly query interface over a collection
of Brazilian soccer datasets (matches, competitions and FIFA players). It speaks
JSON-RPC 2.0 over stdio and can be connected to any MCP-compatible LLM client.

The full requirements are in [`TASK.md`](TASK.md) /
[`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md).

## What was built

- **Unified data loader** (`src/data.rs`) that ingests all six CSV files into a
  single in-memory model, reconciling their different schemas, column orders,
  date formats (`2023-09-24`, `2012-05-19 18:30:00`, `29/03/2003`) and encodings.
- **Team-name normalization** (`src/normalize.rs`) that reconciles the many
  naming conventions in the data — state suffixes (`Palmeiras-SP`), country codes
  (`Nacional (URU)`), accents (`São Paulo`, `Grêmio`) and spelling variants
  (`Athletico`/`Atletico Paranaense`).
- **Canonical match set**: Série A is covered by three overlapping datasets with
  incompatible naming. Rather than merge them (which double-counts fixtures),
  the loader keeps the single most-complete source per *(competition, season)*,
  giving correct counts and consistent club names. As a check, the computed 2019
  Brasileirão table reproduces the real result exactly (Flamengo 90 pts, 28-6-4).
- **Query engine** (`src/queries.rs`): match search, team records, head-to-head,
  player search, league standings computed from results, and aggregate stats.
- **MCP protocol layer** (`src/mcp.rs`) + **tool surface** (`src/tools.rs`).

Every source file opens with a context block comment describing its role.

## Tools exposed

| Tool | Answers questions like |
|------|------------------------|
| `search_matches` | "Show me all Flamengo vs Fluminense matches", "What matches did Palmeiras play in 2019?" |
| `team_stats` | "What is Corinthians' home record in 2022?" |
| `head_to_head` | "Compare Palmeiras and Santos head-to-head" |
| `search_players` | "Find all Brazilian players", "Highest-rated players at a club" |
| `competition_standings` | "Who won the 2019 Brasileirão?" |
| `competition_stats` | "Average goals per match?", "Biggest wins in the dataset" |
| `list_competitions` | "What competitions and seasons are available?" |

## Build & test

```sh
cargo build --release      # build
cargo test                 # 30 unit + BDD (Given/When/Then) integration tests
cargo clippy --all-targets # lint (clean)
```

Tests live in `tests/bdd.rs` and exercise the full stack against the bundled
data, mirroring the scenarios in the specification.

## Running the server

The server reads JSON-RPC requests (one per line) on stdin and writes responses
on stdout; diagnostics go to stderr. The data directory defaults to
`data/kaggle` and can be overridden with the `SOCCER_DATA_DIR` env var or a
single CLI argument.

```sh
./target/release/brazilian-soccer-mcp
```

Example session:

```jsonc
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}
{"jsonrpc":"2.0","method":"notifications/initialized"}
{"jsonrpc":"2.0","id":2,"method":"tools/list"}
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"competition_standings","arguments":{"season":2019}}}
```

### Connecting from an MCP client

Add the built binary as a stdio MCP server. For example, in a Claude Desktop
`claude_desktop_config.json`:

```jsonc
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/absolute/path/to/target/release/brazilian-soccer-mcp",
      "env": { "SOCCER_DATA_DIR": "/absolute/path/to/data/kaggle" }
    }
  }
}
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

### Data notes

- The FIFA player edition bundled here licenses only some Brazilian clubs
  (e.g. Santos, Cruzeiro, Fluminense) and anonymizes player names; nationality
  and club filtering work as specified, but not every club is present.
- Match coverage by competition/season is reported by the `list_competitions`
  tool.
