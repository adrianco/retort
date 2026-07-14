# Summary: agent=hermes-local language=python prompt=none stack=s1 · rep 3

- **Shape:** Flask REST API with raw SQLite (sqlite3), per-request connection on Flask `g`.
- **Structure:** 1 source module (`app.py`), 1 test file (`test_app.py`, 16 tests).
- **Interfaces:** 6 HTTP routes (full CRUD + `?author=` filter + `/health`); one `books` SQLite table.
- **Notable:** Complete, idiomatic Flask; input validation with blank-string checks and year type coercion; WAL journal mode; author filter is a substring `LIKE` match rather than exact match.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
