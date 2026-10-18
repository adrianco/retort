# Flow

```mermaid
sequenceDiagram
    Client->>main.c: start (data-dir)
    main.c->>db.c: db_load(dir)
    db.c->>csv.c: csv_load(each source)
    csv.c-->>db.c: CsvTable
    db.c-->>main.c: Db (matches sorted by date, players by overall)
    Client->>mcp.c: {"method":"tools/call","name":"find_matches",...}
    mcp.c->>json.c: json_parse(line)
    mcp.c->>query.c: query_run(db, "find_matches", args)
    query.c->>db.c: db_find_team(name)
    query.c-->>mcp.c: text + QueryStatus
    mcp.c->>json.c: json_quote(text)
    mcp.c-->>Client: {"result":{"content":[{"type":"text","text":...}],"isError":false}}
```

On startup `main.c` loads the six CSVs via `db.c:db_load`, which de-duplicates overlapping (competition, season) pairs, normalizes team names, marks knockout finals, and sorts matches by date and players by overall rating. The server then reads newline-delimited JSON-RPC requests from stdin in `mcp.c:mcp_serve`; each request is parsed by `json.c`, dispatched by method, and `tools/call` routes through `query.c:query_run` to one of seven tool functions, which filter the in-memory arrays and format a human-readable text block. The result text is JSON-escaped and written back as one line per request. Notifications (requests without an `id`) are intentionally not answered. Errors are reported both as JSON-RPC errors (unknown method/tool, malformed input) and, for tool-level problems like an unresolvable team, as a successful result with `isError:true`.
