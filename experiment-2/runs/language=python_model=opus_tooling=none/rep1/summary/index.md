# Architecture Summary: Brazilian Soccer MCP Server

## Overview

A Python MCP (Model Context Protocol) server providing a knowledge graph interface for Brazilian soccer data. The server exposes 7 tools via FastMCP for querying match histories, team statistics, player information, and competition standings across 6 Kaggle datasets.

## System Design

```
┌─────────────────────────────────────────────────────────┐
│  MCP Server (FastMCP) - brazilian_soccer/server.py      │
│  ┌─────────────────────────────────────────────────────┐ │
│  │  Tools: find_matches, head_to_head, team_stats,    │ │
│  │         standings, biggest_wins, average_goals,    │ │
│  │         search_players                             │ │
│  └─────────────────────────────────────────────────────┘ │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
┌───────▼────────────┐  ┌────────▼──────────────┐
│  Data Layer        │  │  Player Data          │
│  SoccerData        │  │  fifa_data.csv        │
│  (data.py)         │  │  (18,207 players)     │
└──────────┬─────────┘  └───────────────────────┘
           │
    ┌──────┴──────────────────────────┐
    │  6 CSV Datasets                 │
    ├─────────────────────────────────┤
    │ • Brasileirão Matches (4,180)   │
    │ • Copa do Brasil (1,337)        │
    │ • Libertadores (1,255)          │
    │ • BR Football Extended (10,296) │
    │ • Historical Brasileirão (6,886)│
    │ • FIFA Players (18,207)         │
    └────────────────────────────────┘
```

## Key Components

### 1. MCP Server (server.py)
- **Framework:** FastMCP
- **Role:** HTTP endpoint for LLM integration
- **Tools:** 7 query handlers with standardized JSON output
- **JSON Serialization:** Handles NaN, datetime objects via custom `_df_to_records()`

### 2. Data Layer (data.py)
- **Class:** `SoccerData` — singleton dataclass managing all datasets
- **Loading:** Lazy-loads 6 CSV files from `data/kaggle/` on first access
- **Normalization:** `normalize_team()` handles state suffixes ("SP", "RJ"), accents (São Paulo → Sao Paulo), and aliases
- **Caching:** `@lru_cache` on `get_data()` for performance
- **Query Methods:** 8 methods for match/player filtering and aggregation

### 3. Testing (test_data.py)
- **Coverage:** 19 tests across 6 feature areas (normalization, loading, matching, aggregates, players)
- **Approach:** Unit tests on data transformations; no mocking (real CSV files)
- **Pass Rate:** 100% (19/19)

## Data Flow

1. **Server Startup:** `FastMCP` server imports `SoccerData.get_data()`
2. **First Query:** `get_data()` triggers `SoccerData.load()` (reads 6 CSVs)
3. **Team Normalization:** Query team names → `normalize_team()` → consistent lookups
4. **Query Execution:** Tool handler filters/aggregates dataframes
5. **JSON Response:** Results serialized via `_df_to_records()` → LLM

## Dependencies

- **mcp** (Model Context Protocol) — FastMCP server framework
- **pandas** — Data manipulation and aggregation

## Metrics

| Metric | Value |
|--------|-------|
| Source code | 647 lines (3 modules) |
| Tests | 19 (0% skipped) |
| Functions/Methods | ~25 public, ~10 private |
| Data sources | 6 CSV files |
| Supported queries | 7 MCP tools covering matches, teams, players, standings |

## Strengths

1. **Separation of Concerns:** Clean layers (MCP server, data querying, CSV loading)
2. **Robustness:** Handles Portuguese diacritics, multiple date formats, team name aliases
3. **Performance:** Lazy loading, @lru_cache prevents re-processing CSVs
4. **Testability:** All query methods unit tested with real datasets
5. **Interoperability:** FastMCP exposes standard tool interface for any MCP client

## Limitations

1. **No Persistence:** Re-reads CSVs on each server restart (acceptable for demo use)
2. **In-Memory:** All 6 datasets must fit in RAM (~50MB uncompressed)
3. **Static Data:** No live API integration (scope limited to provided Kaggle datasets)

---

See also: [Modules](modules.md), [Interfaces](interfaces.md)
