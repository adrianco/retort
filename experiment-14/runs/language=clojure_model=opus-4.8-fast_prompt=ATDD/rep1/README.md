# Brazilian Soccer MCP with spec and basic data sets

An MCP (Model Context Protocol) server, written in Clojure, that answers
natural-language questions about Brazilian soccer — matches, teams, players,
competitions and statistics — over the provided Kaggle datasets.

## Specification
brazilian-soccer-mcp-guide.md (also mirrored in `TASK.md`)

## Quick start

The server speaks JSON-RPC 2.0 over stdio (standard MCP stdio transport):

```bash
clojure -M:run            # serves data/kaggle by default
clojure -M:run /path/to/data
```

Example session (one JSON-RPC request per line in, one response per line out):

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
  '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"competition_standings","arguments":{"competition":"Brasileirão","season":2019}}}' \
  | clojure -M:run
```

To register with an MCP client, run `clojure -M:run` as the server command in
the project directory.

## Tools

The server advertises six tools, one per capability category in the spec:

| Tool | Answers questions like |
|------|------------------------|
| `find_matches` | "Show me all Flamengo vs Fluminense matches", "What matches did Palmeiras play in 2019?" (by team/opponent/competition/season/date range, with head-to-head) |
| `team_stats` | "What is Corinthians' home record in 2022?" (matches, W/D/L, goals for/against, win rate; scoped by season/competition/venue) |
| `compare_teams` | "Compare Palmeiras and Santos head-to-head" |
| `search_players` | "Find all Brazilian players", "Who are the highest-rated players at Flamengo?" (by name/nationality/club/position, ranked by rating) |
| `competition_standings` | "Who won the 2019 Brasileirão?" (league table calculated from match results) |
| `competition_stats` | "What's the average goals per match?", "Show me the biggest wins" |

## Design notes

- **`src/soccer/data.clj`** — loads every CSV, classifying each by its header
  columns, and normalizes the real-world messiness called out in the spec:
  team-name suffixes (`Palmeiras-SP`, `Nacional (URU)`), three date formats,
  float-encoded goals (`1.0`), and UTF-8 accents. Several files overlap (the
  2019 Brasileirão lives in both its own file and the 2003–2019 historical
  file); for each competition+season the most complete single source is kept,
  eliminating cross-file double counting.
- **`src/soccer/query.clj`** — the domain queries and statistics; returns
  human-readable, domain-language answers.
- **`src/soccer/tools.clj`** — the MCP tool catalogue (names, JSON schemas).
- **`src/soccer/server.clj`** — the JSON-RPC / MCP protocol layer and stdio loop.

## Development methodology

Built with executable Acceptance Test-Driven Development. Every requirement in
the spec is first expressed as an automated acceptance test that drives the
server **only through the MCP protocol** (`tools/list`, `tools/call`), asserting
on domain outcomes (matches found, head-to-head records, standings) rather than
internals. Each scenario boots a running-but-empty server over its own isolated
on-disk fixture dataset, so tests share no state. Finer-grained unit tests cover
the normalization internals.

```bash
clojure -M:test
```

`test/soccer/acceptance_test.clj` is the executable specification;
`test/soccer/real_data_test.clj` confirms all six real CSV files load and
answer queries (e.g. Flamengo won the 2019 Brasileirão).

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
