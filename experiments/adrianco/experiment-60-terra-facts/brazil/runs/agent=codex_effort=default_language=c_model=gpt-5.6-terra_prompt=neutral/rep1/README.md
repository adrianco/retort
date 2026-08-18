# Brazilian Soccer MCP Server

A dependency-free C17 MCP (Model Context Protocol) server that loads all six bundled Kaggle CSV files and exposes tools for match search, team statistics, head-to-head comparisons, FIFA player search, calculated standings, and aggregate analysis.

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

Pass a different data directory as its only argument if needed. It exposes `search_matches`, `team_statistics`, `head_to_head`, `search_players`, `standings`, and `dataset_statistics` through `tools/list`, plus a dataset resource through `resources/list`.

Team matching is case-, accent-, and state-suffix-tolerant (for example, `São Paulo`, `Sao Paulo`, and `São Paulo-SP` match consistently). Standings and aggregate analysis use one canonical source per competition/season so the historical and extended files do not double-count overlapping results. The server loads 23,000+ matches and 18,000+ players at startup, then answers queries from memory.
