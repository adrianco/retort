# Brazilian Soccer MCP Server

A dependency-free C++17 MCP stdio server over the six supplied Kaggle CSV files. It exposes `search_matches`, `team_statistics`, `head_to_head`, `search_players`, `standings`, `analyze`, and `query` (a natural-language convenience tool).

Build and test:

```sh
cmake -S . -B build && cmake --build build && ctest --test-dir build --output-on-failure
```

Run it with `./build/brazilian_soccer_mcp`. The server expects newline-delimited JSON-RPC MCP messages on stdin. By default it loads `data/kaggle`; set `SOCCER_DATA_DIR` to use another data directory.

Example tool call:

```json
{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"team_statistics","arguments":{"team":"Palmeiras","season":"2023","competition":"Brasileirao","venue":"home"}}}
```
