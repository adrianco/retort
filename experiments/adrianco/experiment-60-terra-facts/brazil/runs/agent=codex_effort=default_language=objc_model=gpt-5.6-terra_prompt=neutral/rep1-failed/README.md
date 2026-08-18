# Brazilian Soccer MCP Server

A self-contained Objective-C MCP server that exposes the supplied Brazilian soccer CSV files as MCP tools over JSON-RPC stdio. It has no network or database dependency and loads the five match datasets plus the FIFA player dataset on startup.

## Build and test

```sh
make
make test
```

Run it from the repository root (or supply another CSV folder):

```sh
./brazilian-soccer-mcp
./brazilian-soccer-mcp --data /path/to/data/kaggle
```

The server implements `initialize`, `tools/list`, and `tools/call` for these tools:

- `search_matches` — team, opponent, competition, season, and date filtering across every match CSV.
- `team_statistics` and `head_to_head` — calculated records, goals, and recent meetings.
- `search_players` — FIFA name, nationality, club, and position lookup.
- `standings` and `competition_statistics` — calculated tables and aggregates.
- `ask_brazilian_soccer` — a small convenience entry point for simple natural-language questions; an MCP client/LLM should use the structured tools for complete natural-language coverage.

Team matching folds accents and common state suffixes (`Palmeiras-SP` matches `Palmeiras`), and input/output use UTF-8. The BDD-style integration test suite verifies the MCP protocol and the core match, player, statistics, comparison, standings, and aggregate flows.
