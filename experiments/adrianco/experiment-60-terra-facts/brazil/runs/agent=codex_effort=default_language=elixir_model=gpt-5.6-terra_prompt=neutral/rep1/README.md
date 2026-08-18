# Brazilian Soccer MCP

An Elixir MCP server that loads all six supplied Kaggle CSV files into an in-memory, normalized soccer catalog. It exposes structured MCP tools for an LLM to answer match, team, player, standings, and aggregate-statistics questions.

## Run

```sh
mix escript.build
./brazilian_soccer_mcp
```

The process communicates through standard input/output using JSON-RPC 2.0. Configure an MCP client with the generated `./brazilian_soccer_mcp` executable as its command. Data is loaded lazily from `data/kaggle/` on the first tool invocation. `mix run -e 'BrazilianSoccerMcp.MCP.run()'` also remains useful during development.

## Tools

- `search_matches`: filters by `team`, `team_a`, `team_b`, `competition`, `season`, `from`, `to`, `stage`, and `limit`.
- `team_statistics`: accepts `team`, plus the match filters and optional `venue` (`home`, `away`, or `all`).
- `compare_teams`: accepts `team_a`, `team_b`, and optional match filters.
- `search_players`: filters FIFA data by `name`, `nationality`, `club`, `position`, and `limit`.
- `standings`: accepts `season` and optional `competition` (default `Brasileirão`).
- `competition_statistics`: supplies goal averages, home/draw/away outcomes, and biggest wins.
- `catalog_summary`: reports source and record coverage.

Team matching ignores accents and state suffixes, so `São Paulo-SP`, `Sao Paulo`, and `São Paulo` resolve consistently. Dates are normalized from ISO, timestamp, and `DD/MM/YYYY` formats.

## Verify

```sh
mix test
```
