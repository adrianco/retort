# Flow

```mermaid
sequenceDiagram
    Client->>mcp.go: tools/call {name:"standings", season:2019}
    mcp.go->>tools.go: Handler(args)
    tools.go->>queries.go: Store.Standings(2019, "")
    queries.go->>store.go: iterate Store.Matches
    store.go-->>queries.go: filtered matches (season+competition, HasGoals)
    queries.go->>queries.go: tally 3/1/0 points per team, sort by pts/GD/GF
    queries.go-->>tools.go: StandingsResult{table, champion}
    tools.go-->>mcp.go: MarshalIndent -> text content
    mcp.go-->>Client: 200 {result:{content:[{type:text,...}]}}
```

At startup `main.go` resolves the data dir (flag → `BRAZIL_MCP_DATA_DIR` → `./data/kaggle`),
`load.go:LoadStore` parses all six CSVs into a single in-memory `Store`, normalizing team
names and deduplicating overlapping real-world matches by season cutoff. Each `tools/call`
request dispatches through `mcp.go` to a `tools.go` handler that calls the matching
`queries.go` method, which linearly scans `Store.Matches`/`Store.Players` with the request
filters and returns a typed result marshaled back as MCP text content.

Notable characteristics: stdlib-only (no MCP SDK — the JSON-RPC server is hand-rolled);
newline-delimited framing rather than Content-Length; queries are O(n) linear scans (no
indexes) — acceptable at this dataset scale. Team resolution is fuzzy: a bare name resolves
to all state variants sharing a base, while an explicit state suffix pins one club. Errors
inside a tool handler are returned as `isError:true` content rather than JSON-RPC errors.
