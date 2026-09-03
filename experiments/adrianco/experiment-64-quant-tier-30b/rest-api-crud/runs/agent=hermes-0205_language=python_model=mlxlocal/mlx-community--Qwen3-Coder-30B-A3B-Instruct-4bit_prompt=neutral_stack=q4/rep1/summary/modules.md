# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | Flask app + route handlers (all stubbed, no DB) | `app`, `health_check`, `create_book`, `list_books`, `get_book`, `update_book`, `delete_book` |
| test_app.py | unittest API tests (2 functions, both failing) | `BookAPITestCase.test_health_check`, `test_create_book` |
| requirements.txt | Dependency pin (`flask`) | — |
| README.md | Setup/run/usage docs | — |

Note: `test_app.py` contains a hard-coded `sys.path.insert` to a now-deleted
`~/.retort/work/...` path — harmless because `app.py` is co-located, but dead.
