# Flow

```mermaid
sequenceDiagram
    Client->>main.c: {"method":"tools/call","params":{"name":"head_to_head",...}}
    main.c->>mcp.c: mcp_handle(db, line)
    mcp.c->>mcp.c: json_parse(line)
    mcp.c->>mcp.c: mcp_call_tool(db, "head_to_head", args)
    mcp.c->>query.c: q_head_to_head(db, team1, team2, comp, out)
    query.c->>data.c: team_key() / comp_canon() normalization
    query.c-->>mcp.c: human-readable text in sb_t
    mcp.c-->>main.c: JSON-RPC result {content:[{type:text,...}]}
    main.c-->>Client: response line on stdout
```

At startup `main.c` calls `data.c:db_load()` once, which reads all six CSVs into arrays and de-duplicates overlapping match records. Each stdin line is parsed by the hand-written JSON parser in `mcp.c`; `tools/call` dispatches by name to a `q_*` function in `query.c`, which filters/aggregates the in-memory arrays (normalizing team names and competitions via `data.c`) and writes formatted text into a growable `sb_t` buffer. The text is JSON-escaped back into a JSON-RPC `result`. Notable: dependency-free C11 (libc only); no persistence or network; team-name normalization (accent folding, state-suffix disambiguation for ambiguous names like Atlético/América/Botafogo) is the main source of complexity.
