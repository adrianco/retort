# Flow

```mermaid
sequenceDiagram
    Client->>server.py: call tool head_to_head("Flamengo","Fluminense")
    server.py->>server.py: get_graph() (load_graph, cached)
    server.py->>queries.py: head_to_head(graph, "Flamengo", "Fluminense")
    queries.py->>graph.py: resolve_team("Flamengo") / resolve_team("Fluminense")
    graph.py->>teams.py: registry.resolve(query)
    teams.py-->>graph.py: Team(team_id)
    queries.py->>graph.py: team_matches(a_id) filtered by opponent
    graph.py-->>queries.py: [Match]
    queries.py->>models.py: TeamRecord.add(match) per match
    queries.py-->>server.py: dict {wins, draws, goals, matches...}
    server.py->>formatting.py: format_head_to_head(dict)
    formatting.py-->>server.py: human-readable text
    server.py-->>Client: text result
```

A tool call resolves free-text team names through the `TeamRegistry` (accent-
and suffix-tolerant, e.g. "Flamengo", "flamengo-rj", "Palmeiras-SP" all map to a
canonical id), pulls the pre-indexed matches for the team from the
`KnowledgeGraph`, filters to the opponent, aggregates with `TeamRecord`, and
returns a JSON-friendly dict which the `formatting` layer renders as text the
LLM can quote. The graph itself is built once per process from the six CSVs by
`loader.load_dataset` — which de-duplicates the same fixture appearing in
multiple source files within a 45-day window so standings and records are not
triple-counted. Lookup failures are turned into guidance (`UnknownTeamError`
with suggestions) rather than exceptions, via the `_guard` wrapper in `server.py`.
Notable: pure standard-library data layer (no pandas); the only runtime
dependency is the MCP SDK. Standings deliberately withhold a "champion" label
when the source data is missing fixtures for that season.
