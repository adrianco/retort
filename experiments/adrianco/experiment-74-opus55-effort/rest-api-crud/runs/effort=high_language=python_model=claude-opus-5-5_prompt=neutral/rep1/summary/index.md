# Summary: effort=high_language=python_model=claude-opus-5-5_prompt=neutral · rep 1

- **Shape:** Standard-library Python REST API — `wsgiref` WSGI server + `sqlite3`, no third-party framework.
- **Structure:** 5 source modules, 2 test files (+ conftest).
- **Interfaces:** 6 HTTP routes (5 CRUD on /books + /health), 1 SQLite table, `create_app()` library entry, `python -m books_api` CLI.
- **Notable:** Zero-dependency runtime (pytest only for tests); thread-safe repository via a shared locked connection; unusually complete edge-case handling (ISBN normalisation/uniqueness→409, 405+Allow, oversize-body guard, trailing-slash normalisation).

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
