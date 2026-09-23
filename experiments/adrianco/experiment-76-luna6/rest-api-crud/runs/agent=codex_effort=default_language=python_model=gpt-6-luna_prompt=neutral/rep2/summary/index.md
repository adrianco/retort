# Summary: agent=codex language=python model=gpt-6-luna prompt=neutral · rep 2

- **Shape:** Stdlib-only WSGI REST API (`wsgiref`) with SQLite persistence — no third-party framework.
- **Structure:** 1 source module (`app.py`, 128 LOC), 1 test file (3 tests).
- **Interfaces:** 7 HTTP routes (health + full books CRUD with `?author=` filter), 1 exported factory `create_app()`.
- **Notable:** Minimal, idiomatic single-file design; per-request connection, `Location`/`Allow` headers, 405/500 handling, and strict type validation on `year`/`isbn` beyond the required `title`/`author`.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
