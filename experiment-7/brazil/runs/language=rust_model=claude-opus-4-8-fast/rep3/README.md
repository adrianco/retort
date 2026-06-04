# Brazilian Soccer MCP Server (Rust)

A [Model Context Protocol](https://modelcontextprotocol.io) server that exposes a
queryable knowledge graph over Brazilian-soccer datasets (matches, teams,
players and competitions). An LLM connected to this server can answer natural
language questions such as *"Who won the 2019 Brasileirão?"*, *"Compare Palmeiras
and Santos head-to-head"* or *"Who are the top-rated Brazilian players?"*.

Implemented in Rust against the specification in [`TASK.md`](TASK.md).

## What was built

* A self-contained **MCP server** speaking JSON-RPC 2.0 over the stdio transport
  (`initialize`, `tools/list`, `tools/call`, `ping`).
* **8 query tools** covering all five capability categories from the spec:

  | Tool | Capability | Example question |
  |------|------------|------------------|
  | `search_matches` | Match queries | "Show me all Flamengo vs Fluminense matches" |
  | `head_to_head` | Team queries | "Compare Palmeiras and Santos head-to-head" |
  | `team_record` | Team queries | "What is Corinthians' home record in 2022?" |
  | `search_players` | Player queries | "Who are the top Brazilian players?" |
  | `competition_standings` | Competition queries | "Who won the 2019 Brasileirão?" |
  | `competition_summary` | Statistical analysis | "Average goals per match and biggest wins" |
  | `list_competitions` | Discovery | "What competitions are available?" |
  | `list_seasons` | Discovery | "What seasons of the Libertadores are covered?" |

* All **6 CSV datasets** are loaded, unified into a common model and made
  queryable (~15.7k de-duplicated matches and 18.2k players).
* **Data-quality handling** as required by the spec:
  * team-name normalization (state suffixes `-SP`, parentheticals `(URU)`,
    accents `São`/`Grêmio`) so variants match consistently;
  * multi-format date parsing (`2023-09-24`, `2012-05-19 18:30:00`,
    `29/03/2003`);
  * UTF-8 throughout (incl. stripping the BOM in `fifa_data.csv`).
* **Source reconciliation**: several files overlap (the 2019 Série A appears in
  three of them). To avoid double-counting, the loader keeps a single
  authoritative source per `(competition, season)`. As a result computed
  standings are exact — e.g. the 2019 Brasileirão returns Flamengo as champion
  with 90 points (28W-6D-4L), matching the real season.

## Architecture

```
src/
  normalize.rs  Team-name normalization, accent stripping, date/int parsing
  data.rs       Record models (Match, Player) + per-file CSV loaders + dedup
  store.rs      DataStore: the in-memory dataset, loaded once at start-up
  queries.rs    Analytical query layer (pure over &DataStore)
  mcp.rs        JSON-RPC 2.0 / stdio MCP transport + tool catalog/schemas
  main.rs       Entry point (mcp | demo | info modes)
tests/
  bdd.rs        Behaviour-Driven (Given/When/Then) scenario suite
```

Every source file starts with a context-block comment describing its role.
Dependencies are intentionally minimal: `csv` and `serde_json`.

## Build & run

```bash
cargo build --release

# Run the MCP server (stdio JSON-RPC) — this is what an MCP client launches:
cargo run --release            # or: ./target/release/brazilian-soccer-mcp

# See answers to sample questions without an MCP client:
cargo run --release -- demo

# Print dataset totals:
cargo run --release -- info
```

The dataset directory is resolved from `$BRAZIL_SOCCER_DATA`, then `data/kaggle`.

### Registering with an MCP client

Example client configuration:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/path/to/target/release/brazilian-soccer-mcp",
      "env": { "BRAZIL_SOCCER_DATA": "/path/to/data/kaggle" }
    }
  }
}
```

### Talking to it directly

```bash
printf '%s\n' \
 '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{}}}' \
 '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"competition_standings","arguments":{"competition":"Brasileirão","season":2019}}}' \
 | ./target/release/brazilian-soccer-mcp
```

## Testing

BDD-style Given/When/Then scenarios (plus unit tests for normalization) run
against the real datasets:

```bash
cargo test
```

27 tests cover data loading, all query categories, the MCP dispatch layer, team
name/date normalization and standings correctness.

## Data Sources

Kaggle data can't be downloaded without an account, so these (freely available,
with attribution) datasets are included under `data/kaggle/`:

* https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro
  — License: CC BY 4.0
  — `Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`, `Libertadores_Matches.csv`
* https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches
  — License: CC0 Public Domain
  — `BR-Football-Dataset.csv`
* https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019
  — License: CC BY 4.0
  — `novo_campeonato_brasileiro.csv`
* https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data
  — License: Apache 2.0
  — `fifa_data.csv`

For demo / non-commercial use.
