# Flow

```mermaid
sequenceDiagram
    Client->>server.py: call_tool find_matches(team, season)
    server.py->>repository.py: repo.find_matches(...)
    repository.py->>repository.py: _filter_matches() — normalize keys, match team/season/comp/date
    repository.py->>normalize.py: team_key() / competition_key() / parse_date()
    normalize.py-->>repository.py: canonical keys
    repository.py-->>server.py: [Match] (sorted by date, capped at limit)
    server.py->>models.py: Match.to_dict() per match
    models.py-->>server.py: JSON-friendly dicts
    server.py-->>Client: {count, matches[]}
```

A tool call enters through the FastMCP server (`server.py`), which is a thin
adapter: it forwards arguments to the matching `SoccerRepository` method. The
repository normalizes inputs (team names stripped of state suffixes/accents,
competitions canonicalized, dates parsed from multiple formats) via
`normalize.py`, filters the in-memory `Match`/`Player` lists, computes any
aggregates (records, standings, statistics), and returns plain values that
`models.py` serializes with `to_dict()`. Data is loaded once at
`create_server()` time by `data_loader.load_dataset()`, which dedups matches
that overlap across the source CSVs.

Deviations / notes:
- `find_matches` applies a default `limit=50` and reports `count` as the size of
  the *truncated* list, so a query with >50 results gives no signal that more
  exist.
- Standings dedup to a single dominant source file per season
  (`_dominant_source_only`) to avoid double-counting, but `statistics()` and
  `biggest_wins()` aggregate across all sources without that dedup.
- No network/API access at query time; all data is in memory. No input
  validation beyond tolerant parsing (malformed rows are dropped, not errored).
