# Flow

```mermaid
sequenceDiagram
    Client->>cli.ex: JSON-RPC line (stdin)
    cli.ex->>server.ex: handle_line(line, store)
    server.ex->>server.ex: Jason.decode, dispatch by method
    server.ex->>tools.ex: call("search_matches", args, store)
    tools.ex->>tools.ex: match_opts(args) — validate/canonicalize
    tools.ex->>query.ex: find_matches(store, opts)
    query.ex-->>tools.ex: [Match] (filtered, most recent first)
    tools.ex->>format.ex: head_to_head_summary + match_list
    format.ex-->>tools.ex: plain text
    tools.ex-->>server.ex: {:ok, text}
    server.ex-->>cli.ex: encoded {result:{content:[{text}]}}
    cli.ex-->>Client: response line (stdout)
```

A client sends one JSON-RPC line per request. `cli.ex:serve/3` reads it, `server.ex:handle_line/2` decodes and dispatches by method. For `tools/call`, `tools.ex` validates and canonicalizes arguments (competition names, seasons, dates, venue) returning a readable `{:error, msg}` on bad input rather than crashing, then runs a pure `query.ex` function over the pre-loaded in-memory `Store`. `format.ex` renders the result as spec-formatted plain text, and `server.ex` wraps it in an MCP `content` block. All data is loaded once at start-up in `cli.ex:main/1`; queries touch no I/O.

Notable: clean separation of protocol / tools / pure query / formatting; argument errors are surfaced as tool `isError` results, not exceptions; no network access (optional APIs in the spec were correctly skipped in favor of the provided CSVs); start-up ~2.5s, queries in milliseconds.
