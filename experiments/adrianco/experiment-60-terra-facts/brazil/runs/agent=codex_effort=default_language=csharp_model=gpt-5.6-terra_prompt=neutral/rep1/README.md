# Brazilian Soccer MCP Server

A dependency-free .NET 10 MCP server that exposes the six supplied Brazilian soccer CSV datasets over standard input/output using JSON-RPC 2.0.

## Run

From the repository root:

```bash
dotnet run --project BrazilianSoccerMcp.csproj
```

The server locates `data/kaggle` automatically. Pass a different data directory as the first argument if needed.

## MCP tools

- `search_matches`: filter by team, opponent, competition, season, date range, or stage.
- `team_statistics`: wins/draws/losses, goals, and venue-specific records.
- `head_to_head`: compares two teams and lists their meetings.
- `search_players`: filters FIFA player data by name, nationality, club, or position.
- `competition_standings`: calculates a season table from results.
- `analyze_matches`: aggregate goals, outcomes, and biggest wins.
- `dataset_summary`: confirms loaded data coverage.
- `query_soccer`: convenience natural-language query for common requests.

Team matching is case-insensitive and normalizes state suffixes such as `Palmeiras-SP`. Dates in ISO, ISO-with-time, and Brazilian `DD/MM/YYYY` formats are supported.

## Example request

```json
{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"team_statistics","arguments":{"team":"Corinthians","season":2022,"competition":"Brasileirao","venue":"home"}}}
```

## Verify

```bash
dotnet build BrazilianSoccerMcp.csproj
dotnet run --project tests/BrazilianSoccerMcp.Tests/BrazilianSoccerMcp.Tests.csproj
```
