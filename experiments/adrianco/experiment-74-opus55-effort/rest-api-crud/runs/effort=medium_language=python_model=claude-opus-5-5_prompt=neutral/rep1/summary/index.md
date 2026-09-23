# Summary: effort=medium_language=python_model=claude-opus-5-5_prompt=neutral · rep 1

- **Shape:** Zero-dependency Python stdlib REST API (`http.server` + `sqlite3`) with a thread-safe SQLite store.
- **Structure:** 1 source module (`app.py`, 243 LOC), 1 test file (11 test functions, one parametrized ×4).
- **Interfaces:** 6 HTTP routes (health + full books CRUD with `?author=` filter), 1 SQLite table, 3 exported symbols.
- **Notable:** Chose stdlib over any web framework — self-contained and dependency-free; validation covers ISBN-10/13 and integer year bounds; PUT is a full replace; persistence verified across restarts by a test.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
