# Brazilian Soccer MCP Server

A dependency-free Swift MCP server over the six supplied Kaggle CSV files. It exposes match search, team records, head-to-head comparison, player search, calculated standings, competition statistics, biggest wins, and a team's competition history.

## Run

```sh
swift run --disable-sandbox brazilian-soccer-mcp
```

The server communicates over JSON-RPC on standard input/output. It loads `data/kaggle` by default; set `BRAZILIAN_SOCCER_DATA` to use another directory.

For this restricted environment, run tests with:

```sh
CLANG_MODULE_CACHE_PATH=/tmp/brazilian-soccer-swift-cache swift test --disable-sandbox
```
