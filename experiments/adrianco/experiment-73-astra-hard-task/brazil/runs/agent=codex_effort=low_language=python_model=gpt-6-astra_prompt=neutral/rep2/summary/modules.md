# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| soccer.py | Dataset ingestion + query engine: loads 6 Kaggle CSVs into a deduplicated in-memory match/player graph and answers all query categories | `SoccerGraph`, `team_key()`, `competition_key()`, `date_key()`, `fold()`, `number()` |
| server.py | MCP stdio JSON-RPC 2.0 server: tool schema definitions, validation, and request dispatch over the `SoccerGraph` | `Server`, `tool_list()`, `validate()`, `main()`, `DEFINITIONS` |
| test_soccer.py | unittest suite exercising ingestion, normalization, filtering, standings, h2h, players, protocol, and stdio integration | `DatasetTests` (9 test methods), `EXAMPLES` (24 sample questions) |
| README.md | Usage and design notes | (docs) |

Stdlib-only implementation: no `requirements.txt`/`pyproject.toml`; `csv`, `json`, `unicodedata`, `datetime`, `argparse`, `subprocess` only.
