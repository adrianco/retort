# Brazilian Soccer MCP Server (Clojure)

An [MCP](https://modelcontextprotocol.io) (Model Context Protocol) server that
answers natural-language questions about Brazilian soccer — players, teams,
matches and competitions — over the bundled Kaggle datasets. It implements the
specification in [`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md).

The server speaks JSON-RPC 2.0 over stdio (the MCP stdio transport) and exposes
a set of tools an LLM can call to query the data. All data is loaded once into
memory at startup, so every query is fast (well under the 2s/5s budgets in the
spec).

## What was built

| Namespace | Responsibility |
|-----------|----------------|
| `soccer.normalize` | Team-name canonicalization (strips `-SP`, `(URU)`, full-name → alias) and multi-format date parsing. Accent-insensitive matching so `Sao Paulo` ≡ `São Paulo`. |
| `soccer.data` | Loads the six CSV files into a uniform in-memory match/player model and **deduplicates** overlapping rows (the 2012–2019 Brasileirão appears in two source files). |
| `soccer.query` | Pure analytics: match search, team records, head-to-head, league standings, competition stats, biggest wins, player search & club summaries. |
| `soccer.format` | Renders query results as the readable, spec-shaped text returned to the LLM. |
| `soccer.tools` | The MCP tool catalogue (names, descriptions, JSON input schemas) and dispatch. |
| `soccer.mcp` | The stdio JSON-RPC 2.0 server loop and protocol handshake (entry point). |

Every source file begins with a context block comment describing its purpose.

## MCP tools

| Tool | Description |
|------|-------------|
| `search_matches` | Find matches by team, opponent, competition, season and/or date range. |
| `team_record` | W/D/L and goal record for a team (filter by season, competition, venue). |
| `head_to_head` | Aggregate record and recent meetings between two teams. |
| `standings` | League table for a competition/season, computed from results (3pts/win). |
| `competition_stats` | Goals-per-match, home/away/draw rates and totals. |
| `biggest_wins` | Matches with the largest goal margin. |
| `search_players` | FIFA player search by name, nationality, club, position, rating. |
| `players_by_club` | Player counts and average rating grouped by club. |
| `list_competitions` | Competitions and seasons available in the dataset. |

## Requirements

- [Clojure CLI](https://clojure.org/guides/install_clojure) (`clojure` / `clj`)
- Java 11+

## Running the server

```bash
clojure -M:run
```

It then reads newline-delimited JSON-RPC requests on stdin and writes responses
on stdout (logs go to stderr). Example handshake + query:

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"standings","arguments":{"season":2019}}}' \
  | clojure -M:run
```

### Registering with an MCP client

Point your MCP-capable client (e.g. Claude Desktop) at the server:

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

## Example results

```
2019 Brasileirão Série A standings (calculated from matches):
 1. Flamengo                90 pts (28W 6D 4L, GF 86 GA 37, GD +49)
 2. Palmeiras               74 pts (21W 11D 6L, GF 61 GA 32, GD +29)
 3. Santos                  74 pts (22W 8D 8L, GF 60 GA 33, GD +27)
 ...

Flamengo vs Fluminense head-to-head (48 matches in dataset):
- Flamengo wins: 20
- Fluminense wins: 15
- Draws: 13
- Goals: Flamengo 67 - 53 Fluminense
```

## Testing (BDD / Given-When-Then)

The suite is written as Given/When/Then behaviour scenarios using
`clojure.test`:

```bash
clojure -M:test
```

- `soccer.normalize-test` — name/date normalization scenarios.
- `soccer.query-test` — analytics verified against a small hand-built fixture
  with known-correct expected values.
- `soccer.mcp-test` — protocol handshake, tool discovery, dispatch and a full
  stdio round-trip.
- `soccer.data-test` — integration tests against the real CSVs (e.g. *Flamengo
  won the 2019 Brasileirão*, 20-team tables, cross-file player+match queries).
  These skip gracefully if `data/kaggle/` is absent.

## Data notes

- **Name variations** are normalized (`Palmeiras-SP`, `Palmeiras`, `Sport Club
  Corinthians Paulista` → canonical forms) with accent-insensitive matching.
- **Date formats** (`2023-09-24`, `2012-05-19 18:30:00`, `29/03/2003`,
  `2003.01.01`) are all parsed.
- **Overlapping sources**: the 2012–2019 Brasileirão appears in both
  `Brasileirao_Matches.csv` and `novo_campeonato_brasileiro.csv`; duplicate
  matches are removed, and `standings` computes from the single most-complete
  source per season to keep tables clean.
- **FIFA edition caveat**: `fifa_data.csv` (FIFA 19 era) lacks club licences for
  Flamengo, Palmeiras, Corinthians and São Paulo, so player-by-club queries for
  those clubs return no rows; other Brazilian clubs (Santos, Grêmio,
  Internacional, Cruzeiro, …) and Brazilian internationals are present.

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
