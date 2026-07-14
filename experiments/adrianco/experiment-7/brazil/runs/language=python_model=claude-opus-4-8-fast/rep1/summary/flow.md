# Flow

```mermaid
sequenceDiagram
    LLM->>server.py: find_matches(team="Flamengo", opponent="Fluminense")
    server.py->>knowledge_graph.py: get_knowledge_graph()
    knowledge_graph.py->>data_loader.py: load_all() (lazy, cached)
    data_loader.py-->>knowledge_graph.py: (matches, players) DataFrames
    server.py->>knowledge_graph.py: find_matches(...)
    knowledge_graph.py->>normalize.py: canonical_norm() for team masks
    knowledge_graph.py-->>server.py: [match dict]
    server.py->>formatting.py: format_matches(...)
    formatting.py-->>server.py: text answer
    server.py-->>LLM: formatted string
```

The first tool call triggers a lazy, cached load of the six Kaggle CSVs into two
DataFrames (`data_loader.load_all`), so start-up is instant and the heavy parse
happens once. Each tool is a thin adapter: it forwards validated arguments to a
`KnowledgeGraph` method, which filters/aggregates the normalised tables using
accent- and suffix-insensitive team masks from `normalize.py`, then renders the
plain dict/list result to text via `formatting.py`. All business logic lives in
`KnowledgeGraph` (transport-agnostic), which is why the suite can test it without
a running server. Overlapping Série A sources are deduplicated by source priority
at load time so standings/aggregate stats are not inflated by duplicate fixtures.
