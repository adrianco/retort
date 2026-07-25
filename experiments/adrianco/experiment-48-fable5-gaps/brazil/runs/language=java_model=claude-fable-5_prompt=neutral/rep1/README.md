# Brazilian Soccer MCP with spec and basic data sets

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

## Implementation

A Java 21 MCP (Model Context Protocol) server, built with Maven, that loads all six
CSV files into memory and answers queries over stdio (newline-delimited JSON-RPC 2.0).

### Layout

- `src/main/java/com/brsoccer/mcp/data/` — CSV loading (`DataStore`) and team-name
  normalization (`TeamRegistry`, which unifies "Flamengo", "Flamengo-RJ", "Flamengo - RJ",
  handles accents, and keeps ambiguous bases like Atlético-MG vs Athletico-PR distinct).
  Matches appearing in several files are de-duplicated (±1 day tolerance, since one
  dataset records dates a day later than the others); extended stats (corners, shots)
  are merged onto the surviving match.
- `src/main/java/com/brsoccer/mcp/query/QueryService.java` — match search, head-to-head,
  team stats, standings computed from results, player search, aggregates, rankings.
- `src/main/java/com/brsoccer/mcp/tools/McpTools.java` — the 9 MCP tool definitions and
  text formatting.
- `src/main/java/com/brsoccer/mcp/server/McpServer.java` — the JSON-RPC / MCP stdio loop.

### Build and test

```bash
mvn test         # 63 tests: BDD scenarios from the spec + 24 sample questions + protocol tests
mvn package      # builds target/brazilian-soccer-mcp-1.0.0.jar (self-contained)
```

### Run

```bash
java -jar target/brazilian-soccer-mcp-1.0.0.jar [data-dir]   # default data dir: ./data/kaggle
```

Claude Desktop / MCP client configuration:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "java",
      "args": ["-jar", "/path/to/target/brazilian-soccer-mcp-1.0.0.jar", "/path/to/data/kaggle"]
    }
  }
}
```

### Tools

| Tool | Purpose |
|------|---------|
| `search_matches` | Matches by team, opponent, competition, season, date range, stage |
| `head_to_head` | Record between two teams with recent meetings |
| `team_stats` | W/D/L, goals, win rate; filter by season/competition/venue |
| `league_standings` | Season table computed from results (e.g. 2019: Flamengo, 90 pts) |
| `search_players` | FIFA players by name/nationality/club/position/rating |
| `player_info` | Detailed profile for one player |
| `competition_stats` | Avg goals, home/away win rates, biggest wins |
| `team_rankings` | Rank teams by points/wins/win_rate/goals, home or away |
| `list_competitions` | Dataset coverage summary |

Notes: rows with "NA" scores (postponed fixtures, the cut-off 2021 Copa do Brasil rounds)
are skipped; the FIFA dataset is FIFA 19 and contains no Brazilian-league clubs, so club
queries for e.g. Flamengo legitimately return no players.
