# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| soccer.py | In-memory knowledge graph: loads 6 CSVs, normalizes team names, answers match/team/player/stat queries | `Graph`, `club()`, `competition()`, `fold()`, `FILES`, `LEAGUE`, `CUP`, `LIB` |
| server.py | MCP server over newline-delimited JSON-RPC on stdio; tool catalog + dispatch | `main()`, `dispatch()`, `catalog()`, `TOOLS` |
| test_soccer.py | BDD-style executable scenarios over the datasets and the stdio transport | 9 test methods (`SoccerScenarios`) |

No dependency manifest — standard library only (`csv`, `json`, `re`, `unicodedata`, `collections`, `datetime`, `functools`, `pathlib`, `subprocess`, `unittest`).
