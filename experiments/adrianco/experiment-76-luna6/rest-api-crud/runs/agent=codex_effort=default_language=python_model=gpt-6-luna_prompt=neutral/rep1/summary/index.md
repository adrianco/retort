# Summary: agent=codex_effort=default_language=python_model=gpt-6-luna_prompt=neutral · rep 1

- **Shape:** Pure-stdlib Python WSGI REST API (`wsgiref`) with SQLite persistence — no third-party dependencies.
- **Structure:** 2 modules (`app.py`, `test_app.py`), 1 test file.
- **Interfaces:** 6 HTTP routes (health + full CRUD), 1 exported factory `create_app()`.
- **Notable:** Single-file WSGI app dispatching by `PATH_INFO`/method rather than a framework router; a per-request SQLite connection opened via a context manager; `db_path` injected for test isolation.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
