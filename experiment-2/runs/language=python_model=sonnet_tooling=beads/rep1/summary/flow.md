# Flow

```mermaid
sequenceDiagram
    LLM->>server.py: call find_matches(team1, team2)
    server.py->>data_loader.py: store.all_matches()
    data_loader.py->>data_loader.py: lazy-load + normalize CSVs (cached)
    data_loader.py-->>server.py: combined matches DataFrame
    server.py->>server.py: mask by normalized team names, sort, head(limit)
    server.py->>server.py: compute head-to-head W/L/D
    server.py-->>LLM: formatted text result
```

A tool call to `find_matches` pulls the combined matches frame from the `DataStore`
singleton (each underlying CSV is lazily loaded and cached on first access).
Team filtering is done on `home_team_norm`/`away_team_norm` — accent-stripped,
state-suffix-stripped, alias-resolved names — via case-insensitive substring
matching. Results are sorted by datetime descending, truncated to `limit`, and
rendered to a human-readable string; when two teams are given an aggregate
head-to-head record is appended. All tools return formatted strings (not
structured JSON), and all computation is synchronous in-process pandas. Note:
team matching is substring-based, so short queries can over-match (e.g. a team
name that is a substring of another).
