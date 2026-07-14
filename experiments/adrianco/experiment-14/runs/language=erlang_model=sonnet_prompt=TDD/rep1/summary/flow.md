# Flow

```mermaid
sequenceDiagram
    Client->>br_soccer_mcp_server: {"method":"tools/call","name":"team_stats",...}
    br_soccer_mcp_server->>br_soccer_mcp_handler: handle(Req, Data)
    br_soccer_mcp_handler->>br_soccer_data: all_matches(Data)
    br_soccer_data-->>br_soccer_mcp_handler: [Match]
    br_soccer_mcp_handler->>br_soccer_query: team_stats(Filtered, Team)
    br_soccer_query-->>br_soccer_mcp_handler: #{wins,draws,losses,goals_for,...}
    br_soccer_mcp_handler-->>br_soccer_mcp_server: {ok, jsonrpc_result(Id, content)}
    br_soccer_mcp_server-->>Client: {"result":{"content":[{"type":"text",...}]}}
```

On startup `br_soccer_data:load_all/1` parses all six CSVs once into memory; the
parsed `Data` map is threaded through every request (no per-call IO). A
`tools/call` line is JSON-decoded in `process_line/2`, dispatched by tool name in
`call_tool/3`, which unifies matches via `all_matches/1`, applies
competition → season → team filters, delegates the aggregate to a pure
`br_soccer_query` function, and renders a human-readable text block returned as
MCP `content`.

Notable: results are formatted as plain text rather than structured JSON content;
team matching is case-insensitive substring on state-suffix-normalized names;
parse errors in `process_line/2` are caught and returned as JSON-RPC -32700 rather
than crashing the loop. The OTP app/supervisor scaffolding exists but is unused by
the escript stdio path (empty child specs).
