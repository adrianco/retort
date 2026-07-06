# Flow

```mermaid
sequenceDiagram
    participant Client as MCP Client/LLM
    participant Server as server.py
    participant Repo as SoccerRepository
    participant Loader as data_loader.load_all
    participant Norm as team_names.normalize_team

    Client->>Server: call find_matches(team="Flamengo-RJ")
    Server->>Server: get_repository() (lazy, cached)
    alt first call only
        Server->>Loader: load_all()
        Loader->>Loader: read 6 CSVs (pandas), build Match/Player
        Loader->>Norm: normalize_team(raw) per row
        Loader->>Loader: _dedupe_overlapping_sources()
        Loader-->>Repo: SoccerData
        Repo->>Repo: index matches by team key
    end
    Server->>Repo: find_matches(team="Flamengo-RJ", ...)
    Repo->>Norm: normalize_team("Flamengo-RJ") -> "flamengo"
    Repo->>Repo: filter self._by_team["flamengo"], sort by date, tail(limit)
    Repo-->>Server: list[Match]
    Server->>Server: [m.to_dict() for m in matches]
    Server-->>Client: list[dict]
```

A client calls an MCP tool such as `find_matches`. The server lazily builds a singleton `SoccerRepository` on first use: `load_all()` reads all six Kaggle CSVs with pandas, normalizes every team name to a canonical key via `normalize_team`, and deduplicates seasons covered by more than one Brasileirao/Copa do Brasil source before the repository indexes matches into a `_by_team` dict. The tool call then normalizes the query team to its key, filters the pre-indexed match list (applying opponent, competition, season, date-range, and venue predicates), sorts by date, truncates to `limit` most-recent, and returns each `Match` serialized via `to_dict()`.

Notable characteristics:
- All data is loaded fully into memory once and served synchronously; no database, no pagination cursor (just a `limit` tail).
- Team-name matching is the central design concern: an alias table plus suffix/parenthetical/accent stripping collapse variant spellings to one key.
- Overlapping source datasets are deduped per (competition, season) by a fixed priority list to avoid double-counting in aggregates like `standings` and `average_goals`.
- Input validation is minimal: dates are parsed with `date.fromisoformat` (raises on malformed input), and `best_record`'s `by` argument does a dict lookup that would `KeyError` on an unknown metric.
