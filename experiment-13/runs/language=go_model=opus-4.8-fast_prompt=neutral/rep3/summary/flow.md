# Flow

```mermaid
sequenceDiagram
    Client->>main.go: launch (stdin/stdout pipe)
    main.go->>soccer.Load: Load(dataDir)
    soccer.Load->>soccer.Load: read 6 CSVs, dedup by source, finalizeTeams
    soccer.Load-->>main.go: *DB
    main.go->>mcp.NewServer: NewServer(db) registers 7 tools
    Client->>server.go: {"method":"tools/call","params":{name:"standings",arguments:{season:2019}}}
    server.go->>tools.go: handler(args)
    tools.go->>query.go: db.Standings("Brasileirão Série A", 2019)
    query.go-->>tools.go: []Record (sorted table)
    tools.go->>format.go: db.FormatStandings(...)
    format.go-->>tools.go: text answer
    tools.go-->>server.go: text
    server.go-->>Client: {"result":{"content":[{type:"text",text}],"isError":false}}
```

At startup `main.go` loads the six bundled Kaggle CSVs into an in-memory
knowledge graph: each loader maps its file's columns onto the common `Match`
shape, `selectCoverage` keeps a single authoritative source per
(competition, season) to avoid cross-file duplication, and `finalizeTeams`
resolves team-name variants (state suffixes, accents, full names) into canonical
keys — disambiguating by region only when a base name is genuinely shared by
multiple major clubs. The server then serves MCP over stdio: each request line
is JSON-RPC-decoded, dispatched by method, and (for `tools/call`) routed to a
tool handler that parses loosely-typed LLM arguments, runs a pure query against
the graph, and formats the result as text. Tool-level errors are returned in the
MCP result envelope (`isError:true`) rather than as JSON-RPC errors, so the model
can read the message. No network access; the optional external APIs in the spec
are not used.
