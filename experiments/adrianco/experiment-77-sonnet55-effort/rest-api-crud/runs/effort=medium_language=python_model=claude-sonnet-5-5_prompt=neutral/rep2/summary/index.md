# Summary: effort=medium_language=python_model=claude-sonnet-5-5_prompt=neutral · rep 2

- **Shape:** Python stdlib-only REST API — raw WSGI (`wsgiref`) + `sqlite3`, zero dependencies.
- **Structure:** 1 source module (`app.py`), 1 test module (`test_app.py`, 7 tests).
- **Interfaces:** 6 HTTP routes (health + full books CRUD with `?author=` filter); 1 exported factory `create_app()`.
- **Notable:** Unusually compact and dependency-free — a single 127-line `app.py` handles routing via regex + a dispatch function, with a clean `HTTPError` → JSON error path. No framework (Flask/FastAPI) used.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
