# Summary: effort=default_language=python_model=claude-opus-5_prompt=neutral · rep 3

- **Shape:** Flask REST API with stdlib `sqlite3` (no ORM), split into app / db / validation modules.
- **Structure:** 3 source modules + 2 test/fixture files (`test_api.py`, `conftest.py`).
- **Interfaces:** 6 HTTP routes (5 CRUD on /books + /health); `?author=` filter; JSON error handlers for 400/404/405/409/500.
- **Notable:** Unusually complete for the spec — application factory, UNIQUE-ISBN → 409, unknown-field rejection, case-insensitive author filter, and 33 integration test cases with zero skips.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
