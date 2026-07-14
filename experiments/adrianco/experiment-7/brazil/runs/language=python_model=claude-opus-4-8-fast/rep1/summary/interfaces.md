# Interfaces

## MCP tools (server.py)

| Tool | Args | Returns | Handler |
|------|------|---------|---------|
| `find_matches` | team, opponent, competition, season, start_date, end_date, limit | formatted match list | `server.py:47` → `KnowledgeGraph.find_matches` |
| `last_meeting` | team1, team2 | most-recent match | `server.py:77` → `KnowledgeGraph.last_meeting` |
| `team_record` | team, season, competition, venue | W/D/L + goals | `server.py:88` → `KnowledgeGraph.team_record` |
| `head_to_head` | team1, team2, competition | H2H summary | `server.py:108` → `KnowledgeGraph.head_to_head` |
| `search_players` | name, nationality, club, position, min_overall, limit | player list | `server.py:117` → `KnowledgeGraph.search_players` |
| `standings` | competition, season | computed table | `server.py:148` → `KnowledgeGraph.standings` |
| `champion` | competition, season | table winner | `server.py:155` |
| `relegated` | competition, season, count | bottom-N teams | `server.py:165` |
| `competition_statistics` | competition, season | avg goals + win rates | `server.py:180` → `KnowledgeGraph.average_goals` |
| `biggest_wins` | competition, season, limit | largest-margin matches | `server.py:190` |
| `best_record` | competition, season, venue, limit | teams ranked by win-rate | `server.py:200` |
| `list_competitions` | — | competition names | `server.py:218` |
| `list_seasons` | competition | season years | `server.py:225` |

Transport: stdio (`FastMCP("brazilian-soccer").run()`).

## Library API

`KnowledgeGraph` exposes the same query methods directly (transport-agnostic, plain dict/list returns), enabling unit tests without a running server. `get_knowledge_graph()` returns a cached singleton.

## Data schema (in-memory DataFrames)

`matches`: competition, season, date, round, home_team, away_team, home_norm, away_norm, home_goal, away_goal, source, extra.

`players`: curated FIFA subset (ID, Name, Age, Nationality, Overall, Potential, Club, Position, …) plus `name_norm`, `club_norm`, `club_clean`, `nat_norm`.

## HTTP routes / CLI commands

(none) — this is an MCP-tool server, launched via `run_server.py` or `python -m brazilian_soccer_mcp.server`.
