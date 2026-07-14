# Flow

```mermaid
sequenceDiagram
    Client->>server.clj: JSON-RPC line "tools/call" find_matches
    server.clj->>server.clj: process-line (json parse)
    server.clj->>tools.clj: by-name lookup -> tool :handler
    tools.clj->>query.clj: find-matches(dataset, args)
    query.clj->>query.clj: filter-matches (team/season/competition)
    query.clj-->>tools.clj: human-readable answer text
    tools.clj-->>server.clj: {:content [{:type "text" :text ...}]}
    server.clj-->>Client: JSON-RPC result line
```

A client sends a `tools/call` JSON-RPC line on stdin. `process-line` parses it and `handle-request` dispatches by method; for `tools/call` it looks the tool up in `tools/by-name`, invokes its `:handler` against the pre-loaded dataset (built once at `create-server` from `data/kaggle`), and wraps the returned answer string as MCP text content. Queries run over the in-memory normalized model, so no CSV is re-read per request. Tool-handler exceptions are caught and returned as JSON-RPC error `-32603`; unknown tools return `-32601`. The dataset is loaded eagerly at startup and held in memory — there is no pagination or streaming, and all filtering is linear scan over the normalized match/player vectors.
