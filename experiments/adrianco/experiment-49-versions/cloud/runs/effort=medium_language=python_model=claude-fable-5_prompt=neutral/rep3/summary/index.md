# Summary: effort=medium_language=python_model=claude-fable-5_prompt=neutral · rep 3

- **Shape:** Flask REST API with raw `sqlite3` persistence (application-factory pattern).
- **Structure:** 1 source module (`app.py`), 1 test file (`test_app.py`, 8 tests).
- **Interfaces:** 6 HTTP routes (5 CRUD + `/health`), 1 exported factory `create_app()`.
- **Notable:** Clean separation via `create_app(db_path=...)` enabling isolated per-test DBs; defensive JSON parsing; partial-update validation; JSON error handlers for 404/405. No ORM — direct parameterized SQL.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
