# Brazilian Soccer MCP Server (Clojure)

An MCP (Model Context Protocol) server that answers natural language questions
about Brazilian soccer — Brasileirão, Copa do Brasil and Copa Libertadores
matches (2003–2023), team records, calculated standings, head-to-head
comparisons and FIFA player data. Implemented in Clojure per the
specification in [TASK.md](TASK.md) / [brazilian-soccer-mcp-guide.md](brazilian-soccer-mcp-guide.md).

## Quick start

```sh
# run the MCP server (JSON-RPC 2.0 over stdio, newline-delimited)
clojure -M:run

# run the BDD test suite (30 tests, 300+ assertions)
clojure -M:test
```

Register with an MCP client (e.g. Claude Desktop / Claude Code):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "clojure",
      "args": ["-M:run"],
      "cwd": "<path to this repo>"
    }
  }
}
```

The data directory defaults to `data/kaggle`; override with the
`BRAZILIAN_SOCCER_DATA` environment variable.

## What was built

```
deps.edn                      Clojure CLI project (data.csv, data.json, test-runner)
src/brazilian_soccer/
  data.clj                    CSV loading, team-name normalization, date parsing,
                              cross-file match de-duplication
  query.clj                   match search, head-to-head, team records, standings,
                              biggest wins, competition stats, player search
  tools.clj                   MCP tool registry: JSON Schemas + formatted answers
  server.clj                  JSON-RPC 2.0 stdio loop (initialize, tools/list,
                              tools/call, ping, notifications, error codes)
test/brazilian_soccer/
  data_test.clj               loading, normalization, dates, de-duplication
  query_test.clj              the TASK.md BDD scenarios + historical anchors
  tools_test.clj              answer formats, 20+ sample questions, performance
  server_test.clj             MCP handshake / protocol behavior
```

### MCP tools exposed

| Tool | Answers questions like |
|------|------------------------|
| `search_matches` | "What matches did Palmeiras play in 2023?" |
| `head_to_head` | "Show me all Flamengo vs Fluminense matches" |
| `team_stats` | "What is Corinthians' home record in 2022?" |
| `league_standings` | "Who won the 2019 Brasileirão?" |
| `biggest_wins` | "Show me the biggest wins in the dataset" |
| `competition_stats` | "Average goals per match in the Brasileirão?" |
| `list_competitions` | "What competitions are covered?" |
| `search_players` | "Who is Neymar?", "Players at Fluminense?" |
| `top_players` | "Who are the top Brazilian players?" |
| `club_player_summary` | "Brazilian players per club with avg rating" |
| `data_summary` | "What data is loaded?" |

### Data quality handling (per the spec)

* **Team name variations** — `"Palmeiras-SP"`, `"Palmeiras"`,
  `"Sport Club Corinthians Paulista"`, `"Atlético - MG"`, `"EC Bahia"`,
  `"Vasco da Gama RJ"` etc. are normalized to one canonical id per club
  (accent stripping, state-suffix logic, alias table), while clubs that
  differ only by state (América-MG vs América-RN, Botafogo-RJ vs
  Botafogo-PB) stay distinct.
* **Date formats** — ISO (`2023-09-24`), Brazilian (`29/03/2003`) and
  datetime (`2012-05-19 18:30:00`) all parse; `NA` is tolerated.
* **UTF-8** — accented names (Grêmio, São Paulo, Avaí) work in both data
  and queries.
* **Overlapping files** — Serie A seasons appear in up to three CSVs, with
  quirks: duplicate rows inside BR-Football-Dataset, the COVID-delayed 2020
  season spilling into Feb 2021, a 2009 fixture where Botafogo hosted
  Flamengo twice, and `NA` scores for some 2016/2022 rows. Matches are
  de-duplicated by `[competition season home away]` (plus date for cups),
  preferring rows with final scores. Result: every Brasileirão season
  2003–2022 reproduces its real 380/552-match shape and real champion
  (e.g. Flamengo 2019 with 90 pts, Cruzeiro 2003 with 100).

### Verification

`clojure -M:test` exercises the BDD scenarios from the spec
(Given/When/Then), including: all six CSVs load with full row counts,
20+ sample questions answered through the MCP tools, cross-file
queries (FIFA players + match data), historical standings anchors, the
JSON-RPC handshake/error codes, and the < 2s / < 5s query budgets.

## Data Sources

Kaggle data can't be downloaded without an account so these (freely
available with attribution) data sets have been downloaded for use here:

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
