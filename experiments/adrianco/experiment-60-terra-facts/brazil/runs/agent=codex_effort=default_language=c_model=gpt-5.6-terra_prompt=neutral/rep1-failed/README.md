# Brazilian Soccer MCP Server

A dependency-free C17 MCP (Model Context Protocol) server that loads all six bundled Kaggle CSV files and exposes tools for match search, team statistics, head-to-head comparisons, FIFA player search, and calculated standings.

## Build and test

```sh
make
make test
```

## Run

The server uses JSON-RPC over standard input/output, as required by MCP stdio transports. Run it from the repository root:

```sh
./brazilian-soccer-mcp
```

Pass a different data directory as its only argument if needed. It exposes `search_matches`, `team_statistics`, `head_to_head`, `search_players`, and `standings` through `tools/list`.

Team matching is case-, accent-, and state-suffix-tolerant (for example, `São Paulo`, `Sao Paulo`, and `São Paulo-SP` match consistently). The server loads 23,000+ matches and 18,000+ players at startup, then answers queries from memory.
