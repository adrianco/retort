# Brazilian Soccer MCP Server

A self-contained Objective-C MCP server that reads the six supplied CSV files and exposes JSON-RPC tools over standard input/output.

Build and test:

```sh
make
make tests
```

Run it from the project root (or pass a data directory as the first argument):

```sh
./brazilian-soccer-mcp data/kaggle
```

Supported tools: `search_matches`, `team_statistics`, `head_to_head`, `search_players`, `standings`, and `aggregate_statistics`. Team comparison is accent-insensitive and tolerates common state suffixes such as `-SP` and `-RJ`. Match responses use a common schema across every match source, with ISO dates and numeric scores.

The implementation uses only Apple Foundation; no network calls or third-party dependencies are required.
