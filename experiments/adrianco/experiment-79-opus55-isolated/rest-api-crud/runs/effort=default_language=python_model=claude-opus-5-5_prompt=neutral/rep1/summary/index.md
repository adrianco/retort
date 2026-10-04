# Summary: rest-api-crud (effort=default, python, claude-opus-5-5, prompt=neutral) · rep 1

- **Shape:** Python stdlib-only REST API — `http.server` (ThreadingHTTPServer) + `sqlite3`, no third-party runtime deps.
- **Structure:** 1 source module (`app.py`), 1 test module (`test_app.py`), README + dev-deps + .gitignore.
- **Interfaces:** 6 HTTP routes (health + full CRUD with `?author=` filter); library API of `validate_book`, `BookStore`, `create_server`.
- **Notable:** Zero-dependency approach — one shared lock-guarded connection makes `:memory:` work under the threaded server; parameterized SQL; per-field validation errors; 1 MB body cap and 413; 405 with `Allow` header. 39 tests pass, 0 skipped.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
