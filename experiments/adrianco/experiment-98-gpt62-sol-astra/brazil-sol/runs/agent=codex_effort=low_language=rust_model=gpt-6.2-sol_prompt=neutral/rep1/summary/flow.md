# Flow

```mermaid
sequenceDiagram
    Client->>main.rs: launch (stdin/stdout)
    main.rs->>data.rs: Graph::load("data/kaggle")
    data.rs->>data.rs: parse 6 CSVs, normalize teams, build+dedup fixtures
    data.rs-->>main.rs: Graph
    main.rs->>lib.rs: serve(graph, stdin, stdout)
    Client->>lib.rs: initialize
    lib.rs-->>Client: protocolVersion + tools capability
    Client->>lib.rs: tools/call {search_matches, args}
    lib.rs->>query.rs: Graph::call("search_matches", args)
    query.rs->>query.rs: deserialize Filter, filter fixtures, paginate
    query.rs-->>lib.rs: JSON result
    lib.rs-->>Client: content[text] + structuredContent
```

At startup `Graph::load` reads all six CSVs once, normalizing team names (accent folding + an alias table resolving suffixes like `-SP` and full club names), parsing both ISO and `DD/MM/YYYY` dates, and merging duplicate match records across feeds into a deduplicated `fixtures` list while retaining raw rows for per-source queries. The server then reads newline-delimited JSON-RPC from stdin; after `initialize` negotiates a protocol version, each `tools/call` deserializes a strongly-typed argument struct (`deny_unknown_fields`), filters the in-memory data, and returns both a text rendering and `structuredContent`. Notable: fully in-memory (no external APIs, no async), strict argument validation rejects unknown fields, pagination via `limit`/`offset`/`next_offset`, and standings/relegation are computed from scores (with a double-round-robin completeness guard) rather than hardcoded.
