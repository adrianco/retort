# Flow

```mermaid
sequenceDiagram
    Client->>server.ts: call tool "standings" {competition, season}
    server.ts->>competitions.ts: calculateStandings(store, competition, season)
    competitions.ts->>store: matches filtered by competition/season
    store-->>competitions.ts: Match[]
    competitions.ts->>competitions.ts: tally points, W/D/L, goals; sort by CBF tie-breaks
    competitions.ts-->>server.ts: StandingsRow[]
    server.ts-->>Client: text table
```

On startup, `index.ts` calls `SoccerDataStore.load(DATA_DIR)`, which reads all six CSVs, normalizes team names/dates, deduplicates overlapping seasons (primary source per competition/season; secondary sources fill gaps only), and builds by-team / by-club indices. `createServer(store)` registers 14 MCP tools over stdio.

A representative request — the `standings` tool — filters the store's matches to one competition/season, aggregates points and goals per team, and sorts using CBF tie-break order (points → wins → goal difference → goals scored) so the calculated 2019 Brasileirão table matches the spec's worked example. All queries run against the in-memory store; latency is sub-10ms. Team lookups go through `normalizeTeamName` so accent/suffix variants (e.g. "Gremio" → "Grêmio") resolve to one canonical key, while a curated alias table keeps genuinely distinct clubs (Atlético-MG vs Athletico-PR) separate.
