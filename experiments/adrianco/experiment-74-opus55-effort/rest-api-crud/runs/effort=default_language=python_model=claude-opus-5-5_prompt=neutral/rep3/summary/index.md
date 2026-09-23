# Summary: effort=default_language=python_model=claude-opus-5-5_prompt=neutral · rep 3

- **Shape:** Python stdlib-only REST API (`http.server` + `sqlite3`), zero runtime dependencies.
- **Structure:** 1 source module (`app.py`), 1 test file (`test_app.py`, 11 test functions / 15 effective cases).
- **Interfaces:** 6 HTTP routes (health + full CRUD with `?author=` filter), 3 exported library symbols.
- **Notable:** No web framework at all — hand-rolled routing on `BaseHTTPRequestHandler`; thread-safe SQLite via a shared connection + lock; ISBN-10/13 shape validation and unknown-field rejection go beyond the spec.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
