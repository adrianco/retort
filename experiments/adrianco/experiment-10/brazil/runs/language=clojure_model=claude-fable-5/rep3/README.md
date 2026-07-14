# Brazilian Soccer MCP Server

An MCP (Model Context Protocol) server, written in Clojure, that answers
natural-language-driven queries about Brazilian soccer: matches, teams,
players, competitions and statistics, backed by the bundled Kaggle datasets.

## Requirements

- Java 11+
- [Clojure CLI](https://clojure.org/guides/install_clojure) (`clojure`)

## Running the server

The server speaks MCP over stdio (newline-delimited JSON-RPC 2.0):

```sh
clojure -M:run
```

The data directory defaults to `data/kaggle`; override with a CLI argument
(`clojure -M:run /path/to/data`) or the `BRAZILIAN_SOCCER_DATA` env var.

Example Claude Desktop / MCP client configuration:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "clojure",
      "args": ["-M:run"],
      "cwd": "/path/to/this/repo"
    }
  }
}
```

## Running the tests

```sh
clojure -X:test
```

The tests are BDD-style scenarios covering data loading, team-name
normalization, match/team/player/competition queries, the MCP protocol
layer, 20+ sample questions from the specification, and the query
performance criteria.

## Tools exposed

| Tool | Purpose |
|------|---------|
| `search_matches` | Matches by team, opponent, competition, season, date range |
| `head_to_head` | Record and recent matches between two teams |
| `get_team_stats` | W/D/L, goals, win rate; filter by season/competition/venue |
| `get_standings` | Season league table calculated from results (champion + relegation zone) |
| `get_competition_stats` | Match counts, goals per match, home/draw/away rates |
| `get_biggest_wins` | Largest victory margins |
| `get_best_records` | Teams ranked by win rate (home/away/overall) |
| `search_players` | FIFA players by name/nationality/club/position/rating/age |
| `get_player` | Detailed FIFA profile for one player |
| `get_extended_match_stats` | Average corners/shots/attacks (BR-Football dataset) |
| `list_competitions` | Dataset coverage: competitions, seasons, match counts |

## Data coverage

- Brasileirão Série A 2003–2023 (three sources, deduplicated per season;
  missing late-2022 scores are backfilled from the extended dataset)
- Brasileirão Série B/C 2014–2023
- Copa do Brasil 2012–2023
- Copa Libertadores 2013–2022
- 18,207 FIFA player profiles

Team names are normalized across the files' different conventions
("Palmeiras-SP", "Palmeiras", "América - MG", "America MG",
"Athletico Paranaense"/"Atlético-PR"), with accent-insensitive matching.

## Code layout

- `src/brazilian_soccer/data.clj` — CSV loading, team-name normalization, dedup/backfill
- `src/brazilian_soccer/queries.clj` — match/team/player/standings/statistics queries
- `src/brazilian_soccer/tools.clj` — MCP tool schemas, handlers and answer formatting
- `src/brazilian_soccer/server.clj` — JSON-RPC 2.0 stdio loop (`initialize`, `tools/list`, `tools/call`)
- `test/brazilian_soccer/` — BDD test scenarios

## Specification

See `TASK.md` (and `brazilian-soccer-mcp-guide.md`).

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
