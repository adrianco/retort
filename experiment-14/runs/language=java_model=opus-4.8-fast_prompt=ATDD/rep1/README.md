# Brazilian Soccer MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io) server (Java) that exposes
Brazilian soccer data — matches, teams, players, competitions and aggregate
statistics — as MCP tools an LLM host can call to answer natural-language questions.

It implements the specification in [`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md)
and is built test-first using executable Acceptance Test-Driven Development (ATDD):
every requirement is encoded as an acceptance test that drives the server **only**
through the public MCP JSON-RPC protocol.

## Tools

| Tool | Capability | Key arguments |
|------|------------|---------------|
| `find_matches` | Match queries by team, opponent, competition, season, venue | `team`, `opponent`, `competition`, `season`, `venue`, `limit` |
| `head_to_head` | Win/draw/goal record between two teams | `teamA`, `teamB` |
| `team_stats` | A team's record (W/D/L, goals, win rate), with home/away splits | `team`, `season`, `competition`, `venue` |
| `search_players` | Player search by name, nationality, club, position, rating | `name`, `nationality`, `club`, `position`, `minOverall`, `limit` |
| `competition_standings` | League table for a season, computed from results | `competition`, `season` |
| `league_statistics` | Goals/match, home–away win rates, biggest wins | `competition`, `season` |

Competition keys: `serie_a`, `copa_do_brasil`, `libertadores`, `serie_b`, `serie_c`
(spelling variants such as `brasileirao` / `Copa do Brasil` are accepted).

## Build & test

```bash
mvn test        # run the acceptance + unit suite
mvn package     # build a runnable fat jar at target/brazilian-soccer-mcp.jar
```

Requires JDK 17+ and Maven.

## Run

The server speaks newline-delimited JSON-RPC over stdio (the standard MCP stdio
transport). Data is loaded from `data/kaggle` by default (override with an argument).

```bash
java -jar target/brazilian-soccer-mcp.jar [data-dir]
```

Example MCP client configuration:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "java",
      "args": ["-jar", "/absolute/path/to/target/brazilian-soccer-mcp.jar"]
    }
  }
}
```

Quick manual smoke test:

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"competition_standings","arguments":{"competition":"serie_a","season":2019}}}' \
  | java -jar target/brazilian-soccer-mcp.jar
# -> 2019 Brasileirão champion: Flamengo-RJ, 90 pts (28W 6D 4L)
```

## Design notes

- **Architecture.** `DataStore` loads and de-duplicates the CSVs; `SoccerService`
  answers domain queries and returns JSON; `McpServer` implements the JSON-RPC 2.0 /
  MCP protocol (`initialize`, `tools/list`, `tools/call`); `Main` wires stdio.
- **Team-name normalization** (`TeamNames`). The same club is spelled many ways across
  files (`Palmeiras-SP`, `Palmeiras`, `São Paulo`/`Sao Paulo`, `Nacional (URU)`). A
  fuzzy `matchKey` (accent/case-insensitive, suffix-stripped) powers search, while an
  `identityKey` retains the state code so `Atlético-MG`, `Atlético-PR` and
  `Atlético-GO` stay distinct clubs for standings.
- **De-duplication.** The Brasileirão appears in three datasets. Sources load in
  priority order and each later source is gated against the `(competition, season)`
  coverage already loaded, so league tables are never double-counted. Standings are
  computed purely from match results.
- **Formats.** Handles ISO, Brazilian (`DD/MM/YYYY`) and timestamped dates, integer
  and float goal columns, UTF-8/BOM and quoted CSV fields.

### Data caveats

- The FIFA player dataset is a FIFA-19-era export and does not include every Brazilian
  club (e.g. Flamengo is unlicensed/absent); club searches reflect what the data
  contains.

## Tests

Acceptance tests drive the server through the MCP protocol via a thin
`McpTestClient` (no back-door access to internals), one suite per capability:
match / team / player / competition–statistics queries, plus the protocol handshake
and discovery. Unit tests cover team-name normalization. The 2019 Brasileirão result
(Flamengo champion on 90 points) is asserted end-to-end as an executable specification.

---

## Data Sources

Kaggle data can't be downloaded without an account, so these (freely available with
attribution) datasets have been downloaded for use here:

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
