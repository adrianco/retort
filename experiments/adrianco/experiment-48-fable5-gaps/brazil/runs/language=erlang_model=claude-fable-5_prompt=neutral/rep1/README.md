# Brazilian Soccer MCP with spec and basic data sets

An MCP (Model Context Protocol) server, written in Erlang/OTP, that answers
questions about Brazilian soccer from the bundled Kaggle datasets: ~17,000
matches across the Brasileirão Série A (2003-2023), Série B, Série C, Copa do
Brasil and Copa Libertadores, plus the 18,207-player FIFA 19 database.

## Requirements

- Erlang/OTP 27+ (uses the built-in `json` module; developed on OTP 29)
- rebar3

## Build, test, run

```sh
rebar3 compile        # build
rebar3 eunit          # run the test suite (52 tests)
rebar3 escriptize     # build the server binary
./_build/default/bin/bsmcp [data-dir]   # run (MCP over stdio)
```

The data directory defaults to `data/kaggle`, and can also be set with the
`BSMCP_DATA_DIR` environment variable. Diagnostics go to stderr; stdout
carries only newline-delimited JSON-RPC (the MCP stdio transport).

Example Claude Desktop / MCP client configuration:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/path/to/repo/_build/default/bin/bsmcp",
      "args": ["/path/to/repo/data/kaggle"]
    }
  }
}
```

## Tools

| Tool | Answers questions like |
|------|------------------------|
| `search_matches` | "Show me all Flamengo vs Fluminense matches", "Find all Copa do Brasil finals" |
| `team_stats` | "What is Corinthians' home record in 2022?" |
| `head_to_head` | "Compare Palmeiras and Santos head-to-head" |
| `competition_standings` | "Who won the 2019 Brasileirão?", "Which teams were relegated?" |
| `search_players` | "Who is Neymar?", "Best Brazilian goalkeepers" |
| `league_stats` | "Average goals per match in the Brasileirão?" |
| `biggest_wins` | "Show me the biggest wins in the dataset" |
| `data_summary` | "What data do you have?" |

Team names are normalized across the datasets' conventions ("Palmeiras-SP",
"Palmeiras", "São Paulo - SP", "Sport Club Corinthians Paulista", accents,
state suffixes), all date formats in the data are handled, and overlapping
sources are de-duplicated so statistics are not double counted. Note that the
FIFA 19 dataset does not include Brazilian-league clubs (unlicensed that
year), so player-by-club queries work best with international clubs.

## Code layout

- `src/bsmcp_csv.erl` – CSV parser (quotes, escapes, BOM, UTF-8)
- `src/bsmcp_names.erl` – team-name/competition normalization, date parsing
- `src/bsmcp_data.erl` – loads the six CSVs into ETS, de-duplication
- `src/bsmcp_query.erl` – search and statistics
- `src/bsmcp_format.erl` – human-readable answer formatting
- `src/bsmcp_tools.erl` – MCP tool schemas and dispatch
- `src/bsmcp_rpc.erl` – JSON-RPC 2.0 / MCP message handling
- `src/bsmcp_server.erl` – stdio transport loop
- `test/` – EUnit suites, including BDD-style scenarios over the real data

## Specification
brazilian-soccer-mcp-guide.md

## Data Sources
Kaggle data can't be downloaded without an account so these (freely available with attribution) data sets have been downloaded for use here:

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
