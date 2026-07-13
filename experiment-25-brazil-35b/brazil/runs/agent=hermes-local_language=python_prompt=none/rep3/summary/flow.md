# Flow

```mermaid
sequenceDiagram
    participant Client
    participant server as server.py
    participant loader as MatchDataset (data_loader.py)
    participant KG as KnowledgeGraph (knowledge_graph.py)

    Note over server,KG: startup — initialize()
    server->>loader: load_all()
    loader->>loader: read 6 CSVs, normalize names/dates, build all_matches/all_players/all_teams
    server->>KG: KnowledgeGraph(dataset)
    KG->>KG: _build_graph() adds team/match/competition/season/player nodes + edges

    Note over Client,loader: request — search_matches(team="Flamengo")
    Client->>server: search_matches(team)
    server->>loader: get_match_by_criteria(team=...)
    loader->>loader: normalize_team_name(team); filter all_matches
    loader-->>server: [match dicts]
    server->>loader: get_team_statistics(team)
    loader-->>server: {wins, draws, losses, goals, win_rate}
    server-->>Client: {success, message, data:{matches, count, team_statistics}}
```

At startup `initialize()` calls `MatchDataset.load_all()`, which reads the six CSVs with pandas, normalizes team names (strip state/country suffixes, accents, lowercase-hyphenate), parses ISO and Brazilian date formats, and flattens the five match tables into a single `all_matches` list plus `all_players` and `all_teams`. It then constructs a `KnowledgeGraph` (NetworkX `MultiDiGraph`). A `search_matches` call normalizes the team name, filters `all_matches` in Python, and — when a team is given — also computes team statistics; the tool returns a plain `{success, message, data}` dict.

Notable deviations from common patterns:
- Data loading and all query filtering iterate row-by-row with `df.iterrows()` / Python list comprehensions rather than vectorized pandas, and re-scan every DataFrame per query (no indexing/caching).
- Pydantic models in `models.py` are defined but unused by the tools, which pass raw params and return untyped dicts.
- `KnowledgeGraph.get_connected_teams` references an undefined variable `next_hop` (line 119), so that branch raises `NameError` at runtime.
- No pagination on match results (list sliced only for display formatting); the graph stores every match as a node.
