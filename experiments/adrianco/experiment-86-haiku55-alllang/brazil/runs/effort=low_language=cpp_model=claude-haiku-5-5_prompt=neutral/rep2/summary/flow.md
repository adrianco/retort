# Flow

```mermaid
sequenceDiagram
    Client->>main.cpp: launch (--data-dir)
    main.cpp->>data_store.cpp: load_data_store(dir)
    data_store.cpp->>csv.cpp: read 6 CSVs
    data_store.cpp->>team.cpp: parse_team_name / normalize
    data_store.cpp-->>main.cpp: DataStore (matches, players)
    main.cpp->>tools.cpp: make_tools(store)
    main.cpp->>mcp_server.cpp: McpServer.run(cin, cout)
    Client->>mcp_server.cpp: {"method":"tools/call","name":"search_matches",...}
    mcp_server.cpp->>tools.cpp: handler(arguments)
    tools.cpp->>queries.cpp: find_matches(store, MatchQuery)
    queries.cpp-->>tools.cpp: [Match*] (newest first)
    tools.cpp-->>mcp_server.cpp: formatted text
    mcp_server.cpp-->>Client: {"result":{content:[{type:text}],isError:false}}
```

On startup `main` loads all six Kaggle CSVs into an in-memory `DataStore` (matches sorted oldest-first, plus FIFA players), normalizing team names and dropping duplicate/overlapping/unparseable rows, then logs the counts to stderr so stdout stays a clean protocol stream. `McpServer::run` reads one JSON-RPC message per line; a `tools/call` for `search_matches` builds a `MatchQuery` from the arguments (requiring at least one filter), calls `find_matches` to get matching `Match` pointers, formats them into human-readable lines via `format_matches`, and wraps the text in an MCP `content` result. Tool-handler exceptions are caught and returned as `isError:true` text rather than JSON-RPC errors; malformed input validation lives in the `*_arg` helpers (type checks, limit 1-200, date parsing, venue whitelist). Processing is synchronous and single-threaded, in-memory, with no network, pagination (results are capped by `limit` with an "N more in dataset" note), or persistence.
