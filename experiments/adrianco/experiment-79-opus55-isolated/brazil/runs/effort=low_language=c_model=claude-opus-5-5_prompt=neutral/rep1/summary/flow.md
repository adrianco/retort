# Flow

```mermaid
sequenceDiagram
    Client->>main.c: JSON-RPC line (stdin)
    main.c->>mcp.c: mcp_handle(db, line)
    mcp.c->>json.c: json_parse(message)
    mcp.c->>mcp.c: dispatch tools/call
    mcp.c->>mcp.c: run_tool() maps args -> Params
    mcp.c->>soccer.c: q_search_matches(db, &p, &out)
    soccer.c->>soccer.c: db_find_team() + filter Match[]
    soccer.c-->>mcp.c: formatted text answer
    mcp.c-->>main.c: {"result":{"content":[{"type":"text",...}]}}
    main.c-->>Client: JSON-RPC response line (stdout)
```

At startup `main()` calls `db_load()`, which reads the six CSVs, normalizes and de-duplicates matches, and builds a FIFA player index sorted by overall rating. Each stdin line is parsed as JSON-RPC by `mcp_handle`; a `tools/call` request resolves the named tool, `run_tool` maps its JSON arguments onto the shared `Params` struct (validating required args and types), and the corresponding `q_*` function walks the in-memory data and writes a human-readable text answer. The answer is wrapped as MCP `content` and written back to stdout, with all logging kept on stderr so the protocol stream stays clean. Team names are matched loosely (accents and state suffixes optional). Errors are reported as tool results with `isError:true` rather than transport-level failures.
