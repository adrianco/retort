# Flow

```mermaid
sequenceDiagram
    Client->>server.py: {"method":"tools/call","params":{"name":"search_matches","arguments":{...}}}
    server.py->>server.py: validate(arguments, inputSchema)
    server.py->>soccer.py: SoccerGraph.search_matches(**arguments)
    soccer.py->>soccer.py: _select(...) filters self.by_team / self.matches
    soccer.py->>soccer.py: page(rows, limit, offset)
    soccer.py-->>server.py: {total, offset, items, next_offset}
    server.py-->>Client: {"result":{"content":[...],"structuredContent":{...},"isError":false}}
```

On construction, `SoccerGraph.__init__` reads all six CSVs once, normalizes team names,
converts rows to a common match shape, and **deduplicates the same fixture across sources**
(merging by competition/date/teams, or by matching scores within one day), building
`self.matches`, `self.players`, and a `by_team` index. A `tools/call` request is parsed from a
stdin line, validated against the tool's generated JSON-Schema, dispatched to the matching
`SoccerGraph` method, and returned as both `content` text and `structuredContent`. Errors raised
by the engine (`ValueError`/`TypeError`/`KeyError`) are returned as `isError: true` results rather
than JSON-RPC errors. Input validation, UTF-8 handling, multi-format date parsing, pagination, and
provenance tracking are all present; there is no network access or external dependency.
