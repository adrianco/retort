# Brazilian Soccer MCP Server

A dependency-free Go MCP server over the six Brazilian soccer CSV datasets in
`data/kaggle`. It loads the data once at startup and exposes natural-language,
match, team, player, competition, and statistical tools over stdio JSON-RPC.

## Features

- Loads all five match files and the 18,207-row FIFA player file.
- Normalizes accents, state suffixes, and common long-form team names while
  keeping ambiguous clubs such as Atlético-MG and Atlético-PR distinct.
- Searches matches by team/opponent, date range, competition, season, stage,
  and home/away role.
- Calculates records, head-to-head results, standings, goals per match,
  home/away rates, and biggest wins.
- Searches and ranks players by name, nationality, club, position, and rating.
- Answers common soccer questions through the `ask` tool and offers a
  cross-file `club_overview` combining match and FIFA data.
- Treats the normalized entities and match/player edges as an in-memory
  knowledge graph, avoiding an external database for this demo-sized dataset.

The supplied match sources overlap. Direct match search returns their union
(with exact duplicates removed), while calculations select one authoritative
source per competition and season. This prevents duplicated games from
inflating tables and team records.

## Build and test

Go 1.22 or newer is required.

```sh
go test ./...
go build -o brazilian-soccer-mcp .
```

The tests cover normalization, all six real CSV loaders, calculations, 21
natural-language question types, known dataset results, and MCP JSON-RPC
integration. For the full quality gate:

```sh
go test -race ./...
go vet ./...
```

## Run

From the repository root:

```sh
go run .
```

Or run the built binary:

```sh
./brazilian-soccer-mcp --data ./data/kaggle
```

The data directory defaults to `data/kaggle`, then to a `data/kaggle`
directory beside the executable. It can also be set with
`BRAZILIAN_SOCCER_DATA` or `--data`.

Example MCP client configuration:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/absolute/path/to/brazilian-soccer-mcp",
      "args": ["--data", "/absolute/path/to/data/kaggle"]
    }
  }
}
```

## MCP surface

| Tool | Purpose |
|---|---|
| `ask` | Rule-based natural-language questions across the dataset |
| `search_matches` | Exact match filters across every match source |
| `team_statistics` | Win/draw/loss, goals, points, and split records |
| `head_to_head` | Meetings and aggregate record for two teams |
| `search_players` | FIFA player lookup and ranking |
| `standings` | Calculated season table with deterministic tie-breaks |
| `competition_statistics` | Goal and result-rate aggregates |
| `biggest_wins` | Largest victory margins |
| `team_competitions` | Competitions containing a given team |
| `club_overview` | Cross-file team, competition, and player view |

The server also exposes `soccer://dataset/summary` as an MCP resource.

Example questions for `ask` include:

- `Show me all Flamengo vs Fluminense matches`
- `What is Corinthians' home record in 2022?`
- `Who won the 2019 Brasileirão?`
- `Show the 2018 Copa Libertadores bracket`
- `Who are the highest-rated Brazilian players?`
- `What's the average goals per match in the Brasileirão?`

Individual top scorers cannot be derived from these files because the match
datasets contain team scores but no goal-scorer events; the server reports that
limitation explicitly rather than fabricating an answer.

## Data and licenses

The datasets and their sources are documented in [TASK.md](TASK.md). They
retain their original licenses: CC BY 4.0, CC0 Public Domain, and Apache 2.0.
