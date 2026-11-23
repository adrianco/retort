# Flow

```mermaid
sequenceDiagram
    Client->>server.py: {"method":"tools/call","params":{"name":"statistics","arguments":{"competition_name":"Serie A","season":2019}}}
    server.py->>server.py: dispatch() validates jsonrpc/method/params
    server.py->>server.py: type-check args against TOOLS[name] schema
    server.py->>Graph: statistics(competition_name="Serie A", season=2019)
    Graph->>Graph: select() iterates matches, de-dups overlapping league sources
    Graph->>Graph: accumulate W/L/D, goals, points per team; rank
    Graph-->>server.py: {matches, goals_per_match, home_win_rate, results:[...]}
    server.py-->>Client: {"result":{"content":[{"type":"text","text":"{...}"}]}}
```

A `tools/call` request is validated by `dispatch()` (JSON-RPC envelope, known tool, per-argument type check against the declared schema), then routed to the matching `Graph` method by name. For `statistics`, `Graph.select()` streams matches, suppressing duplicate league fixtures that appear in multiple source CSVs (it keeps only the canonical `Brasileirao_Matches` copy for seasons present there), re-orients each score to the home/away club, and tallies points (3/1/0). The result is JSON-serialized into MCP `content`. Notable: graph is built once at startup in `Graph.__init__`; notifications (no `id`) return `None` and emit no response; argument validation rejects wrong-typed params with `isError` rather than crashing the session; team-name normalization (`fold`/`club`/`ALIASES`/`DEFAULT_STATE`) reconciles state-suffixed, accented, and full-name variants across datasets.
