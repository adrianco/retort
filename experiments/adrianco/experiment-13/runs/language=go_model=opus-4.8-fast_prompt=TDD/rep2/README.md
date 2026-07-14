# Brazilian Soccer MCP with spec and basic data sets

A Model Context Protocol (MCP) server, written in Go, that exposes a queryable
knowledge base of Brazilian soccer — matches, teams, players, competitions and
statistics — built from the bundled Kaggle CSV datasets. It speaks JSON-RPC 2.0
over stdio so it can be connected to an LLM client such as Claude.

## Specification
brazilian-soccer-mcp-guide.md (and `TASK.md`)

## Quick start

```sh
# Build
go build -o brazilian-soccer-mcp .

# Run (serves MCP over stdio; loads ./data/kaggle by default)
./brazilian-soccer-mcp                 # or: ./brazilian-soccer-mcp -data path/to/csvs

# Run the tests
go test ./...
```

The server reads JSON-RPC requests on stdin and writes responses on stdout;
progress and errors go to stderr. Example session:

```sh
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"standings","arguments":{"competition":"Brasileirão","season":2019}}}' \
  | ./brazilian-soccer-mcp
```

### Connecting to Claude Desktop / Claude Code

Add to your MCP client configuration (adjust the paths):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/absolute/path/to/brazilian-soccer-mcp",
      "args": ["-data", "/absolute/path/to/data/kaggle"]
    }
  }
}
```

## Architecture

```
main.go                     CLI entry point: load datasets, serve over stdio
internal/soccer/            Domain layer (no MCP/JSON concerns)
  model.go                  Match, Player, KB types
  normalize.go              Team-name normalization & matching (accent/suffix tolerant)
  parse.go                  Multi-format date and integer parsing
  load.go                   CSV loaders for all six datasets -> KB
  query.go                  SearchMatches with a flexible MatchFilter
  players.go                SearchPlayers with a PlayerFilter
  stats.go                  TeamRecord, HeadToHead
  competition.go            Standings, CompetitionStats, BiggestWins, dataset dedup
internal/mcp/               MCP/JSON-RPC layer
  server.go                 JSON-RPC 2.0 dispatch + stdio transport
  tools.go                  Tool schemas and implementations
  format.go                 Human-readable rendering of results
```

The code is built test-first (TDD); `go test ./... -cover` reports ~90%
coverage on the domain layer.

## MCP tools

| Tool | Purpose | Key arguments |
|------|---------|---------------|
| `search_matches` | Find matches by team/opponent/home/away, competition, season, date range | `team`, `opponent`, `home_team`, `away_team`, `competition`, `season`, `season_from`, `season_to`, `date_from`, `date_to`, `limit` |
| `head_to_head` | Head-to-head record + recent meetings between two teams | `team1`, `team2`, `limit` |
| `team_record` | W/D/L, goals, points and win rate for a team | `team`, `competition`, `season`, `home_only`, `away_only` |
| `search_players` | Search FIFA players by name/nationality/club/position/rating | `name`, `nationality`, `club`, `position`, `min_overall`, `limit` |
| `standings` | League table calculated from match results | `competition`, `season` |
| `competition_stats` | Avg goals, home/away/draw rates, biggest victories | `competition`, `season`, `limit` |

### Data-quality handling

- **Team names** are normalized (accent-folded, lowercased, tokenized) so
  `Palmeiras-SP`, `Palmeiras`, `São Paulo`/`Sao Paulo` match correctly, while
  distinct same-named clubs (`Atletico-MG` vs `Atletico-GO`) stay separate.
- **Dates** in ISO (`2023-09-24`), ISO+time (`2012-05-19 18:30:00`) and
  Brazilian (`29/03/2003`) formats are all parsed.
- **UTF-8** (including the BOM on `fifa_data.csv`) is handled.
- **Overlapping datasets**: several files cover the same competition+season.
  Standings and aggregate statistics deduplicate by selecting the single most
  complete source per (competition, season) so counts and averages are not
  inflated.

## Example questions it can answer

Matches: *"Show me all Flamengo vs Fluminense matches"*, *"What matches did
Palmeiras play in 2023?"*, *"When did Flamengo last play Corinthians?"*,
*"Show all Copa do Brasil matches in 2022"*, *"Find Palmeiras away matches in
the Libertadores"*.

Teams: *"What is Corinthians' home record in 2022?"*, *"Compare Palmeiras and
Santos head-to-head"*, *"How many goals did Grêmio concede in 2019?"*,
*"What is Flamengo's away record?"*.

Players: *"Find all Brazilian players"*, *"Who are the highest-rated Brazilian
players?"*, *"Show forwards at Santos"*, *"Who is Neymar?"*, *"List goalkeepers
rated 85+"*.

Competitions: *"Who won the 2019 Brasileirão?"*, *"Show the 2018 Brasileirão
standings"*, *"Which teams finished bottom in 2020?"*.

Statistics: *"What's the average goals per match in the Brasileirão?"*,
*"What's the home win rate?"*, *"Show the biggest wins in the dataset"*,
*"Compare the 2018 and 2019 seasons"*.

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
