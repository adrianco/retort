# Flow

```mermaid
sequenceDiagram
    Client->>main.rs: tools/call query_soccer {sql}
    main.rs->>main.rs: rpc() validate jsonrpc/method/tool
    main.rs->>query(): run SELECT
    query()->>SQLite: stmt.prepare + readonly check
    SQLite-->>query(): rows (deadline 4s, cap 100)
    query()-->>main.rs: {columns, rows, truncated}
    main.rs-->>Client: {content:[text json], isError:false}
```

On startup `main()` calls `data::load()`, which creates an in-memory SQLite DB, registers the
`team_key`/`fold` scalar functions, streams the 6 CSVs into `records`/`players`, reconciles each
raw match row into a deduplicated `matches` row (matching on competition+teams+date/season, folding
team names and normalizing dates), and finally runs `views.sql` to build the `team_results` and
`standings` views and tag cup finals. `secure()` then installs an authorizer that denies anything
but reads and blocks `load_extension`/`writefile`/`readfile`.

Each `tools/call` runs exactly one statement through `query()`, which rejects non-`SELECT`/write
statements (`stmt.readonly()` + column-count check), enforces a 4-second progress deadline, caps
output at 100 rows, and returns columns+rows as JSON text.

Notable deviations from a typical MCP server: a **single generic SQL tool** rather than one tool per
query category — the model pushes all query semantics into SQL and documents the schema in the tool
description. Query safety rests on the SQLite authorizer + `stmt.readonly()` rather than input
parsing. No pagination beyond `LIMIT/OFFSET` the caller supplies; no external API calls.
