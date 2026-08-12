# Flow

```mermaid
sequenceDiagram
    Client->>main.rs: JSON-RPC {"method":"tools/call","name":"standings","season":2019}
    main.rs->>mcp.rs: McpServer::handle(request)
    mcp.rs->>mcp.rs: call_tool → required_u16("season")
    mcp.rs->>store.rs: standings(2019, "Brasileirão")
    store.rs->>store.rs: search_matches(filter, MAX)
    store.rs->>store.rs: unique_match_indices (dedup ±1 day)
    store.rs->>normalize.rs: team_key() / competition_key()
    normalize.rs-->>store.rs: canonical keys
    store.rs->>store.rs: apply_match() → accumulate TeamStats per team
    store.rs->>store.rs: sort by points, GD, goals_for
    store.rs-->>mcp.rs: Vec<Standing>
    mcp.rs-->>main.rs: {content:[text], structuredContent:{standings}}
    main.rs-->>Client: JSON-RPC result line
```

At startup `main.rs` calls `SoccerStore::load`, which reads all six CSVs, then builds a deduplicated fixture index by canonicalizing `(date, season, competition, home_team, away_team)` — collapsing rows that repeat across the five overlapping match files, allowing a ±1-day date offset to reconcile local-vs-UTC kickoff dates. Each JSON-RPC request line is parsed and dispatched by `McpServer::handle`; a `standings` call filters the deduplicated matches by season/competition, accumulates `TeamStats` for the home and away side of every fixture (3 points win / 1 draw), sorts by points then goal difference then goals scored, and returns both a text table and structured JSON. Notable: fixture dedup and team-name normalization (accent folding, `-SP`/`-MG` state-suffix stripping, alias table with explicit disambiguation for América/Atlético/Athletico/Botafogo) are the two mechanisms the repair targeted — the FEEDBACK flagged inflated records from surviving duplicates and both over-merged and fragmented clubs. Team names are canonicalized to a lowercase key for matching and title-cased for display. No input beyond argument type-checks is validated; queries run as linear scans over the in-memory match/player vectors (no index), and the data is loaded once per process.
