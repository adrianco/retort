# Brazilian Soccer MCP Server

A Python-based Model Context Protocol (MCP) server exposing a knowledge graph for Brazilian soccer data. Parses 6 Kaggle CSV datasets, builds a NetworkX graph, and provides natural language query capabilities through MCP tools.

## Data Sources

### Match Data (23,954 total matches)

| Dataset | File | Matches | License |
|---------|------|---------|---------|
| Brasileirao Serie A | `data/kaggle/Brasileirao_Matches.csv` | 4,180 | CC BY 4.0 |
| Copa do Brasil | `data/kaggle/Brazilian_Cup_Matches.csv` | 1,337 | CC BY 4.0 |
| Copa Libertadores | `data/kaggle/Libertadores_Matches.csv` | 1,255 | CC BY 4.0 |
| Extended Stats | `data/kaggle/BR-Football-Dataset.csv` | 10,296 | CC0 Public Domain |
| Historic (2003-2019) | `data/kaggle/novo_campeonato_brasileiro.csv` | 6,886 | CC BY 4.0 |

### Player Data

| Dataset | File | Players | License |
|---------|------|---------|---------|
| FIFA Database | `data/kaggle/fifa_data.csv` | 18,207 | Apache 2.0 |

Full attribution URLs:
- https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro
- https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches
- https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019
- https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data

## Architecture

### Modules

| File | Description |
|------|-------------|
| `data_loader.py` | Loads all 6 CSVs, normalizes team names (removes state suffixes like -SP, -RJ), parses multiple date formats (ISO and DD/MM/YYYY Brazilian format) |
| `models.py` | Pydantic models for all MCP request/response types |
| `knowledge_graph.py` | NetworkX graph with team, match, competition, season, and player nodes and relationship edges |
| `server.py` | MCP server with 12 tools exposed via stdio transport |

### Knowledge Graph

Nodes: teams, matches, competitions, seasons, players, player_clubs
Edges: PLAYED_IN, HOME, AWAY, HAS_SEASON, PLAYS_FOR

Graph queries: team connections, path finding, common opponents, graph statistics.

### MCP Tools

| Tool | Description |
|------|-------------|
| `search_matches` | Filter matches by team, date range, competition, season |
| `get_team_stats` | Wins, draws, losses, goals for a team |
| `get_head_to_head` | Comparison between two teams |
| `search_players` | FIFA player search by nationality, club, position, rating |
| `get_season_standings` | Calculated standings for a season |
| `get_average_goals` | Aggregate goals statistics |
| `get_top_scoring_matches` | Highest-scoring matches in dataset |
| `get_graph_stats` | Knowledge graph node/edge counts |
| `find_team_connections` | Teams connected via shared competitions |
| `find_path_between_teams` | Graph paths between two teams |
| `get_common_opponents` | Teams both sides have played |
| `get_health_check` | Server status and data load summary |

## Installation

```bash
pip install -r requirements.txt
```

### Dependencies

- `pandas >= 2.0.0` - CSV data loading and processing
- `pydantic >= 2.0.0` - Data validation models
- `networkx >= 3.0.0` - Knowledge graph storage and traversal
- `mcp >= 1.0.0` - MCP server framework
- `pytest >= 7.0.0` - Test framework

## Running

```bash
python server.py
```

The server starts in stdio mode, ready to accept MCP protocol messages from a client (e.g., Claude, Cursor).

## Testing

```bash
python -m pytest tests/ -v
```

### Test Coverage (64 tests)

| Category | Tests | Description |
|----------|-------|-------------|
| Team Name Normalization | 12 | State suffix removal, accent handling, country codes, edge cases |
| Date Parsing | 7 | ISO dates, Brazilian DD/MM/YYYY format, error handling |
| Dataset Loading | 10 | All 6 CSV files load correctly with proper columns |
| Data Quality | 5 | Goals are integers, no state suffixes in normalized names |
| Match Queries | 5 | Filter by team, competition, season, date range |
| Team Statistics | 3 | Win rates, score balance, computation accuracy |
| Head-to-Head | 3 | Match counts, win/draw balance, empty teams |
| Player Queries | 6 | Filtering, sorting, rating thresholds, result limits |
| Graph Building | 7 | All node types created with correct counts |
| Graph Queries | 5 | Team connections, self-loop prevention, paths, common opponents |

## Team Name Normalization

The system normalizes team names across all 5 match datasets to enable cross-dataset queries:

1. Remove parenthetical annotations (e.g., "(antigo Esporte Clube Barreira)")
2. Remove country codes (e.g., "(URU)")
3. Remove trailing state suffixes (e.g., "-SP", "-RJ", "-MG", "-PR")
4. Remove accents/diacritics (e.g., "Gremio" -> "gremio")
5. Replace spaces with hyphens and lowercase

Examples:
- `Palmeiras-SP` -> `palmeiras`
- `Sao Paulo` -> `sao-paulo`
- `Gremio` (with accent) -> `gremio`
- `Nacional (URU)` -> `nacional`

## Query Examples

### Find Flamengo matches in 2023
```python
search_matches(team="Flamengo", season=2023)
```

### Head-to-head: Palmeiras vs Santos
```python
get_head_to_head(team1="Palmeiras", team2="Santos")
```

### Top 10 Brazilian players by rating
```python
search_players(nationality="Brazil", min_overall=85, max_results=10)
```

### 2019 Brasileirao standings
```python
get_season_standings(season=2019, competition="Brasileirao")
```

### Teams connected to Flamengo
```python
find_team_connections(team="Flamengo")
```
