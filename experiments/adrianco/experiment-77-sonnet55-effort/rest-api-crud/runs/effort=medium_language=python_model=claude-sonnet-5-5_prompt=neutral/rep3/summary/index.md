# Summary: effort=medium_language=python_model=claude-sonnet-5-5_prompt=neutral · rep 3

- **Shape:** Python stdlib WSGI REST API (no framework) backed by `sqlite3`.
- **Structure:** 2 source modules (`app.py`, `test_app.py`), 1 test file, 1 README.
- **Interfaces:** 6 HTTP routes (full books CRUD + `/health`), 3 exported functions (`create_app`, `connect`, `validate`).
- **Notable:** Zero third-party runtime dependencies — the whole service is one 138-line stdlib WSGI file. Validation is centralized in `validate()`, and PUT validates the body *before* the existence check.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
