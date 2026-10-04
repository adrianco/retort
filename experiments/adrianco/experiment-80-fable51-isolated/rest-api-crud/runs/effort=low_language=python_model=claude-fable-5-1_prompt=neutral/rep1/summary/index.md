# Summary: rest-api-crud · effort=low model=claude-fable-5-1 prompt=neutral · rep 1

- **Shape:** Python stdlib-only REST API — `wsgiref` WSGI app + `sqlite3`, zero dependencies.
- **Structure:** 1 source module (`app.py`, 196 LOC), 1 test file (`test_app.py`, 10 tests), README.
- **Interfaces:** 6 HTTP routes (health + full books CRUD with `?author=` filter); one `books` SQLite table.
- **Notable:** Deliberately dependency-free; clean `ApiError`→status mapping, per-request connections, 1 MiB body cap. Full CRUD + validation + method/404 handling covered by tests.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
