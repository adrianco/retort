# Brazilian Soccer MCP Server

An MCP (Model Context Protocol) server, written in Rust, that turns six Kaggle
CSV datasets into a queryable knowledge base of Brazilian soccer: matches,
teams, players, competitions and statistics. It speaks JSON-RPC 2.0 over
stdio, so it plugs directly into any MCP client (Claude Desktop, Claude Code,
etc.) and lets an LLM answer natural-language questions like *"Who won the
2019 Brasileirão?"* or *"Compare Palmeiras and Santos head-to-head"*.

## What was built

- **`src/normalize.rs`** – team-name canonicalization. The datasets spell the
  same club many ways (`Palmeiras-SP`, `Palmeiras`, `Atlético-MG`,
  `Atletico Mineiro`, `América FC (Minas Gerais)`, `EC Bahia`...). Names are
  de-accented, lowercased, stripped of parentheticals and state/country
  suffixes, and folded through an alias table. Ambiguous bases (Atlético,
  América, Botafogo...) keep their state so distinct clubs never merge.
  Also handles all three date formats found in the data.
- **`src/data.rs`** – loads all six CSVs into unified `Match` / `Player`
  models (~23.8k match records, 18,207 players), tolerating each file's
  quirks: UTF-8 BOM, float-typed goals, quoted numbers, `NA` scores for
  unplayed fixtures, missing season columns (derived from dates, including
  the COVID-delayed 2020 season that finished in February 2021).
- **`src/queries.rs`** – the query engine: match search, team statistics with
  home/away splits, head-to-head records, standings computed from results
  (3 pts/win with official tie-breakers), FIFA player search/profiles,
  aggregate statistics and win-rate rankings. Série A 2012–2019 appears in
  three files, so results are deduplicated by fixture; for league seasons the
  ordered home/away pair is unique per season, which also lets the merge fill
  gaps in one file with results from another.
- **`src/server.rs`** – the MCP layer: `initialize`, `ping`, `tools/list`,
  `tools/call`, JSON-RPC errors for unknown methods, in-band `isError`
  results for tool failures, silence for notifications.
- **`src/main.rs`** – stdio loop. Data loads once at startup (<1s); every
  query is in-memory and answers far inside the spec's 2s/5s budgets.

## Tools exposed (9)

| Tool | Answers questions like |
|------|------------------------|
| `search_matches` | "Show me all Flamengo vs Fluminense matches", "What did Palmeiras play in 2023?" |
| `get_team_stats` | "What is Corinthians' home record in 2022?" |
| `head_to_head` | "Compare Palmeiras and Santos head-to-head" |
| `get_standings` | "Who won the 2019 Brasileirão?", "Which teams were relegated in 2020?" |
| `search_players` | "Find all Brazilian players", "Forwards at São Paulo FC" |
| `get_player` | "Who is Neymar?" |
| `analyze_stats` | "Average goals per match in the Brasileirão?", "Biggest wins in the dataset" |
| `best_records` | "Which team has the best away record?" |
| `list_competitions` | dataset coverage and diagnostics |

## Build, test, run

```sh
cargo build --release
cargo test                       # 38 tests: unit + BDD integration suites
./target/release/brazilian-soccer-mcp            # serves MCP on stdio
```

The data directory defaults to `./data/kaggle`; override with the first CLI
argument or the `BRAZIL_SOCCER_DATA` environment variable.

Register with an MCP client, e.g. in Claude Desktop's config:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/path/to/target/release/brazilian-soccer-mcp",
      "args": ["/path/to/data/kaggle"]
    }
  }
}
```

## Testing approach (BDD)

Tests follow the Given/When/Then structure from the spec, against the real
CSV files:

- `tests/bdd_match_queries.rs` – match search, filters, normalization,
  cross-file deduplication (2015 Série A = exactly one 380-match season).
- `tests/bdd_team_and_player_queries.rs` – team records (Corinthians' 2022
  home record verified against the raw data, including the late-season
  results merged in from a second file), head-to-head, FIFA player queries,
  cross-file club linking.
- `tests/bdd_competitions_and_stats.rs` – standings (Flamengo champion 2019
  with 90 points; Cruzeiro 2003 in the 24-team format; 2020 relegation zone),
  averages, biggest wins, best away record.
- `tests/bdd_mcp_protocol.rs` – MCP handshake, tool discovery, error paths,
  all six files loadable, and 20 sample questions answered end-to-end through
  the protocol.

## Specification

`TASK.md` / `brazilian-soccer-mcp-guide.md`

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
