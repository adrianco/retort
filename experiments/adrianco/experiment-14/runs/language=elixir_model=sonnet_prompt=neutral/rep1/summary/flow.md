# Flow

```mermaid
sequenceDiagram
    Client->>mcp_server.ex: {"method":"tools/call","params":{"name":"search_matches",...}}
    mcp_server.ex->>tools.ex: call_tool("search_matches", args)
    tools.ex->>query_engine.ex: search_matches(params)
    query_engine.ex->>data_store.ex: get_all_matches()
    data_store.ex-->>query_engine.ex: [match]
    query_engine.ex->>team_normalizer.ex: matches?(home/away, team)
    team_normalizer.ex-->>query_engine.ex: bool
    query_engine.ex-->>tools.ex: formatted string
    tools.ex-->>mcp_server.ex: text
    mcp_server.ex-->>Client: {"result":{"content":[{"type":"text",...}],"isError":false}}
```

A `tools/call` line arrives on stdin; `mcp_server.ex` decodes JSON-RPC, dispatches through `tools.ex` to the matching `query_engine.ex` function. The query engine pulls the pre-loaded dataset from the `DataStore` GenServer (CSVs parsed once at app start), filters via composable `filter_by_*` pipelines using `TeamNormalizer` for fuzzy team matching, formats a human-readable string, and the server wraps it in the MCP `content` envelope. Notable: all data is loaded eagerly into memory at startup (30s GenServer call timeouts); tool results are plain formatted strings rather than structured JSON payloads; CSV parse failures degrade to an empty list with a warning rather than crashing.
