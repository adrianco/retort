# Flow

```mermaid
sequenceDiagram
    Client->>main.go: initialize
    main.go-->>Client: protocolVersion + tools capability
    Client->>main.go: tools/call {name:"head_to_head", arguments:{team,opponent}}
    main.go->>query.go: Graph.Query("head_to_head", Filter)
    query.go->>query.go: Filter.validate()
    query.go->>query.go: Graph.matches(f)  (filter + dedup-aware slice)
    query.go->>query.go: accumulate Record from each match
    query.go-->>main.go: {record, home, away, by_season, ...}
    main.go-->>Client: result {content:[text], structuredContent, isError:false}
```

At startup `main()` calls `Load("data/kaggle")`, which reads all six CSVs, normalizes team names (accent-folding + state-suffix stripping + alias table) and dates (multiple layouts), and **deduplicates matches across overlapping sources** (Serie A keyed by competition|season|home|away, merging provenance and reconciling conflicting scores with a warning). `Serve` then runs a JSON-RPC read loop over stdin. A `tools/call` validates the decoded `Filter` (rejecting unknown fields, bad venue/date/limit), filters `g.Matches`, aggregates into the tool-specific shape, and returns both a text rendering and `structuredContent`. Query errors surface as `isError:true` tool results rather than protocol errors. All handlers are read-only.
