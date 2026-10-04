# Summary: rest-api-crud · effort=default language=python model=claude-opus-5-5 prompt=neutral · rep 2

- **Shape:** Standard-library-only Python REST API (wsgiref WSGI + sqlite3), no web framework.
- **Structure:** 3 modules (app.py, db.py, test_app.py), 1 test file.
- **Interfaces:** 6 HTTP routes (+ 405/413/404 handling), 1 `books` SQLite table, `BookStore` persistence API.
- **Notable:** Zero runtime dependencies; threaded server; parameterized SQL; thorough validation and error handling; 22 tests including a real over-HTTP end-to-end lifecycle test.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
