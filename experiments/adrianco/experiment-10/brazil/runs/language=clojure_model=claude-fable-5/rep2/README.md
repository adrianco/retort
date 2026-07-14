# Brazilian Soccer MCP Server

An MCP (Model Context Protocol) server, written in Clojure, that answers
natural-language questions about Brazilian soccer: Brasileirão Série A/B/C,
Copa do Brasil and Copa Libertadores matches (2003–2023) plus the FIFA 19
player database. Built to the specification in `TASK.md` /
`brazilian-soccer-mcp-guide.md`.

## Running

Requires the [Clojure CLI](https://clojure.org/guides/install_clojure) (Java 11+).

```sh
clojure -M:run     # start the MCP server on stdio
clojure -M:test    # run the BDD test suite
```

MCP client configuration (e.g. `claude mcp add` or `.mcp.json`):

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

The server speaks JSON-RPC 2.0 over stdio (MCP protocol version
`2024-11-05`): `initialize`, `ping`, `tools/list`, `tools/call`.
Set `BRAZILIAN_SOCCER_DATA` to override the default `data/kaggle` data
directory.

## Tools

| Tool | Purpose |
|------|---------|
| `search_matches` | Find matches by team, opponent, competition, season, date range or stage |
| `head_to_head` | Full match list and win/draw tally between two teams |
| `get_team_stats` | W/D/L and goals for a team, filterable by season/competition/venue |
| `get_standings` | League table for a season, calculated from match results |
| `search_players` | FIFA 19 player search by name/nationality/club/position/rating |
| `get_player` | Detailed single-player profile |
| `get_competition_stats` | Average goals, home-win/draw/away-win rates |
| `get_biggest_wins` | Largest goal-margin victories |
| `list_teams` | Canonical team names per competition/season |

## Implementation notes

```
src/brazilian_soccer/data.clj    CSV loading, team-name normalization, dedup
src/brazilian_soccer/query.clj   match/player/standings/statistics queries
src/brazilian_soccer/tools.clj   MCP tool registry + response formatting
src/brazilian_soccer/server.clj  JSON-RPC 2.0 stdio loop
test/brazilian_soccer/...        BDD (Given/When/Then) test suite
```

- **Team-name normalization** — the datasets spell the same club three ways
  ("Palmeiras-SP", "Palmeiras", "Sociedade Esportiva Palmeiras"). Names are
  lower-cased, de-accented and resolved through an alias table; unknown names
  drop a trailing state suffix only when the base name is unambiguous
  (América-MG vs América-RN stay distinct).
- **Cross-file deduplication** — Série A 2012–2019 appears in three files and
  Copa do Brasil in two, with kick-off dates differing by a day (timezones).
  A match is a duplicate when the same competition + home/away pair occurs
  within 3 days (30 days when one row has no score, which is how rescheduled
  fixtures appear). When the primary file lists a fixture without a result
  (late 2022 rounds), the score is merged in from the extended dataset.
- **Standings** are computed from match results (3 pts/win) and ordered by
  the CBF tie-breakers (points, wins, goal difference, goals for). Verified
  against history: 2015 Corinthians, 2019/2020 Flamengo (90 pts, 28W 6D 4L),
  2022 Palmeiras. Historical point deductions are not modeled.
- **Dates** — `2012-05-19 18:30:00`, `2023-09-24` and `29/03/2003` all
  normalize to ISO `yyyy-MM-dd`; all text is handled as UTF-8.
- **Copa do Brasil finals** — the cup file only has numeric rounds; the
  highest round of each season is tagged as the final.
- Datasets load once at startup (~16,900 deduplicated matches, 18,207
  players); every query is an in-memory scan, well inside the 2 s/5 s
  response budgets (asserted in the acceptance tests).

Known data limitations: the FIFA 19 snapshot lacks some Brazilian clubs
(e.g. Flamengo, Palmeiras) and players (e.g. Gabriel Barbosa); Libertadores
coverage is 2013–2022; the 2023 Série A season is missing its last three
fixtures.

## Testing

BDD scenarios (Given/When/Then) using `clojure.test`, 30 tests / 168
assertions covering: loading of all six CSVs, name normalization, date
formats, UTF-8, deduplication, every query category from the spec, the MCP
protocol layer (handshake, tool listing, tool calls, error codes), 22
sample questions end-to-end, response-time budgets and cross-file queries.

## Specification

See `TASK.md` (a.k.a. `brazilian-soccer-mcp-guide.md`).

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
