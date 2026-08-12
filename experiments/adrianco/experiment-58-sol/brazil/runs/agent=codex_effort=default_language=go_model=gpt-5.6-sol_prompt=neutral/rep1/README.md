# Brazilian Soccer MCP Server

A dependency-free Go MCP server for the six bundled Brazilian soccer datasets. It exposes normalized match, team, player, competition, and cross-file queries over JSON-RPC 2.0 on standard input/output. It supports current MCP `2026-07-28` stateless discovery/calls and legacy initialize/initialized clients back through `2024-11-05`.

The server loads 23,954 match rows and 18,207 FIFA player rows at startup. Team lookup is case- and accent-insensitive, understands state suffixes such as `Flamengo-RJ`, and maps common full club names. Match search retains the source CSV; aggregate tools select one authoritative feed per competition/season so overlapping datasets do not inflate standings or statistics.

## Build and test

Go 1.23 or newer is required.

```sh
go test -race ./...
go build -o brazilian-soccer-mcp .
```

Run from this repository (the default data path is `data/kaggle`):

```sh
./brazilian-soccer-mcp
```

From another working directory, provide the data location:

```sh
./brazilian-soccer-mcp -data /absolute/path/to/data/kaggle
```

Example MCP client configuration:

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

## Tools

| Tool | Purpose |
|---|---|
| `search_matches` | Filter all match feeds by team, opponent, home/away side, date range, competition, season, stage, or source |
| `team_statistics` | Wins/draws/losses, goals, points, and win rate, including home/away splits |
| `head_to_head` | Aggregate and list results between two teams |
| `search_players` | Filter FIFA players by name, nationality, club, position, and rating |
| `standings` | Calculate a season table with league tie-break ordering |
| `competition_statistics` | Goals per match and home/away/draw aggregates |
| `biggest_wins` | Rank results by winning margin |
| `team_profile` | Combine a team's record and competitions with FIFA players at the club |
| `derbies` | Find and label matches between curated traditional Brazilian rivals |

The MCP client/LLM translates natural-language questions into these structured tools. Examples covered by the contract include:

1. Show all Flamengo vs Fluminense matches.
2. When did Flamengo last play Corinthians?
3. What matches did Palmeiras play in 2023?
4. Find Copa do Brasil finals.
5. Find Libertadores group-stage matches in 2019.
6. Find matches in a date range.
7. Show only home matches for Santos.
8. Inspect raw rows from one named CSV source.
9. What was Corinthians' home record in 2022?
10. What was Palmeiras' away record in 2023?
11. Compare Palmeiras and Santos head-to-head.
12. Who are the highest-rated Brazilian players?
13. Who are the highest-rated players at Flamengo?
14. Show forwards from São Paulo FC.
15. Who is Gabriel Barbosa?
16. Who won the 2019 Brasileirão?
17. Show the 2019 Brasileirão table.
18. What was the average goals per match in the Brasileirão?
19. What was the home win rate in Copa do Brasil?
20. Show the biggest victories in the dataset.
21. Which competitions has Palmeiras played in?
22. Combine Flamengo's match record with players at the club.

For a direct protocol smoke test:

```sh
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"demo","version":"1"}}}' \
  '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"standings","arguments":{"competition":"Brasileirao","season":2019,"limit":3}}}' \
  | ./brazilian-soccer-mcp
```

## Data behavior

- Dates accepted by the loaders: ISO date, ISO date/time, RFC 3339, and Brazilian `DD/MM/YYYY`.
- The one bundled Libertadores final with `NA` date/season and missing scores is retained for match search with `result_missing: true`, but excluded from aggregates.
- `source` on every match identifies its CSV. Supplying a `source` filter returns that feed's raw records; otherwise exact duplicate results are merged.
- Aggregate source precedence is official Brasileirão/Copa/Libertadores feed, then historical Brasileirão, then the extended statistics feed. Serie B and Serie C come from the extended feed.
- Standings use points, wins, goal difference, goals scored, then team name as deterministic tie-breaks. They do not infer regulatory deductions or competition-specific rules not present in the CSVs.
- Player records come from the bundled historical FIFA snapshot, not live rosters. Player-level goal scorers and relegation rules cannot be inferred from the provided columns.

## Data sources and licenses

- [Brazilian championship matches](https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro): `Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`, and `Libertadores_Matches.csv` — CC BY 4.0.
- [Brazilian football matches](https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches): `BR-Football-Dataset.csv` — CC0 Public Domain.
- [Campeonato Brasileiro 2003–2019](https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019): `novo_campeonato_brasileiro.csv` — Attribution 4.0.
- [FIFA players data](https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data): `fifa_data.csv` — Apache 2.0.

The original task specification is in [TASK.md](TASK.md).
