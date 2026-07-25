# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| server.py | Data loading, query functions, FastAPI REST endpoints | `app`, `load_data()`, `normalize_team_name()`, `get_team_matches()`, `get_head_to_head()`, `calculate_team_stats()`, `calculate_standings()`, `calculate_top_scorers()`, `format_match()` |
| test_server.py | Pytest/BDD-style tests of the query functions | 32 test functions across 8 classes |
| README.md | API usage docs (REST endpoints) | — |

Note: `data/kaggle/*.csv` are the provided datasets (not generated).
