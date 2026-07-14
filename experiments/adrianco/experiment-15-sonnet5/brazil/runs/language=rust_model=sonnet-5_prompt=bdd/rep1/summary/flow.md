# Flow

```mermaid
sequenceDiagram
    Client->>main.rs: launch (stdio)
    main.rs->>loaders.rs: load_from_dir(data/kaggle)
    loaders.rs->>normalize.rs: normalize_team_name / display_team_name
    loaders.rs->>dates.rs: parse_flexible_date
    loaders.rs-->>main.rs: KnowledgeBase (matches + players)
    main.rs->>server.rs: BrazilianSoccerServer::new(kb)
    Client->>server.rs: tools/call find_matches {team, competition, season}
    server.rs->>store.rs: find_matches(&filter, limit)
    store.rs->>normalize.rs: name_matches for team filter
    store.rs-->>server.rs: FindMatchesResult
    server.rs-->>Client: Json result (matches + total_count)
```

At startup the binary loads all six CSVs once into an in-memory `KnowledgeBase`, normalizing team names and parsing mixed date formats as it goes (rows with unrecorded results — goals logged as `"NA"`/`"-"` — are skipped). The server is then served over stdio via `rmcp`. Each MCP `tools/call` is a stateless, read-only lookup against the shared `Arc<KnowledgeBase>`: e.g. `find_matches` builds a `MatchFilter`, filters via flexible team-name matching (state suffixes, accents, and full-vs-abbreviated legal names handled, while disambiguating region codes like `-MG`/`-PR` are preserved), sorts newest-first, and returns a JSON result including `total_count` before truncation by `limit`. Team-name normalization is the load-bearing cross-cutting concern shared by loaders and every match query.
